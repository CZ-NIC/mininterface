import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type
from unittest.mock import patch


from .Mininterface import EnvClass, Mininterface
from .TextInterface import ReplInterface, TextInterface
from .FormField import FormField
from .common import InterfaceNotAvailable

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


def run(env_class: Type[EnvClass] | None = None,
        interface: Type[Mininterface] = GuiInterface or TuiInterface,
        config_file: Path|str = "",
        **kwargs) -> Mininterface[EnvClass]:
    """
    Main access.
    Wrap your configuration dataclass into `run` to access the interface. An interface is chosen automatically,
    with the preference of the graphical one, regressed to a text interface for machines without display.
    Besides, if given a configuration dataclass, the function enriches it with the CLI commands and possibly
    with the default from a config file if such exists.
    It searches the config file in the current working directory,
    with the program name ending on *.yaml*, ex: `program.py` will fetch `./program.yaml`.

    :param config: Dataclass with the configuration.
    :param interface: Which interface to prefer. By default, we use the GUI, the fallback is the Tui.
    :param **kwargs The same as for [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html).
    :return: Interface used.

    Undocumented: The `config` may be function as well. We invoke its parameters.
    However, as Mininterface.env stores the output of the function instead of the Argparse namespace,
    methods like `Mininterface.ask_env()` will work unpredictibly.
    Also, the config file seems to be fetched only for positional (missing) parameters,
    and ignored for keyword (filled) parameters.
    It seems to be this is the tyro's deal and hence it might start working any time.
    If not, we might help it this way:
        `if isinstance(config, FunctionType): config = lambda: config(**kwargs["default"])`
    """

    # Prepare the config file
    if not config_file and not kwargs.get("default") and env_class:
        cf = Path(sys.argv[0]).with_suffix(".yaml")
        if cf.exists():
            config_file = cf


    # Build the interface
    prog = kwargs.get("prog") or Path(sys.argv[0]).name
    try:
        interface = interface(prog, env_class, config_file, **kwargs)
    except InterfaceNotAvailable:  # Fallback to a different interface
        interface = TuiInterface(prog, env_class, config_file, **kwargs)

    # Load configuration from CLI and a config file
    # if env_class:
    #     cf = Path(sys.argv[0]).with_suffix(".yaml")
    #     interface._parse_env(env_class, cf if cf.exists() and not kwargs.get("default") else None, **kwargs)

    # NOTE draft – move the functionality inside Mininterface?
    # What will be the most used params?
    # run(config: Type[EnvInstance],
    #     prog="merge to kwargs later",
    #     config_file:Path|str="",
    #     interface: Type[Mininterface] = GuiInterface or TuiInterface,
    #     **kwargs)
    # title = prog or sys.argv
    # Mininterface(title, env_class, config_file, **kwargs)

    return interface


__all__ = ["run", "FormField", "InterfaceNotAvailable",
           "Mininterface", "GuiInterface", "TuiInterface", "TextInterface", "TextualInterface"
           ]
