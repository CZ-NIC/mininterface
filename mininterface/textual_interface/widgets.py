from typing import Optional
from textual import events
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioSet

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
    # NOTE the password can be probably copied out from the terminal, it is hidden just by CSS
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_password = False
        self.update_class()

        self._arbitrary = SecretInputToggle(self, "👁")

    def update_class(self):
        self.classes = "shown" if self.show_password else "hidden"

    def toggle_password(self):
        self.show_password = not self.show_password
        self.update_class()


class SecretInputToggle(Button):
    def __init__(self, input: SecretInput, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input = input

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.input.toggle_password()
        self.label = "🙈" if self.input.show_password else "👁"
