"""Child process side of the persistent Tk subprocess.

Spawned via `python -c "...run_child_main(read_fd, write_fd)"`.
Reads commands from read_fd, displays Tk dialogs, writes results to write_fd.

Threading model (mirrors the Textual child)
-------------------------------------------
Tk requires all UI work to happen on the thread that created the root, so:

* the **main thread** runs ``Tk.mainloop`` persistently for the whole session
  (the window is never destroyed between dialogs),
* an **IPC worker thread** reads pipe commands and schedules UI work on the main
  thread via ``root.after(0, ...)``,
* a ``threading.Event`` (``_submitted``) synchronises the worker with the main
  thread — exactly like Textual's ``call_from_thread`` + ``_submitted`` pair.

Callback channel
----------------
on_change: the parent replaces ``tag.on_change`` with the shared
``_OnChangeProxy``.  When fired (synchronously, in a Tk event callback on the
main thread) it does a brief blocking round-trip with the parent.  The IPC
worker is parked in ``_submitted.wait()`` meanwhile, so it is the only reader of
the pipe — no contention.

button: a callback button calls ``facet.submit`` → ``adaptor._ok`` which detects
``post_submit_action`` and reports a CALLBACK("button") to the parent.

Closing the window (the X button) tears the child down; the parent then sees the
pipe close (EOF) and raises ``Cancelled``.
"""
import threading
import tkinter

from .._lib.auxiliary import flatten
from .._lib.subprocess_child_base import read_msg, send_msg, register_hooks
from .._lib.tui_command import TuiCommand
from ..exceptions import Cancelled


def _make_child_adaptor_class():
    """Return _ChildTkAdaptor (deferred import to keep tkinter_form out of module load)."""
    from tkinter import END
    from .adaptor import TkAdaptor
    from .utils import widgets_to_dict

    class _ChildTkAdaptor(TkAdaptor):
        """Persistent Tk adaptor living in the child process.

        Reuses TkAdaptor's widget building (`_build_form` / `_build_buttons`) but
        replaces the per-dialog mainloop with a single persistent one driven by
        the IPC worker thread.
        """

        def __init__(self, interface, settings):
            read_fd, write_fd = interface._child_fds
            super().__init__(interface, settings)
            self.read_fd = read_fd
            self.write_fd = write_fd
            self._submitted = threading.Event()
            self._ipc_result: tuple = (TuiCommand.CANCEL,)
            self._button_mode = False
            self._always_shown = False
            self.protocol("WM_DELETE_WINDOW", self._on_close)
            # Read-only output: disabled state blocks editing but still allows
            # mouse selection + copy (Ctrl+C). Toggled to "normal" only for writes.
            self.text_widget.configure(state="disabled")
            self.withdraw()  # stay hidden until the first form arrives

        # -------------------------------------------------------------- lifecycle

        def start_ipc(self):
            threading.Thread(target=self._ipc_worker, daemon=True).start()

        def run_persistent(self):
            # The plain Tk mainloop — NOT TkAdaptor.mainloop (which has submit semantics).
            tkinter.Tk.mainloop(self)

        def _on_close(self):
            """X button: end the session. Parent will see EOF → Cancelled."""
            self._ipc_result = (TuiCommand.CANCEL,)
            self._submitted.set()  # unblock the worker if a form is currently active
            self.destroy()

        # -------------------------------------------------------------- output

        def _write_output(self, text: str) -> None:
            try:
                w = self.text_widget
                if not w.winfo_manager():
                    # side="bottom" keeps the output area below the form regardless
                    # of packing order (e.g. when history arrives before the form).
                    w.pack(side="bottom", expand=True, fill="both")
                w.configure(state="normal")  # temporarily writable for the insert
                w.insert(END, text)
                w.see(END)
                lines = int(w.index("end-1c").split(".")[0])
                if lines > 1000:
                    w.delete(1.0, f"{lines - 1000}.0")
                w.configure(state="disabled")  # back to read-only
                self.update_idletasks()
            except Exception:
                pass

        def _append_line(self, line: str) -> None:
            """Hook target for streamed OUTPUT.
            Live-streamed lines arrive without trailing newline; bulk redirected_text has it."""
            self._write_output(line if line.endswith("\n") else line + "\n")

        # -------------------------------------------------------------- form update

        def _apply_form_update(self, updates: list, title: str) -> None:
            """Push the parent's new tag values into the live Tk widgets.

            Runs on the main thread (the on_change proxy fires there).
            """
            tags = list(flatten(self.facet._form or {}))
            try:
                field_forms = list(flatten(widgets_to_dict(self.form.fields)))
            except Exception:
                field_forms = []
            for pos, new_val in updates:
                if not (0 <= pos < len(tags)):
                    continue
                tags[pos].val = new_val
                tags[pos]._last_ui_val = new_val  # prevent re-triggering on the same value
                if pos < len(field_forms):
                    try:
                        field_forms[pos].variable.set(new_val)
                    except Exception:
                        pass
            if title:
                # Update the in-window header, NOT the WM window title.
                self.facet.set_title(title)

        # -------------------------------------------------------------- submit / cancel

        def _clear_dialog(self):
            """Like TkAdaptor._clear_dialog but keeps the window size.

            The base resets geometry to "" (fit content), which makes the window
            visibly shrink when a dialog disappears. Here we keep the current size
            between dialogs — the next dialog calls _refresh_size to resize."""
            self.frame.pack_forget()
            for widget in self.frame.winfo_children():
                if widget not in [self.text_widget, self.label_frame, self.label]:
                    widget.destroy()
            for key in self._event_bindings:
                self.unbind(key)
            self._event_bindings.clear()
            self._result = None

        def _ok(self, val=None):
            """Persistent-mode replacement for TkAdaptor._ok (no quit())."""
            if val is Cancelled:
                self._ipc_result = (TuiCommand.CANCEL,)
            elif self._button_mode:
                self._ipc_result = (TuiCommand.RESULT, val)
            elif self.post_submit_action is not None:
                pending = self.post_submit_action
                self.post_submit_action = None
                tags = list(flatten(self.facet._form or {}))
                tag_pos = next((i for i, t in enumerate(tags) if t._run_callable == pending), -1)
                self._ipc_result = (TuiCommand.CALLBACK, "button", tag_pos)
            else:
                # Collect the raw UI values; the parent validates and may resend the form.
                ui_vals = list(flatten(self.form.get()))
                self._ipc_result = (TuiCommand.RESULT, ui_vals)
            self._clear_dialog()  # keep the persistent mainloop running
            self._submitted.set()

        # -------------------------------------------------------------- UI builders (main thread)

        def _show_form(self, form, title, submit_flag, raw_layout, redirected_text,
                       always_shown, program_title=None):
            try:
                self._always_shown = always_shown
                if program_title:
                    self.title(program_title)  # WM window title = program name
                self._button_mode = False
                for t in flatten(form):
                    t._facet = self.facet
                self.facet._fetch_from_adaptor(form)
                if self.settings.mnemonic is not False:
                    self._determine_mnemonic(form, self.settings.mnemonic is True)
                if redirected_text:
                    self._write_output(redirected_text)
                self._build_form(form, title, submit_flag)
                if raw_layout:
                    self.facet._layout(raw_layout)
                self.deiconify()
                self.after(1, self._refresh_size)
            except Exception:
                self._ipc_result = (TuiCommand.CANCEL,)
                self._submitted.set()

        def _show_buttons(self, text, buttons_list, focused, timeout, redirected_text,
                          always_shown=False, program_title=None):
            try:
                self._always_shown = always_shown
                if program_title:
                    self.title(program_title)  # WM window title = program name
                self._button_mode = True
                if redirected_text:
                    self._write_output(redirected_text)
                self._build_buttons(text, buttons_list, focused, timeout=timeout)
                self.deiconify()
                self.after(1, self._refresh_size)
            except Exception:
                self._ipc_result = (TuiCommand.CANCEL,)
                self._submitted.set()

        def _after_submit(self):
            if not self._always_shown:
                self.withdraw()

        # -------------------------------------------------------------- IPC worker (background thread)

        def _ipc_worker(self):
            while True:
                msg = read_msg(self.read_fd)
                if msg is None:
                    self.after(0, self.destroy)
                    return

                command, *args = msg

                if command == TuiCommand.SHUTDOWN:
                    self.after(0, self.destroy)
                    return

                if command == TuiCommand.OUTPUT:
                    self.after(0, self._append_line, args[0])
                    continue

                try:
                    if command == TuiCommand.FORM:
                        form, title, submit_flag, redirected_text, raw_layout, *rest = args
                        always_shown = rest[0] if rest else False
                        program_title = rest[1] if len(rest) > 1 else None
                        self._submitted.clear()
                        self.after(0, self._show_form, form, title, submit_flag,
                                   raw_layout, redirected_text, always_shown, program_title)
                        self._submitted.wait()
                        send_msg(self.write_fd, self._ipc_result)
                        if self._ipc_result[0] == TuiCommand.CANCEL:
                            self.after(0, self.destroy)
                            return
                        self.after(0, self._after_submit)

                    elif command == TuiCommand.BUTTONS:
                        text, buttons_list, focused, timeout, redirected_text, *rest = args
                        always_shown = rest[0] if rest else False
                        program_title = rest[1] if len(rest) > 1 else None
                        self._submitted.clear()
                        self.after(0, self._show_buttons, text, buttons_list,
                                   focused, timeout, redirected_text, always_shown, program_title)
                        self._submitted.wait()
                        send_msg(self.write_fd, self._ipc_result)
                        if self._ipc_result[0] == TuiCommand.CANCEL:
                            self.after(0, self.destroy)
                            return
                        self.after(0, self._after_submit)

                except Exception:
                    send_msg(self.write_fd, (TuiCommand.CANCEL,))

    return _ChildTkAdaptor


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_child_main(read_fd: int, write_fd: int) -> None:
    """Entry point called by the subprocess via `python -c`.

    Creates a minimal interface whose adaptor is the persistent child Tk adaptor,
    wires the callback/output hooks, then runs the persistent mainloop.
    No user code is re-executed.
    """
    from mininterface._lib.redirectable import Redirectable
    from mininterface._mininterface import Mininterface

    AdaptorCls = _make_child_adaptor_class()

    class _ChildInterface(Redirectable, Mininterface):
        _adaptor: AdaptorCls  # type: ignore[valid-type]

        def __init__(self):
            self._child_fds = (read_fd, write_fd)
            super().__init__()

    interface = _ChildInterface()
    adaptor = interface._adaptor

    register_hooks(
        read_fd, write_fd,
        apply_form_update=adaptor._apply_form_update,
        append_output=adaptor._append_line,
    )
    adaptor.start_ipc()
    adaptor.run_persistent()
