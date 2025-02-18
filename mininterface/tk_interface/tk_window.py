import sys
from tkinter import LEFT, Button, Frame, Label, Text, Tk
from typing import TYPE_CHECKING, Any, Callable

from tkscrollableframe import ScrolledFrame
from tktooltip import ToolTip

from tkinter_form import Form, Value

from ..exceptions import Cancelled
from ..facet import BackendAdaptor
from ..form_dict import TagDict, formdict_to_widgetdict
from ..tag import Tag
from .tk_facet import TkFacet
from .utils import recursive_set_focus, replace_widgets

if TYPE_CHECKING:
    from . import TkInterface


class TkWindow(Tk, BackendAdaptor):
    """ An editing window. """

    def __init__(self, interface: "TkInterface"):
        super().__init__()
        self.facet = interface.facet = TkFacet(self, interface.env)
        self.params = None
        self._result = None
        self._event_bindings = {}
        self.interface = interface
        self.title(interface.title)
        self.bind('<Escape>', lambda _: self._ok(Cancelled))

        # NOTE it would be nice to auto-hide the scrollbars if not needed
        self.sf = ScrolledFrame(self, use_ttk=True)
        """ scrollable superframe """
        self.sf.pack(side="top", expand=1, fill="both")

        self.frame = self.sf.display_widget(Frame)
        """ dialog frame """

        self.label = Label(self.frame, text="")
        self.label.pack_forget()

        self.text_widget = Text(self.frame, wrap='word', height=20, width=80)
        self.text_widget.pack_forget()
        self.pending_buffer = []
        """ Text that has been written to the text widget but might not be yet seen by user.
            Because no mainloop was invoked.
        """

    @staticmethod
    def widgetize(tag: Tag) -> Value:
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
                         form_dict=formdict_to_widgetdict(form, self.widgetize),
                         name_button=submit if isinstance(submit, str) else "Ok",
                         button_command=self._ok if submit else None
                         )
        self.form.pack()

        # Add radio etc.
        replace_widgets(self, self.form.fields, form)

        # Set the submit and exit options
        if self.form.button:
            tip, keysym = ("Enter", "<Return>")
            ToolTip(self.form.button, msg=tip)  # NOTE is not destroyed in _clear
            self._bind_event(keysym, self._ok)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        recursive_set_focus(self.form)
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
