from dataclasses import dataclass
from typing import Annotated, Literal

from . import Tag, Validation, run
from .validators import not_empty


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


def showcase(interface: Literal["gui"] | Literal["tui"] | Literal["all"]):
    if interface in ["gui", "all"]:
        m = run(Env, title="My program", args=[], interface="gui")
        print("GUI output", m.env)
        m.form()
    if interface in ["tui", "all"]:
        m = run(Env, title="My program", args=[], interface="tui")
        print("TUI output", m.env)
        m.form()
