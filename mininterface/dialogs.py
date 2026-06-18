"""Static dialog functions — prompt the user without calling [`run`][mininterface.run] first.

```python
from mininterface.dialogs import ask, confirm, select, alert, form

name = ask("What's your name?")
if confirm("Continue?"):
    alert(f"Hello {name}!")
```

Every function delegates to a single, lazily-created interface shared across the module.
This is the shortcut to use when you only need a few dialogs and do not parse the CLI nor a
config file. Should you need the parsed env, the persistent `with` window or full control,
use [`run`][mininterface.run] instead.
"""

# Helper imports are underscore-aliased so that `from mininterface.dialogs import <TAB>`
# offers only the five dialog functions, nothing else.
from typing import (
    Any as _Any,
    Iterable as _Iterable,
    Literal as _Literal,
    Optional as _Optional,
    Type as _Type,
    TYPE_CHECKING as _TYPE_CHECKING,
    overload as _overload,
)

from ._mininterface import Mininterface as _Mininterface
from .interfaces import get_interface as _create_interface
from .tag.select_tag import OptionsType as _OptionsType
from .tag.tag import Tag as _Tag, TagValue as _TagValue, ValidationCallback as _ValidationCallback

if _TYPE_CHECKING:
    from ._lib.form_types import DataClass as _DataClass
    from ._lib.form_dict import FormDict as _FormDict

__all__ = ["ask", "confirm", "select", "alert", "form"]

_m: _Optional[_Mininterface] = None
""" The single interface shared by every module-level dialog function. """


def _get_interface() -> _Mininterface:
    """The single interface shared by the dialog functions, created lazily on first use.

    The first dialog call builds one interface and caches it; every later call reuses it.
    The best available interface is chosen (GUI → TUI → text); ``MININTERFACE_INTERFACE``
    overrides the preference. For an explicitly configured interface, use
    [`mininterface.interfaces.get_interface`][mininterface.interfaces.get_interface]
    or [`run`][mininterface.run] instead.
    """
    global _m
    if _m is None:
        _m = _create_interface()  # respects MININTERFACE_INTERFACE / MININTERFACE_ENFORCED_WEB
    return _m


def alert(text: str, *, timeout: int = 0) -> None:
    """Prompt the user to confirm the text. See [`Mininterface.alert`][mininterface.Mininterface.alert]."""
    return _get_interface().alert(text, timeout=timeout)


def ask(
    text: str,
    annotation: _Type[_TagValue] | _Tag[_TagValue] = str,
    validation: _Iterable[_ValidationCallback] | _ValidationCallback | None = None,
) -> _TagValue:
    """Prompt the user to input a value – text, number, ... See [`Mininterface.ask`][mininterface.Mininterface.ask]."""
    return _get_interface().ask(text, annotation, validation)


def confirm(text: str, default: bool = True, *, timeout: int = 0) -> bool:
    """Display confirm box and return bool. See [`Mininterface.confirm`][mininterface.Mininterface.confirm]."""
    return _get_interface().confirm(text, default, timeout=timeout)


# default + multiple none -> single
@_overload
def select(
    options: _OptionsType[_TagValue],
    title: str = "",
    default: None = ...,
    tips: _OptionsType[_TagValue] | None = None,
    multiple: None = ...,
    skippable: bool = True,
    launch: bool = True,
) -> _TagValue: ...


# Multiple is True → list
@_overload
def select(
    options: _OptionsType[_TagValue],
    title: str = "",
    default: None = None,
    tips: _OptionsType[_TagValue] | None = None,
    multiple: _Literal[True] = True,
    skippable: bool = True,
    launch: bool = True,
) -> list[_TagValue]: ...


# default is iterable -> list
@_overload
def select(
    options: _OptionsType[_TagValue],
    title: str = "",
    default: _OptionsType[_TagValue] = ...,
    tips: _OptionsType[_TagValue] | None = None,
    multiple: None = None,
    skippable: bool = True,
    launch: bool = True,
) -> list[_TagValue]: ...


# multiple is False or unspecified, default is singular → single
@_overload
def select(
    options: _OptionsType[_TagValue],
    title: str = "",
    default: _TagValue = ...,
    tips: _OptionsType[_TagValue] | None = None,
    multiple: _Literal[False] = False,
    skippable: bool = True,
    launch: bool = True,
) -> _TagValue: ...


def select(
    options: _OptionsType[_TagValue],
    title: str = "",
    default: _TagValue | _OptionsType[_TagValue] | None = None,
    tips: _OptionsType[_TagValue] | None = None,
    multiple: _Optional[bool] = None,
    skippable: bool = True,
    launch: bool = True,
) -> _TagValue | list[_TagValue] | _Any:
    """Prompt the user to select. See [`Mininterface.select`][mininterface.Mininterface.select]."""
    # The wrapper's @overloads above give callers precise types. The implementation forwards
    # argument unions wider than any single Mininterface.select overload, so a typed call would
    # never resolve — `m: _Any` erases the type only here (and, unlike a concrete annotation, is
    # not narrowed back to the overloaded method).
    m: _Any = _get_interface()
    return m.select(options, title, default, tips, multiple, skippable, launch)


# form=None edits the shared interface's (untyped) env, hence the _Any return there.
@_overload
def form(form: None = None, title: str = "", *, submit: str | bool = True) -> _Any: ...
@_overload
def form(form: "_FormDict", title: str = "", *, submit: str | bool = True) -> "_FormDict": ...
@_overload
def form(form: "_Type[_DataClass]", title: str = "", *, submit: str | bool = True) -> "_DataClass": ...
@_overload
def form(form: "_DataClass", title: str = "", *, submit: str | bool = True) -> "_DataClass": ...


def form(
    form: "_DataClass | _Type[_DataClass] | _FormDict | None" = None,
    title: str = "",
    *,
    submit: str | bool = True,
) -> _Any:
    """Prompt the user to fill up an arbitrary form. See [`Mininterface.form`][mininterface.Mininterface.form]."""
    m: _Any = _get_interface()  # untyped forward — see the note in select() above
    return m.form(form, title, submit=submit)
