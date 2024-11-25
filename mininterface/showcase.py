from dataclasses import dataclass
from typing import Annotated, Literal

from . import Tag, Validation, run
from .validators import not_empty

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


@dataclass
class NestedEnv:
    another_number: int = 7
    """ This field is nested """


@dataclass
class Env:
    nested_config: NestedEnv

    mandatory_str: str
    """ As there is no default value, you will be prompted automatically to fill up the field """

    my_number: int | None = None
    """ This is not just a dummy number, if left empty, it is None. """

    my_string: str = "Hello"
    """ A dummy string """

    my_flag: bool = False
    """ Checkbox test """

    my_validated: Annotated[str, Validation(not_empty)] = "hello"
    """ A validated field """

    my_complex: list[tuple[int, str]] = field(default_factory=lambda: [(1, 'foo')])
    """ List of tuples. """


def showcase(interface: Literal["gui"] | Literal["tui"] | Literal["all"], case: int):
    if interface == "all":
        interface = None
    kw = {"args": [], "interface": interface}
    if case == 1:
        m = run(Env, title="My program", **kw)
        m.form()
        print("Output", m.env)
    elif case == 2:
        m = run([Subcommand1, Subcommand2, SubcommandPlaceholder], **kw)
    else:
        print("Unknown showcase")
