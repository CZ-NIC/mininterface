# Configuration used by all minterfaces in the program.
# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass, field
from typing import Literal, Optional

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceName = Literal["gui"] | Literal["tui"] | Literal["textual"] | Literal["text"]


@dataclass
class UiSettings:
    toggle_widget: str = "f4"
    """ Shortcuts to toggle ex. calendar or file picker. """

    # NOTE should be used in tkinter
    # But we have to convert textual shortcut to tkinter shortcut with something like this
    # mods = {
    #     "ctrl": "Control",
    #     "alt": "Alt",
    #     "shift": "Shift",
    # }

    # parts = shortcut.lower().split("+")
    # keys = [mods.get(p, p) for p in parts]
    # modifiers = keys[:-1]
    # key = keys[-1]

    # return f"<{'-'.join(modifiers + [key])}>"


@dataclass
class GuiSettings(UiSettings):
    # If multiple Gui interfaces exist, this had to be TkSettings instead.

    combobox_since: int = 10
    """ The threshold to switch from radio buttons to a combobox. """

    radio_select_on_focus: bool = False
    """ Select the radio button on focus. Ex. when navigating by arrows. """


@dataclass
class TuiSettings(UiSettings):
    ...


@dataclass
class TextualSettings(TuiSettings):
    ...


@dataclass
class TextSettings(TuiSettings):
    ...


@dataclass
class WebSettings(TextualSettings):
    ...


# NOTE elaborate in the docs when more examples exist
# TuiSettings works as a default for TextSettings and TextualSettings

@dataclass
class MininterfaceSettings:
    ui: UiSettings = field(default_factory=UiSettings)
    gui: GuiSettings = field(default_factory=GuiSettings)
    tui: TuiSettings = field(default_factory=TuiSettings)
    textual: TextualSettings = field(default_factory=TextualSettings)
    text: TextSettings = field(default_factory=TextSettings)
    web: WebSettings = field(default_factory=WebSettings)
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """
