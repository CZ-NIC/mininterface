""" Raises InterfaceNotAvailable at module import time if textual not installed or session is non-interactive. """
import sys
from typing import Optional, Type

from ..mininterface.mixin import RichUiMixin

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


class TextualInterface(RichUiMixin, Redirectable, Mininterface):

    _adaptor: TextualAdaptor

    def __init__(self, *args, need_atty=True, **kwargs):
        if need_atty and not sys.stdin.isatty():
            # We cannot have the check at the module level due to WebUI (without atty).
            # Without this check, an erroneous textual instance appears.
            raise InterfaceNotAvailable
        super().__init__(*args, **kwargs)
