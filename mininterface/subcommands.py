""" Dealing with CLI subcommands, `from mininterface.subcommands import *`  """
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .facet import Facet
else:
    Facet = None


@dataclass
class Command(ABC):
    """ The Command is automatically run while instantanied.
    TODO Example

    Experimental. Should it receive _facet?


    What if I TODO
    Special placeholder class SubcommandPlaceholder.
    This special class let the user to choose the subcommands via UI,
    while still benefiniting from default CLI arguments.

    Alternative to argparse [subcommands](https://docs.python.org/3/library/argparse.html#sub-commands).

    from tyro.conf import Positional

    The CLI behaviour:
    * `./program.py` -> UI started with choose_subcommand
    * `./program.py subcommand --flag` -> special class SubcommandPlaceholder allows using flag
        while still starting UI with choose_subcommand
    * `./program.py subcommand1 --flag` -> program run
    * `./program.py subcommand1` -> fails with tyro now  # NOTE nice to have implemented


    An example of Command usage:

    ```python
    from mininterface.subcommands import Command

    @dataclass
    class SharedArgs:
        common: int
        files: Positional[list[Path]] = field(default_factory=list)

        def __post_init__(self):
            self.internal = "value"

    @dataclass
    class Subcommand1(SharedArgs):
        my_local: int = 1

        def run(self):
            print("Common", self.common)  # user input
            print("Number", self.my_local)  # 1 or user input
            ValidationFail("The submit button blocked!")

    @dataclass
    class Subcommand2(SharedArgs):
        def run(self):
            self._facet.set_title("Button clicked")  # you can access internal self._facet: Facet
            print("Common files", self.files)

    subcommand = run(Subcommand1 | Subcommand2)
    ```

    TODO img
    """
    # Why to not document the Subcommand in the Subcommand class itself? It would be output to the user with --help,
    # I need the text to be available to the developer in the docs, not to the user.

    def __post_init__(self):
        self._facet: "Facet" = None  # As this is dataclass, the internal facet cannot be defined as one of the fields.

    def init(self):
        """ Just before the form appears.
        As the `__post_init__` method is not guaranteed to run just once (internal CLI behaviour),
        you are welcome to override this method instead. You can use [self._facet][mininterface.facet.Facet] from within.
        """
        ...

    @abstractmethod
    def run(self):
        """ This method is run automatically in CLI or by a button button it generates in a UI."""
        ...


@dataclass
class SubcommandPlaceholder(Command):
    """ Use this placeholder to choose the subcomannd via a UI. """

    def run(self):
        ...


SubcommandPlaceholder.__name__ = "subcommand"  # show just the shortcut in the CLI
