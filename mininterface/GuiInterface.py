import sys
from typing import Any, Callable

try:
    from tkinter import TclError, LEFT, Button, Frame, Label, Text, Tk
    from tktooltip import ToolTip
    from tkinter_form import Form, Value
except ImportError:
    from .common import InterfaceNotAvailable
    raise InterfaceNotAvailable


from .common import InterfaceNotAvailable
from .FormDict import FormDict, config_to_formdict, dict_to_formdict, formdict_to_widgetdict
from .auxiliary import recursive_set_focus, flatten
from .Redirectable import RedirectTextTkinter, Redirectable
from .FormField import FormField
from .Mininterface import BackendAdaptor, Cancelled, EnvClass, Mininterface


class GuiInterface(Redirectable, Mininterface):
    """ When used in the with statement, the GUI window does not vanish between dialogues. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.window = TkWindow(self)
        except TclError:
            # even when installed the libraries are installed, display might not be available, hence tkinter fails
            raise InterfaceNotAvailable
        self._redirected = RedirectTextTkinter(self.window.text_widget, self.window)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self.window.buttons(text, [("Ok", None)])

    def ask(self, text: str) -> str:
        return self.form({text: ""})[text]

    def ask_env(self) -> EnvClass:
        """ Display a window form with all parameters. """
        formDict = config_to_formdict(self.env, self.descriptions)

        # formDict automatically fetches the edited values back to the EnvInstance
        self.window.run_dialog(formDict)
        return self.env

    def form(self, form: FormDict, title: str = "") -> dict:
        """ Prompt the user to fill up whole form.
            :param form: Dict of `{labels: default value}`. The form widget infers from the default value type.
                The dict can be nested, it can contain a subgroup.
                The default value might be `mininterface.FormField` that allows you to add descriptions.
                A checkbox example: {"my label": FormField(True, "my description")}
            :param title: Optional form title.
        """
        self.window.run_dialog(dict_to_formdict(form), title=title)
        return form

    def ask_number(self, text: str) -> int:
        return self.form({text: 0})[text]

    def is_yes(self, text):
        return self.window.yes_no(text, False)

    def is_no(self, text):
        return self.window.yes_no(text, True)


class TkWindow(Tk, BackendAdaptor):
    """ An editing window. """

    def __init__(self, interface: GuiInterface):
        super().__init__()
        self.params = None
        self._result = None
        self._event_bindings = {}
        self.interface = interface
        self.title(interface.title)
        self.bind('<Escape>', lambda _: self._ok(Cancelled))

        self.frame = Frame(self)
        """ dialog frame """

        self.text_widget = Text(self, wrap='word', height=20, width=80)
        self.text_widget.pack_forget()
        self.pending_buffer = []
        """ Text that has been written to the text widget but might not be yet seen by user. Because no mainloop was invoked. """

    @staticmethod
    def widgetize(ff: FormField) -> Value:
        """ Wrap FormField to a textual widget. """
        return Value(ff.val, ff.description)

    def run_dialog(self, formDict: FormDict, title: str = "") -> FormDict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """
        if title:
            label = Label(self.frame, text=title)
            label.pack(pady=10)
        self.form = Form(self.frame,
                        name_form="",
                        form_dict=formdict_to_widgetdict(formDict, self.widgetize),
                        name_config="Ok",
                        )
        self.form.pack()

        # Set the submit and exit options
        self.form.button.config(command=self._ok)
        tip, keysym = ("Enter", "<Return>")
        ToolTip(self.form.button, msg=tip)  # NOTE is not destroyed in _clear
        self._bind_event(keysym, self._ok)
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        recursive_set_focus(self.form)
        return self.mainloop(lambda: self.validate(formDict, title))

    def validate(self, formDict: FormDict, title: str) -> FormDict:
        if not FormField.submit_values(zip(flatten(formDict), flatten(self.form.get()))):
            return self.run_dialog(formDict, title)
        return formDict

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
