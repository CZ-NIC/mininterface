from argparse import ArgumentParser
import csv
import logging
import re
import string
from pathlib import Path
import sys
from typing import List, Optional, TypeVar
from sys import exit

from dialog import Dialog, DialogError, ExecutableNotFound

from .auxiliary import get_terminal_size
import re
import sys
from argparse import ArgumentParser
from tkinter import TclError
from typing import TypeVar

from tyro import cli
from tyro.extras import get_parser

from tkinter_form import Value


logger = logging.getLogger(__name__)
OutT = TypeVar("OutT")


class Cancelled(Exception):
    pass


# class Debugged(Exception): TODO
#     pass

class HeadlessInterface:
    """ The base interface.
        Does not require any user input and hence is suitable for headless testing.
    """

    def __init__(self, parser: ArgumentParser, args: OutT):
        self.parser = parser
        self.args = args

    def __enter__(self) -> "HeadlessInterface":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def _load_descriptions(self) -> dict:
        """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
        return {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help)
                             for action in self.parser._actions}

    def _dataclass_to_dict(self, args, descr:dict, _path="") -> dict:
        """ Convert the dataclass produced by tyro into dict of dicts. """
        main = ""
        params = {main: {}} if not _path else {}
        for param, val in vars(args).items():
            if hasattr(val, "__dict__"):
                params[param] = self._dataclass_to_dict(val, descr, _path=f"{_path}{param}.")
                ...
            elif not _path:
                params[main][param] = Value(val, descr.get(param))
            else:
                params[param] = Value(val, descr.get(f"{_path}{param}"))
        return params

    def _dict_to_dataclass(self, args: OutT, data: dict):
        """ Convert the dict of dicts from the GUI back into the object holding the configuration. """
        for group, params in data.items():
            for key, val in params.items():
                if group:
                    setattr(getattr(args, group), key, val)
                else:
                    setattr(args, key, val)

    def alert(self, text: str) -> None:
        print("Alert text", text)
        return

    def ask(self, text:str) -> str:
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_args(self) -> OutT:
        print("Asking the args", self.args)
        return self.args


    def ask_number(self, text: str) -> int:
        """
        Let user write number. Empty input = 0.
        """
        print("Asking number", text)
        return 0

    def get_args(self, ask_on_empty_cli=True) -> OutT:
        # Empty CLI → GUI edit
        if ask_on_empty_cli and len(sys.argv) <= 1:
            return self.ask_args()
        return self.args

    def is_yes(self, text: str) -> bool:
        """ Display confirm box, focusing yes"""
        print("Asking yes:", text)
        return True

    def is_no(self, text: str) -> bool:
        """ Display confirm box, focusing no"""
        print("Asking no:", text)
        return False

    def hit_any_key(self, text: str) -> None:
        """ Display text and let the user hit any key. Skip when headless. """
        print(text + " Hit any key.")
        return
