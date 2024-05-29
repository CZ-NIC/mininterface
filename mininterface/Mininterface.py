from argparse import ArgumentParser
import csv
import logging
import re
import string
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Callable, List, Optional, TypeVar
from sys import exit
from dataclasses import MISSING
import yaml

from dialog import Dialog, DialogError, ExecutableNotFound

from .auxiliary import ConfigClass, ConfigInstance, get_args_allow_missing, get_descriptions, get_terminal_size
import re
import sys
from argparse import ArgumentParser
from tkinter import TclError
from typing import TypeVar

from tyro import cli
from tyro.extras import get_parser




logger = logging.getLogger(__name__)


class Cancelled(SystemExit):
    # We inherit from SystemExit so that the program exits without a traceback on GUI Escape.
    pass

class Mininterface:
    """ The base interface.
        Does not require any user input and hence is suitable for headless testing.
    """

    def __init__(self, title: str = ""):
        # , parser: ArgumentParser= None, args: ConfigInstance= None
        # self.parser = parser or ArgumentParser()
        # self.args = args or SimpleNamespace()
        # self.parser = ArgumentParser()
        self.title = title or "Mininterface"
        self.args : ConfigInstance = SimpleNamespace()
        """ Parsed arguments, fetched from cli by parse.args :meth:~Mininterface.parse_args """
        self.descriptions = {}
        """ Field descriptions """

    def __enter__(self) -> "Mininterface":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def alert(self, text: str) -> None:
        print("Alert text", text)
        return

    def ask(self, text: str) -> str:
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_args(self) -> ConfigInstance:
        print("Asking the args", self.args)
        return self.args

    def ask_number(self, text: str) -> int:
        """
        Let user write number. Empty input = 0.
        """
        print("Asking number", text)
        return 0

    def get_args(self, ask_on_empty_cli=True) -> ConfigInstance:
        """ Returns parsed .args. If program launched with no arguments, empty CLI, self.ask_args() are called """
        # Empty CLI → GUI edit
        if ask_on_empty_cli and len(sys.argv) <= 1:
            return self.ask_args()
        return self.args

    def parse_args(self, config: ConfigClass,
                   config_file: Path | None = None,
                   **kwargs) -> ConfigInstance:
        """ Parse CLI arguments, possibly merged from those in a config file.

        :param config: Class with the configuration.
        :param config_file: File to load YAML to be merged with the configuration. You do not have to re-define all the settings, you can choose a few.
        :param **kwargs The same as for argparse.ArgumentParser.
        :return: Configuration namespace.
        """
        # Load config file
        if config_file:
            disk = yaml.safe_load(config_file.read_text()) or {}  # empty file is ok
            # Nested dataclasses have to be properly initialized. YAML gave them as dicts only.
            for key in (key for key, val in disk.items() if isinstance(val, dict)):
                disk[key] = config.__annotations__[key](**disk[key])
            # To ensure the configuration file does not need to contain all keys, we have to fill in the missing ones.
            # Otherwise, tyro will spawn warnings about missing fields.
            static = {key: getattr(config, key, MISSING)
                      for key in config.__annotations__ if not key.startswith("__") and not key in disk}
            kwargs["default"] = SimpleNamespace(**(disk | static))

        # Load configuration from CLI
        parser: ArgumentParser = get_parser(config, **kwargs)
        self.descriptions = get_descriptions(parser)
        self.args = get_args_allow_missing(config, kwargs, parser)
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
