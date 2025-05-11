import sys
from tkinter import LEFT, Button, Frame, Label, TclError, Text, Tk
from typing import TYPE_CHECKING, Any, Callable

try:
    from tkscrollableframe import ScrolledFrame
    from tktooltip import ToolTip
    from tkinter_form import Form, Value
except ImportError:
    from ..exceptions import DependencyRequired
    raise DependencyRequired("basic")

from ..exceptions import Cancelled, InterfaceNotAvailable
from .._lib.form_dict import TagDict, tagdict_to_widgetdict
from .._mininterface.adaptor import BackendAdaptor
from .._mininterface.mixin import RichUiAdaptor
from ..settings import GuiSettings
from ..tag import Tag
from .facet import TkFacet
from .utils import recursive_set_focus, replace_widgets


class TkAdaptor(Tk, RichUiAdaptor, BackendAdaptor):
    """ An editing Tk window. """

    facet: TkFacet
    settings: GuiSettings

    def __init__(self, *args):
        BackendAdaptor.__init__(self, *args)

        try:
            Tk.__init__(self)
        except TclError:
            # even when installed the libraries are installed, display might not be available, hence tkinter fails
            raise InterfaceNotAvailable

        self.params = None
        self._result = None
        self._event_bindings = {}
        # NOTE: I'd prefer to have shortcuts somewhere ex. in the status bar ad hoc
        self.shortcuts = set([
            "F1: Show this help",
            "Enter: Submit form",
            "Escape: Cancel"
        ])
        self.title(self.interface.title)
        self.bind('<Escape>', lambda _: self._ok(Cancelled))
        self.bind('<F1>', self._show_help)  # Help with Ctrl+H

        # NOTE it would be nice to auto-hide the scrollbars if not needed
        self.sf = ScrolledFrame(self, use_ttk=True)
        """ scrollable superframe """
        self.sf.pack(side="top", expand=1, fill="both")

        self.frame = self.sf.display_widget(Frame)
        """ dialog frame """

        # Without label frame, self.label would be repacked to the end, not to the top.
        # (As the packing does not occur in __init__ but later via facet.set_title.)
        self.label_frame = Frame(self.frame)
        self.label_frame.pack()
        self.label = Label(self.label_frame, text="")

        self.text_widget = Text(self.frame, wrap='word', height=20, width=80)
        self.text_widget.pack_forget()
        self.pending_buffer = []
        """ Text that has been written to the text widget but might not be yet seen by user.
            Because no mainloop was invoked.
        """

    def _show_help(self, event=None):
        """Show help information in a popup window"""
        help_window = Tk()
        help_window.title("Keyboard Shortcuts")

        # Display all shortcuts
        help_text = "Keyboard Shortcuts:\n" + "\n".join(f"- {hint}" for hint in sorted(self.shortcuts))
        help_label = Label(
            help_window, text=help_text, justify=LEFT, padx=20, pady=20)
        help_label.pack()
        help_window.bind('<Escape>', lambda e: help_window.destroy())
        help_window.focus_set()

    def widgetize(self, tag: Tag) -> Value:
        """ Wrap Tag to a textual widget. """
        v = tag._get_ui_val()
        if tag.annotation is bool and not isinstance(v, bool):
            # tkinter_form unfortunately needs the bool type to display correct widget,
            # otherwise we end up with a text Entry.
            v = bool(v)
        elif not isinstance(v, (float, int, str, bool)):
            v = str(v)
        return Value(v, tag.description)

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """
        super().run_dialog(form, title, submit)
        if title:
            self.facet.set_title(title)

        self.form = Form(self.frame,
                         name_form="",
                         form_dict=tagdict_to_widgetdict(form, self.widgetize),
                         name_button=submit if isinstance(submit, str) else "Ok",
                         button_command=self._ok if submit else None
                         )
        self.form.pack()

        # Add radio etc.
        replace_widgets(self, self.form.fields, form)

        # Set the submit and exit settings
        if self.form.button:
            tip, keysym = ("Enter", "<Return>")
            ToolTip(self.form.button, msg=tip)  # NOTE is not destroyed in _clear
            self._bind_event(keysym, self._ok)

            # submit button styling
            # self.form.button.grid_configure(sticky="", pady=15)
            # self.form.button.config(width=15)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        recursive_set_focus(self.form)

        # status bar would look like this
        # status_var = StringVar()
        # status_var.set("F1 – help")
        # status_label = Label(self.frame, textvariable=status_var, relief="sunken", anchor="w", padx=5)
        # status_label.pack(side="bottom", fill="x", pady=(20, 0))

        return self.mainloop(lambda: self.validate(form, title, submit))

    def validate(self, form: TagDict, title: str, submit) -> TagDict:
        if not Tag._submit(form, self.form.get()) or not self.submit_done():
            return self.run_dialog(form, title, submit)
        return form

    def yes_no(self, text: str, focus_no=True):
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no)+1)

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        label = Label(self.frame, text=text)
        label.pack(pady=10)

        for i, (text, value) in enumerate(buttons):
            button = Button(self.frame, text=text, command=lambda v=value: self._ok(v))
            button.pack(side=LEFT, padx=10)
            if i == focused-1:
                button.focus_set()
                b = button
                button.bind("<Return>", lambda _: b.invoke())
        return self.mainloop()

    def _bind_event(self, event, handler):
        self._event_bindings[event] = handler
        self.bind(event, handler)

    def _refresh_size(self):
        """ Autoshow scrollbars."""
        self.update_idletasks()  # finish drawing
        width = self.frame.winfo_width()
        height = self.frame.winfo_height()

        if width < self.winfo_screenwidth():
            self.sf._x_scrollbar.grid_forget()
        else:
            self.sf._x_scrollbar.grid(row=1, column=0, sticky="we")

        if height < self.winfo_screenheight():
            self.sf._y_scrollbar.grid_forget()
        else:
            self.sf._y_scrollbar.grid(row=0, column=1, sticky="ns")

        # The widgets do not know their size at the begginning, they must be drawn.
        # Hence we recommend the window size here and not in the constructor.
        self.geometry(f"{width}x{height}")

    def mainloop(self, callback: Callable = None):
        self.deiconify()  # show if hidden
        self.pending_buffer.clear()
        self.after(1, self._refresh_size)
        super().mainloop()
        if not self.interface._always_shown:
            self.withdraw()  # hide

        if self._result is Cancelled:
            raise Cancelled
        if callback:
            return callback()
        return self._result

    def _ok(self, val=None):
        # self.destroy()
        self.quit()
        # self.withdraw()
        self._clear_dialog()
        self._result = val

    def _clear_dialog(self):
        self.frame.pack_forget()
        for widget in self.frame.winfo_children():
            if widget not in [self.text_widget, self.label]:
                widget.destroy()
        for key in self._event_bindings:
            self.unbind(key)
        self._event_bindings.clear()
        self._result = None
        self.geometry("")  # resize the window so that it does not end up large

    def _destroy(self):
        self.destroy()
