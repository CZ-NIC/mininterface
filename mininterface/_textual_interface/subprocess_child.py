"""Child process side of the persistent Textual subprocess.

Spawned via `python -c "...run_child_main(read_fd, write_fd)"`.
Reads commands from read_fd, displays Textual dialogs, writes results to write_fd.
stdin / stdout / stderr are inherited → Textual can reach the tty normally.

Callback channel
----------------
on_change callbacks: _OnChangeProxy replaces tag.on_change.  When fired
(synchronously in Textual's event loop), it does a blocking send+receive with
the parent — brief, but acceptable since the handlers are not `async def`.

button callbacks: MyButton.on_button_pressed → facet.submit(_post_submit=callable)
sets adaptor.post_submit_action before app.exit().  After app.run() returns we
detect this, send CALLBACK("button"), and wait for the parent's decision.

WebChildApp (web mode)
----------------------
When TEXTUAL_DRIVER is set, one persistent WebChildApp handles all forms for the
session.  The WebSocket stays open across multiple .form() calls.  An IPC worker
thread reads commands and updates the Textual UI reactively (no app.exit between
forms).  _OnChangeProxy still works: it fires on the main thread, sends CALLBACK
and waits for FORM_UPDATE — safe because the worker is blocked on _submitted at
that point, not reading from read_fd.
"""
import asyncio
import os
import pickle
import struct
import threading
from typing import TYPE_CHECKING

from .tui_command import TuiCommand

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor

# Set once in run_child_loop; read by _OnChangeProxy instances
_CHILD_WRITE_FD: int | None = None
_CHILD_READ_FD: int | None = None


# ---------------------------------------------------------------------------
# Low-level I/O
# ---------------------------------------------------------------------------

def _read_exactly(fd: int, n: int) -> bytes | None:
    data = b""
    while len(data) < n:
        chunk = os.read(fd, n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def _read_msg(fd: int):
    header = _read_exactly(fd, 4)
    if not header:
        return None
    (msg_length,) = struct.unpack("!I", header)
    if msg_length == 0:
        return None
    payload = _read_exactly(fd, msg_length)
    return pickle.loads(payload) if payload else None


def _send_msg(fd: int, data) -> None:
    serialized = pickle.dumps(data)
    frame = struct.pack("!I", len(serialized)) + serialized
    while frame:
        n = os.write(fd, frame)
        frame = frame[n:]


# ---------------------------------------------------------------------------
# Callback support
# ---------------------------------------------------------------------------

class _OnChangeProxy:
    """Picklable proxy sent to child in place of tag.on_change.

    When fired (synchronously in Textual's event loop) it does a brief
    blocking exchange with the parent, which runs the real callback and
    returns updated tag values.
    """

    def __init__(self, tag_pos: int):
        self.tag_pos = tag_pos

    def __call__(self, tag):
        assert _CHILD_WRITE_FD is not None
        assert _CHILD_READ_FD is not None
        _send_msg(_CHILD_WRITE_FD, (TuiCommand.CALLBACK, "on_change", self.tag_pos, tag.val))
        response = _read_msg(_CHILD_READ_FD)
        if response:
            command, *args = response
            if command == TuiCommand.FORM_UPDATE:
                _apply_form_update(args[0], args[1] if len(args) > 1 else "", tag._facet.adaptor)


def _apply_form_update(updates: list, title: str, adaptor: "TextualAdaptor") -> None:
    """Apply (pos, new_val) pairs to the child's tag copies and refresh widgets."""
    from .._lib.auxiliary import flatten
    from .widgets import MyCheckbox, MyInput, TagWidget

    if title:
        adaptor.facet._title = title
        if adaptor.app is not None:
            adaptor.app.title = title

    tags = list(flatten(adaptor.facet._form))  # type: ignore[arg-type]
    tag_widgets = [w for w in adaptor.app.widgets if isinstance(w, TagWidget)] if adaptor.app else []

    for pos, new_val in updates:
        if not (0 <= pos < len(tags)):
            continue
        tags[pos].val = new_val
        tags[pos]._last_ui_val = new_val  # prevent re-triggering on the same value

        # Best-effort visual refresh
        if pos < len(tag_widgets):
            w = tag_widgets[pos]
            if isinstance(w, MyInput):
                w.value = str(new_val)
            elif isinstance(w, MyCheckbox):
                w.value = bool(new_val)


# ---------------------------------------------------------------------------
# Main child loop
# ---------------------------------------------------------------------------

def run_child_loop(adaptor: "TextualAdaptor", read_fd: int, write_fd: int) -> None:
    """Persistent loop: receive commands, run Textual dialogs, send results."""
    global _CHILD_WRITE_FD, _CHILD_READ_FD
    _CHILD_WRITE_FD = write_fd
    _CHILD_READ_FD = read_fd

    from .._lib.auxiliary import flatten
    from ..exceptions import Cancelled
    from .textual_app import TextualApp
    from .widgets import TagWidget

    while True:
        msg = _read_msg(read_fd)
        if msg is None:
            break

        command, *args = msg

        if command == TuiCommand.SHUTDOWN:
            break

        try:
            if command == TuiCommand.FORM:
                form, title, submit, redirected_text, raw_layout = args
                for t in flatten(form):  # type: ignore[arg-type]
                    t._facet = adaptor.facet
                adaptor.button_app = False
                adaptor.facet._fetch_from_adaptor(form)
                adaptor.facet._title = title
                if adaptor.settings.mnemonic is not False:
                    adaptor._determine_mnemonic(form, adaptor.settings.mnemonic is True)

                if redirected_text:
                    adaptor.interface._redirected.write(redirected_text)  # type: ignore[attr-defined]
                adaptor.layout_elements.clear()
                if raw_layout:
                    adaptor.facet._layout(raw_layout)

                adaptor.app = app = TextualApp(adaptor, submit)
                if title:
                    app.title = title

                confirmed = app.run()
                adaptor.layout_elements.clear()

                if not confirmed:
                    _send_msg(write_fd, (TuiCommand.CANCEL,))
                    continue

                # Button callback: post_submit_action is set before app.exit()
                if adaptor.post_submit_action is not None:
                    pending = adaptor.post_submit_action
                    adaptor.post_submit_action = None
                    tags = list(flatten(form))  # type: ignore[arg-type]
                    tag_pos = next(
                        (i for i, t in enumerate(tags) if t._run_callable == pending),
                        -1,
                    )
                    _send_msg(write_fd, (TuiCommand.CALLBACK, "button", tag_pos))
                    continue  # outer loop waits for next FORM / BUTTONS command

                ui_vals = [
                    field.get_ui_value()
                    for field in app.widgets
                    if isinstance(field, TagWidget)
                ]
                _send_msg(write_fd, (TuiCommand.RESULT, ui_vals))

            elif command == TuiCommand.BUTTONS:
                text, buttons_list, focused, timeout, redirected_text = args
                if redirected_text:
                    adaptor.interface._redirected.write(redirected_text)  # type: ignore[attr-defined]
                adaptor._build_buttons(text, buttons_list, focused)
                adaptor.app = app = TextualApp(adaptor, False, timeout=timeout)

                if not app.run():
                    _send_msg(write_fd, (TuiCommand.CANCEL,))
                    continue

                try:
                    val = adaptor._get_buttons_val()
                    _send_msg(write_fd, (TuiCommand.RESULT, val))
                except Cancelled:
                    _send_msg(write_fd, (TuiCommand.CANCEL,))

        except Exception:
            _send_msg(write_fd, (TuiCommand.CANCEL,))


# ---------------------------------------------------------------------------
# Persistent web app (used when TEXTUAL_DRIVER is set)
# ---------------------------------------------------------------------------

class WebChildApp:
    """Placeholder — real class injected below after textual imports are available."""


def _make_web_child_app_class():
    """Return the WebChildApp class (deferred to avoid importing Textual at module level)."""
    from textual.app import App
    from textual.containers import Container

    from .._lib.auxiliary import flatten
    from ..exceptions import Cancelled
    from .button_contents import ButtonContents
    from .form_contents import FormContents
    from .timeout import TextualTimeout
    from .widgets import TagWidget

    class _WebChildApp(App[None]):
        """Single persistent Textual app that serves all forms in one web session.

        Never calls self.exit() between forms — keeps the WebSocket open.
        An IPC worker thread reads pipe commands and signals the main thread
        via threading.Event.
        """

        CSS_PATH = "../_textual_interface/style.tcss"
        BINDINGS = [("escape", "exit_app", "Cancel")]

        def __init__(self, adaptor, read_fd: int, write_fd: int):
            super().__init__()
            self.adaptor = adaptor
            self.read_fd = read_fd
            self.write_fd = write_fd
            # submit is read by FormContents.on_key (self.app.submit)
            self.submit: bool | str = True
            # widgets / focusable_ mirror TextualApp naming used by _apply_form_update
            self.widgets = []
            self.focusable_ = []
            self._submitted = threading.Event()
            self._result: tuple = (TuiCommand.CANCEL,)

        def compose(self):
            yield Container()

        async def on_mount(self):
            self.run_worker(self._ipc_worker, thread=True, exclusive=True)

        # ------------------------------------------------------------------ IPC

        def _safe_exit(self):
            try:
                self.call_from_thread(self.exit)
            except RuntimeError:
                pass

        def _ipc_worker(self):
            global _CHILD_WRITE_FD, _CHILD_READ_FD
            _CHILD_WRITE_FD = self.write_fd
            _CHILD_READ_FD = self.read_fd

            while True:
                msg = _read_msg(self.read_fd)
                if msg is None:
                    self._safe_exit()
                    return

                command, *args = msg

                if command == TuiCommand.SHUTDOWN:
                    self._safe_exit()
                    return

                try:
                    if command == TuiCommand.FORM:
                        form, title, submit_flag, redirected_text, raw_layout = args
                        self._setup_form(form, title, submit_flag, redirected_text, raw_layout)
                        self._submitted.clear()
                        self.call_from_thread(self._refresh)
                        self._submitted.wait()
                        _send_msg(self.write_fd, self._result)
                        if self._result[0] == TuiCommand.CANCEL:
                            self._safe_exit()
                            return

                    elif command == TuiCommand.BUTTONS:
                        text, buttons_list, focused, timeout, redirected_text = args
                        if redirected_text:
                            self.adaptor.interface._redirected.write(redirected_text)
                        self.adaptor._build_buttons(text, buttons_list, focused)
                        self.submit = False
                        self._submitted.clear()
                        self.call_from_thread(self._refresh, timeout)
                        self._submitted.wait()
                        _send_msg(self.write_fd, self._result)
                        if self._result[0] == TuiCommand.CANCEL:
                            self._safe_exit()
                            return

                except Exception:
                    _send_msg(self.write_fd, (TuiCommand.CANCEL,))

        def _setup_form(self, form, title, submit_flag, redirected_text, raw_layout):
            for t in flatten(form):
                t._facet = self.adaptor.facet
            self.adaptor.button_app = False
            self.adaptor.facet._fetch_from_adaptor(form)
            self.adaptor.facet._title = title
            if self.adaptor.settings.mnemonic is not False:
                self.adaptor._determine_mnemonic(form, self.adaptor.settings.mnemonic is True)
            if redirected_text:
                self.adaptor.interface._redirected.write(redirected_text)
            self.adaptor.layout_elements.clear()
            if raw_layout:
                self.adaptor.facet._layout(raw_layout)
            self.submit = submit_flag

        def _refresh(self, timeout=None):
            """Called from worker via call_from_thread; schedules async UI update."""
            try:
                asyncio.ensure_future(self._async_refresh(timeout))
            except RuntimeError:
                pass

        async def _async_refresh(self, timeout=None):
            self.adaptor.app = self
            container = self.query_one(Container)
            await container.remove_children()
            self.widgets.clear()
            self.focusable_.clear()

            if self.adaptor.button_app:
                c = ButtonContents(self.adaptor, self.adaptor.button_app)
                await container.mount(c)
                if timeout and c.to_focus:
                    TextualTimeout(timeout=timeout, adaptor=self.adaptor, button=c.to_focus)
            else:
                c = FormContents(self.adaptor, self.widgets, self.focusable_)
                await container.mount(c)

            if self.adaptor.facet._title:
                self.title = self.adaptor.facet._title

        # ------------------------------------------------------------------ Actions

        def action_confirm(self):
            if self.adaptor.button_app:
                try:
                    val = self.adaptor._get_buttons_val()
                    self._result = (TuiCommand.RESULT, val)
                except Cancelled:
                    self._result = (TuiCommand.CANCEL,)
            elif self.adaptor.post_submit_action is not None:
                pending = self.adaptor.post_submit_action
                self.adaptor.post_submit_action = None
                tags = list(flatten(self.adaptor.facet._form))
                tag_pos = next(
                    (i for i, t in enumerate(tags) if t._run_callable == pending), -1
                )
                self._result = (TuiCommand.CALLBACK, "button", tag_pos)
            else:
                ui_vals = [w.get_ui_value() for w in self.widgets if isinstance(w, TagWidget)]
                self._result = (TuiCommand.RESULT, ui_vals)
            self._submitted.set()

        def action_exit_app(self):
            self._result = (TuiCommand.CANCEL,)
            self._submitted.set()

    return _WebChildApp


# ---------------------------------------------------------------------------
# Main child loop (tty mode)
# ---------------------------------------------------------------------------


def run_child_main(read_fd: int, write_fd: int) -> None:
    """Entry point called by the subprocess via `python -c`.

    Creates a minimal interface + TextualAdaptor, then enters the dialog loop.
    No user code is re-executed.
    """
    from mininterface._lib.redirectable import Redirectable
    from mininterface._mininterface import Mininterface
    from mininterface._textual_interface.adaptor import TextualAdaptor

    class _ChildInterface(Redirectable, Mininterface):
        _adaptor: TextualAdaptor  # type: ignore[assignment]

    interface = _ChildInterface()
    adaptor = TextualAdaptor(interface, None)

    if os.environ.get("TEXTUAL_DRIVER"):
        _make_web_child_app_class()(adaptor, read_fd, write_fd).run()
    else:
        run_child_loop(adaptor, read_fd, write_fd)
