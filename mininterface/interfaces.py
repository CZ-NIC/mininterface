# Access to interfaces via this module assures lazy loading
from code import interact
from dataclasses import replace
from importlib import import_module
from os import isatty
import sys
from typing import Literal, Optional, Type

from .mininterface import Mininterface
from .options import MininterfaceOptions, InterfaceName
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


def _choose_options(type_: Mininterface, options: Optional[MininterfaceOptions]):
    """ Pass only the relevant options section suitable for the given interface type """
    opt = None
    if options:
        match type(type_):
            case "TkInterface":
                opt = options.gui
            case "TextualInterface":
                opt = options.textual
            case "TextInterface":
                opt = options.text
            case "WebInterface":
                opt = options.web
    return opt


def _get_interface_type(interface: InterfaceType = None):
    match interface:
        case "gui" | None:
            return __getattr__("GuiInterface")
        case "text":
            return __getattr__("TextInterface")
        case "web":
            return __getattr__("WebInterface")
        case "tui" | "textual":
            return __getattr__("TuiInterface")
        case _:
            raise InterfaceNotAvailable


def get_interface(title="", interface: InterfaceType = None, env=None, options: Optional[MininterfaceOptions] = None):
    def call(type_):
        opt = _choose_options(type_, options)
        return type_(title, opt, env)

    interface = interface or (options.interface if options else None)

    if isinstance(interface, type) and issubclass(interface, Mininterface):
        # the user gave a specific interface, let them catch InterfaceNotAvailable then
        return call(interface)

    try:
        return call(_get_interface_type(interface))
    except InterfaceNotAvailable:
        pass
    try:  # try a default TUI
        if interface not in ("text", "textual", "tui"):
            return call(_get_interface_type("tui"))
    except InterfaceNotAvailable:
        # Even though TUI is able to claim a non-interactive terminal,
        # ex. when doing a cron job, a terminal cannot be made interactive.
        pass
    return call(Mininterface)


__all__ = ["GuiInterface", "TuiInterface", "TkInterface", "TextualInterface", "TextInterface"]
