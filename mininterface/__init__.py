from argparse import ArgumentParser
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Sequence, Type

from .cli_parser import assure_args, parse_cli, parse_config_file, parser_to_dataclass
from .exceptions import Cancelled, InterfaceNotAvailable
from .form_dict import DataClass, EnvClass
from .interfaces import get_interface
from .mininterface import EnvClass, Mininterface
from .settings import MininterfaceSettings
from .start import Start
from .subcommands import Command, SubcommandPlaceholder
from .tag import Tag
from .tag.alias import Options, Validation

# NOTE:
# ask_for_missing does not work with tyro Positional, stays missing.
# @dataclass
# class Env:
#   files: Positional[list[Path]]

# NOTE: imgs missing in Interfaces.md


@dataclass
class _Empty:
    pass


def run(env_or_list: Type[EnvClass] | list[Type[Command]] | ArgumentParser | None = None,
        ask_on_empty_cli: bool = False,
        title: str = "",
        config_file: Path | str | bool = True,
        add_verbosity: bool = True,
        ask_for_missing: bool = True,
        # We do not use InterfaceType as a type here because we want the documentation to show full alias:
        interface: Type[Mininterface] | Literal["gui"] | Literal["tui"] | Literal["text"] | None = None,
        args: Optional[Sequence[str]] = None,
        settings: Optional[MininterfaceSettings] = None,
        **kwargs) -> Mininterface[EnvClass]:
    """ The main access, start here.
    Wrap your configuration dataclass into `run` to access the interface. An interface is chosen automatically,
    with the preference of the graphical one, regressed to a text interface for machines without display.
    Besides, if given a configuration dataclass, the function enriches it with the CLI commands and possibly
    with the default from a config file if such exists.
    It searches the config file in the current working directory,
    with the program name ending on *.yaml*, ex: `program.py` will fetch `./program.yaml`.

    Args:
        env_or_list:
            * `dataclass` Dataclass with the configuration. Their values will be modified with the CLI arguments.
            * `list` of [Commands][mininterface.subcommands.Command] let you create multiple commands within a single program, each with unique options.
            * `argparse.ArgumentParser` Not as powerful as the `dataclass` but should you need to try out whether to use the Mininterface instead of the old [`argparse`](https://docs.python.org/3/library/argparse.html), this is the way to go.
            * `None` You need just the dialogs, no CLI/config file parsing.


        ask_on_empty_cli: If program was launched with no arguments (empty CLI), invokes self.form() to edit the fields.
            (Withdrawn when `ask_for_missing` happens.)
            ```python
            @dataclass
            class Env:
            number: int = 3
            text: str = ""
            m = run(Env, ask_on_empty=True)
            ```

            ```bash
            $ program.py  #  omitting all parameters
            # Dialog for `number` and `text` appears
            $ program.py --number 3
            # No dialog appears
            ```
        title: The main title. If not set, taken from `prog` or program name.
        config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
            If set to True (default), we try to find one in the current working dir,
            whose name stem is the same as the program's.
            Ex: `program.py` will search for `program.yaml`.
            If False, no config file is used.
        add_verbosity: Adds the verbose flag that automatically sets the level to `logging.INFO` (*-v*) or `logging.DEBUG` (*-vv*).

            ```python
            import logging
            logger = logging.getLogger(__name__)

            m = run(Env, add_verbosity=True)
            logger.info("Info shown") # needs `-v` or `--verbose`
            logger.debug("Debug not shown")  # needs `-vv`
            # $ program.py --verbose
            # Info shown
            ```

            ```bash
            $ program.py --verbose
            Info shown
            ```

        ask_for_missing: If some required fields are missing at startup, we ask for them in a UI instead of program exit.

            ```python
            @dataclass
            class Env:
                required_number: int
            m = run(Env, ask_for_missing=True)
            ```

            ```bash
            $ program.py  # omitting --required-number
            # Dialog for `required_number` appears
            ```
        interface: Which interface to prefer. By default, we use the GUI, the fallback is the TUI.
            You may write "gui" or "tui" literal or pass a specific Mininterface type,
            see the full [list](Interfaces.md) of possible interfaces.
            If not set, we look also for an environment variable MININTERFACE_INTERFACE and in the config file.
        args: Parse arguments from a sequence instead of the command line.
        settings: Default settings. These might be further modified by the 'mininterface' section in the config file.
    Kwargs:
        The same as for [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html).


    Returns:
        An interface, ready to be used.

    You cay context manager the function by a `with` statement.
    The stdout will be redirected to the interface (ex. a GUI window).

    ```python
    from dataclasses import dataclass
    from mininterface import run

    @dataclass
    class Env:
        my_number: int = 4

    with run(Env) as m:
        print(f"Your important number is {m.env.my_number}")
        boolean = m.confirm("Is that alright?")
    ```

    ![Small window with the text 'Your important number'](asset/hello-with-statement.webp "With statement to redirect the output")
    ![The same in terminal'](asset/hello-with-statement-tui.avif "With statement in TUI fallback")
    """
    # Undocumented experimental: The `env_class` may be a function as well. We invoke its parameters.
    # However, as Mininterface.env stores the output of the function instead of the Argparse namespace,
    # methods like `Mininterface.form(None)` (to ask for editing the env values) will work unpredictibly.
    # Also, the config file seems to be fetched only for positional (missing) parameters,
    # and ignored for keyword (filled) parameters.
    # It seems to be this is the tyro's deal and hence it might start working any time.
    # If not, we might help it this way:
    #     `if isinstance(config, FunctionType): config = lambda: config(**kwargs["default"])`
    #
    # Undocumented experimental: `default` keyword argument for tyro may serve for default values instead of a config file.

    # Prepare the config file
    if config_file is True and not kwargs.get("default"):
        # Undocumented feature. User put a namespace into kwargs["default"]
        # that already serves for defaults. We do not fetch defaults yet from a config file.
        try:
            cf = Path(sys.argv[0]).with_suffix(".yaml")
        except ValueError:
            # when invoking raw python interpreter in CLI: PosixPath('.') has an empty name
            config_file = None
        else:
            if cf.exists():
                config_file = cf
    if isinstance(config_file, bool):
        config_file = None
    elif isinstance(config_file, str):
        config_file = Path(config_file)

    # Determine title
    title = title or kwargs.get("prog") or Path(sys.argv[0]).name
    if not interface:
        interface = os.environ.get("MININTERFACE_INTERFACE")
    start = Start(title, interface)

    # Convert argparse
    if isinstance(env_or_list, ArgumentParser):
        env_or_list = parser_to_dataclass(env_or_list)

    # Hidden meta-commands in args
    args = assure_args(args)
    if len(args) == 1 and args[0] == "--integrate-to-system":
        start.integrate(env_or_list or _Empty)
        quit()

    env, wrong_fields = None, {}
    if isinstance(env_or_list, list) and SubcommandPlaceholder in env_or_list and args and args[0] == "subcommand":
        start.choose_subcommand(env_or_list, args=args[1:])
    elif isinstance(env_or_list, list) and not args:
        start.choose_subcommand(env_or_list)
    else:
        # Parse CLI arguments, possibly merged from a config file.
        kwargs, settings = parse_config_file(env_or_list or _Empty, config_file, settings, **kwargs)
        if env_or_list:
            # Load configuration from CLI and a config file
            env, wrong_fields = parse_cli(env_or_list, kwargs, add_verbosity, ask_for_missing, args)
        else:  # even though there is no configuration, yet we need to parse CLI for meta-commands like --help or --verbose
            parse_cli(_Empty, {}, add_verbosity, ask_for_missing, args)

    # Build the interface
    if os.environ.get("MININTERFACE_ENFORCED_WEB"):
        interface = "web"
    m = get_interface(interface, title, settings, env)

    # Empty CLI → GUI edit
    if ask_for_missing and wrong_fields:
        # Some fields must be set.
        m.form(wrong_fields)
        {setattr(m.env, k, v.val) for k, v in wrong_fields.items()}
    elif ask_on_empty_cli and len(sys.argv) <= 1:
        m.form()

    return m


__all__ = ["run", "Mininterface", "Tag",
           "InterfaceNotAvailable", "Cancelled",
           "Validation", "Options"]
