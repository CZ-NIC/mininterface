import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from .types import Validation, Choices, PathTag
from .cli_parser import _parse_cli
from .common import InterfaceNotAvailable, Cancelled
from .form_dict import DataClass, EnvClass
from .tag import Tag
from .mininterface import EnvClass, Mininterface
from .text_interface import ReplInterface, TextInterface
from . import validators

# Import optional interfaces
try:
    from mininterface.gui_interface import GuiInterface
except ImportError:
    if TYPE_CHECKING:
        pass  # Replace TYPE_CHECKING with `type GuiInterface = None` since Python 3.12
    else:
        GuiInterface = None
try:
    from mininterface.textual_interface import TextualInterface
except ImportError:
    TextualInterface = None


class TuiInterface(TextualInterface or TextInterface):
    pass

# NOTE:
# ask_for_missing does not work with tyro Positional, stays missing.
# @dataclass
# class Env:
#   files: Positional[list[Path]]


def run(env_class: Type[EnvClass] | None = None,
        ask_on_empty_cli: bool = False,
        title: str = "",
        config_file: Path | str | bool = True,
        add_verbosity: bool = True,
        ask_for_missing: bool = True,
        interface: Type[Mininterface] = GuiInterface or TuiInterface,
        **kwargs) -> Mininterface[EnvClass]:
    """ The main access, start here.
    Wrap your configuration dataclass into `run` to access the interface. An interface is chosen automatically,
    with the preference of the graphical one, regressed to a text interface for machines without display.
    Besides, if given a configuration dataclass, the function enriches it with the CLI commands and possibly
    with the default from a config file if such exists.
    It searches the config file in the current working directory,
    with the program name ending on *.yaml*, ex: `program.py` will fetch `./program.yaml`.

    Args:
        env_class: Dataclass with the configuration. Their values will be modified with the CLI arguments.
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
        interface: Which interface to prefer. By default, we use the GUI, the fallback is the TUI. See the full [list](Overview.md#all-possible-interfaces) of possible interfaces.

    Kwargs:
        The same as for [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html).


    Returns:
        An interface, ready to be used.

    You cay context manager the function by a `with` statement.
    The stdout will be redirected to the interface (ex. a GUI window).

    ```python
    with run(Env) as m:
        print(f"Your important number is {m.env.important_number}")
        boolean = m.is_yes("Is that alright?")
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
    if config_file is True and not kwargs.get("default") and env_class:
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

    # Load configuration from CLI and a config file
    env, wrong_fields = None, {}
    if env_class:
        env, wrong_fields = _parse_cli(env_class, config_file, add_verbosity, ask_for_missing, **kwargs)

    # Build the interface
    title = title or kwargs.get("prog") or Path(sys.argv[0]).name
    if "prog" not in kwargs:
        kwargs["prog"] = title
    try:
        if interface == "tui":  # undocumented feature
            interface = TuiInterface
        elif interface == "gui":  # undocumented feature
            interface = GuiInterface
        if interface is None:
            raise InterfaceNotAvailable  # GuiInterface might be None when import fails
        interface = interface(title, env)
    except InterfaceNotAvailable:  # Fallback to a different interface
        interface = TuiInterface(title, env)

    # Empty CLI → GUI edit
    if ask_for_missing and wrong_fields:
        # Some fields must be set.
        interface.form(wrong_fields)
        {setattr(interface.env, k, v.val) for k, v in wrong_fields.items()}
    elif ask_on_empty_cli and len(sys.argv) <= 1:
        interface.form()

    return interface


__all__ = ["run", "Tag", "validators", "InterfaceNotAvailable", "Cancelled",
           "Validation", "Choices", "PathTag",
           "Mininterface", "GuiInterface", "TuiInterface", "TextInterface", "TextualInterface"
           ]
