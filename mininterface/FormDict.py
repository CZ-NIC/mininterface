""" FormDict tools.
    FormDict is not a real class, just a normal dict. But we need to put somewhere functions related to it.
"""
import logging
from argparse import Action, ArgumentParser
from typing import Callable, Optional, Type, TypeVar, Union, get_type_hints
from unittest.mock import patch

from tyro import cli
from tyro._argparse_formatter import TyroArgumentParser

from .FormField import FormField

logger = logging.getLogger(__name__)

ConfigInstance = TypeVar("ConfigInstance")
ConfigClass = Type[ConfigInstance]
FormDict = dict[str, Union[FormField, 'FormDict']]
""" Nested form that can have descriptions (through FormField) instead of plain values. """


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
            # NOTE name=param is not set (yet?) in `config_to_formdict`, neither `src`
            fd[key] = FormField(val, "", name=key, src=(data, key))
    return fd


def config_to_formdict(args: ConfigInstance, descr: dict, _path="") -> FormDict:
    """ Convert the dataclass produced by tyro into dict of dicts. """
    main = ""
    params = {main: {}} if not _path else {}
    for param, val in vars(args).items():
        annotation = None
        if val is None:
            wanted_type = get_type_hints(args.__class__).get(param)
            if wanted_type in (Optional[int], Optional[str]):
                # Since tkinter_form does not handle None yet, we have help it.
                # We need it to be able to write a number and if empty, return None.
                # This would fail: `severity: int | None = None`
                # Here, we convert None to str(""), in normalize_types we convert it back.
                annotation = wanted_type
                val = ""
            else:
                # An unknown type annotation encountered-
                # Since tkinter_form does not handle None yet, this will display as checkbox.
                # Which is not probably wanted.
                val = False
                logger.warn(f"Annotation {wanted_type} of `{param}` not supported by Mininterface."
                            "None converted to False.")
        if hasattr(val, "__dict__"):  # nested config hierarchy
            params[param] = config_to_formdict(val, descr, _path=f"{_path}{param}.")
        elif not _path:  # scalar value in root
            params[main][param] = FormField(val, descr.get(param), annotation, param, src2=(args, param))
        else:  # scalar value in nested
            params[param] = FormField(val, descr.get(f"{_path}{param}"), annotation, param, src2=(args, param))
    return params


def get_args_allow_missing(config: Type[ConfigInstance], kwargs: dict, parser: ArgumentParser) -> ConfigInstance:
    """ Fetch missing required options in GUI. """
    # On missing argument, tyro fail. We cannot determine which one was missing, except by intercepting
    # the error message function. Then, we reconstruct the missing options.
    # NOTE But we should rather invoke a GUI with the missing options only.
    original_error = TyroArgumentParser.error
    eavesdrop = ""

    def custom_error(self, message: str):
        nonlocal eavesdrop
        if not message.startswith("the following arguments are required:"):
            return original_error(self, message)
        eavesdrop = message
        raise SystemExit(2)  # will be catched

    # Set args to determine whether to use sys.argv.
    # Why settings args? Prevent tyro using sys.argv if we are in an interactive shell like Jupyter,
    # as sys.argv is non-related there.
    try:
        # Note wherease `"get_ipython" in globals()` returns True in Jupyter, it is still False
        # in a script a Jupyter cell runs. Hence we must put here this lengthty statement.
        global get_ipython
        get_ipython()
    except:
        args = None
    else:
        args = []
    try:
        with patch.object(TyroArgumentParser, 'error', custom_error):
            return cli(config, args=args, **kwargs)
    except BaseException as e:
        if hasattr(e, "code") and e.code == 2 and eavesdrop:  # Some arguments are missing. Determine which.
            for arg in eavesdrop.partition(":")[2].strip().split(", "):
                argument: Action = next(iter(p for p in parser._actions if arg in p.option_strings))
                argument.default = "DEFAULT"  # NOTE I do not know whether used
                if "." in argument.dest:  # missing nested required argument handler not implemented, we make tyro fail in CLI
                    pass
                else:
                    match argument.metavar:
                        case "INT":
                            setattr(kwargs["default"], argument.dest, 0)
                        case "STR":
                            setattr(kwargs["default"], argument.dest, "")
                        case _:
                            pass  # missing handler not implemented, we make tyro fail in CLI
            return cli(config, **kwargs)  # second attempt
        raise
