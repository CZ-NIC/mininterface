from typing import get_args, get_origin, Union
from dataclasses import fields, is_dataclass
import os
import re
from argparse import ArgumentParser
from types import UnionType
from typing import Callable, Iterable, Optional, TypeVar, Union, get_args, get_origin

from annotated_types import Gt, Ge, Lt, Le, MultipleOf, Len

try:
    from tyro.extras import get_parser
except ImportError:
    get_parser = None

try:
    from humanize import naturalsize as naturalsize_
except ImportError:
    naturalsize_ = None

T = TypeVar("T")
KT = str
common_iterables = list, tuple, set
""" collections, and not a str """


def flatten(d: dict[str, T | dict], include_keys: Optional[Callable[[str], list]] = None) -> Iterable[T]:
    """ Recursively traverse whole dict """
    for k, v in d.items():
        if isinstance(v, dict):
            if include_keys:
                yield from include_keys(k)
            yield from flatten(v)
        else:
            yield v


# NOTE: Not used.
def flatten_keys(d: dict[KT, T | dict]) -> Iterable[tuple[KT, T]]:
    """ Recursively traverse whole dict """
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_keys(v)
        else:
            yield k, v


def guess_type(val: T) -> type[T]:
    t = type(val)
    if t in common_iterables:
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
        # NOTE why not using os.get_terminal_size()
        height, width = (int(s) for s in os.popen('stty size', 'r').read().split())
        return height, width
    except (OSError, ValueError):
        return 0, 0


def get_descriptions(parser: ArgumentParser) -> dict:
    """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
    # clean-up tyro stuff that may have a meaning in the CLI, but not in the UI
    return {action.dest.replace("-", "_"): re.sub(r"\((default|fixed to|required).*\)", "", action.help or "")
            for action in parser._actions}


def get_description(obj, param: str) -> str:
    if get_parser:
        return get_descriptions(get_parser(obj))[param]
    else:
        # We are missing mininterface[basic] requirement. Tyro is missing.
        # Without tyro, we are not able to evaluate the class: m.form(Env),
        # we can still evaluate its instance: m.form(Env()).
        # However, without descriptions.
        return ""


def yield_annotations(dataclass):
    yield from (cl.__annotations__ for cl in dataclass.__mro__ if is_dataclass(cl))


def matches_annotation(value, annotation) -> bool:
    """ Check whether the value type corresponds to the annotation.
    Because built-in isinstance is not enough, it cannot determine parametrized generics.
    """
    # union, including Optional and UnionType
    if isinstance(annotation, UnionType) or get_origin(annotation) is Union:
        return any(matches_annotation(value, arg) for arg in get_args(annotation))

    # generics, ex. list, tuple
    origin = get_origin(annotation)
    if origin:
        if not isinstance(value, origin):
            return False

        subtypes = get_args(annotation)
        if origin is list:
            return all(matches_annotation(item, subtypes[0]) for item in value)
        elif origin is tuple:
            if len(subtypes) != len(value):
                return False
            return all(matches_annotation(v, t) for v, t in zip(value, subtypes))
        elif origin is dict:
            key_type, value_type = subtypes
            return all(matches_annotation(k, key_type) and matches_annotation(v, value_type) for k, v in value.items())
        else:
            return True

    # ex. annotation=int
    return isinstance(value, annotation)


def subclass_matches_annotation(cls, annotation) -> bool:
    """
    Check whether the type in the value corresponds to the annotation.
    """
    # Union (Optional and UnionType)
    if isinstance(annotation, UnionType) or get_origin(annotation) is Union:
        return any(subclass_matches_annotation(cls, arg) for arg in get_args(annotation))

    # generics (list[int], tuple[int, str])
    origin = get_origin(annotation)
    if origin:
        # origin match (ex. list, tuple)
        if not issubclass(cls, origin):
            return False

        # subtype match (ex. `int` v `list[int]`)
        subtypes = get_args(annotation)
        if origin is list or origin is set:  # list and set have the single subtype
            return all(subclass_matches_annotation(object, subtypes[0]))
        elif origin is tuple:  # tuple has multiple subtypes
            return all(subclass_matches_annotation(object, t) for t in subtypes)
        elif origin is dict:
            key_type, value_type = subtypes
            return subclass_matches_annotation(object, key_type) and subclass_matches_annotation(object, value_type)
        else:
            return True

    # simple types like scalars
    try:
        return issubclass(cls, annotation)  # cls=tuple[int, str] raises an error since Python 3.13
    except TypeError:
        return False


def serialize_structure(obj):
    """ Ex: [Path("/tmp"), Path("/usr"), 1] -> ["/tmp", "/usr", 1]. """
    if isinstance(obj, (str, int, float)):
        return obj
    elif isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        return type(obj)(serialize_structure(item) for item in obj)
    else:
        return str(obj)


def dataclass_asdict_no_defaults(obj) -> dict:
    """ Ignore the dataclass default values. """
    if not hasattr(obj, "__dataclass_fields__"):
        return obj

    result = {}
    for field in fields(obj):
        field_value = getattr(obj, field.name)
        default_value = field.default
        if field_value != default_value:
            if hasattr(field_value, "__dataclass_fields__"):
                result[field.name] = dataclass_asdict_no_defaults(field_value)
            else:
                result[field.name] = field_value
    return result


def merge_dicts(d1: dict, d2: dict):
    """ Recursively merge second dict to the first. """
    for key, value in d2.items():
        if isinstance(value, dict) and isinstance(d1.get(key), dict):
            merge_dicts(d1[key], value)
        else:  # replace / insert value
            d1[key] = value
    return d1


def naturalsize(value: float | str, *args) -> str:
    """ For a bare interface, humanize might not be installed. """
    if naturalsize_:
        return naturalsize_(value, *args)
    return str(value)


def validate_annotated_type(meta, value) -> bool:
    """ Raises: ValueError, NotImplementedError """
    if isinstance(meta, Gt):
        if not value > meta.gt:
            raise ValueError(f"Value {value} must be > {meta.gt}")
    elif isinstance(meta, Ge):
        if not value >= meta.ge:
            raise ValueError(f"Value {value} must be ≥ {meta.ge}")
    elif isinstance(meta, Lt):
        if not value < meta.lt:
            raise ValueError(f"Value {value} must be < {meta.lt}")
    elif isinstance(meta, Le):
        if not value <= meta.le:
            raise ValueError(f"Value {value} must be ≤ {meta.le}")
    elif isinstance(meta, MultipleOf):
        if value % meta.multiple_of != 0:
            raise ValueError(f"Value {value} must be a multiple of {meta.multiple_of}")
    elif isinstance(meta, Len):
        if meta.max_length is None:
            if not (meta.min_length <= len(value)):
                raise ValueError(f"Length {len(value)} must be at least {meta.min_length}")
        elif not (meta.min_length <= len(value) <= meta.max_length):
            raise ValueError(f"Length {len(value)} must be between {meta.min_length} and {meta.max_length}")
    else:
        raise NotImplementedError(f"Unknown predicated {meta}")
    return True
