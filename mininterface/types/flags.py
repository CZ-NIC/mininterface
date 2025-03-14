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

    raise ValueError(_blank_error.format(args[0]))


def _assure_blank_or_any(args):
    try:
        return _assure_blank_or_bool(args)
    except TypeError:
        return args[0]


_BlankTrue = Annotated[
    list[str] | None,
    PrimitiveConstructorSpec(
        nargs="*",
        # metavar="blank|str",
        # metavar="blank true|false|0|1|on|off|str",
        # metavar="blank true|1|on | false|0|off",
        metavar="blank=true|false",
        instance_from_str=_assure_blank_or_bool,
        is_instance=lambda instance: True,  # NOTE not sure
        str_from_instance=lambda instance: [instance],
    )]
"""
NOTE Experimental. Undocumented, untested, does not work in the UI. Great for CLI.
When left blank, this flag produces True.
    Return boolean for 0/false/off/1/true/on.
    Return a metavar value if metavar is a list.
    Else raises ValueError.
"""


_BlankTrueString = Annotated[
    list[str] | str | None,
    PrimitiveConstructorSpec(
        nargs="*",
        # metavar="blank|str",
        # metavar="blank true|false|0|1|on|off|str",
        # metavar="blank true|1|on | false|0|off | str",
        metavar="blank=true|false|str",
        instance_from_str=_assure_blank_or_any,
        is_instance=lambda instance: True,  # NOTE not sure
        str_from_instance=lambda instance: [instance],
    )]
"""
NOTE Experimental. Undocumented, untested, does not work in the UI. Great for CLI.

When left blank, this flag produces True.
        Return boolean for 0/false/off/1/true/on.
        Else returns input value or None if flag omitted.
"""
