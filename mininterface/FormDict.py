""" FormDict tools.
    FormDict is not a real class, just a normal dict. But we need to put somewhere functions related to it.
"""
import logging
from typing import Any, Callable, Optional, TypeVar, Union, get_type_hints

from .FormField import FormField

logger = logging.getLogger(__name__)

EnvClass = TypeVar("EnvClass")
FormDict = dict[str, Union[FormField, 'FormDict']]
""" Nested form that can have descriptions (through FormField) instead of plain values. """

# NOTE: In the future, allow `bound=FormDict | EnvClass`, a dataclass (or its instance)
# to be edited too
# is_dataclass(v) -> dataclass or its instance
# isinstance(v, type) -> class, not an instance
FormDictOrEnv = TypeVar('FormT', bound=FormDict)  # | EnvClass)


def formdict_repr(d: FormDict) -> dict:
    """ For the testing purposes, returns a new dict when all FormFields are replaced with their values. """
    out = {}
    for k, v in d.items():
        if isinstance(v, FormField):
            v = v.val
        out[k] = formdict_repr(v) if isinstance(v, dict) else v
    return out


def dict_to_formdict(data: dict) -> FormDict:
    fd = {}
    for key, val in data.items():
        if isinstance(val, dict):  # nested config hierarchy
            fd[key] = dict_to_formdict(val)
        else:  # scalar value
            fd[key] = FormField(val, "", name=key, _src_dict=data, _src_key=key) \
                if not isinstance(val, FormField) else val
    return fd


def formdict_to_widgetdict(d: FormDict | Any, widgetize_callback: Callable, _key=None):
    if isinstance(d, dict):
        return {k: formdict_to_widgetdict(v, widgetize_callback, k) for k, v in d.items()}
    elif isinstance(d, FormField):
        if not d.name:  # restore the name from the user provided dict
            d.name = _key
        return widgetize_callback(d)
    else:
        return d


def dataclass_to_formdict(env: EnvClass, descr: dict, _path="") -> FormDict:
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
                logger.warn(f"Annotation {annotation} of `{param}` not supported by Mininterface."
                            "None converted to False.")
        if hasattr(val, "__dict__"):  # nested config hierarchy
            subdict[param] = dataclass_to_formdict(val, descr, _path=f"{_path}{param}.")
        else:
            params = {"val": val,
                      "_src_key": param,
                      "_src_obj": env
                      }
            if not _path:  # scalar value in root
                subdict[main][param] = FormField(description=descr.get(param), **params)
            else:  # scalar value in nested
                subdict[param] = FormField(description=descr.get(f"{_path}{param}"), **params)
    return subdict
