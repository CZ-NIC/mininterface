# Access to interfaces via this module assures lazy loading
from importlib import import_module
from os import isatty
import sys
from typing import Literal, Type

from .mininterface import Mininterface
from .config import Config, InterfaceName
from .exceptions import InterfaceNotAvailable

InterfaceType = Type[Mininterface] | InterfaceName | None


def _load(name, mod, attr):
    try:
        globals()[name] = getattr(import_module(mod, __name__), attr)
        return globals()[name]
    except InterfaceNotAvailable:
        return None


def __getattr__(name):
    match name:
        # shortcuts
        case "GuiInterface":
            return __getattr__("TkInterface")
        case "TuiInterface":
            # if textual not installed or isatty False, return TextInterface
            if sys.stdin.isatty():
                try:
                    return __getattr__("TextualInterface")
                except ImportError:
                    pass
            return __getattr__("TextInterface")

        # real interfaces
        case "TkInterface":
            return _load(name, "..tk_interface", "TkInterface")
        case "TextualInterface":
            return _load(name, "..textual_interface", "TextualInterface")
        case "TextInterface":
            return _load(name, "..text_interface", "TextInterface")
        case "WebInterface":
            return _load(name, "..web_interface", "WebInterface")
        case _:
            return None  # such attribute does not exist


def get_interface(title="", interface: InterfaceType = None, env=None):
    args = title, env
    interface = interface or Config.interface
    if isinstance(interface, type) and issubclass(interface, Mininterface):
        # the user gave a specific interface, let them catch InterfaceNotAvailable then
        return interface(*args)
    try:
        match interface:
            case "gui" | None:
                return __getattr__("GuiInterface")(*args)
            case "text":
                return __getattr__("TextInterface")(*args)
            case "web":
                return __getattr__("WebInterface")(*args)
    except InterfaceNotAvailable:
        pass
    try:  # case "tui" | "textual"
        return __getattr__("TuiInterface")(*args)
    except InterfaceNotAvailable:
        # Even though TUI is able to claim a non-interactive terminal,
        # ex. when doing a cron job, a terminal cannot be made interactive.
        pass
    return Mininterface(*args)


__all__ = ["GuiInterface", "TuiInterface", "TextInterface", "TextualInterface", "TkInterface"]
