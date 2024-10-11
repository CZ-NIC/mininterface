import sys
from tkinter import LEFT, Button, Frame, Label, Text, Tk
from typing import TYPE_CHECKING, Any, Callable

from tktooltip import ToolTip

from tkinter_form import Form, Value

from ..facet import BackendAdaptor
from ..form_dict import TagDict, formdict_to_widgetdict
from ..common import Cancelled
from ..tag import Tag
from .tk_facet import TkFacet
from .utils import recursive_set_focus, replace_widgets

if TYPE_CHECKING:
    from . import GuiInterface


class TkWindow(Tk, BackendAdaptor):
    """ An editing window. """

    def __init__(self, interface: "GuiInterface"):
        super().__init__()
        self.facet = interface.facet = TkFacet(self, interface.env)
        self.params = None
        self._result = None
        self._event_bindings = {}
        self._post_submit_action: Callable | None = None  # TODO Migrate to the BackendAdaptor?
        self.interface = interface
        self.title(interface.title)
        self.bind('<Escape>', lambda _: self._ok(Cancelled))

        self.frame = Frame(self)
        """ dialog frame """

        self.label = Label(self, text="")
        self.label.pack_forget()

        self.text_widget = Text(self, wrap='word', height=20, width=80)
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

    def run_dialog(self, form: TagDict, title: str = "") -> TagDict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """
        self.facet._fetch_from_adaptor(form)
        if title:
            self.facet.set_title(title)

        self.form = Form(self.frame,
                         name_form="",
                         form_dict=formdict_to_widgetdict(form, self.widgetize),
                         name_config="Ok",
                         )
        self.form.pack()

        # Add radio etc.
        replace_widgets(self, self.form.widgets, form)

        # Set the submit and exit options
        self.form.button.config(command=self._ok)
        tip, keysym = ("Enter", "<Return>")
        ToolTip(self.form.button, msg=tip)  # NOTE is not destroyed in _clear
        self._bind_event(keysym, self._ok)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        recursive_set_focus(self.form)
        return self.mainloop(lambda: self.validate(form, title))

    def validate(self, form: TagDict, title: str) -> TagDict:
        if not Tag._submit(form, self.form.get()):
            return self.run_dialog(form, title)
        if self._post_submit_action:  # TODO, textual implementation
            self._post_submit_action()
        return form

    def yes_no(self, text: str, focus_no=True):
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no)+1)

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        label = Label(self.frame, text=text)
        label.pack(pady=10)

        for i, (text, value) in enumerate(buttons):
            button = Button(self.frame, text=text, command=lambda v=value: self._ok(v))
            if i == focused-1:
                b = button
                button.bind("<Return>", lambda _: b.invoke())
            button.pack(side=LEFT, padx=10)
        self.frame.winfo_children()[focused].focus_set()
        return self.mainloop()

    def _bind_event(self, event, handler):
        self._event_bindings[event] = handler
        self.bind(event, handler)

    def mainloop(self, callback: Callable = None):
        self.frame.pack(pady=5)
        self.deiconify()  # show if hidden
        self.pending_buffer.clear()
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
            widget.destroy()
        for key in self._event_bindings:
            self.unbind(key)
        self._event_bindings.clear()
        self._result = None
