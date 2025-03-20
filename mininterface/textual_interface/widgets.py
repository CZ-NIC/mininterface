from typing import Optional
from textual import events
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioSet
from textual.binding import Binding

from ..types.rich_tags import SecretTag, PathTag
from ..tag import Tag, TagValue
from pathlib import Path


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


class MyInput(Input, Changeable):
    def __init__(self, value_or_tag, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Handle both cases: when called with a Tag object or with a direct value
        if isinstance(value_or_tag, Tag):
            # Case 1: Called with a Tag object
            tag = value_or_tag
            self._link = tag
            initial_value = ""
            if hasattr(tag, 'val') and tag.val is not None:
                if isinstance(tag.val, list):
                    initial_value = ", ".join(str(p) for p in tag.val)
                else:
                    initial_value = str(tag.val)
            self.value = initial_value
        else:
            # Case 2: Called with a direct value (str, int, etc.)
            self.value = str(value_or_tag)
            # The _link will be set later by the calling function (widgetize)

    def _convert_value(self, value: str):
        """Convert the string value to the appropriate type."""
        if not value:
            return None

        value = value.strip()
        if not value:
            return None

        # If _link isn't set yet, return the value as is
        if not hasattr(self, '_link'):
            return value

        # Special handling for PathTag
        if isinstance(self._link, PathTag):
            try:
                if getattr(self._link, 'multiple', False):
                    paths = [p.strip() for p in value.split(',') if p.strip()]
                    if not paths:
                        return None
                    # Make sure all paths exist with Path objects
                    return [Path(p) for p in paths]
                # Single path case
                return Path(value)
            except Exception:  # noqa
                # Always return the original string value for PathTag if conversion fails
                # This prevents "Type must be str" error
                if getattr(self._link, 'multiple', False):
                    return [value.strip()] if value.strip() else None
                return value

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
            if hasattr(self._link, 'facet'):
                self._link.facet.submit()

    def get_ui_value(self):
        if not self.value:
            return None
        return self._convert_value(self.value)


class MyCheckbox(Checkbox, Changeable):
    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioSet(RadioSet, Changeable):
    def on_radio_set_changed(self):
        return self.trigger_change()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            if not self._nodes[self._selected].value:
                event.stop()
                self.action_toggle()


class MyButton(Button, Changeable):
    _val: TagValue

    def on_button_pressed(self, event):
        self._link.facet.submit(_post_submit=self._link._run_callable)

    def get_ui_value(self):
        return self._link.val


class MySubmitButton(MyButton):
    def on_button_pressed(self, event):
        event.prevent_default()  # prevent calling the parent MyButton
        self._val = True
        self._link.facet.submit()


class SecretInput(MyInput):
    """A password input widget with toggle functionality."""

    BINDINGS = [Binding("ctrl+t", "toggle_visibility", "Toggle visibility")]

    def __init__(self, tag: SecretTag, *args, **kwargs):
        self.tag = tag
        super().__init__(tag._get_ui_val(), *args, password=tag._masked, **kwargs)
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
