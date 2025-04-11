from dataclasses import dataclass, field
from typing import Optional

from mininterface.settings import InterfaceName,  UiSettings as UOrig,  MininterfaceSettings as MOrig


@dataclass
class UiSettings(UOrig):
    foo: int = 0
    p_config: int = 0
    p_dynamic: int = 0


@dataclass
class GuiSettings(UiSettings):
    # If multiple Gui interfaces exist, this had to be TkSettings instead.

    combobox_since: int = 5
    """ The threshold to switch from radio buttons to a combobox. """

    test: bool = False


@dataclass
class TuiSettings(UiSettings):
    ...


@dataclass
class TextualSettings(TuiSettings):
    foobar: int = 74
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
class MininterfaceSettings(MOrig):
    ui: UiSettings = field(default_factory=UiSettings)
    gui: GuiSettings = field(default_factory=GuiSettings)
    tui: TuiSettings = field(default_factory=TuiSettings)
    textual: TextualSettings = field(default_factory=TextualSettings)
    text: TextSettings = field(default_factory=TextSettings)
    web: WebSettings = field(default_factory=WebSettings)
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """
