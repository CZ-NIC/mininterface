from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.widgets import Button, Footer, Label

from ..common import Cancelled

if TYPE_CHECKING:
    from . import TextualInterface

@dataclass
class DummyWrapper:
    """ Value wrapped, since I do not know how to get it from textual app.
    False would mean direct exit. """
    val: Any



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

    def __init__(self, interface: "TextualInterface"):
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