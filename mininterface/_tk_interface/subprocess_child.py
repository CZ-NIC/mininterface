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
from .._lib.subprocess_child_base import error_payload, read_msg, send_msg, register_hooks
from .._lib.ipc_command import IpcCommand
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
            self._ipc_result: tuple = (IpcCommand.CANCEL,)
            self._closing = False
            """ True once the session is genuinely ending (window X / EOF / SHUTDOWN).
                A plain Esc cancel does NOT set this: the form is cleared but the
                persistent app stays alive for the next dialog, exactly like a submit. """
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
            """X button: the user wants to quit the whole program (unlike Esc,
            which only cancels the current dialog) — matching the in-process GUI's
            WM_DELETE_WINDOW → sys.exit. Sent directly (not via _submitted) so it
            works whether or not a dialog is currently active."""
            self._closing = True
            try:
                send_msg(self.write_fd, (IpcCommand.QUIT,))
            except OSError:
                pass
            self.destroy()

        # -------------------------------------------------------------- output

        def _write_output(self, text: str) -> None:
            try:
                w = self.text_widget
                if not w.winfo_manager():
                    # side="bottom" keeps the output area below the form regardless
                    # of packing order (e.g. when history arrives before the form).
                    w.pack(side="bottom", expand=True, fill="both")
                    # The text widget appearing for the first time changes the frame
                    # dimensions — resize the window and reset scroll so the form stays visible.
                    self.after(1, self._layout_new_dialog)
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

        def _clear_output(self) -> None:
            """Empty the output Text widget (parent's facet._clear)."""
            try:
                w = self.text_widget
                w.configure(state="normal")
                w.delete("1.0", END)
                w.configure(state="disabled")
            except Exception:
                pass

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
                self._ipc_result = (IpcCommand.CANCEL,)
            elif self._button_mode:
                self._ipc_result = (IpcCommand.RESULT, val)
            elif self.post_submit_action is not None:
                pending = self.post_submit_action
                self.post_submit_action = None
                tags = list(flatten(self.facet._form or {}))
                tag_pos = next((i for i, t in enumerate(tags) if t._run_callable == pending), -1)
                # Send the current field values too: a button is a submit, so the
                # parent validates the whole form before running the callable.
                ui_vals = list(flatten(self.form.get()))
                self._ipc_result = (IpcCommand.CALLBACK, "button", tag_pos, ui_vals)
            else:
                # Collect the raw UI values; the parent validates and may resend the form.
                ui_vals = list(flatten(self.form.get()))
                self._ipc_result = (IpcCommand.RESULT, ui_vals)
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
                self._setup_form_facet(form)
                if redirected_text:
                    self._write_output(redirected_text)
                # Layout first so it appears above the form, matching the
                # in-process adaptor (the user's facet._layout packs before
                # run_dialog builds the form).
                if raw_layout:
                    self.facet._layout(raw_layout)
                self._build_form(form, title, submit_flag)
                self.deiconify()
                self.after(1, self._layout_new_dialog)
            except Exception as exc:
                self._dialog_failed(exc)

        def _show_buttons(self, text, buttons_list, focused, timeout, redirected_text,
                          raw_layout=None, always_shown=False, program_title=None):
            try:
                self._always_shown = always_shown
                if program_title:
                    self.title(program_title)  # WM window title = program name
                self._button_mode = True
                if redirected_text:
                    self._write_output(redirected_text)
                # Layout first so it appears above the question + buttons.
                if raw_layout:
                    self.facet._layout(raw_layout)
                self._build_buttons(text, buttons_list, focused, timeout=timeout)
                self.deiconify()
                self.after(1, self._layout_new_dialog)
            except Exception as exc:
                self._dialog_failed(exc)

        def _dialog_failed(self, exc: BaseException) -> None:
            """A dialog build crashed mid-way: remove whatever widgets it already
            packed (the parent may catch the error and open another dialog in this
            same live window), then unblock the worker with an ERROR result."""
            try:
                self._clear_dialog()
            except Exception:
                pass
            self._ipc_result = error_payload(exc)
            self._submitted.set()

        def _layout_new_dialog(self):
            """Resize window to content and reset scroll to top.

            Called 1 ms after a new form/buttons dialog is shown.  The delay
            lets Tk finish rendering widgets so winfo_width/height are accurate.
            Resetting the scroll position is critical: Tk may have auto-scrolled
            the canvas to a focused widget (e.g. the OK button at the bottom of
            the previous form), leaving the canvas viewport offset — making the
            new dialog appear empty/gray until the user maximises the window."""
            self._refresh_size()
            self.sf.scroll_to_top()

        def _after_submit(self):
            if not self._always_shown:
                self.withdraw()

        # -------------------------------------------------------------- IPC worker (background thread)

        def _handle_form(self, write_fd, form, title, submit_flag, redirected_text, raw_layout, *rest):
            always_shown = rest[0] if rest else False
            program_title = rest[1] if len(rest) > 1 else None
            self._submitted.clear()
            self.after(0, self._show_form, form, title, submit_flag,
                       raw_layout, redirected_text, always_shown, program_title)
            self._submitted.wait()
            send_msg(write_fd, self._ipc_result)
            if self._closing:
                self.after(0, self.destroy)
                return
            # A plain Esc cancel (or a submit) keeps the persistent app alive: hide
            # the window and park for the next dialog. The parent raises Cancelled on
            # its side but reuses this same live child for the next form/alert.
            self.after(0, self._after_submit)

        def _handle_buttons(self, write_fd, text, buttons_list, focused, timeout, redirected_text,
                            raw_layout=None, *rest):
            always_shown = rest[0] if rest else False
            program_title = rest[1] if len(rest) > 1 else None
            self._submitted.clear()
            self.after(0, self._show_buttons, text, buttons_list,
                       focused, timeout, redirected_text, raw_layout, always_shown, program_title)
            self._submitted.wait()
            send_msg(write_fd, self._ipc_result)
            if self._closing:
                self.after(0, self.destroy)
                return
            self.after(0, self._after_submit)

        def _ipc_worker(self):
            from .._lib.subprocess_child_base import _ipc_worker_loop
            handlers = {
                'OUTPUT': lambda text: self.after(0, self._append_line, text),
                'CLEAR_OUTPUT': lambda: self.after(0, self._clear_output),
                # The user's settings arrive before the first form; apply them to
                # this adaptor (created with defaults) so widget building matches.
                'SETTINGS': lambda settings: setattr(self, 'settings', settings),
                'FORM': self._handle_form,
                'BUTTONS': self._handle_buttons,
                'on_eof': lambda: self.after(0, self.destroy),
            }
            _ipc_worker_loop(self.read_fd, self.write_fd, handlers)

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
        shutdown=lambda: adaptor.after(0, adaptor.destroy),
    )
    adaptor.start_ipc()
    adaptor.run_persistent()
