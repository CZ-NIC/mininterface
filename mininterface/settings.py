# Might be changed by a 'mininterface' section in a config file.
from dataclasses import dataclass as _dataclass, field as _field
from typing import Literal, Optional

# We do not use InterfaceType as a type in run because we want the documentation to show full alias.
InterfaceName = Literal["gui"] | Literal["tui"] | Literal["textual"] | Literal["text"]

@_dataclass
class CliSettings:
    omit_arg_prefixes: bool = False
    """ Simplify argument names by removing parent field prefixes from flags.

    ```bash
    $ ./program.py --help
    # omit_arg_prefixes = False
    usage: program.py [-h] [-v] --arg.subarg.text STR
    # omit_arg_prefixes = True
    usage: program.py [-h] [-v] --text STR
    ```

    ??? Code
        ```python
        @dataclass
        class SubMessage:
            text: str

        @dataclass
        class Message:
            subarg: SubMessage

        @dataclass
        class Env:
            arg: Message

        run(Env, settings=CliSettings(omit_arg_prefixes=True/False))
        ```

    See: [https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.OmitArgPrefixes]()
    """

    omit_subcommand_prefixes: bool = False
    """
    Simplify subcommand names by removing parent field prefixes from subcommands.

    ```bash
    $ ./program.py --help
    # omit_subcommand_prefixes = False
    usage: program.py [-h] [-v] {subcommand:message,subcommand:console}
    # omit_subcommand_prefixes = True
    usage: program.py [-h] [-v] {message,console}
    ```

    ??? Code
        ```python
        @dataclass
        class SubMessage:
            text: str

        @dataclass
        class Message:
            subarg: SubMessage

        @dataclass
        class Env:
            subcommand: Message | Console

        run(Env, settings=CliSettings(omit_subcommand_prefixes=True/False))
        ```

    See: [https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.OmitSubcommandPrefixes]()
    """

    disallow_none: bool = False
    """ Disallow passing None in via the command-line interface for union types containing None.

    ```bash
    $ ./program.py --help
    # disallow_none = False
    usage: program.py [-h] [-v] [--field {None}|INT]
    # disallow_none = True
    usage: program.py [-h] [-v] [--field INT]
    ```

    ??? Code
        ```python
        @dataclass
        class Env:
            field: int | None = None
        run(Env, settings=CliSettings(disallow_none=True/False))
        ```

    See: [https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.DisallowNone]()
    """

    flag_create_pairs_off: bool = False
    """ Disable creation of matching flag pairs for boolean types.

    ```bash
    $ ./program.py --help
    # flag_create_pairs_off = False
    usage: program.py [-h] [-v] [--foo | --no-foo]
    # flag_create_pairs_off = True
    usage: program.py [-h] [-v] [--foo]
    ```

    ??? Code
        ```python
        @dataclass
        class Env:
            foo: bool = False
        run(Env, settings=CliSettings(flag_create_pairs_off=True/False))
        ```

    See: [https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.FlagCreatePairsOff]()
    """



@_dataclass
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


@_dataclass
class GuiSettings(UiSettings):
    # If multiple Gui interfaces exist, this had to be TkSettings instead.

    combobox_since: int = 10
    """ The threshold to switch from radio buttons to a combobox.

    Without combobox:

    ![Default](asset/configuration-not-used.avif)

    With combobox:

    ![Combobox](asset/configuration-used.avif)

    (Note, there must be multiple fields for combobox to appear.)
    """

    radio_select_on_focus: bool = False
    """ Select the radio button on focus. Ex. when navigating by arrows. """


@_dataclass
class TuiSettings(UiSettings): ...


@_dataclass
class TextualSettings(TuiSettings): ...


@_dataclass
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


@_dataclass
class WebSettings(TextualSettings):
    # This is ready and working and waiting for the demand.
    ...


@_dataclass
class MininterfaceSettings:
    ui: UiSettings = _field(default_factory=UiSettings)
    gui: GuiSettings = _field(default_factory=GuiSettings)
    tui: TuiSettings = _field(default_factory=TuiSettings)
    textual: TextualSettings = _field(default_factory=TextualSettings)
    text: TextSettings = _field(default_factory=TextSettings)
    web: WebSettings = _field(default_factory=WebSettings)
    cli: CliSettings = _field(default_factory=CliSettings)
    interface: Optional[InterfaceName] = None
    """ Enforce an interface. By default, we choose automatically. """
