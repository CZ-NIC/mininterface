# Configuration used by all minterfaces in the program.
# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass
from typing import Literal


@dataclass
class Gui:
    combobox_since: int = 5
    """ The threshold to switch from radio buttons to a combobox. """
    test: bool = False


@dataclass
class Tui:
    ...


@dataclass  # (slots=True)
class MininterfaceConfig:
    gui: Gui
    tui: Tui
    interface: Literal["gui"] | Literal["tui"] | None = None
    """ Enforce an interface. By default, we choose automatically. """


Config = MininterfaceConfig(Gui(), Tui())
""" Global configuration singleton to be accessed by all minterfaces. """
