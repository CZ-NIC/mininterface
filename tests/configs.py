from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Annotated, Callable, Optional

from annotated_types import Gt, Le, Len, Lt
from tyro.conf import Positional, arg

from mininterface import Literal, Tag
from mininterface.cli import Command
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
    """Receives a tag"""
    print("Printing", type(tag))
    return 100


def callback_tag2(tag: Tag):
    """Receives a tag"""
    print("Printing", type(tag))


def callback_raw():
    """Dummy function"""
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
class ComplexEnv:
    a1: dict[int, str]
    a2: dict[int, tuple[str, int]]
    a3: dict[int, list[str]]
    a4: list[int]
    a5: tuple[str, int]
    a6: list[int | str]
    a7: list[tuple[str, float]]


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

    test: Annotated[str, Tag(validation=not_empty, label="Better name")] = "hello"
    """My testing flag"""

    test2: Annotated[str, Validation(not_empty)] = "hello"

    options: Annotated[str, SelectTag(options=("one", "two"))] = "one"

    liter1: Literal["one"] = "one"
    liter2: Literal["one", "two"] = "two"


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
    files2: Annotated[list[Path], Tag(label="Custom name")] = field(
        default_factory=list
    )

    # NOTE this should become PathTag(multiple=True)
    # files3: Annotated[list, PathTag(name="Custom name")] = field(default_factory=list)


@dataclass
class DatetimeTagClass:
    p1: datetime = datetime.fromisoformat("2024-09-10 17:35:39.922044")
    p2: time = time.fromisoformat("17:35:39.922044")
    p3: date = date.fromisoformat("2024-09-10")
    pAnnot: Annotated[date, Tag(label="hello")] = datetime.fromisoformat(
        "2024-09-10 17:35:39.922044"
    )


@dataclass
class MissingPositional:
    files: Positional[list[Path]]


@dataclass
class MissingPositionalScalar:
    file: Positional[Path]


@dataclass
class MissingCombined:
    file: Positional[Path]
    foo: str
    bar: str = "hello"


@dataclass
class AnnotatedClass:
    # NOTE some of the entries are not well supported
    files1: Positional[list[Path]]
    files2: list[Path]
    # files4: Positional[list[Path]] = field(default_factory=list)  # raises error
    # files7: Annotated[list[Path], None]
    # files8: Annotated[list[Path], Tag(annotation=str)]
    files3: list[Path] = field(default_factory=list)
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
class AnnotatedClass3:
    foo1: Positional[int]
    foo2: list[Path]
    foo3: Annotated[list[Path], Validation(not_empty)]
    foo4: Positional[list[bool]] = field(default_factory=list)  # raises error


@dataclass
class InheritedAnnotatedClass(AnnotatedClassInner):
    pass


@dataclass
class SharedArgs(Command):
    """Class with a shared argument."""

    foo: int

    def run(self):
        pass


@dataclass
class Subcommand1(SharedArgs):
    """Class inheriting from SharedArgs."""

    a: int = 1


@dataclass
class Subcommand2(SharedArgs):
    b: int


@dataclass
class SharedArgsB(Command):
    """Class with a shared argument."""

    foo: int = 7

    def init(self):
        self._trace = []

    def run(self):
        self._trace.append(1)


@dataclass
class SubcommandB1(SharedArgsB):
    """Class inheriting from SharedArgs."""

    a: int = 1

    def run(self):
        self._trace.append(2)


@dataclass
class SubcommandB2(SharedArgsB):
    b: int = 2


dynamic_str = "My dynamic str"


def validation1(tag: Tag):
    if tag.val < 10:
        return True
    if tag.val < 50:
        return True, tag.val * 2
    if tag.val < 90:
        return False
    return "too big"


@dataclass
class AnnotatedTypes:
    age: Annotated[int, Gt(18)] = 20  # Valid: 19, 20, ...
    # Invalid: 17, 18, "19", 19.0, ...
    my_list: Annotated[list[int], Len(0, 10)] = field(
        default_factory=lambda: []
    )  # Valid: [], [10, 20, 30, 40, 50]
    # Invalid: (1, 2), ["abc"], [0] * 20
    percent: Annotated[int, Gt(0), Le(100)] = 5
    percent_fl: Annotated[float, Gt(0), Le(100)] = 5


@dataclass
class AnnotatedTypesCombined:
    combined1: Annotated[int, Tag(validation=validation1), Gt(-100), Lt(95)] = 5
    combined2: Annotated[int, Gt(-100), Tag(validation=validation1), Lt(95)] = 5
    combined3: Annotated[int, Lt(95), Gt(-100), Tag(validation=validation1)] = 5
    combined4: Annotated[int, Tag(validation=(validation1, Lt(95), Gt(-100)))] = 5


@dataclass
class DynamicDescription:
    foo: Annotated[str, Tag(label="Foo"), arg(help=dynamic_str)] = "hello"
