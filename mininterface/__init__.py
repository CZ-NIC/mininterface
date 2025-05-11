from argparse import ArgumentParser
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Sequence, Type

from .exceptions import Cancelled, DependencyRequired, InterfaceNotAvailable
from ._lib.form_dict import DataClass, EnvClass
from .interfaces import get_interface
from ._mininterface import EnvClass, Mininterface
from .settings import MininterfaceSettings
from .tag import Tag
from .tag.alias import Options, Validation

try:
    from ._lib.start import ChooseSubcommandOverview, Start
    from .cli import Command, SubcommandPlaceholder
    from ._lib.cli_parser import assure_args, parse_cli, parse_config_file, parser_to_dataclass
except DependencyRequired as e:
    assure_args, parse_cli, parse_config_file, parser_to_dataclass = (e,) * 4
    ChooseSubcommandOverview, Start, SubcommandPlaceholder = (e,) * 3


@dataclass
class _Empty:
    pass


def run(env_or_list: Type[EnvClass] | list[Type[EnvClass]] | ArgumentParser | None = None,
        ask_on_empty_cli: bool = False,
        title: str = "",
        config_file: Path | str | bool = True,
        add_verbose: bool = True,
        ask_for_missing: bool = True,
        # We do not use InterfaceType as a type here because we want the documentation to show full alias:
        interface: Type[Mininterface] | Literal["gui"] | Literal["tui"] | Literal["text"] | Literal["web"] | None = None,
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
            * `list` of dataclasses let you create multiple commands within a single program, each with unique options. You may use [Command][mininterface.cli.Command] descendants to be automatically run.
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
        add_verbose: Adds the verbose flag that automatically sets the level to `logging.INFO` (*-v*) or `logging.DEBUG` (*-vv*).

            ```python
            import logging
            logger = logging.getLogger(__name__)

            m = run(Env, add_verbose=True)
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
            If not set, we look also for an environment variable [`MININTERFACE_INTERFACE`](Interfaces.md#environment-variable-mininterface_interface) and in the config file.
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
    # NOTE add add_integrate flag

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
    if os.environ.get("MININTERFACE_ENFORCED_WEB"):
        interface = "web"

    if isinstance(assure_args, DependencyRequired) and not env_or_list:
        # Basic dependencies missing, we have no CLI capacities
        # Since the user needs no CLI, we return a bare interface.
        return get_interface(interface, title)
    args = assure_args(args)

    # Hidden meta-commands in args
    if os.environ.get("MININTERFACE_INTEGRATE_TO_SYSTEM"):
        del os.environ["MININTERFACE_INTEGRATE_TO_SYSTEM"]
        Start(title, interface).integrate(env_or_list or _Empty)
        quit()

    # Convert argparse
    if isinstance(env_or_list, ArgumentParser):
        env_or_list = parser_to_dataclass(env_or_list)

    # A) Superform – overview of the subcommands
    if ask_for_missing and isinstance(env_or_list, list):
        superform_args = None
        if SubcommandPlaceholder in env_or_list and args and args[0] == "subcommand":
            superform_args = args[1:]
        elif not args:
            superform_args = []

        if superform_args is not None:
            # Run Superform as multiple subcommands exist and we have to decide which one to run.
            m = get_interface(interface, title, settings, None)
            ChooseSubcommandOverview(env_or_list, m, args=superform_args, ask_for_missing=ask_for_missing)
            return m  # m with added `m.env`

    # B) A single Env object, or a list of such objects (with one is being selected via args)
    # C) No Env object

    # Parse CLI arguments, possibly merged from a config file.
    kwargs, settings = parse_config_file(env_or_list or _Empty, config_file, settings, **kwargs)
    if env_or_list:
        # B) single Env object
        # Load configuration from CLI and a config file
        env, wrong_fields = parse_cli(env_or_list, kwargs, add_verbose, ask_for_missing, args)
        m = get_interface(interface, title, settings, env)

        # Empty CLI → GUI edit
        if ask_for_missing and wrong_fields:
            # Some fields must be set.
            m.form(wrong_fields)
        elif ask_on_empty_cli and len(sys.argv) <= 1:
            m.form()

        # Even though Command is not documented to work with run(Env) (but only as run([Env])), it works.
        # Why? Because the subcommand chosen by CLI and not here in the SubcommandOverview will get here.
        # Why it is not documented? – What use-case would it have?
        # And if this env.run() raises a ValidationFail (as suggested in the documentation),
        # should we repeat? And will not it cycle in a cron script?
        if isinstance(env, Command):
            env.facet = m.facet
            env.interface = m
            env.init()
            env.run()
    else:
        # C) No Env object
        # even though there is no configuration, yet we need to parse CLI for meta-commands like --help or --verbose
        parse_cli(_Empty, {}, add_verbose, ask_for_missing, args)
        m = get_interface(interface, title, settings, None)

    return m


__all__ = ["run", "Mininterface", "Tag",
           "Cancelled",
           "Validation", "Options"]
