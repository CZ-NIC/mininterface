from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from warnings import warn

from numpy import isin

from ..auxiliary import common_iterables
from ..tag import ChoiceLabel, ChoicesType, Tag, TagValue


@dataclass
class CallbackTag(Tag):
    ''' Callback function is guaranteed to receive the [Tag][mininterface.Tag] as a parameter.

    !!! warning
        Experimental. May change.

    For the following examples, we will use these custom callback functions:
    ```python
    from mininterface import run

    def callback_raw():
        """ Dummy function """
        print("Priting text")
        return 50

    def callback_tag(tag: Tag):
        """ Receives a tag """
        print("Printing", type(tag))
        return 100

    m = run()
    ```

    Use as buttons in a form:
    ```
    m.form({"Button": callback_raw})
    m.form({"Button": CallbackTag(callback_tag)})
    ```

    ![Callback button](asset/callback_button.avif)

    Via form, we receive the function handler:
    ```python
    out = m.form({
        "My choice": Tag(choices=[callback_raw, CallbackTag(callback_tag)])
    })
    print(out)  # {'My choice': <function callback_raw at 0x7ae5b3e74ea0>}
    ```

    Via choice, we receive the function output:

    ```python
    out = m.choice({
        "My choice1": callback_raw,
        "My choice2": CallbackTag(callback_tag),
        # Not supported: "My choice3": Tag(callback_tag, annotation=CallbackTag),
    })
    print(out)  # output of callback0 or callback_tag, ex:
    #    Printing <class 'mininterface.types.CallbackTag'>
    #    100
    ```

    ![Callback choice](asset/callback_choice.avif)


    You may use callback in a dataclass.
    ```python
    @dataclass
    class Callbacks:
        p1: Callable = callback0
        p2: Annotated[Callable, CallbackTag(description="Foo")] = callback_tag
        # Not supported: p3: CallbackTag = callback_tag
        # Not supported: p4: CallbackTag = field(default_factory=CallbackTag(callback_tag))
        # Not supported: p5: Annotated[Callable, Tag(description="Bar", annotation=CallbackTag)] = callback_tag

    m = run(Callbacks)
    m.form()
    ```
    '''
    val: Callable[[str], Any]

    def _run_callable(self):
        return self.val(self)


@dataclass(repr=False)
class PathTag(Tag):
    """
    Contains a Path or their list. Use this helper object to select files.

    In the following example, we see that it is not always needed to use this
    object.

    * File 1 – plain detection, button to a file picker appeared.
    * File 2 – the same.
    * File 3 – we specified multiple paths can be selected.

    ```python
    from pathlib import Path
    from mininterface import run, Tag
    from mininterface.types import PathTag

    m = run()
    out = m.form({
        "File 1": Path("/tmp"),
        "File 2": Tag("", annotation=Path),
        "File 3": PathTag([Path("/tmp")], multiple=True),
    })
    print(out)
    # {'File 1': PosixPath('/tmp'), 'File 2': PosixPath('.')}
    # {'File 3': [PosixPath('/tmp')]}
    ```

    ![File picker](asset/file_picker.avif)
    """
    multiple: Optional[bool] = None
    """ The user can select multiple files. """

    exist: Optional[bool] = None
    """ If True, validates that the selected file exists """

    is_dir: Optional[bool] = None
    """ If True, validates that the selected path is a directory """

    is_file: Optional[bool] = None
    """ If True, validates that the selected path is a file """

    def __post_init__(self):
        # Determine annotation from multiple
        if not self.annotation and self.multiple is not None:
            self.annotation = list[Path] if self.multiple else Path

        # Determine the annotation from the value and correct it,
        # as the Tag.guess_type will fetch a mere `str` from `PathTag("/var")`
        super().__post_init__()
        if self.annotation == str:  # PathTag("/var")
            self.annotation = Path
        if self.annotation == list[str]:  # PathTag(["/var"])
            self.annotation = list[Path]
        if self.annotation == list:  # PathTag([])
            self.annotation = list[Path]

        # Determine multiple from annotation
        if self.multiple is None:
            for origin, _ in self._get_possible_types():
                if origin in common_iterables:
                    self.multiple = True
                    break

    def _validate(self, value):
        """Validate the path value based on exist and is_dir attributes"""

        value = super()._validate(value)
        # Check for multiple paths before any conversion
        if not self.multiple and isinstance(value, (list, tuple)):
            self.set_error_text("Multiple paths are not allowed")
            raise ValueError()
        # Convert to list for validation
        paths = value if isinstance(value, list) else [value]

        # Validate each path
        for path in paths:
            if not isinstance(path, Path):
                try:
                    path = Path(path)
                except Exception:
                    self.set_error_text(f"Invalid path format: {path}")
                    raise ValueError()

            if self.exist and not path.exists():
                self.set_error_text(f"Path does not exist: {path}")
                raise ValueError()

            if self.is_dir and self.is_file:
                self.set_error_text(f"Path cannot be both a file and a directory: {path}")
                raise ValueError()

            if self.is_dir and not path.is_dir():
                self.set_error_text(f"Path is not a directory: {path}")
                raise ValueError()

            if self.is_file and not path.is_file():
                self.set_error_text(f"Path is not a file: {path}")
                raise ValueError()

        return value


@dataclass(repr=False)
class DatetimeTag(Tag):
    """
    Datetime, date and time types are supported.

    ```python3
    from datetime import datetime
    from dataclasses import dataclass
    from mininterface import run

    @dataclass
    class Env:
        my_date: datetime

    m = run(Env)
    ```

    The arrows change the day (or the datetime part the keyboard caret is currently editing).

    ![Datetime](asset/datetimetag_datetime.avif)

    In this code, we want only the date part.

    ```python3
    from datetime import date
    from dataclasses import dataclass
    from mininterface import run

    @dataclass
    class Env:
        my_date: date

    m = run(Env)
    ```

    After clicking the button (or hitting `Ctrl+Shift+C`), a calendar appear.

    ![Date with calendar](asset/datetimetag_date_calendar.avif)
    """

    # NOTE, document using full_precision.
    # You may use the DatetimeTag to specify more options.

    # ```python3
    # from mininterface import run
    # from mininterface.types import DatetimeTag

    # run().form({
    #     "my_date": DatetimeTag(time=True)
    # })
    # ```

    # ![Time only](asset/datetime_time.avif)

    # NOTE: It would be nice we might put any date format to be parsed.

    date: bool = False
    """ The date part is active. True for datetime and date. """

    time: bool = False
    """ The time part is active. True for datetime and time.  """

    full_precision: bool = False
    """ Include full time precison, seconds, microseconds. """

    # NOTE calling DatetimeTag("2025-02") should convert str to date?
    def __post_init__(self):
        super().__post_init__()
        if self.annotation:
            self.date = issubclass(self.annotation, date)
            self.time = issubclass(self.annotation, time) or issubclass(self.annotation, datetime)

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def _make_default_value(self):
        return datetime.now()


@dataclass(repr=False)
class SecretTag(Tag):
    """
    Contains a secret value that should be masked in the UI.

    ```python
    from mininterface import run, Tag
    from mininterface.types import SecretTag

    m = run()
    out = m.form({
        "My password": SecretTag("TOKEN"),
    })
    print(out)
    # {'My password': 'TOKEN'}
    ```

    ![File picker](asset/secret_tag.avif)
    """

    show_toggle: bool = True
    """ Toggle visibility button (eye icon) """

    _masked: bool = True
    """ Internal state for visibility """

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def toggle_visibility(self):
        """Toggle the masked state"""
        self._masked = not self._masked
        return self._masked

    def _get_masked_val(self):
        """Value representation, suitable for an UI that does not handle a masked representation itself."""
        if self._masked and self.val:
            return "•" * len(str(self.val))
        return super()._get_ui_val()

    def __repr__(self):
        """Ensure secrets are not accidentally exposed in logs/repr"""
        return f"{self.__class__.__name__}(masked_value)"

    def __hash__(self):
        """Make SecretTag hashable for use with Annotated"""
        return hash((self.show_toggle, self._masked))


@dataclass(repr=False)
class EnumTag(Tag):
    """ Handle choices – radio buttons / select box.
    The value serves as the initially selected choice.
    It is constrained to those defined in the `choices` attribute.
    """

    choices: ChoicesType | None = None
    """ The possible values.


    ```python
    m.form({"My restrained": EnumTag(choices=("one", "two"))})
    ```

    You can denote the choices in many ways. Either put options in an iterable, or to a dict with keys as a values. You can also you tuples for keys to get a table-like formatting. Use the Enums or nested Tags... See the [`ChoicesType`][mininterface.tag.ChoicesType] for more details.

    Here we focus at the `EnumTag` itself and its [`Choices`][mininterface.types.Choices] alias. It can be used to annotate a default value in a dataclass.

    ```python
    from dataclasses import dataclass
    from typing import Annotated
    from mininterface import run, Choices
    from mininterface.types import EnumTag

    @dataclass
    class Env:
        foo: Annotated["str", Choices("one", "two")] = "one"
        # `Choices` is an alias for `EnumTag(choices=)`
        #   so the same would be:
        # foo: Annotated["str", EnumTag(choices=("one", "two"))] = "one"

    m = run(Env)
    m.form()  # prompts a dialog
    ```
    ![Form choice](asset/tag_choices.avif)

    !!! Tip
        When dealing with a simple use case, use the [mininterface.choice][mininterface.Mininterface.choice] dialog.
    """
    # NOTE we should support (maybe it is done)
    # * Enums: Tag(enum) # no `choice` param`
    # * more date types (now only str possible)
    # * mininterface.choice `def choice(choices=, guesses=)`

    multiple: Optional[bool] = None

    # TODO choice multiple test, docs, IDE type hint
    # TODO choice changelog, docs
    # TODO choice multiple tk and text notimplemented

    tips: ChoicesType | None = None

    def __repr__(self):
        return super().__repr__()[:-1] + f", choices={[k for k, *_ in self._get_choices()]})"

    def __post_init__(self):
        # Determine multiple
        candidate = self.val
        if isinstance(self.val, list):
            if self.multiple is False:
                raise ValueError("Multiple cannot be set to False when value is a list")
            self.multiple = True
            if len(self.val):
                candidate = self.val[0]
        elif self.val is not None:
            if self.multiple:
                raise ValueError("Multiple cannot be set to True when value is not a list")
            self.multiple = False

        # Disabling annotation is not a nice workaround, but it is needed for the `super().update` to be processed
        self.annotation = type(self)
        super().__post_init__()
        self.annotation = None

        # Assure list val for multiple selection
        if self.val is None and self.multiple:
            self.val = []

        # Determine choices
        if not self.choices:
            if isinstance(candidate, Enum):  # Enum instance, ex: val=ColorEnum.RED
                self.choices = candidate.__class__
            elif isinstance(candidate, type) and issubclass(candidate, Enum):  # Enum type, ex: val=ColorEnum
                self.choices = self.val
                self.val = None

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def _build_choices(self) -> dict[ChoiceLabel, TagValue]:
        """ Whereas self.choices might have different format, this returns a canonic dict. """

        if self.choices is None:
            return {}
        if isinstance(self.choices, dict):
            if isinstance(next(iter(self.choices)), tuple):
                # Span key tuple into a table
                # Ex: [ ("one", "two"), ("hello", "world") ]
                # one   - two
                # hello - world"
                data = list(self.choices)
                col_widths = [max(len(row[i]) for row in data) for i in range(len(data[0]))]
                keys = (" - ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) for row in data)
                try:
                    return {key: value for key, value in zip(keys, self.choices.values())}
                except IndexError:
                    # different lengths, table does not work
                    # Ex: [ ("one", "two", "three"), ("hello", "world") ]
                    return {" - ".join(key): value for key, value in self.choices.items()}
            return self.choices
        if isinstance(self.choices, common_iterables):
            return {self._repr_val(v): v for v in self.choices}
        if isinstance(self.choices, type) and issubclass(self.choices, Enum):  # Enum type, ex: choices=ColorEnum
            return {str(v.value): v for v in list(self.choices)}

        warn(f"Not implemented choices: {self.choices}")

    def _get_choices(self) -> list[tuple[ChoiceLabel, TagValue], bool]:
        """ Return a list of tuples (label, choice value, is tip) """

        if not self.tips:
            return list((k, v, False) for k, v in self._build_choices().items())

        index = set(self.tips)
        front = []
        back = []
        for k, v in self._build_choices().items():
            if v in index:
                front.append((k, v, True))
            else:
                back.append((k, v, False))
        return front + back

    def update(self, ui_value: TagValue | list[TagValue]) -> bool:
        """ For self.multiple, UI is the value.
            For not self.multiple, UI value is the label. We store the key. """
        ch = self._build_choices()

        if self.multiple:
            vals = set(ch.values())
            for v in ui_value:
                if v not in vals:
                    self.set_error_text(f"Must be one of {list(ch.keys())}")
                    return False
            return super().update(ui_value)
        else:
            if ui_value in ch:
                return super().update(ch[ui_value])
            else:
                self.set_error_text(f"Must be one of {list(ch.keys())}")
                return False

    def _validate(self, out_value):
        vals = self._build_choices().values()

        if self.multiple:
            if all(v in vals for v in out_value):
                return out_value
            else:
                self.set_error_text(f"A value is not one of the allowed")
                raise ValueError
        else:
            if out_value in vals:
                return out_value
            else:
                self.set_error_text(f"Not one of the allowed values")
                raise ValueError
