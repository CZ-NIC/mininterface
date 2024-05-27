#!/usr/bin/env python3
import re
import sys
from argparse import ArgumentParser
from tkinter import TclError
from typing import TypeVar

from tyro import cli
from tyro.extras import get_parser

from mininterface.GuiInterface import GuiInterface
from mininterface.HeadlessInterface import HeadlessInterface
from tkinter_form import Value

OutT = TypeVar("OutT")


class Mininterface:
    def __init__(self, *args, **kwargs):
        self.parser: ArgumentParser = get_parser(*args, **kwargs)
        self.args: OutT = cli(*args, **kwargs)
        try:
            self.window: HeadlessInterface = GuiInterface()
        except TclError:  # Fallback to a different interface
            self.window = HeadlessInterface()

    def get_args(self, ask_on_empty_cli=True):
        # Empty CLI → GUI edit
        if ask_on_empty_cli and len(sys.argv) <= 1:
            return self.ask_args()
        return self.args

    def ask_args(self) -> OutT:
        """ Display a window form with all parameters. """

        # Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form.
        self.descriptions = {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help)
                             for action in self.parser._actions}

        print("44: p self.descriptions", self.descriptions)  # TODO

        params_ = self._dataclass_to_dict(self.args)

        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        data = self.window.run_dialog(self.parser.prog, params_)
        self._dict_to_dataclass(self.args, data)
        return self.args

    def _dataclass_to_dict(self, args, _path="") -> dict:
        """ Convert the dataclass produced by tyro into dict of dicts. """
        main = ""
        params = {main: {}} if not _path else {}
        for param, val in vars(args).items():
            if hasattr(val, "__dict__"):
                params[param] = self._dataclass_to_dict(val, _path=f"{_path}{param}.")
                ...
            elif not _path:
                params[main][param] = Value(val, self.descriptions.get(param))
            else:
                params[param] = Value(val, self.descriptions.get(f"{_path}{param}"))
        return params

    def _dict_to_dataclass(self, args: OutT, data: dict):
        """ Convert the dict of dicts from the GUI back into the object holding the configuration. """
        for group, params in data.items():
            for key, val in params.items():
                if group:
                    setattr(getattr(args, group), key, val)
                else:
                    setattr(args, key, val)


