"""Shared IPC base for subprocess-based UI adaptors (TUI and GUI).

Subclasses supply _CHILD_CMD and UI-specific facet/settings annotations.
The IPC protocol and pipe management are identical for all backends.
"""
import atexit
import copy
import os
import pickle
import struct
import subprocess
import sys
import warnings
from typing import Any

from .auxiliary import flatten
from .form_dict import TagDict
from .tui_command import TuiCommand
from ..exceptions import Cancelled
from .._mininterface.adaptor import BackendAdaptor


class _StrippedCallable:
    """Picklable placeholder for a lambda/closure that cannot be serialised."""
    def __call__(self, *_):
        pass


class SubprocessAdaptorBase(BackendAdaptor):
    """Generic IPC adaptor base.  Subclasses must define _CHILD_CMD."""

    _CHILD_CMD: str  # python -c template with {read_fd} / {write_fd} placeholders

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._process: subprocess.Popen | None = None
        self._read_fd: int | None = None
        self._write_fd: int | None = None
        self._output_history: str = ""
        """ Full session stdout. Replayed to a freshly spawned child so its output
            area is restored after the window was closed and reopened. """
        atexit.register(self._destroy)

    def _record_output(self, text: str) -> None:
        """Accumulate output so it can be replayed to a respawned child."""
        if not text:
            return
        self._output_history += text
        cap = 200_000
        if len(self._output_history) > cap:
            self._output_history = self._output_history[-cap:]

    # ------------------------------------------------------------------
    # Process management
    # ------------------------------------------------------------------

    def _ensure_process(self):
        """Spawn the child subprocess if it is not running yet."""
        spawned = False
        if self._process is None or self._process.poll() is not None:
            cmd_r, cmd_w = os.pipe()
            res_r, res_w = os.pipe()

            self._process = subprocess.Popen(
                [sys.executable, "-c",
                 self._CHILD_CMD.format(read_fd=cmd_r, write_fd=res_w)],
                pass_fds=(cmd_r, res_w),
            )

            os.close(cmd_r)
            os.close(res_w)
            self._write_fd = cmd_w
            self._read_fd = res_r
            spawned = True

        # (Re)wire stdout streaming. Done outside the spawn guard because an
        # eager _ensure_process (at interface construction) can run before
        # Redirectable has created interface._redirected — then output_callback
        # would never be set.
        self._wire_output()

        # A freshly spawned child has an empty output area. Replay the whole
        # session output so text printed before a window close+reopen survives.
        if spawned and self._output_history:
            try:
                self._send(TuiCommand.OUTPUT, self._output_history)
            except OSError:
                pass

    def _wire_output(self):
        try:
            redirected = self.interface._redirected
        except AttributeError:
            return
        if redirected.output_callback is self._send_output:
            return
        # Don't drain pending_buffer here — let _get_redirected() flush it as
        # redirected_text in the next dialog message (correct path, no extra \n).
        redirected.output_callback = self._send_output

    def _send_output(self, text: str) -> None:
        # Record before sending: the text then survives even if the pipe is racing
        # a dying child, and will be replayed when a new child spawns.
        self._record_output(text + "\n")
        if self._write_fd is not None:
            try:
                self._send(TuiCommand.OUTPUT, text)
            except OSError:
                # Child is gone (broken pipe). The text is preserved in
                # _output_history; stop streaming to the dead pipe so further
                # prints just go to pending_buffer (handled by _get_redirected).
                try:
                    self.interface._redirected.output_callback = None
                except AttributeError:
                    pass

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def _read_exactly(self, n: int) -> bytes | None:
        assert self._read_fd is not None
        data = b""
        while len(data) < n:
            try:
                chunk = os.read(self._read_fd, n - len(data))
            except (OSError, KeyboardInterrupt):
                return None
            if not chunk:
                return None
            data += chunk
        return data

    def _send(self, *data) -> None:
        assert self._write_fd is not None
        serialized = pickle.dumps(data)
        frame = struct.pack("!I", len(serialized)) + serialized
        while frame:
            n = os.write(self._write_fd, frame)
            frame = frame[n:]

    def _receive(self):
        header = self._read_exactly(4)
        if not header:
            return None, None
        (msg_length,) = struct.unpack("!I", header)
        payload = self._read_exactly(msg_length)
        if not payload:
            return None, None
        command, *args = pickle.loads(payload)
        return command, args

    # ------------------------------------------------------------------
    # Form serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_form(form: TagDict) -> TagDict:
        """Return a copy of form safe to pickle.

        on_change callbacks are replaced with _OnChangeProxy so the child can
        trigger them via the callback channel.  Other non-serialisable callables
        (validator, button val) are replaced with stubs.
        """
        from .subprocess_child_base import _OnChangeProxy

        form_copy = copy.deepcopy(form)
        for i, tag in enumerate(flatten(form_copy)):  # type: ignore[arg-type]
            if getattr(tag, "on_change", None) is not None:
                tag.on_change = _OnChangeProxy(i)

            val = getattr(tag, "validator", None)
            if val is not None:
                try:
                    pickle.dumps(val)
                except Exception:
                    tag.validator = None
                    warnings.warn(
                        f"Tag '{tag.label}': validator callback cannot be serialised "
                        "and will not fire in the subprocess.",
                        stacklevel=4,
                    )

            if callable(getattr(tag, "val", None)):
                try:
                    pickle.dumps(tag.val)
                except Exception:
                    tag.val = _StrippedCallable()
                    warnings.warn(
                        f"Tag '{tag.label}': callable val cannot be serialised; "
                        "button click will be a no-op in the subprocess.",
                        stacklevel=4,
                    )
        return form_copy

    # ------------------------------------------------------------------
    # Redirected output
    # ------------------------------------------------------------------

    def _get_redirected(self) -> str:
        """Drain the parent stdout buffer. Override to change streaming behaviour."""
        return ""

    # ------------------------------------------------------------------
    # Callback handling
    # ------------------------------------------------------------------

    def _handle_callback(self, callback_type: str, tag_pos: int, *extra) -> str:
        """Process a CALLBACK message from the child. Returns 'continue', 'done', or 'retry'."""
        from ..exceptions import ValidationFail

        tags = list(flatten(self.facet._form))  # type: ignore[arg-type]
        orig_vals = [t.val for t in tags]

        if callback_type == "on_change" and 0 <= tag_pos < len(tags):
            tag = tags[tag_pos]
            tag.update(extra[0] if extra else None)
            if tag.on_change:
                tag.on_change(tag)
            updates = [(i, t.val) for i, t in enumerate(tags) if t.val != orig_vals[i]]
            self._send(TuiCommand.FORM_UPDATE, updates, self.facet._title)
            return "continue"

        if callback_type == "button" and 0 <= tag_pos < len(tags):
            try:
                tags[tag_pos]._run_callable()
            except ValidationFail as e:
                if msg := str(e):
                    self.interface.alert(msg)
                return "retry"
            return "done"

        return "continue"

    # ------------------------------------------------------------------
    # High-level dialog methods
    # ------------------------------------------------------------------

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        self._ensure_process()
        BackendAdaptor.run_dialog(self, form, title, submit)

        while True:
            redirected = self._get_redirected()
            self._record_output(redirected)
            raw_layout = list(self.facet._raw_layout)
            self.facet._raw_layout.clear()

            safe_form = self._safe_form(self.facet._form or {})
            effective_title = self.facet._title or title
            always_shown = getattr(self.interface, "_always_shown", False)
            program_title = getattr(self.interface, "title", None)
            self._send(TuiCommand.FORM, safe_form, effective_title, submit, redirected,
                       raw_layout, always_shown, program_title)

            while True:
                command, args = self._receive()

                if command == TuiCommand.RESULT:
                    ui_vals = args[0]  # type: ignore[index]
                    if self._try_submit(zip(flatten(self.facet._form or {}), ui_vals)):  # type: ignore[arg-type]
                        return form
                    break
                elif command == TuiCommand.CANCEL:
                    self._on_cancel()
                    raise Cancelled
                elif command == TuiCommand.CALLBACK:
                    result = self._handle_callback(*args)  # type: ignore[misc]
                    if result == "done":
                        return form
                    elif result == "retry":
                        break
                else:
                    self._on_cancel()
                    raise Cancelled

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1, *, timeout: int = 0):
        self._ensure_process()
        redirected = self._get_redirected()
        self._record_output(redirected)
        always_shown = getattr(self.interface, "_always_shown", False)
        program_title = getattr(self.interface, "title", None)
        self._send(TuiCommand.BUTTONS, text, buttons, focused, timeout, redirected,
                   always_shown, program_title)
        command, args = self._receive()
        if command != TuiCommand.RESULT:
            self._on_cancel()
            raise Cancelled
        return args[0]

    def _on_cancel(self):
        """Child is gone or cancelled. Clear output_callback so subsequent prints
        go to pending_buffer rather than a dead pipe, preserving them for the
        next dialog's redirected_text."""
        try:
            self.interface._redirected.output_callback = None
        except AttributeError:
            pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _destroy(self):
        """Terminate the child subprocess and close pipe FDs."""
        try:
            self.interface._redirected.output_callback = None
        except AttributeError:
            pass
        if self._process and self._process.poll() is None:
            try:
                self._send(TuiCommand.SHUTDOWN)
                self._process.wait(timeout=2)
            except Exception:
                self._process.kill()
        self._process = None
        for attr in ("_read_fd", "_write_fd"):
            fd = getattr(self, attr, None)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, attr, None)
