from dataclasses import dataclass
from typing import Any

try:
    from textual import events
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import VerticalScroll
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, RadioSet, RadioButton
except ImportError:
    from mininterface.common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from .auxiliary import flatten
from .facet import BackendAdaptor, Facet, MinFacet
from .form_dict import (EnvClass, FormDict, FormDictOrEnv, TagDict,
                        dataclass_to_tagdict, dict_to_tagdict, formdict_resolve,
                        formdict_to_widgetdict)
from .mininterface import Cancelled
from .redirectable import Redirectable
from .tag import Tag
from .text_interface import TextInterface


@dataclass
class DummyWrapper:
    """ Value wrapped, since I do not know how to get it from textual app.
    False would mean direct exit. """
    val: Any


class TextualInterface(Redirectable, TextInterface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.facet: TextualAppFacet = TextualAppFacet(self)  # since no app is running

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp(self).buttons(text, [("Ok", None)]).run()

    def ask(self, text: str = None):
        return self.form({text: ""})[text]

    def _ask_env(self) -> EnvClass:
        """ Display a window form with all parameters. """
        params_ = dataclass_to_tagdict(self.env, self._descriptions)

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        return TextualApp.run_dialog(TextualApp(self), params_)

    # NOTE: This works bad with lists. GuiInterface considers list as combobox (which is now suppressed by str conversion),
    # TextualInterface as str. We should decide what should happen.
    def form(self, form: FormDictOrEnv | None = None, title: str = "") -> FormDictOrEnv | EnvClass:
        if form is None:
            return self._ask_env()  # NOTE should be integrated here when we integrate dataclass, see FormDictOrEnv
        else:
            return formdict_resolve(TextualApp.run_dialog(TextualApp(self), dict_to_tagdict(form, self.facet), title), extract_main=True)

    # NOTE we should implement better, now the user does not know it needs an int
    def ask_number(self, text: str):
        return self.form({text: Tag("", "", int, text)})[text].val

    def is_yes(self, text: str):
        return TextualButtonApp(self).yes_no(text, False).val

    def is_no(self, text: str):
        return TextualButtonApp(self).yes_no(text, True).val


# NOTE: For a metaclass conflict I was not able to inherit from BackendAdaptor
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

    def __init__(self, interface: TextualInterface):
        super().__init__()
        self.facet = interface.facet
        self.title = self.facet._title
        self.widgets = None
        self.focused_i: int = 0
        self.interface = interface

    @staticmethod
    def widgetize(tag: Tag) -> Checkbox | Input:
        """ Wrap Tag to a textual widget. """
        v = tag._get_ui_val()
        if tag.annotation is bool or not tag.annotation and (v is True or v is False):
            o = Checkbox(tag.name or "", v)
        elif tag._get_choices():
            o = RadioSet(*(RadioButton(label, value=val == tag.val) for label, val in tag.choices.items()))
        else:
            if not isinstance(v, (float, int, str, bool)):
                v = str(v)
            o = Input(str(v), placeholder=tag.name or "")
        o._link = tag  # The Textual widgets need to get back to this value
        return o

    # Why class method? I do not know how to re-create the dialog if needed.
    @classmethod
    def run_dialog(cls, window: "TextualApp", form: TagDict, title: str = "") -> TagDict:
        if title:
            window.title = title

        # NOTE Sections (~ nested dicts) are not implemented, they flatten.
        # Maybe just 'flatten' might be removed.
        widgets: list[Checkbox | Input] = [f for f in flatten(formdict_to_widgetdict(form, cls.widgetize))]
        window.widgets = widgets

        if not window.run():
            raise Cancelled

        # validate and store the UI value → Tag value → original value
        candidates = ((
            field._link,
            str(field.pressed_button.label) if isinstance(field, RadioSet) else field.value
        ) for field in widgets)
        if not Tag._submit_values(candidates):
            return cls.run_dialog(TextualApp(window.interface), form, title)
        return form

    def compose(self) -> ComposeResult:
        if self.title:
            yield Header()
        yield Footer()
        if text := self.interface._redirected.join():
            yield Label(text, id="buffered_text")
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
    """ A helper TextualApp, just for static dialogs, does not inherit from BackendAdaptor and thus has not Facet. """

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 2;
        padding: 2;
    }
    #buffered_text {
        width: 100%;
        height: 100%;
        column-span: 2;
        # content-align: center bottom;
        text-style: bold;
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

    def __init__(self, interface: TextualInterface):
        super().__init__()
        self.title = ""
        self.text: str = ""
        self._buttons = None
        self.focused_i: int = 0
        self.values = {}
        self.interface = interface

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
        if text := self.interface._redirected.join():
            yield Label(text, id="buffered_text")
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


class TextualAppFacet(Facet):
    def __init__(self, window: TextualApp):
        self.window = window
        # Since TextualApp turns off, we need to have its values stored somewhere
        self._title = ""

    def set_title(self, title: str):
        self._title = title
