import os
import re
import sys
from argparse import Action, ArgumentParser
from dataclasses import MISSING
from pathlib import Path
from tkinter import TclError
from types import SimpleNamespace
from typing import Callable, Generator, List, Optional, Type, TypeVar
from unittest.mock import patch

import yaml
from tyro import cli
from tyro._argparse_formatter import TyroArgumentParser
from tyro.extras import get_parser
from tkinter_form import Value

ConfigInstance = TypeVar("ConfigInstance")
ConfigClass = Callable[..., ConfigInstance]

def dataclass_to_dict(args: ConfigInstance, descr: dict, _path="") -> dict:
        """ Convert the dataclass produced by tyro into dict of dicts. """
        main = ""
        params = {main: {}} if not _path else {}
        for param, val in vars(args).items():
            if hasattr(val, "__dict__"):
                params[param] = dataclass_to_dict(val, descr, _path=f"{_path}{param}.")
            elif not _path:
                params[main][param] = Value(val, descr.get(param))
            else:
                params[param] = Value(val, descr.get(f"{_path}{param}"))
        return params

def dict_to_dataclass(args: ConfigInstance, data: dict):
    """ Convert the dict of dicts from the GUI back into the object holding the configuration. """
    for group, params in data.items():
        for key, val in params.items():
            if group:
                setattr(getattr(args, group), key, val)
            else:
                setattr(args, key, val)

def get_terminal_size():
    try:
        # XX when piping the input IN, it writes
        # echo "434" | convey -f base64  --debug
        # stty: 'standard input': Inappropriate ioctl for device
        # I do not know how to suppress this warning.
        height, width = (int(s) for s in os.popen('stty size', 'r').read().split())
        return height, width
    except (OSError, ValueError):
        return 0, 0

def get_args_allow_missing(config: ConfigClass, kwargs: dict, parser: ArgumentParser):
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
    try:
        with patch.object(TyroArgumentParser, 'error', custom_error):
            return cli(config, **kwargs)
    except BaseException as e:
        if hasattr(e, "code") and e.code == 2 and eavesdrop:  # Some arguments are missing. Determine which.
            for arg in eavesdrop.partition(":")[2].strip().split(", "):
                argument: Action = next(iter(p for p in parser._actions if arg in p.option_strings))
                argument.default = "HALO"
                if "." in argument.dest:  # missing nested required argument handler not implemented, we make tyro fail in CLI
                    pass
                else:
                    match argument.metavar:
                        case "INT":
                            setattr(kwargs["default"], argument.dest, 0)
                        case "STR":
                            setattr(kwargs["default"], argument.dest, "")
                        case _:
                            pass # missing handler not implemented, we make tyro fail in CLI
            return cli(config, **kwargs)  # second attempt
        raise

def get_descriptions(parser: ArgumentParser) -> dict:
        """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
        return {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help)
                for action in parser._actions}