""" Raises InterfaceNotAvailable at module import time if textual not installed or session is non-interactive. """
import sys
from typing import Optional, Type

from ..mininterface.mixin import ButtonMixin

from ..settings import TextualSettings

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
from .adaptor import TextualAdaptor
from .button_contents import ButtonContents


class TextualInterface(ButtonMixin, Redirectable, Mininterface):

    _adaptor: TextualAdaptor

    def __init__(self, *args, need_atty=True, **kwargs):
        if need_atty and not sys.stdin.isatty():
            # TODO
            # We cannot have the check at the module level due to WebUI (without atty).
            # Without this check, an erroneous textual instance appears.
            # With the, a TextInterface run – arrows work, not text.
            # Investigate, whether we can grasp text input with TextInterface when piping stdin.
            # We should do it as ipdb did that (as it is mentioned in Interfaces.md).
            # Then, put into Interfaces.md
            # interactive terminal -> TextualInterface
            # non-interactive -> TextInterface
            # non-terminal (cron) -> Mininterface
            raise InterfaceNotAvailable
        super().__init__(*args, **kwargs)

    def ask(self, text: str = None):
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True,
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self._adaptor, submit=submit)

    def ask_number(self, text: str):
        return self.form({text: Tag("", "", int, text)})[text]
