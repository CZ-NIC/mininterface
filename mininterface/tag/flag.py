from pathlib import Path
from typing import Annotated, TypeVar, Any
from tyro.constructors import PrimitiveConstructorSpec

from .path_tag import PathTag

File = Annotated[Path, PathTag(is_file=True)]
""" An existing file.
from mininterface import run
from mininterface.tag.flag import File

```python
@dataclass
class Env:
    my_file: File

m = run(Env)
m.env.my_file  # guaranteed to be an existing dir
```

!!! Warning
    EXPERIMENTAL.
"""
# NOTE missing test
Dir = Annotated[Path, PathTag(is_dir=True)]
""" An existing directory.
from mininterface import run
from mininterface.tag.flag import Dir

```python
@dataclass
class Env:
    my_dir: Dir

m = run(Env)
m.env.my_dir  # guaranteed to be an existing dir
```

!!! Warning
    EXPERIMENTAL.
"""
# NOTE missing test

_blank_error = "Unrecognised value '{}'. Allowed values are blank for True/1/on / False/0/off" \
    " (case insensitive). Should the value be considered a positional parameter,"\
    " move the parameter behind."


def _assure_blank_or_bool(args):
    match len(args):
        case 0:
            return True
        case 1:
            if args[0].lower() in ["0", "false", "off"]:
                return False
            elif args[0].lower() in ["1", "true", "on"]:
                return True
            raise TypeError(_blank_error.format(args[0]))
        case _:
            raise ValueError(_blank_error.format(args[0]))


BlankTrue = Annotated[
    list[str] | None,
    PrimitiveConstructorSpec(
        nargs="*",
        metavar="blank=True|BOOL",
        instance_from_str=_assure_blank_or_bool,
        is_instance=lambda instance: True,  # NOTE not sure
        str_from_instance=lambda instance: [instance],
    )]
"""
When left blank, this flag produces True.


Returns:
    bool: for `0/false/off/1/true/on` in the parameter
    True: When parameter is left blank.

Raises:
    ValueError: Raised on an unknown parameter.

!!! Warning
    Experimental.

"""
# NOTE untested
# NOTE Works good with static type checking.


T = TypeVar("T")


class Blank:
    """
    When left blank, this flag produces True.
        Return boolean for True|False.
        Return None if the flag is omitted.
        Else returns T created from the input value.

    Note that you can not use 'True' or 'False' for values, as the parameter becomes a bool.

    !!! Warning
        Experimental.

    """
    # NOTE untested
    # NOTE Works bad with static type checking. Because `Blank[str]` pylance never matches with 'my text'.
    # We had to have Blank=Annotated instead, which would prevent instantianting str_from_instance and dynamic metavar.

    def __class_getitem__(cls, item_type: type[T]) -> Any:
        def instance_from_str(args: list[str]) -> T | bool:
            if not args:
                return True
            if len(args) > 1:
                raise NotImplemented("Describe your use case in an issue please.")
            match args:
                case ("True",):
                    return True
                case ("False",):
                    return False
                case _:
                    return item_type(*args)

        def is_instance(_: object) -> bool:
            return True

        def str_from_instance(val: T | bool) -> list[str]:
            return [str(val)]

        return Annotated[
            str | None,  # the base type is not used, we parse arbitrary
            PrimitiveConstructorSpec(
                nargs="*",
                metavar=f"blank=True|BOOL|{item_type.__name__.upper()}",
                instance_from_str=instance_from_str,
                is_instance=is_instance,
                str_from_instance=str_from_instance,
            )
        ]
