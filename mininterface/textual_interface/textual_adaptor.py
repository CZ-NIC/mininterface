from typing import TYPE_CHECKING
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import (
    Rule, Label, RadioButton, Button, Input, Tree, Static
)
from textual import events
from textual.widgets.tree import TreeNode

from .textual_facet import TextualFacet

from ..exceptions import Cancelled
from ..experimental import SubmitButton
from ..facet import BackendAdaptor
from ..form_dict import TagDict
from ..tag import Tag
from ..types import DatetimeTag, PathTag, SecretTag
from .textual_app import TextualApp
from .widgets import (Changeable, MyButton, MyCheckbox, MyInput, MyRadioSet,
                      MySubmitButton, SecretInput)

if TYPE_CHECKING:
    from . import TextualInterface


class FilePickerInput(Horizontal, Changeable):
    """A custom widget that combines an input field with a file picker button."""

    def __init__(self, tag: PathTag, **kwargs):
        super().__init__()
        self._link = tag
        initial_value = ""
        if tag.val is not None:
            if isinstance(tag.val, list):
                initial_value = ", ".join(str(p) for p in tag.val)
            else:
                initial_value = str(tag.val)
        self.input = Input(value=initial_value, **kwargs)
        self.button = Button("Browse", variant="primary", id="file_picker")
        self.browser = None

    def compose(self) -> ComposeResult:
        yield self.input
        yield self.button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "file_picker":
            self.browser.remove()
            self.browser = None

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input == self.input:
            self.trigger_change()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # This is triggered when Enter is pressed in the input
        self.trigger_change()
        if hasattr(self._link, 'facet'):
            self._link.facet.submit()

    def get_ui_value(self):
        if not self.input.value:
            return None
        if self._link.multiple:
            paths = [p.strip() for p in self.input.value.split(',') if p.strip()]
            return paths if paths else None
        return self.input.value.strip() or None


class TextualAdaptor(BackendAdaptor):

    def __init__(self, interface: "TextualInterface"):
        self.interface = interface
        self.facet = interface.facet = TextualFacet(self, interface.env)
        self.app: TextualApp | None = None
        self.layout_elements = []

    @staticmethod
    def widgetize(tag: Tag) -> Widget | Changeable:
        """ Wrap Tag to a textual widget. """

        v = tag._get_ui_val()
        # Handle boolean
        if tag.annotation is bool or not tag.annotation and (v is True or v is False):
            o = MyCheckbox(tag.name or "", v)
        # Replace with radio buttons
        elif tag._get_choices():
            o = MyRadioSet(*(RadioButton(label, value=val == tag.val) for label, val in tag._get_choices().items()))
        elif isinstance(tag, (PathTag, DatetimeTag, SecretTag)):
            match tag:
                case PathTag():
                    o = FilePickerInput(
                        tag, placeholder=tag.name or ""
                    )
                case SecretTag():
                    o = SecretInput(tag, placeholder=tag.name or "", type="text")
                case DatetimeTag():
                    o = MyInput(str(v), placeholder=tag.name or "", type="text")
        # Special type: Submit button
        elif tag.annotation is SubmitButton:
            o = MySubmitButton(tag.name)
        # Replace with a callback button
        elif tag._is_a_callable():
            o = MyButton(tag.name)
        else:
            if not isinstance(v, (float, int, str, bool)):
                v = str(v)
            if tag._is_subclass(int):
                type_ = "integer"
            elif tag._is_subclass(float):
                type_ = "number"
            else:
                type_ = "text"
            o = MyInput(str(v), placeholder=tag.name or "", type=type_)

        o._link = tag
        tag._last_ui_val = o.get_ui_value()
        return o

    def header(self, text: str):
        """ Generates a section header """
        if text:
            return [Rule(), Label(f" === {text} ===")]
        else:
            return []

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        super().run_dialog(form, title, submit)
        # Unfortunately, there seems to be no way to reuse the app.
        # Which blocks using multiple form external .form() calls from the web interface.
        # Textual cannot run in a thread, it seems it cannot run in another process, self.suspend() is of no use.
        self.app = app = TextualApp(self, submit)
        if title:
            app.title = title

        if not app.run():
            raise Cancelled

        # validate and store the UI value → Tag value → original value
        vals = ((field._link, field.get_ui_value()) for field in app.widgets if hasattr(field, "_link"))
        if not Tag._submit_values(vals) or not self.submit_done():
            return self.run_dialog(form, title, submit)

        return form
