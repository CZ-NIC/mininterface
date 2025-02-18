# Access to interfaces via this module assures lazy loading
from importlib import import_module
import sys
from typing import Literal, Type


from .config import Config
from .mininterface import Mininterface
from .exceptions import InterfaceNotAvailable
from .text_interface import TextInterface

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceType = Type[Mininterface] | Literal["gui"] | Literal["tui"] | None


def __getattr__(name):
    # shortcuts
    if name == "GuiInterface":
        return __getattr__("TkInterface")
    if name == "TuiInterface":
        # if textual not installed or isatty False, return TextInterface
        return __getattr__("TextualInterface") or TextInterface

    # real interfaces
    if name == "TkInterface":
        try:
            globals()[name] = import_module("..tk_interface", __name__).TkInterface
            return globals()[name]
        except InterfaceNotAvailable:
            return None

    if name == "TextualInterface":
        try:
            globals()[name] = import_module("..textual_interface", __name__).TextualInterface
            return globals()[name]
        except InterfaceNotAvailable:
            return None
    return None  # such attribute does not exist


def get_interface(title="", interface: InterfaceType = None, env=None):
    args = title, env
    interface = interface or Config.interface
    if isinstance(interface, type) and issubclass(interface, Mininterface):
        # the user gave a specific interface, let them catch InterfaceNotAvailable then
        return interface(*args)
    if interface == "gui" or interface is None:
        try:
            return __getattr__("GuiInterface")(*args)
        except InterfaceNotAvailable:
            pass
    try:
        return __getattr__("TuiInterface")(*args)
    except InterfaceNotAvailable:
        # Even though TUI is able to claim a non-interactive terminal,
        # ex. when doing a cron job, a terminal cannot be made interactive.
        pass
    return Mininterface(*args)


__all__ = ["GuiInterface", "TuiInterface", "TextInterface", "TextualInterface", "TkInterface"]
