from typing import Annotated, TypeVar, Any
from typing import Annotated
from tyro.constructors import PrimitiveConstructorSpec

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

Return boolean for 0/false/off/1/true/on.

Else raises ValueError.

!!! Warning
    NOTE Experimental. Undocumented, untested, does not work in the UI. Great for CLI.

"""


T = TypeVar("T")


class Blank:
    def __class_getitem__(cls, item_type: type[T]) -> Any:
        def instance_from_str(args: list[str]) -> T | bool:
            if not args:
                return True
            if len(args) > 1:
                raise NotImplemented("Describe your use case in an issue please.")
            match args:
                case "True":
                    return True
                case "False":
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


"""
When left blank, this flag produces True.
    Return boolean for True|False.
    Return None if the flag is omitted.
    Else returns T created from the input value.

Note that you can not use 'True' or 'False' for values, as the parameter becomes a bool.

!!! Warning
    NOTE Experimental. Undocumented, untested, does not work in the UI. Great for CLI.

"""
