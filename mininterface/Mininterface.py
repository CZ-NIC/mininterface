import logging
import sys
from argparse import ArgumentParser
from dataclasses import MISSING
from pathlib import Path
from types import SimpleNamespace
from typing import Generic, Type

import yaml
from tyro.extras import get_parser

from .FormDict import ConfigClass, ConfigInstance, FormDict, get_args_allow_missing
from .auxiliary import get_descriptions

logger = logging.getLogger(__name__)


class Cancelled(SystemExit):
    # We inherit from SystemExit so that the program exits without a traceback on GUI Escape.
    pass


class Mininterface(Generic[ConfigInstance]):
    """ The base interface.
        Does not require any user input and hence is suitable for headless testing.
    """

    def __init__(self, title: str = ""):
        self.title = title or "Mininterface"
        self.args: ConfigInstance = SimpleNamespace()
        """ Parsed arguments, fetched from cli by parse.args """
        self.descriptions = {}
        """ Field descriptions """

    def __enter__(self) -> "Mininterface":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def alert(self, text: str) -> None:
        """ Prompt the user to confirm the text.  """
        print("Alert text", text)
        return

    def ask(self, text: str) -> str:
        """ Prompt the user to input a text.  """
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_args(self) -> ConfigInstance:
        """ Allow the user to edit whole configuration. (Previously fetched from CLI and config file by parse_args.) """
        print("Asking the args", self.args)
        return self.args

    def ask_number(self, text: str) -> int:
        """ Prompt the user to input a number. Empty input = 0. """
        print("Asking number", text)
        return 0

    def form(self, data: FormDict, title: str = "") -> dict:
        """ Prompt the user to fill up whole form.
            :param args: Dict of `{labels: default value}`. The form widget infers from the default value type.
                The dict can be nested, it can contain a subgroup.
                The default value might be `mininterface.FormField` that allows you to add descriptions.
                A checkbox example: `{"my label": FormField(True, "my description")}`
        """
        print(f"Asking the form {title}", data)
        return data  # NOTE – this should return dict, not FormDict (get rid of auxiliary.FormField values)

    def get_args(self, ask_on_empty_cli=True) -> ConfigInstance:
        """ Returns whole configuration (previously fetched from CLI and config file by parse_args).
            If program was launched with no arguments (empty CLI), invokes self.ask_args() to edit the fields. """
        # Empty CLI → GUI edit
        if ask_on_empty_cli and len(sys.argv) <= 1:
            return self.ask_args()
        return self.args

    def parse_args(self, config: Type[ConfigInstance],
                   config_file: Path | None = None,
                   **kwargs) -> ConfigInstance:
        """ Parse CLI arguments, possibly merged from a config file.

        :param config: Class with the configuration.
        :param config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
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
        """ Display confirm box, focusing yes. """
        print("Asking yes:", text)
        return True

    def is_no(self, text: str) -> bool:
        """ Display confirm box, focusing no. """
        print("Asking no:", text)
        return False
