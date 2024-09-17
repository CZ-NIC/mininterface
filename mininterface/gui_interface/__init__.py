try:
    from tkinter import TclError
except ImportError:
    from ..common import InterfaceNotAvailable
    raise InterfaceNotAvailable


from .tk_window import TkWindow
from ..common import InterfaceNotAvailable
from ..form_dict import FormDictOrEnv, dataclass_to_tagdict, dict_to_tagdict, formdict_resolve
from ..redirectable import RedirectTextTkinter, Redirectable
from ..mininterface import EnvClass, Mininterface


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

    def _ask_env(self) -> EnvClass:
        """ Display a window form with all parameters. """
        form = dataclass_to_tagdict(self.env, self._descriptions, self.facet)

        # formDict automatically fetches the edited values back to the EnvInstance
        return self.window.run_dialog(form)

    def form(self, form: FormDictOrEnv | None = None, title: str = "") -> FormDictOrEnv | EnvClass:
        """ Prompt the user to fill up whole form.
         See Mininterface.form
        """
        if form is None:
            # NOTE should be integrated here when we integrate dataclass, see FormDictOrEnv
            return self._ask_env()
        else:
            return formdict_resolve(self.window.run_dialog(dict_to_tagdict(form, self.facet), title=title), extract_main=True)

    def ask_number(self, text: str) -> int:
        return self.form({text: 0})[text]

    def is_yes(self, text):
        return self.window.yes_no(text, False)

    def is_no(self, text):
        return self.window.yes_no(text, True)
