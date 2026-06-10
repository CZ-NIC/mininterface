"""Tyro-dependent docstring/description helpers, split out from auxiliary.py.

Keeping these separate lets child processes import auxiliary.flatten without
paying the ~20 ms cost of loading tyro. Tyro itself is imported lazily inside
the functions that need it, so importing this module is also cheap.
"""
from functools import lru_cache
from typing import Annotated, get_args, get_origin, get_type_hints
from dataclasses import fields

_tyro_loaded = False
_tyro_docstrings_available = False
_tyro_get_field_docstring = None
_tyro_get_callable_description = None
tyro = None


def _ensure_tyro():
    global _tyro_loaded, _tyro_docstrings_available, _tyro_get_field_docstring, _tyro_get_callable_description, tyro
    if _tyro_loaded:
        return
    _tyro_loaded = True
    try:
        import tyro as _tyro
        from tyro._docstrings import get_field_docstring as _gfd
        from tyro._docstrings import get_callable_description as _gcd
        tyro = _tyro
        _tyro_get_field_docstring = _gfd
        _tyro_get_callable_description = _gcd
        _tyro_docstrings_available = True
    except ImportError:
        pass


def get_class_description(obj) -> str:
    _ensure_tyro()
    if _tyro_get_callable_description:
        return _tyro_get_callable_description(obj)
    return ""


@lru_cache
def _get_descriptions_from_docstring(obj) -> dict[str, str]:
    """Extract field descriptions for all fields of a class.

    Uses tyro's internal helptext extraction (tyro._docstrings.get_field_docstring),
    which supports the same sources and precedence as tyro's own CLI generation:
      1. tyro.conf.arg(help=...)
      2. PEP 727 Doc
      3. Docstrings (attribute docstrings or class docstring params)
      4. Comments (inline or preceding)

    We used to rely on tyro.extras.get_parser(), but that was marked deprecated,
    so we call tyro's internal API directly instead.
    """
    _ensure_tyro()
    if not _tyro_docstrings_available:
        return {}

    result = {}

    # Highest priority: tyro.conf.arg(help=...) in Annotated metadata.
    try:
        hints = get_type_hints(obj, include_extras=True)
        ArgConfig = tyro.conf._confstruct._ArgConfig
        for field_name, hint in hints.items():
            if get_origin(hint) is Annotated:
                for meta in hint.__metadata__:
                    if isinstance(meta, ArgConfig) and meta.help:
                        result[field_name] = meta.help
    except Exception:
        hints = {}

    # Mid priority: docstrings and comments via tyro's own extraction.
    for field_name in hints:
        doc = _tyro_get_field_docstring(obj, field_name, ())
        if doc:
            result.setdefault(field_name, doc)

    # Lowest priority: field.metadata["help"] from dynamically generated
    # dataclasses (e.g. built from ArgumentParser via make_dataclass).
    try:
        for f in fields(obj):  # type: ignore
            if help_text := f.metadata.get("help"):
                result.setdefault(f.name, help_text)
    except TypeError:
        pass

    return result


def get_description(obj, param: str) -> str:
    desc = _get_descriptions_from_docstring(obj).get(param, "")
    if desc and desc.replace("-", "_") != param:
        return desc

    # We are missing mininterface[basic] requirement. Tyro is missing.
    # Without tyro, we are not able to evaluate the class: m.form(Env),
    # we can still evaluate its instance: m.form(Env()).
    # However, without descriptions.
    return ""
