from textual.widgets import Button, Checkbox, Input, RadioSet

from ..tag import Tag


class Changeable:
    """ Widget that can implement on_change method. """

    _link: Tag

    def trigger_change(self):
        if tag := self._link:
            tag: Tag
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


class MySubmitButton(Button, Changeable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._val = False

    def on_button_pressed(self):
        self._val = True
        self._link.facet.submit()

    def get_ui_value(self):
        return self._val


class MyInput(Input, Changeable):
    async def on_blur(self):
        return self.trigger_change()


class MyCheckbox(Checkbox, Changeable):
    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioSet(RadioSet, Changeable):
    def on_radio_set_changed(self):
        return self.trigger_change()


class MyButton(Button, Changeable):

    def on_button_pressed(self):
        return self._link.val()
