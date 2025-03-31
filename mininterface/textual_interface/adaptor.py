from textual.widget import Widget
from textual.widgets import Label, RadioButton, Rule

from ..exceptions import Cancelled
from ..form_dict import TagDict
from ..mininterface.adaptor import BackendAdaptor
from ..options import TextualOptions
from ..tag import Tag
from ..types import PathTag, SecretTag, EnumTag
from ..types.internal import (BoolWidget, CallbackButtonWidget,                               SubmitButtonWidget)
from .facet import TextualFacet
from .file_picker_input import FilePickerInput
from .textual_app import TextualApp
from .widgets import (Changeable, MyButton, MyCheckbox, MyInput, MyRadioSet,
                      MySecretInput, MySubmitButton)


class TextualAdaptor(BackendAdaptor):

    facet: TextualFacet
    options: TextualOptions

    def __init__(self, *args):
        super().__init__(*args)

        self.app: TextualApp | None = None
        self.layout_elements = []

    def widgetize(self, tag: Tag) -> Widget | Changeable:
        """ Wrap Tag to a textual widget. """

        v = tag._get_ui_val()
        w = tag._recommend_widget()

        match w:
            # NOTE: DatetimeTag not implemented
            case BoolWidget():
                o = MyCheckbox(tag, tag.name or "", v)
            case EnumTag():
                radio_buttons = [RadioButton(label, value=val == tag.val)
                                 for label, val in tag._get_choices().items()]
                o = MyRadioSet(tag, *radio_buttons)
            case PathTag():
                o = FilePickerInput(tag, placeholder=tag.name or "")
            case SecretTag():
                o = MySecretInput(tag, placeholder=tag.name or "", type="text")
            case SubmitButtonWidget():
                # Special type: Submit button
                # NOTE EXPERIMENTAL
                o = MySubmitButton(tag, tag.name)
            case CallbackButtonWidget():
                o = MyButton(tag, tag.name)
            case _:
                if not isinstance(v, (float, int, str)):
                    v = str(v)
                if tag._is_subclass(int):
                    type_ = "integer"
                elif tag._is_subclass(float):
                    type_ = "number"
                else:
                    type_ = "text"
                o = MyInput(tag, str(v), placeholder=tag.name or "", type=type_)

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
        vals = ((field.tag, field.get_ui_value()) for field in app.widgets if hasattr(field, "tag"))
        if not Tag._submit_values(vals) or not self.submit_done():
            return self.run_dialog(form, title, submit)

        return form
