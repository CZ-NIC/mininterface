from typing import TYPE_CHECKING, Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Container
from textual.widgets import Footer, Label


from .widgets import MySubmitButton


if TYPE_CHECKING:
    from . import TextualAdaptor


ButtonAppType = bool | tuple[str, list[tuple[MySubmitButton, bool]]]


class ButtonContents(Center):
    """A helper TextualApp, just for static dialogs, does not inherit from BackendAdaptor and thus has not Facet."""

    def __init__(self, adaptor: "TextualAdaptor", buttons: ButtonAppType, show_footer: bool = True):
        super().__init__()
        # this has to be a class and not an ID
        # as WebInterface would not create second button form
        # – an empty screen would appear.
        self.classes = "button-app"
        self.adaptor = adaptor
        self.text, self._buttons = buttons
        self.to_focus: Optional[MySubmitButton] = None
        self.show_footer = show_footer
        """ False when the host app provides its own screen-docked Footer. """

    def compose(self) -> ComposeResult:
        if self.show_footer:
            yield Footer()
        yield from self.adaptor.layout_elements
        yield (Label(self.text, id="question", markup=False))
        with Container(id="button-container"):
            for button, focused in self._buttons:
                if focused:
                    self.to_focus = button
                yield button

    def on_mount(self):
        if b := self.to_focus:
            b.focus()

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case "right":
                self.move_focus(1)
            case "left":
                self.move_focus(-1)
            case "n":
                for button, _ in self._buttons:
                    if button.tag.label == "No":
                        button.press()
            case "y":
                for button, _ in self._buttons:
                    if button.tag.label == "Yes":
                        button.press()

    def move_focus(self, direction: int) -> None:
        focused = self.app.focused
        focusable = list(self.query("Button").results())
        if focused in focusable:
            index = focusable.index(focused) + direction
            index %= len(focusable)
        else:
            index = 0
        focusable[index].focus()
