# Access to interfaces via this module assures lazy loading
from importlib import import_module
from .exceptions import InterfaceNotAvailable
from .text_interface import TextInterface


def __getattr__(name):
    # shortcuts
    if name == "GuiInterface":
        return __getattr__("TkInterface")
    if name == "TuiInterface":
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
    try:
        if interface == "tui":  # undocumented feature
            interface = __getattr__("TuiInterface")
        elif interface == "gui":  # undocumented feature
            interface = __getattr__("GuiInterface")
        if interface is None:
            interface = __getattr__("GuiInterface") or __getattr__("TuiInterface")
        interface = interface(title, env)
    except InterfaceNotAvailable:  # Fallback to a different interface
        interface = __getattr__("TuiInterface")(title, env)
    return interface


__all__ = ["GuiInterface", "TuiInterface", "TextInterface", "TextualInterface", "TkInterface"]
