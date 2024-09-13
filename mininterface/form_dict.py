""" FormDict tools.
    FormDict is not a real class, just a normal dict. But we need to put somewhere functions related to it.
"""
import logging
from types import FunctionType, MethodType
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, Union, get_type_hints

if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self


from .tag import Tag, TagValue

if TYPE_CHECKING:
    from .facet import Facet

logger = logging.getLogger(__name__)

EnvClass = TypeVar("EnvClass")
FormDict = dict[str, TypeVar("FormDictRecursiveValue", TagValue, Tag, "Self")]
""" Nested form that can have descriptions (through Tag) instead of plain values.

Attention to programmers. Should we to change this type, check these IDE suggestions are still the same.
It is easy to mess it up because it is partly unclear and fragile.

```
from dataclasses import dataclass
from mininterface import run, Tag

@dataclass
class Env:
    test:int = 1
    pass

m = run(Env)
o1 = {"test1": "str", "test2": Tag(True)}
r1 = m.form(o1)
r1  # dict[str, Any] | Env
o2 = {"test1": "str"}
r2 = m.form(o2)
r2  # dict[str, str] | Env
o3 = {"test2": Tag(True)}
r3 = m.form(o3)
r3  # dict[str, Tag] | Env
r4 = m.form()
r4  # Env
```
"""
TagDict = dict[str, Union["Self" , Tag]]
""" Strict FormDict where the values are just recursive TagDicts or tags. """

# NOTE: In the future, allow `FormDict , EnvClass`, a dataclass (or its instance)
# to be edited too
# is_dataclass(v) -> dataclass or its instance
# isinstance(v, type) -> class, not an instance
# Then, we might get rid of ._descriptions because we will read from the model itself
# TypeVar('FormDictOrEnv', FormDict, EnvClass)
FormDictOrEnv = TypeVar('FormDictOrEnv', bound=FormDict)  # , EnvClass)


def formdict_resolve(d: FormDict, extract_main=False, _root=True) -> dict:
    """ For the testing purposes, returns a new dict when all Tags are replaced with their values.

    Args:
        extract_main: UI need the main section act as nested.
            At least `dataclass_to_formdict` does this.
            This extracts it back.
            {"": {"key": "val"}, "nested": {...}} -> {"key": "val", "nested": {...}}
    """
    out = {}
    for k, v in d.items():
        while isinstance(v, Tag):
            v = v.val
        out[k] = formdict_resolve(v, _root=False) if isinstance(v, dict) else v
    if extract_main and _root and "" in out:
        main = out[""]
        del out[""]
        return {**main, **out}
    return out


def dict_to_tagdict(data: dict, facet: "Facet" = None) -> TagDict:
    fd = {}
    for key, val in data.items():
        if isinstance(val, dict):  # nested config hierarchy
            fd[key] = dict_to_tagdict(val, facet)
        else:  # scalar value
            # TODO implement object fetching to the dataclasses below too
            # dataclass_to_tagdict
            d = {"facet": facet, "_src_dict":data, "_src_key":key}
            if not isinstance(val, Tag):
                tag = Tag(val, "", name=key, **d)
            else:
                tag = Tag(**d)._fetch_from(val)
            fd[key] = tag
    return fd


def formdict_to_widgetdict(d: FormDict | Any, widgetize_callback: Callable, _key=None):
    if isinstance(d, dict):
        return {k: formdict_to_widgetdict(v, widgetize_callback, k) for k, v in d.items()}
    elif isinstance(d, Tag):
        if not d.name:  # restore the name from the user provided dict
            d.name = _key
        return widgetize_callback(d)
    else:
        return d


def dataclass_to_tagdict(env: EnvClass, descr: dict, _path="") -> TagDict:
    """ Convert the dataclass produced by tyro into dict of dicts. """
    main = ""
    subdict = {main: {}} if not _path else {}
    for param, val in vars(env).items():
        annotation = get_type_hints(env.__class__).get(param)
        if val is None:
            if annotation in (Optional[int], Optional[str]):
                # Since tkinter_form does not handle None yet, we have help it.
                # We need it to be able to write a number and if empty, return None.
                # This would fail: `severity: int | None = None`
                # Here, we convert None to str(""), in normalize_types we convert it back.
                val = ""
            else:
                # An unknown type annotation encountered.
                # Since tkinter_form does not handle None yet, this will display as checkbox.
                # Which is not probably wanted.
                val = False
                logger.warning(f"Annotation {annotation} of `{param}` not supported by Mininterface."
                            "None converted to False.")
        if hasattr(val, "__dict__") and not isinstance(val, (FunctionType, MethodType)):  # nested config hierarchy
            # Why checking the isinstance? See Tag._is_a_callable.
            subdict[param] = dataclass_to_tagdict(val, descr, _path=f"{_path}{param}.")
        else:
            params = {"val": val,
                      "_src_key": param,
                      "_src_obj": env
                      }
            if not _path:  # scalar value in root
                subdict[main][param] = Tag(description=descr.get(param), **params)
            else:  # scalar value in nested
                subdict[param] = Tag(description=descr.get(f"{_path}{param}"), **params)
    return subdict
