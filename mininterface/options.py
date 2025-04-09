# Configuration used by all minterfaces in the program.
# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass, field
from typing import Literal, Optional

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceName = Literal["gui"] | Literal["tui"] | Literal["textual"] | Literal["text"]


@dataclass
class UiOptions:
    toggle_widget: str = "f4"
    """ Shortcuts to toggle ex. calendar or file picker. """


@dataclass
class GuiOptions(UiOptions):
    # If multiple Gui interfaces exist, this had to be TkOptions instead.

    combobox_since: int = 5
    """ The threshold to switch from radio buttons to a combobox. """

    radio_select_on_focus: bool = False
    """ Select the radio button on focus. Ex. when navigating by arrows. """


@dataclass
class TuiOptions(UiOptions):
    ...


@dataclass
class TextualOptions(TuiOptions):
    ...


@dataclass
class TextOptions(TuiOptions):
    ...


@dataclass
class WebOptions(TextualOptions):
    ...


# NOTE elaborate in the docs when more examples exist
# TuiOptions works as a default for TextOptions and TextualOptions

@dataclass
class MininterfaceOptions:
    ui: UiOptions = field(default_factory=UiOptions)
    gui: GuiOptions = field(default_factory=GuiOptions)
    tui: TuiOptions = field(default_factory=TuiOptions)
    textual: TextualOptions = field(default_factory=TextualOptions)
    text: TextOptions = field(default_factory=TextOptions)
    web: WebOptions = field(default_factory=WebOptions)
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """
