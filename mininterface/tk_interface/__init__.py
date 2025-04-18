from typing import Type

try:
    # It seems tkinter is installed either by default or not installable at all.
    # Tkinter is not marked as a requirement as other libraries does that neither.
    from tkinter import TclError
except ImportError:
    from ..exceptions import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..exceptions import InterfaceNotAvailable

from ..mininterface import EnvClass, Mininterface, TagValue
from ..mininterface.mixin import RichUiMixin
from ..tag import Tag
from ..settings import GuiSettings
from ..redirectable import Redirectable
from .adaptor import TkAdaptor
from .redirect_text_tkinter import RedirectTextTkinter


class TkInterface(Redirectable, RichUiMixin, Mininterface):
    """ When used in the with statement, the GUI window does not vanish between dialogues. """

    _adaptor: TkAdaptor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._redirected = RedirectTextTkinter(self._adaptor.text_widget, self._adaptor)

    def __exit__(self, *_):
        super().__exit__(self)
        # The window must disappear completely. Otherwise an empty trailing window would appear in the case another TkInterface would start.
        self._adaptor.destroy()

    def ask(self, text: str, annotation: Type[TagValue] = str) -> TagValue:
        if annotation is int:
            # without 0, tkinter_form would create a mere text Entry
            return self.form({text: 0})[text]
        return self.form({text: Tag(annotation=annotation)})[text]
