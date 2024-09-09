import logging
from abc import ABC, abstractmethod
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Generic, Self
else:
    from typing import Generic

from .FormDict import EnvClass, FormDict, FormDictOrEnv
from .tag import Tag

logger = logging.getLogger(__name__)


class Cancelled(SystemExit):
    # We inherit from SystemExit so that the program exits without a traceback on GUI Escape.
    pass



class Mininterface(Generic[EnvClass]):
    """ The base interface.
        You get one through `mininterface.run` which fills CLI arguments and config file to `mininterface.env`
        or you can create it directly (without benefiting from the CLI parsing).

        This base interface does not require any user input and hence is suitable for headless testing.
    """

    def __init__(self, title: str = "",
                 _env: EnvClass | None = None,
                 _descriptions: dict | None = None,
                 ):
        self.title = title or "Mininterface"
        # Why `or SimpleNamespace()`?
        # We want to prevent error raised in `self.form(None)` if self.env would have been set to None.
        # It would be None if the user created this mininterface (without setting env)
        # or if __init__.run is used but Env is not a dataclass but a function (which means it has no attributes).
        self.env: EnvClass = _env or SimpleNamespace()
        """ Parsed arguments, fetched from cli
            Contains whole configuration (previously fetched from CLI and config file).
        """
        self._descriptions = _descriptions or {}
        """ Field descriptions """

    def __enter__(self) -> "Self":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def alert(self, text: str) -> None:
        """ Prompt the user to confirm the text.  """
        print("Alert text", text)
        return

    def ask(self, text: str) -> str:
        """ Prompt the user to input a text.  """
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_number(self, text: str) -> int:
        """ Prompt the user to input a number. Empty input = 0. """
        print("Asking number", text)
        return 0

    def form(self, form: FormDictOrEnv | None = None, title: str = "") -> FormDictOrEnv | EnvClass:
        """ Prompt the user to fill up whole form.
            :param form: Dict of `{labels: default value}`. The form widget infers from the default value type.
                The dict can be nested, it can contain a subgroup.
                The default value might be `mininterface.Tag` that allows you to add descriptions.
                If None, the `self.env` is being used as a form, allowing the user to edit whole configuration.
                    (Previously fetched from CLI and config file.)
                A checkbox example: `{"my label": Tag(True, "my description")}`
            :param title: Optional form title
        """
        f = self.env if form is None else form
        print(f"Asking the form {title}".strip(), f)
        return f  # NOTE – this should return dict, not FormDict (get rid of auxiliary.Tag values)

    def is_yes(self, text: str) -> bool:
        """ Display confirm box, focusing yes. """
        print("Asking yes:", text)
        return True

    def is_no(self, text: str) -> bool:
        """ Display confirm box, focusing no. """
        print("Asking no:", text)
        return False


class BackendAdaptor(ABC):

    @staticmethod
    @abstractmethod
    def widgetize(tag: Tag):
        """ Wrap Tag to a textual widget. """
        pass

    @abstractmethod
    def run_dialog(self, formDict: FormDict, title: str = "") -> FormDict:
        """ Let the user edit the dict values. """
        pass
