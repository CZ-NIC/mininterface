from typing import TYPE_CHECKING
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Input

from ..tag.secret_tag import SecretTag
from .widgets import TagWidgetWithInput

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor


def SecretInputFactory(adaptor: "TextualAdaptor", tag: SecretTag, **kwargs):

    class SecretInput(TagWidgetWithInput, Horizontal):
        """A custom widget that combines an input field with a visibility toggle button."""

        BINDINGS = [Binding(adaptor.settings.toggle_widget, "toggle_visibility", "Toggle visibility")]

        DEFAULT_CSS = """
        SecretInput {
            layout: horizontal;
            height: auto;
            width: 100%;
        }

        SecretInput Input {
            width: 80%;
            margin: 1;
        }

        SecretInput Button {
            width: 20%;
            margin: 1;
            background: $accent;
            color: $text;
        }
        """

        tag: SecretTag

        def __init__(self, tag: SecretTag, **kwargs):
            super().__init__(tag)

            initial_value = tag._get_ui_val()
            self.input = Input(value=initial_value, placeholder=kwargs.get("placeholder", ""), password=tag._masked)
            self.button = Button("👁", variant="primary", id="toggle_visibility")

        def compose(self) -> ComposeResult:
            """Compose the widget layout."""
            yield self.input
            yield self.button

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button press event."""
            if event.button.id == "toggle_visibility":
                self.action_toggle_visibility()

        def action_toggle_visibility(self):
            """Toggle password visibility.

            This action method is called when:
            1. User presses the visibility toggle button
            2. User presses Ctrl+T keyboard shortcut
            """
            is_masked = self.tag.toggle_visibility()
            self.input.password = is_masked
            self.button.label = "🙈" if is_masked else "👁"

        def get_ui_value(self):
            """Get the current value of the input field."""
            return self.input.value

    return SecretInput(tag, **kwargs)
