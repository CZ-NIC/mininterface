"""Raises InterfaceNotAvailable at module import time if textual not installed or session is non-interactive."""

import sys

from .._mininterface.mixin import RichUiMixin

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from ..exceptions import InterfaceNotAvailable

    raise InterfaceNotAvailable

from ..exceptions import InterfaceNotAvailable
from .._lib.redirectable import Redirectable
from .._mininterface import Mininterface
from .adaptor import TextualAdaptor
from .subprocess_adaptor import TextualSubprocessAdaptor


class TextualInterface(RichUiMixin, Redirectable, Mininterface):

    _adaptor: TextualSubprocessAdaptor

    def __init__(self, *args, need_atty=True, **kwargs):
        if need_atty and not sys.stdin.isatty():
            # We cannot have the check at the module level due to WebUI (without atty).
            # Without this check, an erroneous textual instance appears.
            raise InterfaceNotAvailable
        super().__init__(*args, **kwargs)

    def __enter__(self):
        # Entering the `with` block: start the TUI now (and wire stdout streaming)
        # so text printed before the first dialog is shown live — the window
        # appears with the first print, not only with the first dialog.
        instance = super().__enter__()
        self._adaptor._ensure_process()
        return instance
