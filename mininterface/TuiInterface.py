from .HeadlessInterface import Cancelled, HeadlessInterface


class TuiInterface(HeadlessInterface):

    def ask(self, text: str=None):
        try:
            txt = input(text + " ") if text else input()
        except EOFError:
            txt = "x"
        if txt == "x":
            raise Cancelled(".. cancelled")
        return txt


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

    def yes_no(self, text: str):
        return self.ask(text=text + " [y]/n: ").lower() in ("y", "yes", "")

    def is_no(self, text):
        return self.ask(text=text + " y/[n]: ").lower() in ("n", "no", "")

    def hit_any_key(self, text: str):
        """ Display text and let the user hit any key. Skip when headless. """
        input(text + " Hit any key.")


class ReplInterface(TuiInterface):
    """ Same as the base TuiInterface, except it starts the REPL. """

    def __getattribute__(self, name):
        """ Run _HeadlessInterface method if exists and starts a REPL. """
        attr = getattr(super(), name, None)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                breakpoint()
                return result
            return wrapper
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")