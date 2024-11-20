# Access to interfaces via this module assures lazy loading
from importlib import import_module
import sys

from .mininterface import Mininterface
from .exceptions import InterfaceNotAvailable
from .text_interface import TextInterface


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
    raise AttributeError(f"Module {__name__} has no attribute {name}")


def get_interface(title="", interface=None, env=None):
    tried_tui = False
    try:
        if interface == "tui":
            interface = __getattr__("TuiInterface")
            tried_tui = True
        elif interface == "gui":
            interface = __getattr__("GuiInterface")
        if interface is None:
            interface = __getattr__("GuiInterface") or __getattr__("TuiInterface")
        return interface(title, env)
    except InterfaceNotAvailable:  # Fallback to a different interface
        pass
    if not tried_tui:
        try:
            return __getattr__("TuiInterface")(title, env)
        except InterfaceNotAvailable:
            # Even though TUI is able to claim a non-interactive terminal,
            # ex. when doing a cron job, a terminal cannot be made interactive.
            pass
    return Mininterface(title, env)


__all__ = ["GuiInterface", "TuiInterface", "TextInterface", "TextualInterface", "TkInterface"]
