import sys
from time import sleep
from tkinter import LEFT, END, Button, Frame, Label, TclError, Tk, Text
from typing import Any, Callable

from tktooltip import ToolTip

from tkinter_form import Form

from .HeadlessInterface import Cancelled, HeadlessInterface, OutT


class RedirectText:
    def __init__(self, widget: Text, window: Tk) -> None:
        self.widget = widget
        self.max_lines = 1000
        self.window = window

    def write(self, text):
        self.widget.pack(expand=True, fill='both')
        self.widget.insert(END, text)
        self.widget.see(END)  # scroll to the end
        self.trim()
        self.window.update_idletasks()

    def flush(self):
        pass  # required by sys.stdout

    def trim(self):
        lines = int(self.widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.widget.delete(1.0, f"{lines - self.max_lines}.0")


class GuiInterface(HeadlessInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = TkWindow(self)
        self._always_shown = False
        self._text_widget = self.window.text_widget
        self._original_stdout = sys.stdout

    def __enter__(self) -> "HeadlessInterface":
        """ When used in the with statement, the GUI window does not vanish between dialogues. """
        self._always_shown = True
        sys.stdout = RedirectText(self._text_widget, self.window)
        return self

    def __exit__(self, *_):
        self._always_shown = False
        sys.stdout = self._original_stdout

    def alert(self, text: str) -> None:
        return self.window.buttons(text, [("Ok", None)])

    def ask_args(self) -> OutT:
        """ Display a window form with all parameters. """
        params_ = self._dataclass_to_dict(self.args, self._load_descriptions())

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        data = self.window.run_dialog(self.parser.prog, params_)
        self._dict_to_dataclass(self.args, data)
        return self.args

    def is_yes(self, text):
        return self.window.yes_no(text, False)

    def is_no(self, text):
        return self.window.yes_no(text, True)


class TkWindow(Tk):
    """ An editing window. """

    def __init__(self, interface: GuiInterface):
        super().__init__()
        self.params = None
        self._result = None
        self._event_bindings = {}
        self.interface = interface
        self.bind('<Escape>', lambda _: self._ok(Cancelled))

        self.frame = Frame(self)
        """ dialog frame """

        self.text_widget = Text(self, wrap='word', height=20, width=80)
        self.text_widget.pack_forget()

    def run_dialog(self, title, form: dict) -> dict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """

        # Init the GUI
        self.title(title)
        self.form = Form(self.frame,
                         name_form="",
                         form_dict=form,
                         name_config="Ok",
                         )
        self.form.pack()

        # Set the enter and exit options
        self.form.button.config(command=self._ok)
        ToolTip(self.form.button, msg="Ctrl+Enter")  # TODO is not destroyed in _clear
        self._bind_event('<Control-Return>', self._ok)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        self.form.winfo_children()[0].winfo_children()[0].focus_set()
        return self.mainloop(lambda: self.form.get())

    def yes_no(self, text: str, focus_no=True):
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no)+1)

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        label = Label(self.frame, text=text)
        label.pack(pady=10)

        for text, value in buttons:
            button = Button(self.frame, text=text, command=lambda v=value: self._ok(v))
            button.bind("<Return>", lambda _: button.invoke())
            button.pack(side=LEFT, padx=10)
        self.frame.winfo_children()[focused].focus_set()
        return self.mainloop()

    def _bind_event(self, event, handler):
        self._event_bindings[event] = handler
        self.bind(event, handler)

    def mainloop(self, callback: Callable = None):
        self.frame.pack(pady=5)
        self.deiconify()  # show if hidden
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
