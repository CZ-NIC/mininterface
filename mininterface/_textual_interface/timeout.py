import asyncio
from .widgets import MyButton as Button
from typing import TYPE_CHECKING

from .._mininterface.adaptor import Timeout

if TYPE_CHECKING:
    from . import TextualAdaptor


class TextualTimeout(Timeout):
    button: Button

    def __init__(self, timeout: int, adaptor: "TextualAdaptor", button: Button):
        super().__init__(timeout, adaptor)
        self.button = button
        self.orig = self.button.label
        self._task = asyncio.create_task(self.countdown(timeout))

        # Cancel countdown on focusing out
        # Why checking .focused? If we jump to another app with Alt+Tab, we do not want the countdown to stop
        # (in such cases, .focused is empty).
        self.button.set_blur_callback(lambda event=None: self.cancel() if adaptor.app.focused else None)

    async def countdown(self, count: int):
        self.button.label = f"{self.orig} ({count})"

        while count > 0:
            await asyncio.sleep(1)
            count -= 1
            self.button.label = f"{self.orig} ({count})"

        self.button.press()

    def cancel(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            self.button.label = self.orig
