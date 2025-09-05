# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass, field
from typing import Literal, Optional

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceName = Literal["gui"] | Literal["tui"] | Literal["textual"] | Literal["text"]


@dataclass
class UiSettings:
    toggle_widget: str = "f4"
    """ Shortcut to toggle widgets like secret fields, file picker, and datetime dialog.

    The shortcut should be in Textual format (e.g., "ctrl+t", "f4").
    This format will be automatically converted to the appropriate format
    for each interface (e.g., "<Control-t>" for Tkinter).

    Examples:
        - "ctrl+t" for Control+T
        - "alt+f" for Alt+F
        - "f4" for F4 key
        - "cmd+s" for Command+S (macOS)
    """

    mnemonic: Optional[bool] = True
    """ Allow users to access fields with the `Alt+char` shortcut.

    * `True`: All Tags with `Tag(mnemonic=char|True|None)` will have a mnemonic enabled.
    * `False`: All mnemonic is disabled, even if configured via `Tag(mnemonic=char)`.
    * `None`: All Tags with `Tag(mnemonic=char|True)` will have a mnemonic enabled.
    """

    mnemonic_hidden: bool = False
    """ If True, the field label is not underlined to mark the mnemonic. """


@dataclass
class GuiSettings(UiSettings):
    # If multiple Gui interfaces exist, this had to be TkSettings instead.


    combobox_since: int = 10
    """ The threshold to switch from radio buttons to a combobox. """

    radio_select_on_focus: bool = False
    """ Select the radio button on focus. Ex. when navigating by arrows. """


@dataclass
class TuiSettings(UiSettings): ...


@dataclass
class TextualSettings(TuiSettings): ...


@dataclass
class TextSettings(TuiSettings):
    mnemonic_over_number: Optional[bool] = None
    """ Even when mnemonic can be determined, use rather number as a shortcut.

    By default if `None`, determine those with `Tag(mnemonic=char|True)`:

    ```bash
    >     ok
    [1] foo1: ×
    [2] foo2: ×
    [g] foo3: ×
    ```

    If `True`, determine also those having `Tag(mnemonic=None)`:

    ```bash
    >     ok
    [f] foo1: ×
    [o] foo2: ×
    [g] foo3: ×
    ```

    If `False`, we prefer numbers:

    ```bash
    >     ok
    [1] foo1: ×
    [2] foo2: ×
    [3] foo3: ×
    ```

    The original code:

    ```python
    from dataclasses import dataclass
    from typing import Annotated
    from mininterface import Tag, run
    from mininterface.settings import MininterfaceSettings, TextSettings


    @dataclass
    class Env:
        foo1: bool = False
        foo2: bool = False
        foo3: Annotated[bool, Tag(mnemonic="g")] = False


    m = run(Env, settings=MininterfaceSettings(text=TextSettings(mnemonic_over_number=True)))
    m.form()
    quit()
    ```
    """


@dataclass
class WebSettings(TextualSettings):
    # This is ready and working and waiting for the demand.
    ...


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
