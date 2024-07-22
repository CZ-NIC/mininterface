from .auxiliary import ConfigInstance, FormDict
from .Mininterface import Cancelled, Mininterface


class TuiInterface(Mininterface):

    def alert(self, text: str):
        """ Display text and let the user hit any key. """
        input(text + " Hit any key.")

    def ask(self, text: str = None):
        try:
            txt = input(text + ": ") if text else input()
        except EOFError:
            txt = "x"
        if txt == "x":
            raise Cancelled(".. cancelled")
        return txt

    # def ask_args(self) -> ConfigInstance: TODO
        # raise NotImplementedError

    def ask_form(self, args: FormDict) -> dict:
        raise NotImplementedError

    def ask_number(self, text):
        """
        Let user write number. Empty input = 0.
        """
        while True:
            try:
                t = self.ask(text=text)
                if not t:
                    return 0
                return int(t)
            except ValueError:
                print("This is not a number")

    def is_yes(self, text: str):
        return self.ask(text=text + " [y]/n").lower() in ("y", "yes", "")

    def is_no(self, text):
        return self.ask(text=text + " y/[n]").lower() in ("n", "no", "")


class ReplInterface(TuiInterface):
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
