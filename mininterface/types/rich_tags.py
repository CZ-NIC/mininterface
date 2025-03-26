from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Optional

from ..auxiliary import common_iterables
from ..tag import Tag


@dataclass
class CallbackTag(Tag):
    ''' Callback function is guaranteed to receives the [Tag][mininterface.Tag] as a parameter.

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

    def __post_init__(self):
        super().__post_init__()
        if self.annotation:
            self.date = issubclass(self.annotation, date)
            self.time = issubclass(self.annotation, time) or issubclass(self.annotation, datetime)

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

    def toggle_visibility(self):
        """Toggle the masked state"""
        self._masked = not self._masked
        return self._masked

    def __repr__(self):
        """Ensure secrets are not accidentally exposed in logs/repr"""
        return f"{self.__class__.__name__}(masked_value)"

    def __hash__(self):
        """Make SecretTag hashable for use with Annotated"""
        return hash((self.show_toggle, self._masked))
