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
"""
import os
import pickle
import struct
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

    run_child_loop(adaptor, read_fd, write_fd)
