from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Callable

from mininterface import Tag
from mininterface.common import Command
from mininterface.types import CallbackTag, Choices, Validation
from mininterface.validators import not_empty


class ColorEnum(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


class ColorEnumSingle(Enum):
    ORANGE = 4


def callback_tag(tag: Tag):
    """ Receives a tag """
    print("Printing", type(tag))
    return 100


def callback_tag2(tag: Tag):
    """ Receives a tag """
    print("Printing", type(tag))


def callback_raw():
    """ Dummy function """
    print("Priting text")
    return 50


@dataclass
class SimpleEnv:
    """Set of options."""
    test: bool = False
    """My testing flag"""
    important_number: int = 4
    """This number is very important"""


@dataclass
class ConflictingEnv:
    verbose: bool = True


@dataclass
class FurtherEnv1:
    token: str = "filled"
    host: str = "example.org"


@dataclass
class NestedDefaultedEnv:
    further: FurtherEnv1


@dataclass
class FurtherEnv2:
    token: str
    host: str = "example.org"


@dataclass
class MissingUnderscore:
    token_underscore: str
    host: str = "example.org"


@dataclass
class NestedMissingEnv:
    further: FurtherEnv2


@dataclass
class FurtherEnv4:
    flag: bool = False
    """ This is a deep flag """


@dataclass
class FurtherEnv3:
    deep: FurtherEnv4
    numb: int = 0


@dataclass
class OptionalFlagEnv:
    further: FurtherEnv3
    severity: int | None = None
    """ This number is optional """

    msg: str | None = None
    """ An example message """

    msg2: str | None = "Default text"
    """ Another example message """


@dataclass
class ConstrainedEnv:
    """Set of options."""

    test: Annotated[str, Tag(validation=not_empty, name="Better name")] = "hello"
    """My testing flag"""

    test2: Annotated[str, Validation(not_empty)] = "hello"

    choices: Annotated[str, Choices("one", "two")] = "one"


@dataclass
class ParametrizedGeneric:
    paths: list[Path]


@dataclass
class ComplicatedTypes:
    p1: Callable = callback_raw
    p2: Annotated[Callable, CallbackTag(description="Foo")] = callback_tag
    # Not supported: p3: CallbackTag = callback_tag
    # Not supported: p4: CallbackTag = field(default_factory=CallbackTag(callback_tag))
    # Not supported: p5: Annotated[Callable, Tag(description="Bar", annotation=CallbackTag)] = callback_tag
    # NOTE add PathTag
    # NOTE not used yet


@dataclass
class SharedArgs(Command):
    foo: int


@dataclass
class Subcommand1(SharedArgs):
    a: int = 1


@dataclass
class Subcommand2(SharedArgs):
    b: int
