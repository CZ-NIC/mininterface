from typing import Type

from ..options import GuiOptions

try:
    # It seems tkinter is installed either by default or not installable at all.
    # Tkinter is not marked as a requirement as other libraries does that neither.
    from tkinter import TclError
except ImportError:
    from ..exceptions import InterfaceNotAvailable
    raise InterfaceNotAvailable

from .adaptor import TkAdaptor
from .redirect_text_tkinter import RedirectTextTkinter
from ..exceptions import InterfaceNotAvailable
from ..form_dict import DataClass, FormDict
from ..redirectable import Redirectable
from ..mininterface import EnvClass, Mininterface


class TkInterface(Redirectable, Mininterface):
    """ When used in the with statement, the GUI window does not vanish between dialogues. """

    _adaptor: TkAdaptor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._redirected = RedirectTextTkinter(self._adaptor.text_widget, self._adaptor)

    def __exit__(self, *_):
        super().__exit__(self)
        # The window must disappear completely. Otherwise an empty trailing window would appear in the case another TkInterface would start.
        self._adaptor.destroy()

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self._adaptor.buttons(text, [("Ok", None)])

    def ask(self, text: str) -> str:
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self._adaptor, submit=submit)

    def ask_number(self, text: str) -> int:
        return self.form({text: 0})[text]

    def is_yes(self, text):
        return self._adaptor.yes_no(text, False)

    def is_no(self, text):
        return self._adaptor.yes_no(text, True)
