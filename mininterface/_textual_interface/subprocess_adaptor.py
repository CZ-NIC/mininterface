"""Parent-side adaptor for the persistent Textual subprocess.

Uses os.pipe() + pass_fds so the child inherits stdin/stdout/stderr (tty access)
and communicates via dedicated file descriptors instead.
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

from .._lib.auxiliary import flatten
from .._lib.form_dict import TagDict
from ..exceptions import Cancelled
from ..settings import TextualSettings
from .adaptor import TextualAdaptor
from .facet import TextualFacet
from .tui_command import TuiCommand

# Launched via python -c; FDs are embedded directly in the command string.
_CHILD_CMD = (
    "from mininterface._textual_interface.subprocess_child import run_child_main;"
    "run_child_main({read_fd},{write_fd})"
)


class _StrippedCallable:
    """Picklable placeholder for a lambda/closure that cannot be serialised."""
    def __call__(self, *_):
        pass


class _SubprocessFacet(TextualFacet):
    """Facet variant for the parent side of the subprocess.

    Stores raw LayoutElement objects instead of converting them to Textual
    widgets (which cannot be pickled and sent to the child).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raw_layout: list = []

    def _layout(self, elements):
        self._raw_layout.extend(elements)


class TextualSubprocessAdaptor(TextualAdaptor):
    """Parent-side adaptor. Communicates with a persistent Textual subprocess."""

    facet: _SubprocessFacet
    settings: TextualSettings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._process: subprocess.Popen | None = None
        self._read_fd: int | None = None   # parent reads child responses
        self._write_fd: int | None = None  # parent writes commands to child
        atexit.register(self._destroy)

    def _ensure_process(self):
        """Spawn the child subprocess if it is not running yet."""
        if self._process is not None and self._process.poll() is None:
            return

        cmd_r, cmd_w = os.pipe()   # parent→child (commands)
        res_r, res_w = os.pipe()   # child→parent (results)

        self._process = subprocess.Popen(
            [sys.executable, "-c", _CHILD_CMD.format(read_fd=cmd_r, write_fd=res_w)],
            pass_fds=(cmd_r, res_w),
            # stdin / stdout / stderr all inherited → Textual reaches the tty
        )

        # Close child-side ends in the parent
        os.close(cmd_r)
        os.close(res_w)

        self._write_fd = cmd_w
        self._read_fd = res_r

        # Drain any prints that happened before the child was spawned
        try:
            pre_spawn = self.interface._redirected.join()
            if pre_spawn:
                self._send(TuiCommand.OUTPUT, pre_spawn)
        except AttributeError:
            pass

        # Wire up live streaming: future print()s go directly via OUTPUT
        try:
            self.interface._redirected.output_callback = self._send_output
        except AttributeError:
            pass

    def _send_output(self, text: str) -> None:
        """Send a live OUTPUT message to the child. Called from print() via output_callback."""
        if self._write_fd is not None:
            try:
                self._send(TuiCommand.OUTPUT, text)
            except OSError:
                pass

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

    @staticmethod
    def _safe_form(form: TagDict) -> TagDict:
        """Return a copy of form safe to pickle.

        on_change callbacks are replaced with _OnChangeProxy so the child can
        trigger them via the callback channel.  Other non-serialisable callables
        (validator, button val) are replaced with stubs.
        """
        from .subprocess_child import _OnChangeProxy

        form_copy = copy.deepcopy(form)
        for i, tag in enumerate(flatten(form_copy)):  # type: ignore[arg-type]
            # Always replace on_change with a picklable proxy
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
                        "and will not fire in the Textual subprocess.",
                        stacklevel=4,
                    )

            if callable(getattr(tag, "val", None)):
                try:
                    pickle.dumps(tag.val)
                except Exception:
                    tag.val = _StrippedCallable()
                    warnings.warn(
                        f"Tag '{tag.label}': callable val cannot be serialised; "
                        "button click will be a no-op in the Textual subprocess.",
                        stacklevel=4,
                    )
        return form_copy

    def _get_redirected(self) -> str:
        """No-op: output now streams live via TuiCommand.OUTPUT / output_callback."""
        return ""

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

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        self._ensure_process()
        super(TextualAdaptor, self).run_dialog(form, title, submit)  # BackendAdaptor

        while True:
            redirected = self._get_redirected()
            raw_layout = list(self.facet._raw_layout)
            self.facet._raw_layout.clear()

            safe_form = self._safe_form(self.facet._form or {})
            effective_title = self.facet._title or title
            self._send(TuiCommand.FORM, safe_form, effective_title, submit, redirected, raw_layout)

            while True:  # inner loop: handle callbacks before final RESULT/CANCEL
                command, args = self._receive()

                if command == TuiCommand.RESULT:
                    ui_vals = args[0]  # type: ignore[index]
                    if self._try_submit(zip(flatten(self.facet._form or {}), ui_vals)):  # type: ignore[arg-type]
                        return form
                    break  # validation failed — re-send form
                elif command == TuiCommand.CANCEL:
                    raise Cancelled
                elif command == TuiCommand.CALLBACK:
                    result = self._handle_callback(*args)  # type: ignore[misc]
                    if result == "done":
                        return form
                    elif result == "retry":
                        break  # re-send form
                    # "continue": keep waiting for more messages
                else:
                    raise Cancelled

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1, *, timeout: int = 0):
        self._ensure_process()
        redirected = self._get_redirected()
        self._send(TuiCommand.BUTTONS, text, buttons, focused, timeout, redirected)
        command, args = self._receive()
        if command != TuiCommand.RESULT:
            raise Cancelled
        return args[0]

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
