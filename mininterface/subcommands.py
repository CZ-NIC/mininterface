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

    Experimental – how should it receive _facet?

    Put list of Commands to the [mininterface.run][mininterface.run] and divide your application into different sections.
    Alternative to argparse [subcommands](https://docs.python.org/3/library/argparse.html#sub-commands).

    Commands might inherit from the same parent to share the common attributes.

    ## SubcommandPlaceholder

    What if I need to use my program
    Special placeholder class SubcommandPlaceholder.
    This special class let the user to choose the subcommands via UI,
    while still benefiniting from default CLI arguments.


    ### The CLI behaviour:
    * `./program.py` -> UI started with subcommand choice
    * `./program.py subcommand --flag` -> special class `SubcommandPlaceholder` allows defining a common `--flag`
        while still starting UI with subcommand choice
    * `./program.py subcommand1 --flag` -> program run
    * `./program.py subcommand1` -> fails to CLI for now


    ## An example of Command usage

    ```python
    from dataclasses import dataclass, field
    from pathlib import Path
    from mininterface import run
    from mininterface.exceptions import ValidationFail
    from mininterface.subcommands import Command, SubcommandPlaceholder
    from tyro.conf import Positional


    @dataclass
    class SharedArgs(Command):
        common: int
        files: Positional[list[Path]] = field(default_factory=list)

        def init(self):
            self.internal = "value"


    @dataclass
    class Subcommand1(SharedArgs):
        my_local: int = 1

        def run(self):
            print("Common:", self.common)  # user input
            print("Number:", self.my_local)  # 1 or user input
            print("Internal:", self.internal)
            raise ValidationFail("The submit button blocked!")


    @dataclass
    class Subcommand2(SharedArgs):
        def run(self):
            self._facet.set_title("Button clicked")  # you can access internal self._facet: Facet
            print("Common files", self.files)


    m = run([Subcommand1, Subcommand2, SubcommandPlaceholder])
    m.alert("App continue")
    ```

    Let's start the program, passing there common flags, all HTML files in a folder and setting `--common` to 7.
    ```bash
    $ program.py  subcommand *.html  --common 7
    ```

    ![Subcommand](asset/subcommands-1.avif)

    As you see, thanks to `SubcommandPlaceholder`, subcommand was not chosen yet. Click to the first button.

    ![Subcommand](asset/subcommands-2.avif)

    and the terminal got:

    ```
    Common: 7
    Number: 1
    Internal: value
    ```

    Click to the second button.

    ![Subcommand](asset/subcommands-3.avif)

    Terminal output:
    ```
    Common files [PosixPath('page1.html'), PosixPath('page2.html')]
    ```

    ### Powerful automation

    Note we use `from tyro.conf import Positional` to denote the positional argument. We did not have to write `--files` to put there HTML files.
    """
    # Why to not document the Subcommand in the Subcommand class itself? It would be output to the user with --help,
    # I need the text to be available to the developer in the docs, not to the user.
    # NOTE * `./program.py subcommand1` -> fails to CLI for now  # nice to have implemented

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
