from dataclasses import is_dataclass
from typing import Type, override

try:
    # It seems tkinter is installed either by default or not installable at all.
    # Tkinter is not marked as a requirement as other libraries does that neither.
    from tkinter import TclError
except ImportError:
    from ..common import InterfaceNotAvailable
    raise InterfaceNotAvailable

from .tk_window import TkWindow
from .redirect_text_tkinter import RedirectTextTkinter
from ..common import InterfaceNotAvailable
from ..form_dict import DataClass, FormDict
from ..redirectable import Redirectable
from ..mininterface import EnvClass, Mininterface


class TkInterface(Redirectable, Mininterface):
    """ When used in the with statement, the GUI window does not vanish between dialogues. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.adaptor = TkWindow(self)
        except TclError:
            # even when installed the libraries are installed, display might not be available, hence tkinter fails
            raise InterfaceNotAvailable
        self._redirected = RedirectTextTkinter(self.adaptor.text_widget, self.adaptor)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self.adaptor.buttons(text, [("Ok", None)])

    def ask(self, text: str) -> str:
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self.adaptor, submit=submit)

    def ask_number(self, text: str) -> int:
        return self.form({text: 0})[text]

    def is_yes(self, text):
        return self.adaptor.yes_no(text, False)

    def is_no(self, text):
        return self.adaptor.yes_no(text, True)
