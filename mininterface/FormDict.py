""" FormDict tools.
    FormDict is not a real class, just a normal dict. But we need to put somewhere functions related to it.
"""
from contextlib import ExitStack
import logging
from argparse import Action, ArgumentParser
from typing import Any, Callable, Optional, Type, TypeVar, Union, get_type_hints
from unittest.mock import patch

from tyro import cli
from tyro._argparse_formatter import TyroArgumentParser

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
            # NOTE name=param is not set (yet?) in `config_to_formdict`, neither `src`
            fd[key] = FormField(val, "", name=key, src_dict=(data, key)) if not isinstance(val, FormField) else val
    return fd


def formdict_to_widgetdict(d: FormDict | Any, widgetize_callback: Callable):
    if isinstance(d, dict):
        return {k: formdict_to_widgetdict(v, widgetize_callback) for k, v in d.items()}
    elif isinstance(d, FormField):
        return widgetize_callback(d)
    else:
        return d


def dataclass_to_formdict(env: EnvClass, descr: dict, _path="") -> FormDict:
    """ Convert the dataclass produced by tyro into dict of dicts. """
    main = ""
    params = {main: {}} if not _path else {}
    for param, val in vars(env).items():
        annotation = None
        if val is None:
            wanted_type = get_type_hints(env.__class__).get(param)
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
            params[param] = dataclass_to_formdict(val, descr, _path=f"{_path}{param}.")
        elif not _path:  # scalar value in root
            params[main][param] = FormField(val, descr.get(param), annotation, param, src_obj=(env, param))
        else:  # scalar value in nested
            params[param] = FormField(val, descr.get(f"{_path}{param}"), annotation, param, src_obj=(env, param))
    return params


def get_env_allow_missing(config: Type[EnvClass], kwargs: dict, parser: ArgumentParser, add_verbosity: bool) -> EnvClass:
    """ Fetch missing required options in GUI. """
    # On missing argument, tyro fail. We cannot determine which one was missing, except by intercepting
    # the error message function. Then, we reconstruct the missing options.
    # NOTE But we should rather invoke a GUI with the missing options only.
    eavesdrop = ""

    def custom_error(self: TyroArgumentParser, message: str):
        nonlocal eavesdrop
        if not message.startswith("the following arguments are required:"):
            return super(TyroArgumentParser, self).error(message)
        eavesdrop = message
        raise SystemExit(2)  # will be catched

    def custom_init(self: TyroArgumentParser, *args, **kwargs):
        super(TyroArgumentParser, self).__init__(*args, **kwargs)
        default_prefix = '-' if '-' in self.prefix_chars else self.prefix_chars[0]
        self.add_argument(default_prefix+'v', default_prefix*2+'verbose', action='count', default=0,
                          help="Verbosity level. Can be used twice to increase.")

    def custom_parse_known_args(self: TyroArgumentParser, args=None, namespace=None):
        namespace, args = super(TyroArgumentParser, self).parse_known_args(args, namespace)
        # NOTE We may check that the Env does not have its own `verbose``
        if hasattr(namespace, "verbose"):
            if namespace.verbose > 0:
                log_level = {
                    1: logging.INFO,
                    2: logging.DEBUG,
                    3: logging.NOTSET
                }.get(namespace.verbose, logging.NOTSET)
                logging.basicConfig(level=log_level, format='%(levelname)s - %(message)s')
            delattr(namespace, "verbose")
        return namespace, args

    # Set env to determine whether to use sys.argv.
    # Why settings env? Prevent tyro using sys.argv if we are in an interactive shell like Jupyter,
    # as sys.argv is non-related there.
    try:
        # Note wherease `"get_ipython" in globals()` returns True in Jupyter, it is still False
        # in a script a Jupyter cell runs. Hence we must put here this lengthty statement.
        global get_ipython
        get_ipython()
    except:
        env = None
    else:
        env = []
    try:
        # Mock parser
        patches = [patch.object(TyroArgumentParser, 'error', custom_error)]
        if add_verbosity:  # Mock parser to add verbosity
            patches.extend((
                patch.object(TyroArgumentParser, '__init__', custom_init),
                patch.object(TyroArgumentParser, 'parse_known_args', custom_parse_known_args)
            ))
        with ExitStack() as stack:
            [stack.enter_context(p) for p in patches]  # apply just the chosen mocks
            return cli(config, args=env, **kwargs)
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
