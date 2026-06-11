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
import traceback
from typing import Callable, Optional

from .ipc_command import IpcCommand

# Set once by the backend child in run_child_main; read by _OnChangeProxy.
_CHILD_WRITE_FD: int | None = None
_CHILD_READ_FD: int | None = None

# Backend-specific hooks, registered by the child via register_hooks().
_apply_form_update: Optional[Callable[[list, str], None]] = None
""" (updates, title) -> None — push parent's new tag values into the live widgets. """
_append_output: Optional[Callable[[str], None]] = None
""" (text) -> None — show a chunk of redirected print() output. """
_shutdown: Optional[Callable[[], None]] = None
""" () -> None — tear down the app and restore the terminal. Called when a proxy
    round-trip is interrupted by a SHUTDOWN (the parent is exiting while the child's
    main thread is parked in a proxy read loop). """
_proxies_active: bool = True
""" While False, on_change/validation proxies are no-ops (return immediately without
    a parent round-trip). Set False once a form is being submitted: pressing Enter
    can also trigger on_blur → trigger_change → a validate/on_change round-trip on the
    main thread, which then races the RESULT the worker thread just sent. The parent,
    seeing RESULT, moves on and may send SHUTDOWN — leaving the main thread parked in
    the proxy read loop so app.exit() never runs and the terminal is left corrupted.
    Suppressing proxies during submit avoids the race; the parent re-validates the
    whole form on submit anyway. """


def set_proxies_active(active: bool) -> None:
    """Enable/disable on_change & validation proxy round-trips (see _proxies_active)."""
    global _proxies_active
    _proxies_active = active


def register_hooks(read_fd: int, write_fd: int,
                   apply_form_update: Callable[[list, str], None],
                   append_output: Callable[[str], None],
                   shutdown: Optional[Callable[[], None]] = None) -> None:
    """Wire the child's FDs and backend-specific callbacks into this module."""
    global _CHILD_WRITE_FD, _CHILD_READ_FD, _apply_form_update, _append_output, _shutdown
    _CHILD_READ_FD = read_fd
    _CHILD_WRITE_FD = write_fd
    _apply_form_update = apply_form_update
    _append_output = append_output
    _shutdown = shutdown


def _request_shutdown() -> None:
    """Ask the backend to exit (restoring the terminal). Safe to call from the main
    thread inside a proxy read loop. No-op if no shutdown hook was registered."""
    if _shutdown is not None:
        _shutdown()


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


def error_payload(exc: BaseException) -> tuple:
    """Build an ERROR message for an exception that crashed a dialog build.

    Ships the exception object itself when the parent can unpickle it (the child
    runs only mininterface/stdlib code, so this is the common case) plus the
    formatted child traceback; falls back to the traceback text alone for an
    unpicklable exception."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        pickle.dumps(exc)
    except Exception:
        exc = None
    return (IpcCommand.ERROR, exc, tb)


# ---------------------------------------------------------------------------
# Callback proxies (on_change and validation)
# ---------------------------------------------------------------------------

class _ValidationProxy:
    """Picklable proxy sent to the child in place of tag.validation.

    When the child calls tag.update() (e.g. on FocusOut/Tab), this proxy fires
    instead of the real validator.  It does a brief blocking round-trip with the
    parent, which runs the real validator and returns the result.  This way ALL
    validators (including __main__-defined ones) work live in the child UI.
    """

    def __init__(self, tag_pos: int):
        self.tag_pos = tag_pos

    def __call__(self, tag):
        if not _proxies_active:
            return True  # submit/shutdown in progress — parent re-validates on submit
        assert _CHILD_WRITE_FD is not None
        assert _CHILD_READ_FD is not None
        send_msg(_CHILD_WRITE_FD, (IpcCommand.CALLBACK, "validate", self.tag_pos, tag.val))
        while True:
            response = read_msg(_CHILD_READ_FD)
            if not response:
                return True  # pipe closed — don't block the UI
            if response[0] == IpcCommand.SHUTDOWN:
                # Parent is tearing down (the form was already submitted/cancelled on
                # another path). Re-dispatch to the app so it exits and restores the
                # terminal, then unblock the main thread instead of parking here.
                _request_shutdown()
                return True
            command, *args = response
            if command == IpcCommand.VALIDATE_RESULT:
                # None → ok; str → error message (shown inline by tag.update)
                return args[0]
            elif command == IpcCommand.OUTPUT:
                if _append_output is not None:
                    _append_output(args[0])


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
        if not _proxies_active:
            return  # submit/shutdown in progress — skip the round-trip
        assert _CHILD_WRITE_FD is not None
        assert _CHILD_READ_FD is not None
        send_msg(_CHILD_WRITE_FD, (IpcCommand.CALLBACK, "on_change", self.tag_pos, tag.val))
        while True:
            response = read_msg(_CHILD_READ_FD)
            if not response:
                return
            command, *args = response
            if command == IpcCommand.SHUTDOWN:
                # The parent is tearing down (e.g. the form was already submitted on
                # another path and the parent moved on). Re-dispatch SHUTDOWN to the
                # app so it exits and restores the terminal, then unblock. Without
                # this the main thread stays parked here and app.exit() never runs.
                _request_shutdown()
                return
            if command == IpcCommand.FORM_UPDATE:
                if _apply_form_update is not None:
                    _apply_form_update(args[0], args[1] if len(args) > 1 else "")
                return
            elif command == IpcCommand.OUTPUT:
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
        handlers: dict with keys 'OUTPUT', 'CLEAR_OUTPUT', 'SETTINGS', 'FORM',
            'BUTTONS', 'on_eof'.
            Each handler is called with the parsed args from the message.
    """
    while True:
        msg = read_msg(read_fd)
        if msg is None:
            handlers['on_eof']()
            return

        command, *args = msg

        if command == IpcCommand.SHUTDOWN:
            handlers['on_eof']()
            return

        if command == IpcCommand.OUTPUT:
            handlers['OUTPUT'](args[0])
            continue

        if command == IpcCommand.CLEAR_OUTPUT:
            handlers['CLEAR_OUTPUT']()
            continue

        if command == IpcCommand.SETTINGS:
            handlers['SETTINGS'](args[0])
            continue

        try:
            if command == IpcCommand.FORM:
                handlers['FORM'](write_fd, *args)
            elif command == IpcCommand.BUTTONS:
                handlers['BUTTONS'](write_fd, *args)
        except Exception as exc:
            # Ship the real error to the parent (which re-raises it) instead of
            # degrading it to a CANCEL the parent would mistake for Esc.
            send_msg(write_fd, error_payload(exc))
