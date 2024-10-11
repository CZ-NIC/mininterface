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
from ..form_dict import DataClass, FormDict, dataclass_to_tagdict, dict_to_tagdict, formdict_resolve
from ..redirectable import Redirectable
from ..mininterface import EnvClass, Mininterface
from ..cli_parser import run_tyro_parser


class GuiInterface(Redirectable, Mininterface):
    """ When used in the with statement, the GUI window does not vanish between dialogues. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.window = TkWindow(self)
        except TclError:
            # even when installed the libraries are installed, display might not be available, hence tkinter fails
            raise InterfaceNotAvailable
        self._redirected = RedirectTextTkinter(self.window.text_widget, self.window)

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self.window.buttons(text, [("Ok", None)])

    def ask(self, text: str) -> str:
        return self.form({text: ""})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = ""
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self.window.run_dialog)

    def ask_number(self, text: str) -> int:
        return self.form({text: 0})[text]

    def is_yes(self, text):
        return self.window.yes_no(text, False)

    def is_no(self, text):
        return self.window.yes_no(text, True)
