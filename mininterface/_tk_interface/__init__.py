from typing import Iterable, Type

try:
    # It seems tkinter is installed either by default or not installable at all.
    # Tkinter is not marked as a requirement as other libraries does that neither.
    from tkinter import TclError
except ImportError:
    from ..exceptions import InterfaceNotAvailable

    raise InterfaceNotAvailable

from ..exceptions import InterfaceNotAvailable

from .._mininterface import EnvClass, Mininterface, TagValue, ValidationCallback
from .._mininterface.mixin import RichUiMixin
from ..tag import Tag
from ..settings import GuiSettings
from .._lib.redirectable import Redirectable
from .subprocess_adaptor import TkSubprocessAdaptor


class TkInterface(Redirectable, RichUiMixin, Mininterface):
    """The Tk GUI runs in a separate process.

    Calling `run` starts loading the child process (lowering the import cost);
    `.form` then displays the form in that Tk subprocess. The GUI stays
    responsive even while the main process sleeps, and closing the window
    (the X button) raises `Cancelled` in the main process.

    When used in the with statement, the GUI window does not vanish between dialogs.
    """

    _adaptor: TkSubprocessAdaptor

    def __exit__(self, *_):
        super().__exit__(self)
        # The window must disappear completely. Otherwise an empty trailing window
        # would appear in the case another TkInterface would start.
        self._adaptor._destroy()

    def ask(
        self,
        text: str,
        annotation: Type[TagValue] | Tag = str,
        validation: Iterable[ValidationCallback] | ValidationCallback | None = None,
    ) -> TagValue:
        if annotation is int and validation is None:
            # without 0, tkinter_form would create a mere text Entry
            return self.form({text: 0})[text]
        return super().ask(text, annotation, validation)
