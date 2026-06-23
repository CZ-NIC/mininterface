from typing import TYPE_CHECKING as _TYPE_CHECKING

# Single source of truth for the lazily-loaded public surface (PEP 562).
# Value is "module" for a submodule, or "module:attr" to pull one name out of it;
# `module` is relative to this package. Keep the _TYPE_CHECKING block below in sync —
# static type checkers / IDEs cannot follow this table.
_LAZY = {
    "run": "._lib.run:run",
    "Mininterface": "._mininterface:Mininterface",
    "Tag": ".tag:Tag",
    "Cancelled": ".exceptions:Cancelled",
    "Validation": ".tag.alias:Validation",
    "Options": ".tag.alias:Options",
    "dialogs": ".dialogs",
    "cli": ".cli",  # specialist sub-namespace; Command, SubcommandPlaceholder, Positional live here
}

__all__ = list(_LAZY)

if _TYPE_CHECKING:
    # Static names for type checkers / IDEs; mirrors _LAZY. Never executes at runtime
    # (the names are loaded lazily in __getattr__, kept out of import time for a faster start).
    from . import cli, dialogs
    from ._lib.run import run
    from ._mininterface import Mininterface
    from .exceptions import Cancelled
    from .tag import Tag
    from .tag.alias import Options, Validation


def __getattr__(name: str):
    if name == "__version__":
        from importlib.metadata import PackageNotFoundError, version

        try:
            value = version("mininterface")
        except PackageNotFoundError:  # running from a source tree, not installed
            value = "0.0.0+unknown"
        globals()["__version__"] = value
        return value

    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    # import_module (not `from . import x`) to avoid re-entering this __getattr__
    from importlib import import_module

    module_path, _, attr = spec.partition(":")
    module = import_module(module_path, __name__)
    value = getattr(module, attr) if attr else module
    globals()[name] = value  # cache: later access bypasses __getattr__ entirely (PEP 562)
    return value


def __dir__():
    # interactive/IDE discovery only — never on the attribute-access hot path.
    # `__version__` is deliberately NOT advertised here: it's an undocumented reflex
    # convenience (resolves on access) so it can be dropped later without a deprecation.
    return sorted(set(globals()) | set(__all__))
