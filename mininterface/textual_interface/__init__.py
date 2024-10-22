from dataclasses import dataclass
from typing import Any, Type

from mininterface.textual_interface.textual_app import TextualApp
from mininterface.textual_interface.textual_button_app import TextualButtonApp
from mininterface.textual_interface.textual_facet import TextualFacet

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from mininterface.common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..form_dict import DataClass, EnvClass, FormDict
from ..redirectable import Redirectable
from ..tag import Tag
from ..text_interface import TextInterface


class TextualInterface(Redirectable, TextInterface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.facet: TextualFacet = TextualFacet(None, self.env)  # window=None, since no app is running

    def _get_app(self):
        return TextualApp(self)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        TextualButtonApp(self).buttons(text, [("Ok", None)]).run()

    def ask(self, text: str = None):
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = ""
             ) -> FormDict | DataClass | EnvClass:
        def clb(form, title, c=self): return TextualApp.run_dialog(c._get_app(), form, title)
        return self._form(form, title, clb)

    def ask_number(self, text: str):
        return self.form({text: Tag("", "", int, text)})[text]

    def is_yes(self, text: str):
        return TextualButtonApp(self).yes_no(text, False).val

    def is_no(self, text: str):
        return TextualButtonApp(self).yes_no(text, True).val
