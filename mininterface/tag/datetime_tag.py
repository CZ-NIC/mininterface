from dataclasses import dataclass
from datetime import date, datetime, time
from .tag import Tag, TagValue, UiValue


@dataclass(repr=False)
class DatetimeTag(Tag[TagValue | date | time | datetime]):
    """
    Datetime, date and time types are supported.

    ```python
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

    ```python
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

    # ```python
    # from mininterface import run
    # from mininterface.tag import DatetimeTag

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
            self.date = self._is_subclass(date)
            self.time = self._is_subclass(time) or self._is_subclass(datetime)
        elif not self.date and not self.time:
            self.date = self.time = True

        if not self.annotation:
            match self.date, self.time:
                case True, True:
                    caster = datetime
                case True, False:
                    caster = date
                case False, True:
                    caster = time
                case _:
                    raise ValueError("Could not determine annotation for %s", self)
            self.annotation = caster
        if self.val is None:
            # I think it's a good idea to put a now-date instead of an empty string in dialogs like:
            # m.ask(f"My date", DatetimeTag(date=True))
            self.val = self._make_default_value()

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def _make_default_value(self):
        if self.annotation is datetime:
            return datetime.now()
        if self.annotation is date:
            return datetime.now().date()
        if self.annotation is time:
            return datetime.now().time().replace(second=0, microsecond=0)
        raise ValueError("Could not determine the default value for %s", self)

    def update(self, ui_value: UiValue) -> bool:
        if isinstance(ui_value, str):
            try:
                ui_value = self.annotation.fromisoformat(ui_value)
            except ValueError:
                # allow annotations like `time | None`
                # Empty input will still have chance to be resolved further.
                pass
        return super().update(ui_value)
