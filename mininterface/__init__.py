__all__ = ["run", "Mininterface", "Tag", "Cancelled", "Validation", "Options"]


def __getattr__(name: str):
    if name == "run":
        from ._lib.run import run
        globals()["run"] = run
        return run
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
