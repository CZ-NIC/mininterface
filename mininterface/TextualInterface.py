from ast import literal_eval
from dataclasses import _MISSING_TYPE, dataclass, field
from types import UnionType
from typing import Any
from dataclasses import fields
from textual import events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container
from textual.widgets import Checkbox, Header, Footer, Input, Label, Welcome, Button, Static
from textual.binding import Binding

from mininterface import TuiInterface
from .common import InterfaceNotAvailable

from .Mininterface import Cancelled, Mininterface
from .auxiliary import ConfigInstance, FormDict, FormField, config_from_dict, config_to_formdict, dict_to_formdict, flatten

from textual.widgets import Checkbox, Input

# TODO
# 1. TuiInterface -> TextInterface.
# 1. TextualInterface inherits from TextInterface.
# 2. TextualInterface is the default for TuiInterface
# Add to docs

@dataclass
class FormFieldTextual(FormField):
    """ Bridge between the values given in CLI, TUI and real needed values (str to int conversion etc). """

    def get_widget(self):
        if self.annotation is bool or not self.annotation and self.val in [True, False]:
            o = Checkbox(self.name, self.val)
        else:
            o = Input(str(self.val), placeholder=self.name or "")
        o._link = self  # The Textual widgets need to get back to this value
        return o


@dataclass
class DummyWrapper:
    """ Value wrapped, since I do not know how to get it from textual app.
    False would mean direct exit. """
    val: Any


class TextualInterface(TuiInterface):

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp().buttons(text, [("Ok", None)]).run()

    def ask(self, text: str = None):
        return self.ask_form({text: ""})[text]

    def ask_args(self) -> ConfigInstance:
        """ Display a window form with all parameters. """
        params_ = config_to_formdict(self.args, self.descriptions, factory=FormFieldTextual)

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        TextualApp.run_dialog(TextualApp(), params_)
        return self.args

    def ask_form(self, form: FormDict, title: str = "") -> dict:
        TextualApp.run_dialog(TextualApp(), dict_to_formdict(form, factory=FormFieldTextual), title)
        return form

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

    def setup(self, title, widgets, focused_i):

        self.focused_i = focused_i
        return self

    # Why class method? I do not know how to re-create the dialog if needed.
    @classmethod
    def run_dialog(cls, window, formDict: FormDict, title: str = "") -> None:  # TODO changed from dict, change everywhere
        if title:
            window.title = title

        # NOTE Sections (~ nested dicts) are not implemented, they flatten
        fd: dict[str, FormFieldTextual] = formDict
        widgets: list[Checkbox | Input] = [f.get_widget() for f in flatten(fd)]
        window.widgets = widgets

        if not window.run():
            raise Cancelled

        # validate and store the UI value → FormField value → original value
        if not all(field._link.update(field.value) for field in widgets):
            return cls.run_dialog(TextualApp(), formDict, title)

    def compose(self) -> ComposeResult:
        if self.title:
            yield Header()
        yield Footer()
        with VerticalScroll():
            for fieldt in self.widgets:
                fieldt: FormFieldTextual
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
