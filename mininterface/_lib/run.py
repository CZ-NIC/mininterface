import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Literal, Optional, Sequence, Type


from .._mininterface import Mininterface
from ..exceptions import DependencyRequired, ValidationFail
from ..interfaces import get_interface
from ..settings import MininterfaceSettings
from .form_dict import EnvClass

try:
    from ..cli import Command, SubcommandPlaceholder
    from .argparse_support import parser_to_dataclass
    from .cli_flags import CliFlags as _CliFlags
    from .cli_parser import assure_args, parse_cli
    from .config_file import parse_config_file, ensure_settings_inheritance
    from .dataclass_creation import choose_subcommand, to_kebab_case
    from .start import Start
except DependencyRequired as e:
    assure_args, parse_cli, parse_config_file, ensure_settings_inheritance, parser_to_dataclass = (e,) * 5
    Start, SubcommandPlaceholder = (e,) * 2
    to_kebab_case, choose_subcommand, _CliFlags = (e,) * 3


def run(
    env_or_list: Type[EnvClass] | list[Type[EnvClass]] | ArgumentParser | None = None,
    ask_on_empty_cli: bool = False,
    title: str = "",
    config_file: Path | str | bool = True,
    *,
    add_help: bool = True,
    add_verbose: bool|int|Sequence[int] = True,
    add_version: Optional[str] = None,
    add_version_package: Optional[str] = None,
    add_quiet: bool = False,
    ask_for_missing: bool = True,
    # We do not use InterfaceType as a type here because we want the documentation to show full alias:
    interface: Type[Mininterface] | Literal["gui"] | Literal["tui"] | Literal["text"] | Literal["web"] | None = None,
    args: Optional[Sequence[str]] = None,
    settings: Optional[MininterfaceSettings] = None,
    **kwargs,
) -> Mininterface[EnvClass]:
    """The main access, start here.
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
            See the [Config file](Config-file.md) section.
        add_help: Adds the help flag.
        add_verbose: The default base Python verbosity logging level is `logging.WARNING`. Here you can add the verbose flag that automatically increases the level to `logging.INFO` (*-v*) or `logging.DEBUG` (*-vv*).
            Either, the value is `True` (the default) which means the base logging level stays at `logging.WARNING` and the flag is added. `False` means no flag is added.
            Also, it can be `int` to determine the default logging state (i.g. some programs prefer to show INFO by default) or a sequnce of `int`s for even finer control.

            The `add_vebose=True` example:

            ```python
            import logging
            from mininterface import run
            logger = logging.getLogger(__name__)

            m = run(add_verbose=True)
            logger.info("Info shown") # needs `-v` or `--verbose`
            logger.debug("Debug shown")  # needs `-vv`
            ```

            ```bash
            $ program.py
            # no output

            $ program.py --verbose
            Info shown

            $ program.py -vv
            Info shown
            Debug shown
            ```

            Apart from `True`, it can also be an `int`, claiming the base logging level. By default, in Python this is `logging.WARNING`. Here, we change it to `logging.INFO`.

            ```python
            m = run(add_verbose=logging.INFO)
            ```

            ```bash
            $ program.py
            Info shown

            $ program.py -v
            Info shown
            Debug shown
            ```

            Finally, it can be a sequence of `int`s, first of them is the base logging level, the others being successing levels.

            ```python
            m = run(add_verbose=(logging.WARNING, 25, logging.INFO, 15, logging.DEBUG))
            logger.warning("Warning shown") # default
            logger.log(25, "Subwarning shown") # needs `-v`
            logger.info("INFO shown")  # needs `-vv`
            logger.log(15, "Subinfo shown") # needs `-vvv`
            ```

            When user writes more `-v` than defined, the level sets to `logging.NOTSET`.

        add_version: Your program version. Adds the version flag.
            ```python
            run(add_version="1.2.5")
            ```

            ```bash
            $ program.py --help
            usage: _debug.py [-h] [--version]

            ╭─ options ───────────────────────────────────────────────────────────╮
            │ -h, --help           show this help message and exit                │
            │ --version            show program's version number (1.2.5) and exit │
            ╰─────────────────────────────────────────────────────────────────────╯
            ```

        add_quiet: Decrease verbosity, only print warnings and errors.
            ```python
            import logging
            logger = logging.getLogger(__name__)

            m = run(add_quiet=True)
            logger.error("Error shown") # needs `-v` or `--verbose`
            logger.warning("Warning shown") # strip with `-q` or `--quiet`
            logger.info("Info shown")
            ```

            ```bash
            $ program.py
            Error shown
            Warning shown

            $ program.py --quiet
            Error shown
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

    # Argparse argument, processed by tyro
    if not add_help:
        kwargs["add_help"] = False

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
        interface = environ.get("MININTERFACE_INTERFACE")
    if environ.get("MININTERFACE_ENFORCED_WEB"):
        interface = "web"

    if isinstance(assure_args, DependencyRequired) and not env_or_list:
        # Basic dependencies missing, we have no CLI capacities
        # Since the user needs no CLI, we return a bare interface.
        return get_interface(interface, title)
    args = assure_args(args)

    # Hidden meta-commands in args
    if environ.get("MININTERFACE_INTEGRATE_TO_SYSTEM"):
        del environ["MININTERFACE_INTEGRATE_TO_SYSTEM"]
        Start(title, interface).integrate(env_or_list or _Empty)
        quit()

    # Convert argparse
    if isinstance(env_or_list, ArgumentParser):
        env_or_list, add_version = parser_to_dataclass(env_or_list)

    # Parse config file
    kwargs, settings_conf = parse_config_file(env_or_list or _Empty, config_file, **kwargs)


    # Ensure settings inheritance
    MininterfaceSettings
    if settings or settings_conf:
        # previous settings are used to complement the 'mininterface' config file section
        settings = ensure_settings_inheritance(settings, settings_conf or {})

    # Choose an interface
    m = get_interface(interface, title, settings)

    # Resolve SubcommandPlaceholder
    if (
        ask_for_missing
        and args
        and args[0] == "subcommand"
        and "--help" not in args
        and isinstance(env_or_list, list)
        and SubcommandPlaceholder in env_or_list
    ):
        args[0] = to_kebab_case(choose_subcommand(env_or_list, m).__name__)

    # Parse CLI arguments, possibly merged from a config file.
    cf = _CliFlags(add_verbose, add_version, add_version_package, add_quiet)
    if env_or_list:
        # A single Env object, or a list of such objects (with one is not/being selected via args)
        # Load configuration from CLI and a config file
        try:
            parse_cli(
                env_or_list, kwargs, m, cf, ask_for_missing, args, ask_on_empty_cli
            )
        except Exception as e:
            # Undocumented MININTERFACE_DEBUG flag. Note ipdb package requirement.
            from ast import literal_eval

            if literal_eval(environ.get("MININTERFACE_DEBUG", "0")):
                import traceback

                import ipdb

                traceback.print_exception(e)
                ipdb.post_mortem()
            else:
                raise

        # Command run
        _ensure_command_run(m)
    else:
        # C) No Env object
        # even though there is no configuration, yet we need to parse CLI for meta-commands like --help or --verbose
        parse_cli(_Empty, {}, m, cf, ask_for_missing, args)

    return m


def _ensure_command_run(m: "Miniterface"):
    env = m.env
    if isinstance(env, Command):
        while True:
            try:
                env.run()
                break
            except ValidationFail:
                m.form()


@dataclass
class _Empty:
    pass
