from typing import Any, Type

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from ..common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..form_dict import DataClass, EnvClass, FormDict
from ..redirectable import Redirectable
from ..tag import Tag
from ..text_interface import TextInterface
from .textual_adaptor import TextualAdaptor
from .textual_button_app import TextualButtonApp
from .textual_facet import TextualFacet


class TextualInterface(Redirectable, TextInterface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptor = TextualAdaptor(self)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp(self).buttons(text, [("Ok", None)]).run()

    def ask(self, text: str = None):
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True,
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self.adaptor, submit=submit)

    def ask_number(self, text: str):
        return self.form({text: Tag("", "", int, text)})[text]

    def is_yes(self, text: str):
        return TextualButtonApp(self).yes_no(text, False).val

    def is_no(self, text: str):
        return TextualButtonApp(self).yes_no(text, True).val
