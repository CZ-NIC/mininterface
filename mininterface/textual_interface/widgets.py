from typing import TYPE_CHECKING, Optional
from textual import events
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioSet


from ..tag import Tag, TagValue


class Changeable:
    """ Widget that can implement on_change method. """

    tag: Tag
    _arbitrary: Optional[Widget] = None
    """ NOTE: Due to the poor design, we attach ex. hide buttons this way. """

    def __init__(self, tag: Tag, *args, **kwargs):
        self.tag = tag
        super().__init__(*args, **kwargs)

    def trigger_change(self):
        if tag := self.tag:
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


class ChangeableWithInput(Changeable):
    """Base class for widgets that contain an input element"""

    def __init__(self, tag: Tag, *args, **kwargs):
        super().__init__(tag, *args, **kwargs)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field to submit the form."""
        self.tag.facet.adaptor.app.action_confirm()

    def focus(self):
        """Focus the input element of this widget."""
        self.input.focus()


class MyInput(Changeable, Input):

    async def on_blur(self):
        return self.trigger_change()


class MyCheckbox(Changeable, Checkbox):
    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioSet(Changeable, RadioSet):
    def on_radio_set_changed(self):
        return self.trigger_change()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            # If the radio button is not selected, select it and prevent default
            # (which is form submittion).
            # If it is selected, do nothing, so the form will be submitted.
            if not self._nodes[self._selected].value:
                event.stop()
                self.action_toggle_button()


class MyButton(Changeable, Button):
    _val: TagValue

    def on_button_pressed(self, event):
        self.tag.facet.submit(_post_submit=self.tag._run_callable)

    def get_ui_value(self):
        return self.tag.val


class MySubmitButton(MyButton):

    def on_button_pressed(self, event):
        event.prevent_default()  # prevent calling the parent MyButton
        self._val = True
        self.tag.facet.submit()
