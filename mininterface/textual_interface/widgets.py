from typing import Optional
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


class MyInput(Input, Changeable):
    async def on_blur(self):
        return self.trigger_change()


class MyCheckbox(Checkbox, Changeable):
    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioSet(RadioSet, Changeable):
    def on_radio_set_changed(self):
        return self.trigger_change()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            # If the radio button is not selected, select it and prevent default
            # (which is form submittion).
            # If it is selected, do nothing, so the form will be submitted.
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

    BINDINGS = [Binding("ctrl+h", "toggle_visibility", "Toggle visibility")]

    def __init__(self, tag: SecretTag, *args, **kwargs):
        self.tag = tag
        super().__init__(tag._get_ui_val(), *args, password=tag._masked, **kwargs)
        self.show_password = not self.password  # False
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
