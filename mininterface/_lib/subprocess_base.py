"""Shared IPC base for subprocess-based UI adaptors (TUI and GUI).

Subclasses supply _CHILD_CMD and UI-specific facet/settings annotations.
The IPC protocol and pipe management are identical for all backends.
"""
import atexit
import copy
import io
import os
import pickle
import struct
import subprocess
import sys
from typing import Any, NoReturn

from .auxiliary import flatten
from .form_dict import TagDict
from .ipc_command import IpcCommand
from ..exceptions import Cancelled
from .._mininterface.adaptor import BackendAdaptor


def _stripped_callback(*_):
    """Placeholder button action sent to the child in place of a real callback.

    Functions only make sense in the parent (that is where the user's program
    and its context live), so they are never serialised.  This is a real
    function (not a callable instance) so the child still recognises the tag as
    a callable and renders a button; pressing it routes a CALLBACK back to the
    parent, which runs the real callable on its own tag.
    """
    pass


class _ChildSimUnpickler(pickle.Unpickler):
    """Mimics the child's import environment.  The child is launched with
    `python -c`, so its __main__ holds none of the parent script's globals;
    anything pickled as a __main__ reference is unreachable there."""
    def find_class(self, module, name):
        if module == "__main__":
            raise ValueError(f"__main__.{name}")
        return super().find_class(module, name)


def _child_can_rebuild(obj) -> bool:
    """Whether the subprocess child could reconstruct obj from the pickle stream.

    False for a lambda/closure (unpicklable) or anything defined in the parent's
    __main__ (a custom class/enum the user wrote in their script).  Reconstruction
    uses __new__/__setstate__, not __init__, so this has no user side effects."""
    try:
        data = pickle.dumps(obj)
    except Exception:
        return False
    try:
        _ChildSimUnpickler(io.BytesIO(data)).load()
    except Exception:
        return False
    return True


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
        self._in_live_callback = False
        """ True while a live on_change/validation callback runs in the parent.
            The child's UI thread is parked in the proxy round-trip meanwhile, so
            opening a nested dialog would deadlock — see _guard_reentrancy. """
        atexit.register(self._destroy)

    def _record_output(self, text: str) -> None:
        """Accumulate output so it can be replayed to a respawned child."""
        if not text:
            return
        self._output_history += text
        cap = 200_000
        if len(self._output_history) > cap:
            self._output_history = self._output_history[-cap:]

    def _clear_output(self) -> None:
        """Drop the streamed-output history and tell a live child to empty its
        output widget. Parent-side hook for facet._clear() — in-process that just
        cleared the redirect buffer, but here the child owns the on-screen output."""
        self._output_history = ""
        if self._process is not None and self._process.poll() is None and self._write_fd is not None:
            try:
                self._send(IpcCommand.CLEAR_OUTPUT)
            except OSError:
                pass

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

        if spawned:
            # The child adaptor is created with default settings; ship the real
            # ones so settings-driven UI (mnemonic, combobox_since, …) matches
            # what the user configured via run(..., settings=...).
            try:
                self._send(IpcCommand.SETTINGS, self.settings)
            except OSError:
                pass
            # A freshly spawned child has an empty output area. Replay the whole
            # session output so text printed before a window close+reopen survives.
            if self._output_history:
                try:
                    self._send(IpcCommand.OUTPUT, self._output_history)
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
                self._send(IpcCommand.OUTPUT, text)
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
        """Return a copy of form safe to send to the child.

        Functions belong to the parent only — they are never serialised:

        * on_change → an _OnChangeProxy that round-trips to the parent,
        * validator → dropped (the parent still validates its real tag on submit),
        * a callable val (a button) → a _stripped_callback placeholder; the child
          renders a button and the press routes back to the parent.

        SelectTag options/values are represented purely by their string labels
        (see _labelize_select), so the child never has to reconstruct the
        user-defined classes (enums, dataclasses, …) those values are instances
        of.  The parent keeps the real tags and maps labels back to real values.
        """
        from .subprocess_child_base import _OnChangeProxy, _ValidationProxy
        from ..tag.select_tag import SelectTag

        form_copy = copy.deepcopy(form)
        for i, tag in enumerate(flatten(form_copy)):  # type: ignore[arg-type]
            if getattr(tag, "on_change", None) is not None:
                tag.on_change = _OnChangeProxy(i)

            # Replace every validator with a proxy that round-trips to the parent.
            # This keeps live FocusOut/Tab validation working for __main__ validators
            # too — the child never calls the real function, just asks the parent.
            if getattr(tag, "validation", None) is not None:
                tag.validation = _ValidationProxy(i)

            if isinstance(tag, SelectTag):
                SubprocessAdaptorBase._labelize_select(tag)
            elif callable(getattr(tag, "val", None)):
                # A button action: the child only needs to know it is callable.
                # The original annotation is the function's own type (unpicklable
                # and child-specific); clear it — val being a function is enough
                # for the child to recognise a button.
                tag.val = tag._original_val = _stripped_callback
                tag.annotation = None
            elif not _child_can_rebuild(tag.val):
                # A custom-class value (e.g. a user object defined in __main__):
                # the child only renders it as an editable string, and the
                # parent's real tag rebuilds the object from that string on
                # submit (Tag.update → annotation(ui_value)).  So send the
                # string and drop the child-unreachable annotation.
                tag.val = str(tag.val)
                tag._original_val = str(tag._original_val) if tag._original_val is not None else None
                tag._last_ui_val = None
                if not _child_can_rebuild(tag.annotation):
                    tag.annotation = None
        return form_copy

    @staticmethod
    def _value_to_label(tag, value):
        """Map a SelectTag's real option value(s) to their string label(s)."""
        options = tag._build_options()  # {label: real_value}
        if tag.multiple:
            seq = value if isinstance(value, (list, tuple, set)) else []
            return [label for label, v in options.items() if v in seq]
        return next((label for label, v in options.items() if v == value), None)

    @staticmethod
    def _labelize_select(tag) -> None:
        """Rewrite a SelectTag so its options and value are plain string labels.

        The label set is exactly what the UI shows.  This keeps the form fully
        picklable even when the option values are user-defined objects (enum
        members, dataclass instances, …).  The parent still holds the real tags,
        so the label the child returns is mapped back to the real option value
        (see _resolve_select_labels).
        """
        try:
            options = tag._build_options()  # {label: real_value}
        except Exception:
            return
        if not options:
            return
        # val and _original_val both hold the selected option value (an enum
        # member, etc.); convert both to labels so no user class is left to
        # serialise.  _last_ui_val is recomputed in the child, so just clear it.
        tag.val = SubprocessAdaptorBase._value_to_label(tag, tag.val)
        tag._original_val = SubprocessAdaptorBase._value_to_label(tag, tag._original_val)
        tag._last_ui_val = None
        tag.options = {label: label for label in options}

    @staticmethod
    def _resolve_select_labels(tags, ui_vals):
        """Map labels the child returned for each SelectTag back to real values."""
        from ..tag.select_tag import SelectTag
        out = []
        for tag, v in zip(tags, ui_vals):
            out.append(tag._resolve_label(v) if isinstance(tag, SelectTag) else v)
        return out

    def _submit_pairs(self, tags, ui_vals):
        """Build (tag, value) pairs to validate/apply on submit from the child's
        raw ui_vals: resolve SelectTag labels and skip callable (button) tags,
        whose real value lives in the parent and must not be overwritten by the
        child's placeholder."""
        ui_vals = self._resolve_select_labels(tags, ui_vals)
        return [(tag, v) for tag, v in zip(tags, ui_vals) if not tag._is_a_callable()]

    @staticmethod
    def _labelize_updates(tags, updates):
        """Convert (pos, real_value) FORM_UPDATE pairs to labels for SelectTags so
        the child (which renders labels) can apply them."""
        from ..tag.select_tag import SelectTag
        out = []
        for pos, val in updates:
            tag = tags[pos] if 0 <= pos < len(tags) else None
            if isinstance(tag, SelectTag):
                val = SubprocessAdaptorBase._value_to_label(tag, val)
            out.append((pos, val))
        return out

    # ------------------------------------------------------------------
    # Redirected output
    # ------------------------------------------------------------------

    def _get_redirected(self) -> str:
        """Drain the parent's pending stdout buffer (e.g. text printed before the
        first dialog) so it can be shown in the next dialog."""
        try:
            return self.interface._redirected.join()
        except AttributeError:
            return ""

    def _confirm_streamed(self) -> None:
        """Tell the redirect buffer that everything streamed to the child so far is
        about to be (re)rendered by the next dialog, so only the not-yet-shown tail
        remains for __exit__ to replay to stdout."""
        try:
            self.interface._redirected.confirm_streamed()
        except AttributeError:
            pass

    # ------------------------------------------------------------------
    # Callback handling
    # ------------------------------------------------------------------

    def _guard_reentrancy(self) -> None:
        """Refuse to open a dialog from inside an on_change/validation callback.

        These run in the parent while the child is blocked mid round-trip (see
        _OnChangeProxy/_ValidationProxy); sending it a nested FORM/BUTTONS would
        hang. Fail fast with a clear, catchable error instead."""
        if self._in_live_callback:
            from ..exceptions import _DialogReentrancyError
            raise _DialogReentrancyError(
                "Cannot open a dialog from an on_change or validation callback. "
                "Use a button callback for that instead."
            )

    def _handle_callback(self, callback_type: str, tag_pos: int, *extra) -> str:
        """Process a CALLBACK message from the child. Returns 'continue', 'done', or 'retry'."""
        from ..exceptions import ValidationFail

        tags = list(flatten(self.facet._form))  # type: ignore[arg-type]
        orig_vals = [t.val for t in tags]

        if callback_type == "validate" and 0 <= tag_pos < len(tags):
            tag = tags[tag_pos]
            new_val = extra[0] if extra else tag.val
            new_val = self._resolve_select_labels([tag], [new_val])[0]
            # _validate() checks `passed is not True` — send True on success, error string on failure.
            # Sending None on success would make `None is not True` raise a spurious ValidationFail.
            result = True
            self._in_live_callback = True  # refuse nested dialogs (see _guard_reentrancy)
            try:
                tag.update(new_val)
                result = True if tag._error_text is None else tag._error_text
            finally:
                self._in_live_callback = False
                # Always answer the child's round-trip, even if the validator raised —
                # otherwise its _ValidationProxy would block forever.
                self._send(IpcCommand.VALIDATE_RESULT, result)
            return "continue"

        if callback_type == "on_change" and 0 <= tag_pos < len(tags):
            tag = tags[tag_pos]
            new = extra[0] if extra else None
            tag.update(self._resolve_select_labels([tag], [new])[0])
            try:
                if tag.on_change:
                    self._in_live_callback = True  # refuse nested dialogs (see _guard_reentrancy)
                    try:
                        tag.on_change(tag)
                    finally:
                        self._in_live_callback = False
            finally:
                # Always answer the child's round-trip, even if on_change raised —
                # otherwise its _OnChangeProxy would block forever.
                updates = [(i, t.val) for i, t in enumerate(tags) if t.val != orig_vals[i]]
                updates = self._labelize_updates(tags, updates)
                self._send(IpcCommand.FORM_UPDATE, updates, self.facet._title)
            return "continue"

        if callback_type == "button" and 0 <= tag_pos < len(tags):
            # A button press is a submit too: validate the whole form first (so an
            # empty/invalid field blocks it, exactly like the plain submit button),
            # then run the button's callable.  _try_submit validates every field
            # and only then calls submit_done(), which runs post_submit_action.
            pairs = self._submit_pairs(tags, extra[0]) if extra else [(t, t.val) for t in tags]
            self.post_submit_action = tags[tag_pos]._run_callable
            try:
                ok = self._try_submit(pairs)
            except ValidationFail as e:
                if msg := str(e):
                    self.interface.alert(msg)
                ok = False
            return "done" if ok else "retry"

        return "continue"

    # ------------------------------------------------------------------
    # High-level dialog methods
    # ------------------------------------------------------------------

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        self._guard_reentrancy()
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
            # This dialog re-renders the output area, so everything streamed so far
            # is now shown — drop it from the not-yet-rendered tail.
            self._confirm_streamed()
            self._send(IpcCommand.FORM, safe_form, effective_title, submit, redirected,
                       raw_layout, always_shown, program_title)

            while True:
                command, args = self._receive()

                if command == IpcCommand.RESULT:
                    ui_vals = args[0]  # type: ignore[index]
                    tags = list(flatten(self.facet._form or {}))
                    if self._try_submit(self._submit_pairs(tags, ui_vals)):  # type: ignore[arg-type]
                        return form
                    break
                elif command == IpcCommand.CANCEL:
                    self._on_cancel()
                    raise Cancelled
                elif command == IpcCommand.QUIT:
                    # The user closed the window — quit the whole program (like the
                    # in-process GUI's WM_DELETE_WINDOW → sys.exit), not a
                    # recoverable Cancelled that a retry loop would answer with a
                    # freshly respawned window.
                    self._on_cancel()
                    sys.exit(0)
                elif command == IpcCommand.ERROR:
                    self._raise_child_error(args)
                elif command == IpcCommand.CALLBACK:
                    result = self._handle_callback(*args)  # type: ignore[misc]
                    if result == "done":
                        return form
                    elif result == "retry":
                        break
                else:
                    self._on_cancel()
                    raise Cancelled

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1, *, timeout: int = 0):
        self._guard_reentrancy()
        self._ensure_process()
        redirected = self._get_redirected()
        self._record_output(redirected)
        # A buttons dialog (confirm/alert/yes_no) can carry a facet._layout too —
        # ship it just like run_dialog does, otherwise a layout set before
        # confirm() would silently never appear.
        raw_layout = list(self.facet._raw_layout)
        self.facet._raw_layout.clear()
        always_shown = getattr(self.interface, "_always_shown", False)
        program_title = getattr(self.interface, "title", None)
        self._confirm_streamed()
        self._send(IpcCommand.BUTTONS, text, buttons, focused, timeout, redirected,
                   raw_layout, always_shown, program_title)
        command, args = self._receive()
        if command == IpcCommand.QUIT:
            self._on_cancel()
            sys.exit(0)
        if command == IpcCommand.ERROR:
            self._raise_child_error(args)
        if command != IpcCommand.RESULT:
            self._on_cancel()
            raise Cancelled
        return args[0]

    def _raise_child_error(self, args) -> NoReturn:
        """The child hit an exception while building the dialog. Re-raise it here
        so the program sees the original error (a missing layout file, a bad
        widget value, …) instead of a misleading Cancelled. The child's traceback
        travels along as the exception's __cause__."""
        self._on_cancel()
        exc = args[0] if args else None
        tb = args[1] if len(args) > 1 else ""
        cause = RuntimeError("the UI subprocess hit an error while building the dialog:\n"
                             + (tb or "(no traceback)"))
        if isinstance(exc, BaseException):
            raise exc from cause
        raise cause

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

    def _shutdown_ui(self):
        """Tear down the child UI and wait for it to restore the terminal.

        Parent and child share the same tty; after a form submit the child's
        Textual/Tk app stays alive (alternate screen, raw mode, hidden cursor)
        ready for the next dialog. On leaving the `with` block the parent is about
        to write plain text (the swallowed-tail reprint, and whatever the script
        prints after the block) to that tty — if the child still owns it the output
        lands in the alternate screen and the terminal is left corrupted. So bring
        the child fully down (SHUTDOWN + wait), which restores the terminal, before
        any such write. Idempotent: a later atexit _destroy is a no-op."""
        self._destroy()

    def _destroy(self):
        """Terminate the child subprocess and close pipe FDs."""
        try:
            self.interface._redirected.output_callback = None
        except AttributeError:
            pass
        if self._process and self._process.poll() is None:
            try:
                self._send(IpcCommand.SHUTDOWN)
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
