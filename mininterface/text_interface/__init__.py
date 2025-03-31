
import sys
from pprint import pprint
from typing import TYPE_CHECKING, Type

from ..exceptions import Cancelled, InterfaceNotAvailable
from ..form_dict import DataClass, EnvClass, FormDict
from ..mininterface import Mininterface
from .adaptor import TextAdaptor

if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self, Type


class AssureInteractiveTerminal:
    """ Try to make the non-interactive terminal interactive. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._entered = False
        self._stdin = sys.stdin
        self._stdout = sys.stdout
        self._reserve_stdin = self._reserve_stdout = None
        try:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                self._reserve_stdin = open('/dev/tty', 'r')
                self._reserve_stdout = open('/dev/tty', 'w')
                if not self._reserve_stdin.isatty() or not self._reserve_stdout.isatty():
                    raise RuntimeError
        except Exception:
            raise InterfaceNotAvailable

    def __enter__(self) -> "Self":
        self._entered = True
        if self._reserve_stdin or self._reserve_stdout:
            sys.stdin = self._reserve_stdin
            sys.stdout = self._reserve_stdout
        return self

    def __exit__(self, *_):
        self._entered = False
        sys.stdout = self._stdout
        sys.stdin = self._stdin

    @property
    def interactive(self):
        return self._entered or sys.stdin.isatty() and sys.stdout.isatty()


class StdinTTYWrapper:
    """ Revive interactive features when piping into the program.
    Fail when in a cron job.
    """

    def __enter__(self):
        self.original_stdin = sys.stdin
        if not sys.stdin.isatty():
            try:
                sys.stdin = open("/dev/tty", "r")
            except OSError:
                sys.stdin = self.original_stdin
        return sys.stdin

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdin = self.original_stdin


class TextInterface(AssureInteractiveTerminal, Mininterface):
    """ Plain text fallback interface. No dependencies. """

    _adaptor: TextAdaptor

    def alert(self, text: str):
        """ Display text and let the user hit any key. """
        with StdinTTYWrapper():
            input(text + " Hit any key.")

    def ask(self, text: str = None):
        with StdinTTYWrapper():
            if not self.interactive:
                return super().ask(text)
            try:
                txt = input(text + ": ") if text else input()
            except EOFError:
                txt = "x"
            if txt == "x":
                raise Cancelled(".. cancelled")
            return txt

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True
             ) -> FormDict | DataClass | EnvClass:
        try:
            with StdinTTYWrapper():
                return self._form(form, title, self._adaptor, submit=submit)
        except NotImplementedError:  # simple-term-menu raises this when vscode runs tests
            if not self.interactive:
                return super().form(form=form, title=title, submit=submit)

            # NOTE: This is minimal implementation that should rather go the ReplInterface.
            # NOTE: Concerning Dataclass form.
            # I might build some menu of changing dict through:
            #   params_ = dataclass_to_dict(self.env, self.descriptions)
            #   data = FormDict → dict self.window.run_dialog(params_)
            #   dict_to_dataclass(self.env, params_)
            # NOTE: Validators, nor type checks are not performed.
            if form is None:
                form = self.env
            print("Access `v` (as var) and change values. Then (c)ontinue.")
            pprint(form)
            v = form
            try:
                import ipdb
                ipdb.set_trace()
            except ImportError:
                import pdb
                pdb.set_trace()
            return form

    def ask_number(self, text):
        """
        Let user write number. Empty input = 0.
        """
        with StdinTTYWrapper():
            while True:
                try:
                    t = self.ask(text=text)
                    if not t:
                        return 0
                    return int(t)
                except ValueError:
                    print("This is not a number")

    def is_yes(self, text: str):
        with StdinTTYWrapper():
            return self.ask(text=text + " [y]/n").lower() in ("y", "yes", "")

    def is_no(self, text):
        with StdinTTYWrapper():
            return self.ask(text=text + " y/[n]").lower() in ("n", "no", "")


class ReplInterface(TextInterface):
    """ Same as the base TuiInterface, except it starts the REPL. """

    def __getattr__(self, name):
        """ Run _Mininterface method if exists and starts a REPL. """
        attr = getattr(super(), name, None)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                breakpoint()
                return result
            return wrapper
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
