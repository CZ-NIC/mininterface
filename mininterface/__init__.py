from typing import TYPE_CHECKING as _TYPE_CHECKING

__all__ = ["run", "Mininterface", "Tag", "Cancelled", "Validation", "Options", "dialogs"]

if _TYPE_CHECKING:
    # Static names for type checkers / IDEs. At runtime these are loaded lazily in __getattr__
    # below (kept out of import time for a faster start); this block never executes at runtime.
    from . import dialogs
    from ._lib.run import run
    from ._mininterface import Mininterface
    from .exceptions import Cancelled
    from .tag import Tag
    from .tag.alias import Options, Validation


def __getattr__(name: str):
    if name == "run":
        from ._lib.run import run
        globals()["run"] = run
        return run
    if name == "dialogs":
        # import_module (not `from . import dialogs`) to avoid re-entering this __getattr__
        from importlib import import_module
        dialogs = import_module(".dialogs", __name__)
        globals()["dialogs"] = dialogs
        return dialogs
    if name == "Mininterface":
        from ._mininterface import Mininterface
        globals()["Mininterface"] = Mininterface
        return Mininterface
    if name == "Cancelled":
        from .exceptions import Cancelled
        globals()["Cancelled"] = Cancelled
        return Cancelled
    if name == "Tag":
        from .tag import Tag
        globals()["Tag"] = Tag
        return Tag
    if name == "Options":
        from .tag.alias import Options
        globals()["Options"] = Options
        return Options
    if name == "Validation":
        from .tag.alias import Validation
        globals()["Validation"] = Validation
        return Validation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
