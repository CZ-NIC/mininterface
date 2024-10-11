import os
import re
from argparse import ArgumentParser
from typing import Iterable, TypeVar

from tyro.extras import get_parser

T = TypeVar("T")
KT = str
common_iterables = list, tuple, set
""" collections, and not a str """


def flatten(d: dict[str, T | dict]) -> Iterable[T]:
    """ Recursively traverse whole dict """
    for v in d.values():
        if isinstance(v, dict):
            yield from flatten(v)
        else:
            yield v


def flatten_keys(d: dict[KT, T | dict]) -> Iterable[tuple[KT, T]]:
    """ Recursively traverse whole dict """
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_keys(v)
        else:
            yield k, v


def guess_type(val: T) -> type[T]:
    t = type(val)
    if t in common_iterables and len(common_iterables):
        elements_type = set(type(x) for x in val)
        if len(elements_type) == 1:
            return t[list(elements_type)[0]]
    return t


def get_terminal_size():
    try:
        # XX when piping the input IN, it writes
        # echo "434" | convey -f base64  --debug
        # stty: 'standard input': Inappropriate ioctl for device
        # I do not know how to suppress this warning.
        height, width = (int(s) for s in os.popen('stty size', 'r').read().split())
        return height, width
    except (OSError, ValueError):
        return 0, 0


def get_descriptions(parser: ArgumentParser) -> dict:
    """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
    # clean-up tyro stuff that may have a meaning in the CLI, but not in the UI
    return {action.dest.replace("-", "_"): re.sub(r"\((default|fixed to).*\)", "", action.help or "")
            for action in parser._actions}


def get_description(obj, param: str) -> str:
    return get_descriptions(get_parser(obj))[param]
