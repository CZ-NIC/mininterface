import sys
from typing import TYPE_CHECKING, Optional
from textual import events
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioButton, RadioSet, SelectionList


from ..tag.tag import Tag, TagValue


class TagWidget:
    """ Widget that has a tag inside, this can implement on_change method etc. """
    # Since every TagWidget has two parent, continue from the constructor to the other brach via `super`.
    # For an unknown reason, the TagWidget cannot inherit directly from Widget, as
    # `MyInput(TagWidget, Input)` would not work would continue here directly to `Widget`, skipping the `Input`.
    # MRO seems fine but instead of the Input, a mere text is shown.

    tag: Tag
    _arbitrary: Optional[Widget] = None
    """ NOTE: Due to the poor design, we attach ex. hide buttons this way. """

    def __init__(self, tag: Tag, *args, **kwargs):
        self.tag = tag
        super().__init__(*args, **kwargs)

    def trigger_change(self):
        self.tag._on_change_trigger(self.get_ui_value())

    def get_ui_value(self):
        if isinstance(self, Button):  # NOTE: I suspect this is not used as Button already implement get_ui_value
            return None
        else:
            return self.value


class TagWidgetWithInput(TagWidget):
    """Base class for widgets that contain an input element"""

    def __init__(self, tag: Tag, *args, **kwargs):
        super().__init__(tag, *args, **kwargs)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field to submit the form."""
        self.tag._facet.adaptor.app.action_confirm()

    def focus(self):
        """Focus the input element of this widget."""
        self.input.focus()


class MyInput(TagWidget, Input):

    async def on_blur(self):
        return self.trigger_change()


class MyCheckbox(TagWidget, Checkbox):
    def on_checkbox_changed(self):
        return self.trigger_change()


class MyRadioButton(RadioButton):
    def __init__(self, ref_ui,  *args, **kwargs):
        self.ref_ui = ref_ui
        super().__init__(*args, **kwargs)


class MyRadioSet(TagWidget, RadioSet):
    def on_radio_set_changed(self):
        return self.trigger_change()

    def on_key(self, event: events.Key) -> None:
        # if event.key == "down":
        #     return False
        if event.key == "enter":
            # If the radio button is not selected, select it and prevent default
            # (which is form submittion).
            # If it is selected, do nothing, so the form will be submitted.
            if not self._nodes[self._selected].value:
                self.action_toggle_button()
                # NOTE: If it is the only tag, we submit the form. But this should be implemented at the Tag level.
                if len(self.tag._facet._form) > 1 or self.tag is not next(iter(self.tag._facet._form.values())):
                    event.stop()

    def get_ui_value(self):
        if self.pressed_button:
            self.pressed_button: MyRadioButton
            return self.pressed_button.ref_ui
        else:
            return None


class MySelectionList(TagWidget, SelectionList):
    def on_selection_changed(self):
        return self.trigger_change()

    def get_ui_value(self):
        return self.selected


class MyButton(TagWidget, Button):
    _val: TagValue

    def __init__(self, tag, *args, **kwargs):
        super().__init__(tag, tag.label, *args, **kwargs)

    def on_button_pressed(self, event):
        self.tag._facet.submit(_post_submit=self.tag._run_callable)

    def get_ui_value(self):
        return self.tag.val


class MySubmitButton(MyButton):
    def __init__(self, *args, **kwargs):
        self._val = None
        super().__init__(*args, **kwargs)

    def on_button_pressed(self, event):
        event.prevent_default()  # prevent calling the parent MyButton
        self._val = True
        self.tag._facet.submit()

    def get_ui_value(self):
        return self._val  # NOTE use self.value instead?
