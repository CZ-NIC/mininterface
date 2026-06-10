"""Child process side of the persistent Textual subprocess.

Spawned via `python -c "...run_child_main(read_fd, write_fd)"`.
Reads commands from read_fd, displays Textual dialogs, writes results to write_fd.
stdin / stdout / stderr are inherited → Textual can reach the tty normally.

Callback channel
----------------
on_change callbacks: _OnChangeProxy replaces tag.on_change.  When fired
(synchronously in Textual's event loop), it does a blocking send+receive with
the parent — brief, but acceptable since the handlers are not `async def`.
If an OUTPUT message arrives while waiting for FORM_UPDATE, it is routed to
the RichLog and the read loop continues until FORM_UPDATE is found.

button callbacks: MyButton.on_button_pressed → facet.submit(_post_submit=callable)
sets adaptor.post_submit_action before action_confirm().  After _submitted is set we
detect this, send CALLBACK("button"), and wait for the parent's decision.

PersistentChildApp
------------------
One app handles all forms for the entire session (tty and web modes).
An IPC worker thread reads pipe commands and updates the Textual UI reactively
via call_from_thread / _submitted threading.Event — no app.exit between forms.
A RichLog widget streams live print() output sent via TuiCommand.OUTPUT.
"""
import asyncio
import threading
from typing import TYPE_CHECKING

from .tui_command import TuiCommand
from .._lib.subprocess_child_base import read_msg as _read_msg, send_msg as _send_msg, register_hooks

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor


# ---------------------------------------------------------------------------
# Callback support
# ---------------------------------------------------------------------------

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
# Persistent app (tty and web modes)
# ---------------------------------------------------------------------------

class PersistentChildApp:
    """Placeholder — real class built by _make_persistent_child_app_class()."""


def _make_persistent_child_app_class():
    """Return PersistentChildApp (deferred import to avoid loading Textual at module level)."""
    from textual.app import App
    from textual.containers import Container
    from textual.widgets import Footer, RichLog

    from .._lib.auxiliary import flatten
    from ..exceptions import Cancelled
    from .button_contents import ButtonContents
    from .form_contents import FormContents
    from .timeout import TextualTimeout
    from .widgets import TagWidget

    class _PersistentChildApp(App[None]):
        """Single persistent Textual app for the whole session (tty and web).

        Never calls self.exit() between forms — keeps the UI alive.
        An IPC worker thread reads pipe commands and signals the Textual
        main thread via threading.Event.
        A RichLog streams live print() output from the parent.
        """

        CSS_PATH = "../_textual_interface/style.tcss"
        BINDINGS = [
            ("escape", "exit_app", "Cancel")
        ]

        def __init__(self, adaptor, read_fd: int, write_fd: int):
            super().__init__()
            self.adaptor = adaptor
            self.read_fd = read_fd
            self.write_fd = write_fd
            self.submit: bool | str = True
            self.widgets = []
            self.focusable_ = []
            self._submitted = threading.Event()
            self._result: tuple = (TuiCommand.CANCEL,)

        def compose(self):
            # Form on top, output log below it, control bar docked at screen bottom.
            yield Container(id="form-container")
            yield RichLog(id="output-log", auto_scroll=True, markup=False, highlight=False)
            yield Footer()

        async def on_mount(self):
            self.run_worker(self._ipc_worker, thread=True, exclusive=True)

        # ------------------------------------------------------------------ output

        def _append_output(self, text: str) -> None:
            """Append text to the RichLog. Auto-scroll keeps the latest output visible.
            Safe to call from the main thread."""
            try:
                log = self.query_one("#output-log", RichLog)
                for line in text.splitlines() or [text]:
                    log.write(line)
            except Exception:
                pass

        # ------------------------------------------------------------------ IPC

        def _safe_exit(self):
            try:
                self.call_from_thread(self.exit)
            except RuntimeError:
                pass

        def _handle_form(self, write_fd, form, title, submit_flag, redirected_text, raw_layout, *_):
            self._setup_form(form, title, submit_flag, raw_layout)
            self._submitted.clear()
            self.call_from_thread(self._refresh)
            if redirected_text:
                # after_refresh: the RichLog must be laid out (sized) first,
                # otherwise a write during startup is stored but never painted.
                self.call_from_thread(self.call_after_refresh, self._append_output, redirected_text)
            self._submitted.wait()
            _send_msg(write_fd, self._result)
            if self._result[0] == TuiCommand.CANCEL:
                self._safe_exit()
                return
            self.call_from_thread(self._clear_form)

        def _handle_buttons(self, write_fd, text, buttons_list, focused, timeout, redirected_text, *_):
            self.adaptor._build_buttons(text, buttons_list, focused)
            self.submit = False
            self._submitted.clear()
            self.call_from_thread(self._refresh, timeout)
            if redirected_text:
                self.call_from_thread(self.call_after_refresh, self._append_output, redirected_text)
            self._submitted.wait()
            _send_msg(write_fd, self._result)
            if self._result[0] == TuiCommand.CANCEL:
                self._safe_exit()
                return
            self.call_from_thread(self._clear_form)

        def _ipc_worker(self):
            from .._lib.subprocess_child_base import _ipc_worker_loop
            handlers = {
                'OUTPUT': lambda text: self.call_from_thread(self._append_output, text),
                'FORM': self._handle_form,
                'BUTTONS': self._handle_buttons,
                'on_eof': self._safe_exit,
            }
            _ipc_worker_loop(self.read_fd, self.write_fd, handlers)

        def _setup_form(self, form, title, submit_flag, raw_layout):
            for t in flatten(form):
                t._facet = self.adaptor.facet
            self.adaptor.button_app = False
            self.adaptor.facet._title = title
            self.adaptor._setup_form_facet(form)
            self.adaptor.layout_elements.clear()
            if raw_layout:
                self.adaptor.facet._layout(raw_layout)
            self.submit = submit_flag

        def _clear_form(self):
            """Remove stale form/button UI between dialogs."""
            try:
                asyncio.ensure_future(self._async_clear_form())
            except RuntimeError:
                pass

        async def _async_clear_form(self):
            container = self.query_one("#form-container", Container)
            await container.remove_children()
            self.widgets.clear()
            self.focusable_.clear()

        def _refresh(self, timeout=None):
            try:
                asyncio.ensure_future(self._async_refresh(timeout))
            except RuntimeError:
                pass

        async def _async_refresh(self, timeout=None):
            self.adaptor.app = self
            container = self.query_one("#form-container", Container)
            await container.remove_children()
            self.widgets.clear()
            self.focusable_.clear()

            if self.adaptor.button_app:
                c = ButtonContents(self.adaptor, self.adaptor.button_app, show_footer=False)
                await container.mount(c)
                if timeout and c.to_focus:
                    TextualTimeout(timeout=timeout, adaptor=self.adaptor, button=c.to_focus)
            else:
                c = FormContents(self.adaptor, self.widgets, self.focusable_, show_footer=False)
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
                # Send the current field values too: a button is a submit, so the
                # parent validates the whole form before running the callable.
                ui_vals = [w.get_ui_value() for w in self.widgets if isinstance(w, TagWidget)]
                self._result = (TuiCommand.CALLBACK, "button", tag_pos, ui_vals)
            else:
                ui_vals = [w.get_ui_value() for w in self.widgets if isinstance(w, TagWidget)]
                self._result = (TuiCommand.RESULT, ui_vals)
            self._submitted.set()

        def action_exit_app(self):
            self._result = (TuiCommand.CANCEL,)
            self._submitted.set()

    return _PersistentChildApp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_child_main(read_fd: int, write_fd: int) -> None:
    """Entry point called by the subprocess via `python -c`.

    Creates a minimal interface + TextualAdaptor, then runs the persistent app.
    No user code is re-executed.  Textual automatically uses the web driver when
    TEXTUAL_DRIVER is set (web mode), or the terminal driver otherwise (tty mode).
    """
    from mininterface._lib.redirectable import Redirectable
    from mininterface._mininterface import Mininterface
    from mininterface._textual_interface.adaptor import TextualAdaptor

    class _ChildInterface(Redirectable, Mininterface):
        _adaptor: TextualAdaptor  # type: ignore[assignment]

    interface = _ChildInterface()
    adaptor = TextualAdaptor(interface, None)
    app = _make_persistent_child_app_class()(adaptor, read_fd, write_fd)

    register_hooks(
        read_fd, write_fd,
        apply_form_update=lambda updates, title: _apply_form_update(updates, title, adaptor),
        append_output=lambda text: app._append_output(text),
    )
    app.run()
