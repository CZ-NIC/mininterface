from dataclasses import dataclass
from typing import Any

from mininterface.textual_interface.textual_button_app import TextualButtonApp
from mininterface.textual_interface.textual_app import TextualApp
from mininterface.textual_interface.textual_facet import TextualFacet

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from mininterface.common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..form_dict import (EnvClass, FormDictOrEnv, dataclass_to_tagdict, dict_to_tagdict, formdict_resolve)
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

    def _ask_env(self) -> EnvClass:
        """ Display a window form with all parameters. """
        form = dataclass_to_tagdict(self.env, self.facet)

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        return TextualApp.run_dialog(self._get_app(), form)

    # NOTE: This works bad with lists. GuiInterface considers list as combobox (which is now suppressed by str conversion),
    # TextualInterface as str. We should decide what should happen.
    def form(self, form: FormDictOrEnv | None = None, title: str = "") -> FormDictOrEnv | EnvClass:
        if form is None:
            return self._ask_env()  # NOTE should be integrated here when we integrate dataclass, see FormDictOrEnv
        else:
            return formdict_resolve(TextualApp.run_dialog(self._get_app(), dict_to_tagdict(form, self.facet), title), extract_main=True)

    # NOTE we should implement better, now the user does not know it needs an int
    def ask_number(self, text: str):
        return self.form({text: Tag("", "", int, text)})[text].val

    def is_yes(self, text: str):
        return TextualButtonApp(self).yes_no(text, False).val

    def is_no(self, text: str):
        return TextualButtonApp(self).yes_no(text, True).val
