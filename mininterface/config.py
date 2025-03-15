# Configuration used by all minterfaces in the program.
# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass
from typing import Literal, Optional

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceName = Literal["gui"] | Literal["tui"] | Literal["text"]


@dataclass
class Gui:
    combobox_since: int = 5
    """ The threshold to switch from radio buttons to a combobox. """
    test: bool = False


@dataclass
class Tui:
    ...


@dataclass
class Text:
    ...


@dataclass  # (slots=True)
class MininterfaceConfig:
    gui: Gui
    tui: Tui
    text: Text
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """


Config = MininterfaceConfig(Gui(), Tui(), Text())
""" Global configuration singleton to be accessed by all minterfaces. """
