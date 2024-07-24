import logging
import os
import re
from argparse import Action, ArgumentParser
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal, Optional, TypeVar, Union, get_args, get_type_hints
from unittest.mock import patch

try:
    # NOTE this should be clean up and tested on a machine without tkinter installable
    from tkinter import END, Entry, Text, Tk, Widget
    from tkinter.ttk import Checkbutton, Combobox
    from tkinter_form import Value
except ImportError:
    tkinter = None
    END, Entry, Text, Tk, Widget = (None,)*5

    @dataclass
    class Value:
        """ This class helps to enrich the field with a description. """
        val: Any
        description: str


from tyro import cli
from tyro._argparse_formatter import TyroArgumentParser

logger = logging.getLogger(__name__)

TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """


@dataclass
class FormField(Value):
    """ Bridge between the input values and a UI widget.
        Helps to creates a widget from the input value (includes description etc.),
        then transforms the value back (str to int conversion etc). """

    annotation: Any | None = None
    """ Used for validation. To convert an empty '' to None. """
    name: str | None = None  # NOTE: Only TextualInterface uses this by now.

    src: tuple[TD, TK] | None = None
    """ The original dict to be updated when UI ends. """
    src2: tuple[TD, TK] | None = None
    """ The original object to be updated when UI ends.
    NOTE should be merged to `src`
    """

    def __post_init__(self):
        self._original_desc = self.description

    def set_error_text(self, s):
        self.description = f"{s} {self._original_desc}"

    # TODO add testing
    def update(self, ui_value):
        """ UI value → FormField value → original value. (With type conversion and checks.)

            The value has been updated in a UI.
            Update accordingly the value in the original linked dict
            the mininterface was invoked with.

            Validates the type and do the transformation.
            (Ex: Some values might be nulled from "".)
        """
        fixed_value = ui_value
        if self.annotation:
            if ui_value == "" and type(None) in get_args(self.annotation):
                # The user is not able to set the value to None, they left it empty.
                # Cast back to None as None is one of the allowed types.
                # Ex: `severity: int | None = None`
                fixed_value = None
            elif self.annotation == Optional[int]:
                try:
                    fixed_value = int(ui_value)
                except ValueError:
                    pass

            if not isinstance(fixed_value, self.annotation):
                self.set_error_text(f"Type must be `{self.annotation}`!")
                return False  # revision needed

        # keep values if revision needed
        # We merge new data to the origin. If form is re-submitted, the values will stay there.
        self.val = ui_value

        # Store to the source user data
        if self.src:
            d, k = self.src
            d[k] = fixed_value
        else:
            d, k = self.src2
            setattr(d, k, fixed_value)
        return True

        # Fixing types:
        # This code would support tuple[int, int]:
        #
        #     self.types = get_args(self.annotation) \
        #     if isinstance(self.annotation, UnionType) else (self.annotation, )
        # "All possible types in a tuple. Ex 'int | str' -> (int, str)"
        #
        #
        # def convert(self):
        #     """ Convert the self.value to the given self.type.
        #         The value might be in str due to CLI or TUI whereas the programs wants bool.
        #     """
        #     # if self.value == "True":
        #     #     return True
        #     # if self.value == "False":
        #     #     return False
        #     if type(self.val) is str and str not in self.types:
        #         try:
        #             return literal_eval(self.val)  # ex: int, tuple[int, int]
        #         except:
        #             raise ValueError(f"{self.name}: Cannot convert value {self.val}")
        #     return self.val




ConfigInstance = TypeVar("ConfigInstance")
ConfigClass = Callable[..., ConfigInstance]
FormDict = dict[str, Union[FormField, 'FormDict']]
""" Nested form that can have descriptions (through FormField) instead of plain values. """


def dict_to_formdict(data: dict, factory=FormField) -> FormDict:
    fd = {}
    for key, val in data.items():
        if isinstance(val, dict):  # nested config hierarchy
            fd[key] = dict_to_formdict(val, factory=factory)
        else:  # scalar value
            # NOTE name=param is not set (yet?) in `config_to_formdict`, neither `src`
            fd[key] = factory(val, "", name=key, src=(data, key))
    return fd


# NOTE: Not used, remove
def config_to_formdict(args: ConfigInstance, descr: dict, _path="", factory=FormField) -> FormDict:
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
            params[param] = config_to_formdict(val, descr, _path=f"{_path}{param}.", factory=factory)
        elif not _path:  # scalar value in root
            params[main][param] = factory(val, descr.get(param), annotation, param, src2=(args, param))
        else:  # scalar value in nested
            params[param] = factory(val, descr.get(f"{_path}{param}"), annotation, param, src2=(args, param))
    return params

# NOTE: Not used, remove
def fix_types(origin: FormDict, data: dict) -> dict:
    """ Run validators of all FormField objects. If fails, outputs info.
        Return corrected data. (Ex: Some values might be nulled from "".)
    """
    def check(ordict, orkey, orval, dataPos: dict, dataKey, val):
        if isinstance(orval, FormField) and orval.annotation:
            fixed_val = val
            if val == "" and type(None) in get_args(orval.annotation):
                # The user is not able to set the value to None, they left it empty.
                # Cast back to None as None is one of the allowed types.
                # Ex: `severity: int | None = None`
                dataPos[dataKey] = fixed_val = None
            elif orval.annotation == Optional[int]:
                try:
                    dataPos[dataKey] = fixed_val = int(val)
                except ValueError:
                    pass

            if not isinstance(fixed_val, orval.annotation):
                orval.set_error_text(f"Type must be `{orval.annotation}`!")
                raise RuntimeError  # revision needed

        # keep values if revision needed
        # We merge new data to the origin. If form is re-submitted, the values will stay there.
        if isinstance(orval, FormField):
            orval.val = val
        else:
            ordict[orkey] = val

    try:
        for (key1, val1), (orkey1, orval1) in zip(data.items(), origin.items()):
            if isinstance(val1, dict):  # nested config hierarchy
                # NOTE: This allows only single nested dict.
                for (key2, val2), (orkey2, orval2) in zip(val1.items(), orval1.items()):
                    check(orval1, orkey2, orval2, data[key1], key2, val2)
            else:
                check(origin, orkey1, orval1, data, key1, val1)
    except RuntimeError:
        return False

    return data


def config_from_dict(args: ConfigInstance, data: dict):
    """ Fetch back data.
        Merge the dict of dicts from the GUI back into the object holding the configuration. """
    for group, params in data.items():
        for key, val in params.items():
            if group:
                setattr(getattr(args, group), key, val.val if isinstance(val, FormField) else val)
            else:
                setattr(args, key, val.val if isinstance(val, FormField) else val)


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


T = TypeVar("T")


def flatten(d: dict[str, T | dict]) -> Iterable[T]:
    """ Recursively traverse whole dict """
    for v in d.values():
        if isinstance(v, dict):
            yield from flatten(v)
        else:
            yield v
