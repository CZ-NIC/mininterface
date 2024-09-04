import sys
from argparse import ArgumentParser
from dataclasses import MISSING
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Type

import yaml
from tyro.extras import get_parser

from .auxiliary import get_descriptions
from .common import InterfaceNotAvailable
from .FormDict import EnvClass, get_env_allow_missing
from .FormField import FormField
from .Mininterface import EnvClass, Mininterface
from .TextInterface import ReplInterface, TextInterface

# Import optional interfaces
try:
    from mininterface.GuiInterface import GuiInterface
except ImportError:
    if TYPE_CHECKING:
        pass  # Replace TYPE_CHECKING with `type GuiInterface = None` since Python 3.12
    else:
        GuiInterface = None
try:
    from mininterface.TextualInterface import TextualInterface
except ImportError:
    TextualInterface = None


# TODO auto-handle verbosity https://brentyi.github.io/tyro/examples/04_additional/12_counters/ ?
# TODO example on missing required options.

class TuiInterface(TextualInterface or TextInterface):
    pass


def _parse_env(env_class: Type[EnvClass],
                config_file: Path | None = None,
                **kwargs) -> tuple[EnvClass|None, dict]:
    """ Parse CLI arguments, possibly merged from a config file.

    :param env_class: Class with the configuration.
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
            disk[key] = env_class.__annotations__[key](**disk[key])
        # To ensure the configuration file does not need to contain all keys, we have to fill in the missing ones.
        # Otherwise, tyro will spawn warnings about missing fields.
        static = {key: getattr(env_class, key, MISSING)
                    for key in env_class.__annotations__ if not key.startswith("__") and not key in disk}
        kwargs["default"] = SimpleNamespace(**(disk | static))

    # Load configuration from CLI
    parser: ArgumentParser = get_parser(env_class, **kwargs)
    descriptions = get_descriptions(parser)
    env = get_env_allow_missing(env_class, kwargs, parser)
    return env, descriptions

def run(env_class: Type[EnvClass] | None = None,
        ask_on_empty_cli: bool=False, # TODO
        title: str = "",
        config_file: Path | str | bool = True,
        interface: Type[Mininterface] = GuiInterface or TuiInterface,
        **kwargs) -> Mininterface[EnvClass]:
    """
    Main access.
    Wrap your configuration dataclass into `run` to access the interface. An interface is chosen automatically,
    with the preference of the graphical one, regressed to a text interface for machines without display.
    Besides, if given a configuration dataclass, the function enriches it with the CLI commands and possibly
    with the default from a config file if such exists.
    It searches the config file in the current working directory,
    with the program name ending on *.yaml*, ex: `program.py` will fetch `./program.yaml`.

    :param env_class: Dataclass with the configuration. Their values will be modified with the CLI arguments.
    :param ask_on_empty: If program was launched with no arguments (empty CLI), invokes self.ask_env() to edit the fields.
    :param title: The main title. If not set, taken from `prog` or program name.
    :param config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
            If set to True (default), we try to find one in the current working dir,
            whose name stem is the same as the program's.
            Ex: `program.py` will search for `program.yaml`.
            If False, no config file is used.
    :param interface: Which interface to prefer. By default, we use the GUI, the fallback is the TUI.
    :param **kwargs The same as for [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html).
    :return: An interface, ready to be used.
    # TODO check docs and to readme

    Undocumented: The `env_class` may be a function as well. We invoke its parameters.
    However, as Mininterface.env stores the output of the function instead of the Argparse namespace,
    methods like `Mininterface.ask_env()` will work unpredictibly.
    Also, the config file seems to be fetched only for positional (missing) parameters,
    and ignored for keyword (filled) parameters.
    It seems to be this is the tyro's deal and hence it might start working any time.
    If not, we might help it this way:
        `if isinstance(config, FunctionType): config = lambda: config(**kwargs["default"])`
    """

    # Prepare the config file
    if config_file is True and not kwargs.get("default") and env_class:
        # NOTE: Why do we check kwargs.get("default") here?
        cf = Path(sys.argv[0]).with_suffix(".yaml")
        if cf.exists():
            config_file = cf
    if isinstance(config_file, bool):
        config_file = None
    elif isinstance(config_file, str):
        config_file = Path(config_file)

    # Load configuration from CLI and a config file
    if env_class:
        env, descriptions = _parse_env(env_class, config_file, **kwargs)

    # Build the interface
    title = title or kwargs.get("prog") or Path(sys.argv[0]).name
    try:
        interface = interface(title, env, descriptions)
    except InterfaceNotAvailable:  # Fallback to a different interface
        interface = TuiInterface(title, env, descriptions)

    # Empty CLI → GUI edit
    if ask_on_empty_cli and len(sys.argv) <= 1:
        interface.ask_env()

    return interface


__all__ = ["run", "FormField", "InterfaceNotAvailable",
           "Mininterface", "GuiInterface", "TuiInterface", "TextInterface", "TextualInterface"
           ]
