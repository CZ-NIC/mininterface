""" Raises InterfaceNotAvailable at module import time if textual not installed or session is non-interactive. """
import sys
from typing import Type

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from ..exceptions import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..exceptions import InterfaceNotAvailable
from ..form_dict import DataClass, EnvClass, FormDict
from ..redirectable import Redirectable
from ..tag import Tag
from ..mininterface import Mininterface
from .textual_adaptor import TextualAdaptor
from .textual_button_app import TextualButtonApp

if not sys.stdin.isatty():
    raise InterfaceNotAvailable


class TextualInterface(Redirectable, Mininterface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptor = TextualAdaptor(self)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp(self).buttons(text, [("Ok", None)])

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
