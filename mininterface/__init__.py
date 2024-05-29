import sys
from pathlib import Path
from tkinter import TclError
from typing import Type
from unittest.mock import patch

from mininterface.GuiInterface import GuiInterface
from mininterface.Mininterface import ConfigClass, ConfigInstance, Mininterface
from mininterface.TuiInterface import ReplInterface, TuiInterface

# TODO auto-handle verbosity https://brentyi.github.io/tyro/examples/04_additional/12_counters/ ?
# TODO example on missing required options.


def run(config: ConfigClass | None = None,
        interface: Type[Mininterface] = GuiInterface,
        **kwargs) -> Mininterface:
    """

    :param config: Class with the configuration.
    :param interface: Which interface to prefer. By default, we use the GUI, the fallback is the REPL.
    :param **kwargs The same as for argparse.ArgumentParser.
    :return: Interface used.
    """
    # Build the interface
    try:
        interface: GuiInterface | Mininterface = interface(kwargs.get("prog"))
    except TclError:  # Fallback to a different interface
        interface = ReplInterface()

    # Load configuration from CLI and a config file
    if config:
        cf = Path(sys.argv[0]).with_suffix(".yaml")
        interface.parse_args(config, cf if cf.exists() and not kwargs.get("default") else None, **kwargs)

    return interface


__all__ = ["run"]
