from typing import Optional, Any
from textual import events
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioSet
from textual.binding import Binding

from ..types.rich_tags import SecretTag
from ..tag import Tag, TagValue


class Changeable:
    """ Widget that can implement on_change method. """

    _link: Tag
    _arbitrary: Optional[Widget] = None
    """ NOTE: Due to the poor design, we attach ex. hide buttons this way. """

    def trigger_change(self):
        if tag := self._link:
            tag._on_change_trigger(self.get_ui_value())

    def get_ui_value(self):
        if isinstance(self, RadioSet):
            if self.pressed_button:
                return str(self.pressed_button.label)
            else:
                return None
        elif isinstance(self, Button):
            return None
        else:
            return self.value


class BaseInput(Input, Changeable):
    """Base class for all input types."""

    def __init__(self, tag: Tag, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link = tag

        # Initialize the value from tag
        initial_value = ""
        if hasattr(tag, 'val') and tag.val is not None:
            initial_value = self._format_initial_value(tag.val)
        self.value = initial_value

    def _format_initial_value(self, val: Any) -> str:
        """Format the initial value for display in the input field."""
        if isinstance(val, list):
            return ", ".join(str(p) for p in val)
        return str(val)

    def _convert_value(self, value: str):
        """Convert the string value to the appropriate type."""
        if not value:
            return None

        value = value.strip()
        if not value:
            return None

        try:
            # Get the expected type from the tag's annotation
            expected_type = getattr(self._link, 'annotation', str)

            if expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            else:
                return value
        except (ValueError, TypeError):
            return None

    def on_blur(self, event: events.Blur) -> None:
        # Only trigger if we can convert the value successfully
        if self._convert_value(self.value) is not None:
            self.trigger_change()

    def on_input_changed(self, event: Input.Changed) -> None:
        # Only trigger if we can convert the value successfully
        if self._convert_value(self.value) is not None:
            self.trigger_change()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # This is triggered when Enter is pressed
        if self._convert_value(self.value) is not None:
            self.trigger_change()
            if hasattr(self._link, 'facet') and self._link.facet:
                self._link.facet.submit()

    def get_ui_value(self):
        if not self.value:
            return None
        return self._convert_value(self.value)


class MyInput(BaseInput):
    """Standard input for text, numbers, etc."""
    pass


class MyCheckbox(Checkbox, Changeable):
    def __init__(self, label: str, value: bool = False, *args, **kwargs):
        super().__init__(label, value, *args, **kwargs)
        # _link will be set later by the calling function (widgetize)

    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioSet(RadioSet, Changeable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # _link will be set later by the calling function (widgetize)

    def on_radio_set_changed(self):
        return self.trigger_change()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            # If the radio button is not selected, select it and prevent default
            if not self._nodes[self._selected].value:
                event.stop()
                self.action_toggle()


class MyButton(Button, Changeable):
    _val: TagValue

    def __init__(self, label: str, *args, **kwargs):
        super().__init__(label, *args, **kwargs)
        # _link will be set later by the calling function (widgetize)

    def on_button_pressed(self, event):
        self._link.facet.submit(_post_submit=self._link._run_callable)

    def get_ui_value(self):
        return self._link.val


class MySubmitButton(MyButton):
    def on_button_pressed(self, event):
        event.prevent_default()  # prevent calling the parent MyButton
        self._val = True
        self._link.facet.submit()


class SecretInput(BaseInput):
    """A password input widget with toggle functionality."""

    BINDINGS = [Binding("ctrl+t", "toggle_visibility", "Toggle visibility")]

    def __init__(self, tag: SecretTag, *args, **kwargs):
        self.tag = tag
        # Pass the tag directly to the BaseInput constructor
        super().__init__(tag, *args, password=tag._masked, **kwargs)
        self.show_password = not self.password
        if tag.show_toggle:
            self._arbitrary = SecretInputToggle(self, "👁")

    def action_toggle_visibility(self):
        self.password = self.tag.toggle_visibility()


class SecretInputToggle(Button):
    def __init__(self, input: SecretInput, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input = input

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.input.action_toggle_visibility()
        self.label = "🙈" if self.input.show_password else "👁"
