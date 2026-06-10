from typing import Callable, Iterable, Optional, TypeVar

T = TypeVar("T")
KT = str
common_iterables = list, tuple, set
""" collections, and not a str """


def flatten(d: dict[str, T | dict], include_keys: Optional[Callable[[str], list]] = None) -> Iterable[T]:
    """Recursively traverse whole dict"""
    for k, v in d.items():
        if isinstance(v, dict):
            if include_keys:
                yield from include_keys(k)
            yield from flatten(v)
        else:
            yield v
