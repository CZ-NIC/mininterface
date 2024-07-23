import os
import re
from argparse import Action, ArgumentParser
from typing import Any, Callable, TypeVar, Union
from unittest.mock import patch
try:
    # NOTE this shuold be clean up and tested on a machine without tkinter installable
    from tkinter import END, Entry, Text, Tk, Widget
    from tkinter.ttk import Combobox, Checkbutton
except ImportError:
    tkinter = None
    END, Entry, Text, Tk, Widget = (None,)*5

from tyro import cli
from tyro._argparse_formatter import TyroArgumentParser
try:
    from tkinter_form import Value
except ImportError:
    Value = None

ConfigInstance = TypeVar("ConfigInstance")
ConfigClass = Callable[..., ConfigInstance]
FormDict = dict[str, Union[Value, Any, 'FormDict']]
""" Nested form that can have descriptions (through Value) instead of plain values. """


def dataclass_to_dict(args: ConfigInstance, descr: dict, _path="") -> FormDict:
    """ Convert the dataclass produced by tyro into dict of dicts. """
    main = ""
    params = {main: {}} if not _path else {}
    for param, val in vars(args).items():
        if val is None:
            # TODO tkinter_form does not handle None yet.
            # This would fail: `severity: int | None = None`
            # We need it to be able to write a number and if empty, return None.
            val = False
        if hasattr(val, "__dict__"):  # nested config hierarchy
            params[param] = dataclass_to_dict(val, descr, _path=f"{_path}{param}.")
        elif not _path:  # scalar value in root
            params[main][param] = Value(val, descr.get(param))
        else:  # scalar value in nested
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
                            pass  # missing handler not implemented, we make tyro fail in CLI
            return cli(config, **kwargs)  # second attempt
        raise


def get_descriptions(parser: ArgumentParser) -> dict:
    """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
    return {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help)
            for action in parser._actions}


class RedirectText:
    """ Helps to redirect text from stdout to a text widget. """

    def __init__(self, widget: Text, pending_buffer: list, window: Tk) -> None:
        self.widget = widget
        self.max_lines = 1000
        self.pending_buffer = pending_buffer
        self.window = window

    def write(self, text):
        self.widget.pack(expand=True, fill='both')
        self.widget.insert(END, text)
        self.widget.see(END)  # scroll to the end
        self.trim()
        self.window.update_idletasks()
        self.pending_buffer.append(text)

    def flush(self):
        pass  # required by sys.stdout

    def trim(self):
        lines = int(self.widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.widget.delete(1.0, f"{lines - self.max_lines}.0")

def recursive_set_focus(widget: Widget):
    for child in widget.winfo_children():
        if isinstance(child, (Entry, Checkbutton, Combobox)):
            child.focus_set()
            return True
        if recursive_set_focus(child):
            return True
