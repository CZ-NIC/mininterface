""" FormDict tools.
    FormDict is not a real class, just a normal dict. But we need to put somewhere functions related to it.
"""
import logging
from warnings import warn
from dataclasses import fields, is_dataclass
from types import FunctionType, MethodType, SimpleNamespace
from typing import (TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar,
                    Union, get_args, get_type_hints)


from .auxiliary import get_description
from .tag import MissingTagValue, Tag, TagValue
from .tag_factory import tag_assure_type, tag_fetch, tag_factory

if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self

    from . import Mininterface

try:
    import attr
except ImportError:
    attr = None
try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None


logger = logging.getLogger(__name__)

DataClass = TypeVar("DataClass")
""" Any dataclass. Or a pydantic model or attrs. """
EnvClass = TypeVar("EnvClass", bound=DataClass)
""" Any dataclass. Its instance will be available through [miniterface.env] after CLI parsing. """
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
TagDict = dict[str, Union["Self", Tag]]
""" Strict FormDict where the values are just recursive TagDicts or tags. """

# NOTE: In the future, allow `FormDict , EnvClass`, a dataclass (or its instance)
# to be edited too
# TypeVar('FormDictOrEnv', FormDict, EnvClass)
# FormDictOrEnv = TypeVar('FormDictOrEnv', bound = FormDict | Type[EnvClass] | EnvClass)
FormDictOrEnv = TypeVar('FormDictOrEnv', bound=FormDict | DataClass)
# FormDictOrEnv = TypeVar('FormDictOrEnv', bound = FormDict | EnvClass)
# FormDictOrEnv = TypeVar('FormDictOrEnv', FormDict, Type[EnvClass], EnvClass)


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


def dict_to_tagdict(data: dict, mininterface: Optional["Mininterface"] = None) -> TagDict:
    fd = {}
    for key, val in data.items():
        if isinstance(val, dict):  # nested config hierarchy
            fd[key] = dict_to_tagdict(val, mininterface)
        else:  # scalar or Tag value
            d = {"facet": getattr(mininterface, "facet", None)}
            if not isinstance(val, Tag):
                tag = Tag(val, "", name=key, _src_dict=data, _src_key=key, **d)
            else:
                tag = tag_fetch(val, d)
            tag = tag_assure_type(tag)
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


def iterate_attributes(env: DataClass):
    """ Iterate public attributes of a model, including its parents. """
    if is_dataclass(env):
        # Why using fields instead of vars(env)? There might be some helper parameters in the dataclasses that should not be form editable.
        for f in fields(env):
            yield f.name, getattr(env, f.name)
    elif BaseModel and isinstance(env, BaseModel):
        for param, val in vars(env).items():
            yield param, val
        # NOTE private pydantic attributes might be printed to forms, because this makes test fail for nested models
        # for param, val in env.model_dump().items():
        #     yield param, val
    elif attr and attr.has(env):
        for f in attr.fields(env.__class__):
            yield f.name, getattr(env, f.name)
    else:  # might be a normal class; which is unsupported but mostly might work
        for param, val in vars(env).items():
            yield param, val


def iterate_attributes_keys(env: DataClass):
    """ Iterate public attributes of a model, including its parents. """
    if is_dataclass(env):
        # Why using fields instead of vars(env)? There might be some helper parameters in the dataclasses that should not be form editable.
        for f in fields(env):
            yield f.name
    elif BaseModel and isinstance(env, BaseModel):
        for param, val in vars(env).items():
            yield param
        # NOTE private pydantic attributes might be printed to forms, because this makes test fail for nested models
        # for param, val in env.model_dump().items():
        #     yield param, val
    elif attr and attr.has(env):
        for f in attr.fields(env.__class__):
            yield f.name
    else:  # might be a normal class; which is unsupported but mostly might work
        for param, val in vars(env).items():
            yield param


def dataclass_to_tagdict(env: EnvClass | Type[EnvClass], mininterface: Optional["Mininterface"] = None, _nested=False) -> TagDict:
    """ Convert the dataclass produced by tyro into dict of dicts. """
    main = {}
    if not _nested:  # root is nested under "" path
        subdict = {"": main} if not _nested else {}
    else:
        subdict = {}

    if isinstance(env, SimpleNamespace):
        raise ValueError(f"We got a namespace instead of class, CLI probably failed: {env}")

    for param, val in iterate_attributes(env):
        if isinstance(val, MissingTagValue):
            val = None  # need to convert as MissingTagValue has .__dict__ too
        if hasattr(val, "__dict__") and not isinstance(val, (FunctionType, MethodType)):  # nested config hierarchy
            # nested config hierarchy
            # Why checking the isinstance? See Tag._is_a_callable.
            subdict[param] = dataclass_to_tagdict(val, mininterface, _nested=True)
        else:  # scalar or Tag value
            d = {"description": get_description(env.__class__, param), "facet": getattr(mininterface, "facet", None)}
            if not isinstance(val, Tag):
                tag = tag_factory(val, _src_key=param, _src_obj=env, **d)
            else:
                tag = tag_fetch(val, d)
                tag = tag_assure_type(tag)
            (subdict if _nested else main)[param] = tag
    return subdict
