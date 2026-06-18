# Access to interfaces via this module assures lazy loading
from importlib import import_module as _import_module
from os import environ as _environ
import sys
from typing import TYPE_CHECKING, Optional, Type

from ._mininterface import EnvClass, Mininterface
from .settings import MininterfaceSettings, InterfaceName
from .exceptions import InterfaceNotAvailable

InterfaceType = Type[Mininterface] | InterfaceName | None
""" Either a class symbol or [a shortcut string](Interfaces.md#all-possible-interfaces). """

if TYPE_CHECKING:
    # static type checker does not see our dynamic interface import (performance reason)
    TextInterface: Type[Mininterface]
    TextualInterface: Type[Mininterface]
    TkInterface: Type[Mininterface]
    TuiInterface: Type[Mininterface]
    GuiInterface: Type[Mininterface]


def _load(name, mod, attr):
    """Raises: InterfaceNotAvailable"""
    globals()[name] = getattr(_import_module(mod, __name__), attr)
    return globals()[name]


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
            return _load(name, ".._tk_interface.interface", "TkInterface")
        case "TextualInterface":
            return _load(name, ".._textual_interface.interface", "TextualInterface")
        case "TextInterface":
            return _load(name, ".._text_interface", "TextInterface")
        case "WebInterface":
            return _load(name, ".._web_interface", "WebInterface")
        case _:
            return None  # such attribute does not exist


def _choose_settings(type_: Mininterface, settings: Optional[MininterfaceSettings]):
    """Pass only the relevant settings section suitable for the given interface type"""
    opt = None
    if settings:
        match type_.__name__:
            case "TkInterface":
                opt = settings.gui
            case "TextualInterface":
                opt = settings.textual
            case "TextInterface":
                opt = settings.text
            case "WebInterface":
                opt = settings.web
            case "Mininterface":
                # Even though this has not any sense to have some settings for Mininterface,
                # they are not used, we test it in TestRun.test_settings_run.
                # An according to MinAdaptor, it should have UiSettings.
                opt = settings.ui
    return opt


def _get_interface_type(interface: InterfaceType | str = None):
    match interface:
        case "gui" | None:
            return __getattr__("GuiInterface")
        case "text":
            return __getattr__("TextInterface")
        case "web":
            return __getattr__("WebInterface")
        case "tui" | "textual":
            return __getattr__("TuiInterface")
        case "min":
            return Mininterface
        case _:
            raise InterfaceNotAvailable


def get_interface(
    interface: InterfaceType = None,
    title: str = "",
    settings: Optional[MininterfaceSettings] = None,
    env: Optional[EnvClass] = None,
) -> Mininterface[EnvClass]:
    """Returns the best available interface.

    Similar to [mininterface.run][mininterface.run] but without CLI or config file parsing.

    ```python
    from mininterface.interfaces import get_interface
    m = get_interface()
    m.ask("...")
    ```

    Args:
        interface: An interface type of preference.
        title: Window title
        settings: [MininterfaceSettings][mininterface.settings.MininterfaceSettings] objects
        env: You can specify the .env attribute of the returned object.

    Without an explicit `interface`, the preference is taken from the `MININTERFACE_INTERFACE`
    environment variable, then from `settings.interface`.
    """

    def call(type_):
        opt = _choose_settings(type_, settings)
        return type_(title, opt, env)

    # Precedence: explicit arg > MININTERFACE_INTERFACE env > config settings (matches `run`).
    # run() resolves this too (it needs the value for Start()) and passes it explicitly; this
    # read is what lets standalone callers (dialogs, a direct get_interface()) honour the env var.
    name = interface or _environ.get("MININTERFACE_INTERFACE") or (settings.interface if settings else None)
    # MININTERFACE_ENFORCED_WEB is internal: set by the web backend when it re-runs the script,
    # so the child renders web instead of re-launching the server.
    if _environ.get("MININTERFACE_ENFORCED_WEB"):
        name = "web"

    try:
        if isinstance(name, type) and issubclass(name, Mininterface):
            return call(name)
        return call(_get_interface_type(name))
    except InterfaceNotAvailable:
        pass
    try:  # try a default TUI
        if name not in ("text", "textual", "tui"):
            return call(_get_interface_type("tui"))
    except InterfaceNotAvailable:
        # Even though TUI is able to claim a non-interactive terminal,
        # ex. when doing a cron job, a terminal cannot be made interactive.
        pass
    return call(Mininterface)


__all__ = ["GuiInterface", "TuiInterface", "TkInterface", "TextualInterface", "TextInterface"]
