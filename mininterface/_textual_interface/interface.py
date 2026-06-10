import sys

from ..exceptions import InterfaceNotAvailable
from .._mininterface.mixin import RichUiMixin
from .._lib.redirectable import Redirectable
from .._mininterface import Mininterface
try:
    from .adaptor import TextualAdaptor
    from .subprocess_adaptor import TextualSubprocessAdaptor
except ImportError:
    raise InterfaceNotAvailable


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
