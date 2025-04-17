from . import Tag


from dataclasses import dataclass
from datetime import date, datetime, time


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
            self.date = issubclass(self.annotation, date)
            self.time = issubclass(self.annotation, time) or issubclass(self.annotation, datetime)

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    def _make_default_value(self):
        return datetime.now()
