from typing import TYPE_CHECKING
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import (Checkbox, Footer, Header, Input, Label,
                             RadioButton, Static)


from .widgets import (Changeable, MyButton, MyCheckbox, MyInput, MyRadioSet,
                      MySubmitButton)

from ..facet import BackendAdaptor

if TYPE_CHECKING:
    from . import TextualInterface
    from .textual_adaptor import TextualAdaptor

WidgetList = list[Widget | Changeable]


class TextualApp(App[bool | None]):
    BINDINGS = [
        ("up", "go_up", "Go up"),
        ("down", "go_up", "Go down"),
        # Form confirmation
        # * ctrl/alt+enter does not work
        # * enter with priority is not shown in the footer:
        #       Binding("enter", "confirm", "Ok", show=True, priority=True),
        # * enter without priority is consumed by input fields (and recaught by on_key)
        Binding("Enter", "confirm", "Ok"),
        ("escape", "exit", "Cancel"),
    ]

    def __init__(self, adaptor: "TextualAdaptor"):
        super().__init__()
        self.title = adaptor.facet._title
        self.widgets: WidgetList = []
        self.focused_i: int = 0
        self.adaptor = adaptor
        self.output = Static("")

    def compose(self) -> ComposeResult:
        if self.title:
            yield Header()
        yield self.output  # NOTE not used
        yield Footer()
        if text := self.adaptor.interface._redirected.join():
            yield Label(text, id="buffered_text")
        focus_set = False
        with VerticalScroll():
            for i, fieldt in enumerate(self.widgets):
                if isinstance(fieldt, Input):
                    yield Label(fieldt.placeholder)
                yield fieldt
                if isinstance(fieldt, Changeable) and fieldt._link.description:
                    if not focus_set:
                        focus_set = True
                        self.focused_i = i
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
            case "enter":
                # NOTE a multiline input might be
                # isinstance(self.focused,
                self.action_confirm()
            case letter if len(letter) == 1:  # navigate by letters
                for inp_ in self.widgets[index+1:] + self.widgets[:index]:
                    label = inp_.label if isinstance(inp_, Checkbox) else inp_.placeholder
                    if str(label).casefold().startswith(letter):
                        inp_.focus()
                        break
