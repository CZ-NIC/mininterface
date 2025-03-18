# Access to interfaces via this module assures lazy loading
from importlib import import_module
import sys
from typing import Literal, Type

from .mininterface import Mininterface
from .config import Config, InterfaceName
from .exceptions import InterfaceNotAvailable

InterfaceType = Type[Mininterface] | InterfaceName | None


def __getattr__(name):
    match name:
        # shortcuts
        case "GuiInterface":
            return __getattr__("TkInterface")
        case "TuiInterface":
            # if textual not installed or isatty False, return TextInterface
            return __getattr__("TextualInterface") or __getattr__("TextInterface")

        # real interfaces
        case "TextInterface":
            try:
                globals()[name] = import_module("..text_interface", __name__).TextInterface
                return globals()[name]
            except InterfaceNotAvailable:
                return None
        case "TkInterface":
            try:
                globals()[name] = import_module("..tk_interface", __name__).TkInterface
                return globals()[name]
            except InterfaceNotAvailable:
                return None

        case "TextualInterface":
            try:
                globals()[name] = import_module("..textual_interface", __name__).TextualInterface
                return globals()[name]
            except InterfaceNotAvailable:
                return None
        case _:
            return None  # such attribute does not exist


def get_interface(title="", interface: InterfaceType = None, env=None):
    args = title, env
    interface = interface or Config.interface
    if isinstance(interface, type) and issubclass(interface, Mininterface):
        # the user gave a specific interface, let them catch InterfaceNotAvailable then
        return interface(*args)
    match interface:
        case "gui" | None:
            try:
                return __getattr__("GuiInterface")(*args)
            except InterfaceNotAvailable:
                pass
        case "text":
            try:
                return __getattr__("TextInterface")(*args)
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
