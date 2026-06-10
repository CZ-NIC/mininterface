import logging
import os
from dataclasses import fields, is_dataclass
from functools import lru_cache
from types import UnionType
from typing import (
    Any,
    Iterable,
    Union,
    Literal,
    get_args,
    get_origin,
    get_type_hints,
)

from annotated_types import Ge, Gt, Le, Len, Lt, MultipleOf
from .dict_utils import T, KT, common_iterables, flatten

logger = logging.getLogger(__name__)



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
        height, width = (int(s) for s in os.popen("stty size", "r").read().split())
        return height, width
    except (OSError, ValueError):
        return 0, 0


def yield_annotations(dataclass):
    yield from (cl.__annotations__ for cl in dataclass.__mro__ if is_dataclass(cl))


def get_annotation(class_, dest: str, crawled: list):
    """Get the attribute annotation according to the path in `dest` (dot means a nested subclass).
    Works for dataclass, pydantic, attrs.

    Ex: get_annotation(AppConfig, "bot.bot_id"))

    Ex: get_annotation(AppConfig, "app.subcommand.bot_id"), "message")
        class AppConfig:
            subcommand: Message|Console

        class Message:
            bot_id: int
    """
    parts = dest.split(".")
    current_cls = class_
    for part, class_name in zip(parts, crawled):
        if not isinstance(current_cls, type):  # `(Message | Console)`
            for cl in get_args(current_cls):
                if cl.__name__.casefold() == class_name:
                    current_cls = cl
                    break
            else:
                raise KeyError(f"Field {part!r} not accessible in {current_cls}")

        hints = get_type_hints(current_cls)

        if part not in hints:
            raise KeyError(f"Field {part!r} not found in {current_cls}")
        current_cls = hints[part]  # přejdi na typ dalšího levelu
    return current_cls


def get_or_create_parent_dict(d: dict, fname: str, ignore_last=False) -> dict:
    """
    Return the subdict for the path in `fname`, but ignore the last part.
    If a subdict does not exist, create it.
    If `fname` has only one part, return `d` directly.
    """
    parts = fname.split(".")
    # if len(parts) == 1:
    #     return d
    if ignore_last:
        parts = parts[:-1]

    current = d
    for part in parts:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    return current


# NOTE Deprecated
# def get_nested_class(class_: type, fname: str, ignore_last=False) -> type:
#     """
#     Traverse the class attributes according to the dot-separated path in `fname`
#     and return the type of the most deeply nested attribute.
#     Works for dataclasses, Pydantic models, and attrs classes.
#     """
#     parts = fname.split(".")
#     if ignore_last:
#         parts = parts[:-1]
#     current = class_

#     for part in parts:
#         if not hasattr(current, part):
#             raise AttributeError(f"{part} not found in {current}")
#         current = getattr(current, part)

#     return current


def matches_annotation(value, annotation) -> bool:
    """Check whether the value type corresponds to the annotation.
    Because built-in isinstance is not enough, it cannot determine parametrized generics.
    """
    # union, including Optional and UnionType
    if isinstance(annotation, UnionType) or get_origin(annotation) is Union:
        return any(matches_annotation(value, arg) for arg in get_args(annotation))

    # generics, ex. list, tuple
    origin = get_origin(annotation)
    if origin is Literal:
        return value in get_args(annotation)
    if origin:
        if not isinstance(value, origin):
            return False

        subtypes = get_args(annotation)
        if origin is list:
            return all(matches_annotation(item, subtypes[0]) for item in value)
        elif origin is tuple:
            if len(subtypes) == 2 and subtypes[1] is Ellipsis:  # ex. tuple[int, ...]
                return all(matches_annotation(v, subtypes[0]) for v in value)
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
    """Ex: [Path("/tmp"), Path("/usr"), 1] -> ["/tmp", "/usr", 1]."""
    if isinstance(obj, (str, int, float)):
        return obj
    elif isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        return type(obj)(serialize_structure(item) for item in obj)
    else:
        return str(obj)


def dataclass_asdict_no_defaults(obj) -> dict:
    """Ignore the dataclass default values."""
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
    """Recursively merge second dict to the first."""
    for key, value in d2.items():
        if isinstance(value, dict) and isinstance(d1.get(key), dict):
            merge_dicts(d1[key], value)
        else:  # replace / insert value
            d1[key] = value
    return d1


def dict_diff(a: dict, b: dict) -> dict:
    """Returns the B values where they differ."""
    result = {}
    for k in b:
        if isinstance(a.get(k), dict) and isinstance(b.get(k), dict):
            nested = dict_diff(a[k], b[k])
            if nested:
                result[k] = nested
        elif a.get(k) != b.get(k):
            result[k] = b[k]
    return result


def naturalsize(value: float | str, *args) -> str:
    """For a bare interface, humanize might not be installed."""
    try:
        from humanize import naturalsize as _naturalsize
        return _naturalsize(value, *args)
    except ImportError:
        return str(value)


def validate_annotated_type(meta, value) -> bool:
    """Raises: ValueError, NotImplementedError"""
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


def allows_none(annotation) -> bool:
    """True, if annotation allows None: `int | None`, `Optional[int]`, `Union[int,None]`."""
    if annotation is None:
        return True
    origin = get_origin(annotation)
    args = get_args(annotation)

    # if NoneType in get_args(self.annotation):

    if origin is Union or origin is UnionType:
        return any(arg is type(None) for arg in args)
    return False


def strip_none(annotation):
    """Return the same annotation but without NoneType inside a Union/Optional."""
    origin = get_origin(annotation)

    if origin is Union or origin is UnionType:
        args = tuple(arg for arg in get_args(annotation) if arg is not type(None))
        if len(args) == 1:
            return args[0]
        return Union[args]

    return annotation


@lru_cache(maxsize=1024 * 10)
def _get_origin(tp: Any):
    """
    Cached version of typing.get_origin.
    Faster when called repeatedly on the same type hints.
    """
    return get_origin(tp)


def remove_empty_dicts(d: dict):
    """Recursively remove empty dicts from a nested dict, in place."""
    for k in list(d):
        if isinstance(d[k], dict):
            remove_empty_dicts(d[k])
            if not d[k]:
                d.pop(k)
