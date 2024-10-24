from typing import TYPE_CHECKING

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Rule, Label, RadioButton

from .textual_facet import TextualFacet

from ..auxiliary import flatten
from ..common import Cancelled
from ..experimental import SubmitButton
from ..facet import BackendAdaptor
from ..form_dict import TagDict, formdict_to_widgetdict
from ..tag import Tag
from .textual_app import TextualApp, WidgetList
from .widgets import (Changeable, MyButton, MyCheckbox, MyInput, MyRadioSet,
                      MySubmitButton)

if TYPE_CHECKING:
    from . import TextualInterface


class TextualAdaptor(BackendAdaptor):

    def __init__(self, interface: "TextualInterface"):
        self.interface = interface
        self.facet = interface.facet = TextualFacet(self, interface.env)

    @staticmethod
    def widgetize(tag: Tag) -> Widget | Changeable:
        """ Wrap Tag to a textual widget. """

        v = tag._get_ui_val()
        # Handle boolean
        if tag.annotation is bool or not tag.annotation and (v is True or v is False):
            o = MyCheckbox(tag.name or "", v)
        # Replace with radio buttons
        elif tag._get_choices():
            o = MyRadioSet(*(RadioButton(label, value=val == tag.val)
                             for label, val in tag._get_choices().items()))
        # Special type: Submit button
        elif tag.annotation is SubmitButton:  # NOTE EXPERIMENTAL
            o = MySubmitButton(tag.name)

        # Replace with a callback button
        elif tag._is_a_callable():
            o = MyButton(tag.name)

        else:
            if not isinstance(v, (float, int, str, bool)):
                v = str(v)
            if issubclass(tag.annotation, int):
                type_ = "integer"
            elif issubclass(tag.annotation, float):
                type_ = "number"
            else:
                type_ = "text"
            o = MyInput(str(v), placeholder=tag.name or "", type=type_)

        o._link = tag  # The Textual widgets need to get back to this value
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
        self.app = app = TextualApp(self, submit)
        if title:
            app.title = title

        widgets: WidgetList = [f for f in flatten(formdict_to_widgetdict(
            form, self.widgetize), include_keys=self.header)]
        if len(widgets) and isinstance(widgets[0], Rule):
            # there are multiple sections in the list, <hr>ed by Rule elements. However, the first takes much space.
            widgets.pop(0)
        app.widgets = widgets

        if not app.run():
            raise Cancelled

        # validate and store the UI value → Tag value → original value
        if not Tag._submit_values((field._link, field.get_ui_value()) for field in widgets if hasattr(field, "_link")):
            return self.run_dialog(form, title, submit)
        self.submit_done()
        return form
