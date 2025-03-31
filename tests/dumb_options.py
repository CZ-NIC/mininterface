from dataclasses import dataclass, field
from typing import Optional

from mininterface.options import InterfaceName,  UiOptions as UOrig,  MininterfaceOptions as MOrig


@dataclass
class UiOptions(UOrig):
    foo: int = 0
    p_config: int = 0
    p_dynamic: int = 0


@dataclass
class GuiOptions(UiOptions):
    # If multiple Gui interfaces exist, this had to be TkOptions instead.

    combobox_since: int = 5
    """ The threshold to switch from radio buttons to a combobox. """

    test: bool = False


@dataclass
class TuiOptions(UiOptions):
    ...


@dataclass
class TextualOptions(TuiOptions):
    foobar: int = 74
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
class MininterfaceOptions(MOrig):
    ui: UiOptions = field(default_factory=UiOptions)
    gui: GuiOptions = field(default_factory=GuiOptions)
    tui: TuiOptions = field(default_factory=TuiOptions)
    textual: TextualOptions = field(default_factory=TextualOptions)
    text: TextOptions = field(default_factory=TextOptions)
    web: WebOptions = field(default_factory=WebOptions)
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """
