"""Shared child-process helpers for subprocess-based UI backends (TUI and GUI).

The child process of every subprocess backend needs the same things:

* the low-level framed pipe protocol (length-prefixed pickle),
* the file descriptors it talks to the parent through,
* an ``_OnChangeProxy`` that is pickled into the form in place of a real
  ``on_change`` callback and, when fired, does a brief blocking round-trip with
  the parent (which owns the real callback).

Only the *effect* of an update differs per backend (how a value is pushed back
into a Textual widget vs. a Tk variable, where print() output is shown).  Those
two operations are injected as hooks via :func:`register_hooks`.
"""
import os
import pickle
import struct
from typing import Callable, Optional

from .tui_command import TuiCommand

# Set once by the backend child in run_child_main; read by _OnChangeProxy.
_CHILD_WRITE_FD: int | None = None
_CHILD_READ_FD: int | None = None

# Backend-specific hooks, registered by the child via register_hooks().
_apply_form_update: Optional[Callable[[list, str], None]] = None
""" (updates, title) -> None — push parent's new tag values into the live widgets. """
_append_output: Optional[Callable[[str], None]] = None
""" (text) -> None — show a chunk of redirected print() output. """


def register_hooks(read_fd: int, write_fd: int,
                   apply_form_update: Callable[[list, str], None],
                   append_output: Callable[[str], None]) -> None:
    """Wire the child's FDs and backend-specific callbacks into this module."""
    global _CHILD_WRITE_FD, _CHILD_READ_FD, _apply_form_update, _append_output
    _CHILD_READ_FD = read_fd
    _CHILD_WRITE_FD = write_fd
    _apply_form_update = apply_form_update
    _append_output = append_output


# ---------------------------------------------------------------------------
# Low-level framed I/O (length-prefixed pickle)
# ---------------------------------------------------------------------------

def _read_exactly(fd: int, n: int) -> bytes | None:
    data = b""
    while len(data) < n:
        chunk = os.read(fd, n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def read_msg(fd: int):
    header = _read_exactly(fd, 4)
    if not header:
        return None
    (msg_length,) = struct.unpack("!I", header)
    if msg_length == 0:
        return None
    payload = _read_exactly(fd, msg_length)
    return pickle.loads(payload) if payload else None


def send_msg(fd: int, data) -> None:
    serialized = pickle.dumps(data)
    frame = struct.pack("!I", len(serialized)) + serialized
    while frame:
        n = os.write(fd, frame)
        frame = frame[n:]


# ---------------------------------------------------------------------------
# on_change callback proxy
# ---------------------------------------------------------------------------

class _OnChangeProxy:
    """Picklable proxy sent to the child in place of tag.on_change.

    When fired (synchronously, in the UI event loop / event callback) it does a
    brief blocking exchange with the parent, which runs the real callback and
    returns updated tag values.  OUTPUT messages that arrive meanwhile are
    routed to the backend's output area and the loop continues.
    """

    def __init__(self, tag_pos: int):
        self.tag_pos = tag_pos

    def __call__(self, tag):
        assert _CHILD_WRITE_FD is not None
        assert _CHILD_READ_FD is not None
        send_msg(_CHILD_WRITE_FD, (TuiCommand.CALLBACK, "on_change", self.tag_pos, tag.val))
        while True:
            response = read_msg(_CHILD_READ_FD)
            if not response:
                return
            command, *args = response
            if command == TuiCommand.FORM_UPDATE:
                if _apply_form_update is not None:
                    _apply_form_update(args[0], args[1] if len(args) > 1 else "")
                return
            elif command == TuiCommand.OUTPUT:
                # OUTPUT can arrive here if print() was called inside the on_change callback.
                if _append_output is not None:
                    _append_output(args[0])


def _ipc_worker_loop(read_fd: int, write_fd: int, handlers: dict) -> None:
    """Generic IPC worker loop for child processes.

    Reads commands from parent, dispatches to handlers, sends results back.
    Handlers are responsible for scheduling work on the UI thread and waiting
    for user interaction (_submitted event).

    Args:
        read_fd: pipe fd to read commands from
        write_fd: pipe fd to send results to
        handlers: dict with keys 'OUTPUT', 'FORM', 'BUTTONS', 'on_eof'
            Each handler is called with the parsed args from the message.
    """
    while True:
        msg = read_msg(read_fd)
        if msg is None:
            handlers['on_eof']()
            return

        command, *args = msg

        if command == TuiCommand.SHUTDOWN:
            handlers['on_eof']()
            return

        if command == TuiCommand.OUTPUT:
            handlers['OUTPUT'](args[0])
            continue

        try:
            if command == TuiCommand.FORM:
                handlers['FORM'](write_fd, *args)
            elif command == TuiCommand.BUTTONS:
                handlers['BUTTONS'](write_fd, *args)
        except Exception:
            send_msg(write_fd, (TuiCommand.CANCEL,))
