# Common objects that might make sense to be used outside the library.

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING


@dataclass
class Command:
    """ The Command is automatically run while instantanied.
    TODO Example
    docs
    Experimental. Should it receive facet? (It cannot be called from the Mininterface init then, but after the adaptor init.)
    """

    @abstractmethod
    def run(self):
        """ This method is run automatically. """
        ...


class Cancelled(SystemExit):
    """ User has cancelled. """
    # We inherit from SystemExit so that the program exits without a traceback on ex. GUI escape.
    pass


class DependencyRequired(ImportError):
    def __init__(self, extras_name):
        super().__init__(extras_name)
        self.message = extras_name

    def __str__(self):
        return f"Required dependency. Run: pip install mininterface[{self.message}]"


class InterfaceNotAvailable(ImportError):
    pass
