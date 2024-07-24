import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type
from unittest.mock import patch

try:
    from mininterface.GuiInterface import GuiInterface
except ImportError:
    if TYPE_CHECKING:
        pass
    else:
        GuiInterface = None

from mininterface.Mininterface import ConfigClass, ConfigInstance, Mininterface
from mininterface.TuiInterface import ReplInterface, TuiInterface
from mininterface.TextualInterface import TextualInterface
from mininterface.auxiliary import FormField

# TODO auto-handle verbosity https://brentyi.github.io/tyro/examples/04_additional/12_counters/ ?
# TODO example on missing required options.


def run(config: ConfigClass | None = None,
        interface: Type[Mininterface] = GuiInterface or ReplInterface,  # NOTE we shuold use TuiInterface as a fallback
        **kwargs) -> Mininterface:
    """
    Wrap your configuration dataclass into `run` to access the interface. Normally, an interface is chosen automatically.
    We prefer the graphical one, regressed to a text interface on a machine without display.
    Besides, if given a configuration dataclass, the function enriches it with the CLI commands and possibly
    with the default from a config file if such exists.
    It searches the config file in the current working directory, with the program name ending on *.yaml*, ex: `program.py` will fetch `./program.yaml`.

    :param config: Dataclass with the configuration.
    :param interface: Which interface to prefer. By default, we use the GUI, the fallback is the REPL.
    :param **kwargs The same as for [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html).
    :return: Interface used.

    Undocumented: The `config` may be function as well. We invoke its paramters.
    However, Mininterface.args stores the output of the function instead of the Argparse namespace
    and methods like `Mininterface.ask_args()` will work unpredictibly..
    """
    # Build the interface
    prog = kwargs.get("prog") or sys.argv[0]
    # try:
    interface: GuiInterface | Mininterface = interface(prog)
    # except InterfaceNotAvailable:  # Fallback to a different interface
    #     interface = TuiInterface(prog)

    # Load configuration from CLI and a config file
    if config:
        cf = Path(sys.argv[0]).with_suffix(".yaml")
        interface.parse_args(config, cf if cf.exists() and not kwargs.get("default") else None, **kwargs)

    return interface


__all__ = ["run", "FormField"]
