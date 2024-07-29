from ast import literal_eval
from dataclasses import dataclass
from typing import Any

try:
    from textual import events
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import VerticalScroll
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label
except ImportError:
    from mininterface.common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from .TextInterface import TextInterface

from .auxiliary import flatten
from .FormDict import (ConfigInstance, FormDict, config_to_formdict,
                       dict_to_formdict)
from .FormField import FormField
from .Mininterface import Cancelled

# TODO with statement hello world example image is wrong – Textual still does not redirect the output as GuiInterface does

@dataclass
class DummyWrapper:
    """ Value wrapped, since I do not know how to get it from textual app.
    False would mean direct exit. """
    val: Any


class TextualInterface(TextInterface):

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp().buttons(text, [("Ok", None)]).run()

    def ask(self, text: str = None):
        return self.form({text: ""})[text]

    def ask_args(self) -> ConfigInstance:
        """ Display a window form with all parameters. """
        params_ = config_to_formdict(self.args, self.descriptions)

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        TextualApp.run_dialog(TextualApp(), params_)
        return self.args

    def form(self, form: FormDict, title: str = "") -> dict:
        return TextualApp.run_dialog(TextualApp(), dict_to_formdict(form), title)

    # NOTE we should implement better, now the user does not know it needs an int
    # def ask_number(self, text):

    def is_yes(self, text):
        return TextualButtonApp().yes_no(text, False).val

    def is_no(self, text):
        return TextualButtonApp().yes_no(text, True).val


class TextualApp(App[bool | None]):

    BINDINGS = [
        ("up", "go_up", "Go up"),
        ("down", "go_up", "Go down"),
        # Form confirmation
        # * ctrl/alt+enter does not work
        # * enter without priority is consumed by input fields
        # * enter with priority is not shown in the footer
        Binding("enter", "confirm", "Ok", show=True, priority=True),
        Binding("Enter", "confirm", "Ok"),
        ("escape", "exit", "Cancel"),
    ]

    def __init__(self):
        super().__init__()
        self.title = ""
        self.widgets = None
        self.focused_i: int = 0

    @staticmethod
    def get_widget(ff:FormField) -> Checkbox | Input:
        """ Wrap FormField to a textual widget. """

        if ff.annotation is bool or not ff.annotation and ff.val in [True, False]:
            o = Checkbox(ff.name, ff.val)
        else:
            o = Input(str(ff.val), placeholder=ff.name or "")
        o._link = ff  # The Textual widgets need to get back to this value
        return o

    # Why class method? I do not know how to re-create the dialog if needed.
    @classmethod
    def run_dialog(cls, window: "TextualApp", formDict: FormDict, title: str = "") -> FormDict:
        if title:
            window.title = title

        # NOTE Sections (~ nested dicts) are not implemented, they flatten
        widgets: list[Checkbox | Input] = [cls.get_widget(f) for f in flatten(formDict)]
        window.widgets = widgets

        if not window.run():
            raise Cancelled

        # validate and store the UI value → FormField value → original value
        if not FormField.submit_values((field._link, field.value) for field in widgets):
            return cls.run_dialog(TextualApp(), formDict, title)
        return formDict

    def compose(self) -> ComposeResult:
        if self.title:
            yield Header()
        yield Footer()
        with VerticalScroll():
            for fieldt in self.widgets:
                if isinstance(fieldt, Input):
                    yield Label(fieldt.placeholder)
                yield fieldt
                yield Label(fieldt._link.description)
                yield Label("")

    def on_mount(self):
        self.widgets[self.focused_i].focus()

    def action_confirm(self):
        # next time, start on the same widget
        # NOTE the functionality is probably not used
        self.focused_i = next((i for i, inp in enumerate(self.widgets) if inp == self.focused), None)
        self.exit(True)

    def action_exit(self):
        self.exit()

    def on_key(self, event: events.Key) -> None:
        try:
            index = self.widgets.index(self.focused)
        except ValueError:  # probably some other element were focused
            return
        match event.key:
            case "down":
                self.widgets[(index + 1) % len(self.widgets)].focus()
            case "up":
                self.widgets[(index - 1) % len(self.widgets)].focus()
            case letter if len(letter) == 1:  # navigate by letters
                for inp_ in self.widgets[index+1:] + self.widgets[:index]:
                    label = inp_.label if isinstance(inp_, Checkbox) else inp_.placeholder
                    if str(label).casefold().startswith(letter):
                        inp_.focus()
                        break


class TextualButtonApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 2;
        padding: 2;
    }
    #question {
        width: 100%;
        height: 100%;
        column-span: 2;
        content-align: center bottom;
        text-style: bold;
    }

    Button {
        width: 100%;
    }
    """

    BINDINGS = [
        ("escape", "exit", "Cancel"),
    ]

    def __init__(self):
        super().__init__()
        self.title = ""
        self.text: str = ""
        self._buttons = None
        self.focused_i: int = 0
        self.values = {}

    def yes_no(self, text: str, focus_no=True) -> DummyWrapper:
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no))

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 0):
        self.text = text
        self._buttons = buttons
        self.focused_i = focused

        ret = self.run()
        if not ret:
            raise Cancelled
        return ret

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Label(self.text, id="question")

        self.values.clear()
        for i, (text, value) in enumerate(self._buttons):
            id_ = "button"+str(i)
            self.values[id_] = value
            b = Button(text, id=id_)
            if i == self.focused_i:
                b.focus()
            yield b

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(DummyWrapper(self.values[event.button.id]))

    def action_exit(self):
        self.exit()
