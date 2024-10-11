import sys
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self, Type
else:
    from typing import Type


class RedirectText:
    """ Helps to redirect text from stdout to a text widget. """

    def __init__(self) -> None:
        self.max_lines = 1000
        self.pending_buffer = []

    def write(self, text):
        self.pending_buffer.append(text)

    def flush(self):
        pass  # required by sys.stdout

    def join(self):
        t = "".join(self.pending_buffer)
        self.pending_buffer.clear()
        return t


class Redirectable:
    # NOTE When used in the with statement, the TUI window should not vanish between dialogues.
    # The same way the GUI does not vanish.
    # NOTE: Current implementation will show only after a dialog submit, not continuously.
    # # with run(Env) as m:
    #     print("First")
    #     sleep(1)
    #     print("Second")
    #     m.is_yes("Was it shown continuously?")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._always_shown = False
        self._redirected: Type[RedirectText] = RedirectText()
        self._original_stdout = sys.stdout

    def __enter__(self) -> "Self":
        self._always_shown = True
        sys.stdout = self._redirected
        return self

    def __exit__(self, *_):
        self._always_shown = False
        sys.stdout = self._original_stdout
        if t := self._redirected.join():  # display text sent to the window but not displayed
            print(t, end="")
