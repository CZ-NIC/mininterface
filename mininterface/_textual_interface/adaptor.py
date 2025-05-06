from typing import TYPE_CHECKING, Any
from textual.widget import Widget
from textual.widgets import Label, Rule

from ..tag.path_tag import PathTag

from ..tag.select_tag import SelectTag

from .button_contents import ButtonAppType

from .secret_input import SecretInputFactory

from ..exceptions import Cancelled
from .._lib.form_dict import TagDict
from .._mininterface.adaptor import BackendAdaptor
from ..settings import TextualSettings
from ..tag.tag import Tag, ValsType
from ..tag.secret_tag import SecretTag
from ..tag.internal import (BoolWidget, CallbackButtonWidget,
                            SubmitButtonWidget)
from .facet import TextualFacet
from .file_picker_input import FilePickerInputFactory
from .textual_app import TextualApp
from .widgets import (TagWidget, MyButton, MyCheckbox, MyInput, MyRadioSet, MyRadioButton, MySelectionList,
                      MySubmitButton)

if TYPE_CHECKING:
    from . import TextualInterface


class TextualAdaptor(BackendAdaptor):

    facet: TextualFacet
    settings: TextualSettings
    interface: "TextualInterface"

    def __init__(self, *args):
        super().__init__(*args)

        self.app: TextualApp | None = None
        self.layout_elements = []
        self.button_app: ButtonAppType = False

    def widgetize(self, tag: Tag) -> Widget | TagWidget:
        """ Wrap Tag to a textual widget. """

        v = tag._get_ui_val()

        match tag:
            # NOTE: DatetimeTag not implemented
            case SelectTag():
                if tag.multiple:
                    selected = set(tag.val)
                    o = MySelectionList(tag, *((label, val, val in selected)
                                        for label, val, *_ in tag._get_options()))
                else:
                    radio_buttons = [MyRadioButton(val, label, value=val == tag.val, classes="enum-highlight" if tip else None)
                                     for label, val, tip, _ in tag._get_options(" | ")]
                    o = MyRadioSet(tag, *radio_buttons)
            case PathTag():
                o = FilePickerInputFactory(self, tag, placeholder=tag.label or "")
            case SecretTag():
                o = SecretInputFactory(self, tag, placeholder=tag.label or "", type="text")
            case _:
                match tag._recommend_widget():
                    case BoolWidget():
                        o = MyCheckbox(tag, tag.label or "", v)
                    case SubmitButtonWidget():
                        # Special type: Submit button
                        # NOTE EXPERIMENTAL
                        o = MySubmitButton(tag)
                    case CallbackButtonWidget():
                        o = MyButton(tag)
                    case _:
                        if not isinstance(v, (float, int, str)):
                            v = str(v)
                        if tag._is_subclass(int):
                            type_ = "integer"
                        elif tag._is_subclass(float):
                            type_ = "number"
                        else:
                            type_ = "text"
                        o = MyInput(tag, str(v), placeholder=tag.label or "", type=type_)

        tag._last_ui_val = o.get_ui_value()
        return o

    def header(self, text: str):
        """ Generates a section header """
        if text:
            return [Rule(), Label(f" === {text} ===")]
        else:
            return []

    def yes_no(self, text: str, focus_no=True):
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no)+1)

    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        self._build_buttons(text, buttons, focused)
        self.app = app = TextualApp(self, False)
        if not app.run():
            raise Cancelled
        return self._get_buttons_val()

    def _build_buttons(self, text, buttons, focused):
        self.button_app = (text,
                           [(MySubmitButton(Tag(value, _facet=self.facet, label=label)), i == focused-1)
                               for i, (label, value) in enumerate(buttons)])

    def _get_buttons_val(self):
        for button, _ in self.button_app[1]:
            if button.get_ui_value():
                return button.tag.val
        raise Cancelled

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        self.button_app: ButtonAppType = False
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
        vals = self._serialize_vals(app)

        if not self._try_submit(vals):
            return self.run_dialog(form, title, submit)

        return form

    def _serialize_vals(self, app: TextualApp) -> ValsType:
        return ((field.tag, field.get_ui_value()) for field in app.widgets if isinstance(field, TagWidget))
