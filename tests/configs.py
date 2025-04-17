from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Annotated, Callable, Optional

from tyro.conf import Positional, arg

from mininterface import Tag
from mininterface.subcommands import Command
from mininterface.tag.callback_tag import CallbackTag
from mininterface.tag.path_tag import PathTag
from mininterface.tag.alias import Options, Validation
from mininterface.tag.select_tag import SelectTag
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
class MissingNonscalar:
    # Missing union and generics.
    # NOTE Put into the showcase.

    path: str | Path
    combined: int | tuple[int, int] | None

    # tolerate_hour: tuple[int, int]

    # number: int | None
    # combined: list[tuple[str, str]] | None

    # NOTE the str works bad. When the form re-appears, the str get splitted into list elements.
    # combined: list[tuple[str, str]]

    # gen1: Optional[list[str]]
    # gen2: list[str] | None
    # gen3: list[str]

    simple_tuple: tuple[int, int]

    # NOTE the str works bad. When the form re-appears, the str get splitted into list elements.
    # gen4: list[int] | str | None

    # NOTE: these work bad, Tag._make_default_value cannot be empty ()
    # suffixes4: tuple[str] | None
    # suffixes5: tuple[str]


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

    options: Annotated[str, SelectTag(options=("one", "two"))] = "one"


@dataclass
class ParametrizedGeneric:
    paths: list[Path]


@dataclass
class ComplicatedTypes:
    # NOTE not used yet
    p1: Callable = callback_raw
    p2: Annotated[Callable, CallbackTag(description="Foo")] = callback_tag
    # Not supported: p3: CallbackTag = callback_tag
    # Not supported: p4: CallbackTag = field(default_factory=CallbackTag(callback_tag))
    # Not supported: p5: Annotated[Callable, Tag(description="Bar", annotation=CallbackTag)] = callback_tag


@dataclass
class PathTagClass:
    files: Positional[list[Path]] = field(default_factory=list)

    # This becomes PathTag(multiple=True)
    files2: Annotated[list[Path], Tag(name="Custom name")] = field(default_factory=list)

    # NOTE this should become PathTag(multiple=True)
    # files3: Annotated[list, PathTag(name="Custom name")] = field(default_factory=list)


@dataclass
class DatetimeTagClass:
    p1: datetime = datetime.fromisoformat("2024-09-10 17:35:39.922044")
    p2: time = time.fromisoformat("17:35:39.922044")
    # TODO
    p3: date = date.fromisoformat("2024-09-10")
    pAnnot: Annotated[date, Tag(name="hello")] = datetime.fromisoformat("2024-09-10 17:35:39.922044")


@dataclass
class MissingPositional:
    files: Positional[list[Path]]


@dataclass
class MissingPositionalScalar:
    file: Positional[Path]


@dataclass
class AnnotatedClass:
    # NOTE some of the entries are not well supported
    files1: list[Path]
    # files2: Positional[list[Path]]  # raises error
    # files7: Annotated[list[Path], None]
    # files8: Annotated[list[Path], Tag(annotation=str)]
    files3: list[Path] = field(default_factory=list)
    # files4: Positional[list[Path]] = field(default_factory=list) # raises error
    files5: Annotated[list[Path], None] = field(default_factory=list)
    files6: Annotated[list[Path], Tag(annotation=str)] = field(default_factory=list)
    """ Files """


@dataclass
class AnnotatedClassInner:
    # NOTE some of the entries are not well supported
    files1: list[Path]
    # files2: Positional[list[Path]]
    # files7: Annotated[list[Path], None]
    # files8: Annotated[list[Path], Tag(annotation=str)]
    files3: list[Path] = field(default_factory=list)
    files4: Positional[list[Path]] = field(default_factory=list)
    files5: Annotated[list[Path], None] = field(default_factory=list)
    files6: Annotated[list[Path], Tag(annotation=str)] = field(default_factory=list)
    """ Files """


@dataclass
class InheritedAnnotatedClass(AnnotatedClassInner):
    pass


@dataclass
class SharedArgs(Command):
    """ Class with a shared argument. """
    foo: int

    def run(self):
        pass


@dataclass
class Subcommand1(SharedArgs):
    """ Class inheriting from SharedArgs. """
    a: int = 1


@dataclass
class Subcommand2(SharedArgs):
    b: int


dynamic_str = "My dynamic str"


@dataclass
class DynamicDescription:
    foo: Annotated[str, Tag(name="Foo"), arg(help=dynamic_str)] = "hello"
