from tkinter import Button
from typing import TYPE_CHECKING
from .._mininterface.adaptor import Timeout

if TYPE_CHECKING:
    from . import TkAdaptor


class TkTimeout(Timeout):
    adaptor: "TkAdaptor"

    def __init__(self, timeout: int, adaptor: "TkAdaptor", button: Button):
        super().__init__(timeout, adaptor)
        self.button = button
        self.after_id = None
        self.orig: str = self.button.cget("text")

        self.countdown(timeout)

        # Cancel countdown on FocusOut
        # Why checking .focus_get()? If we jump to another app with Alt+Tab, we do not want the countdown to stop
        # (in such cases, .focus_get() is empty).
        self.button.bind("<FocusOut>", lambda e: self.cancel() if e.widget.focus_get() else None)

    def countdown(self, count):
        try:
            self.button.config(text=f"{self.orig} ({count})")
        except:  # The form has been submitted and the button is not valid anymore
            return

        if count > 0:
            self.after_id = self.adaptor.after(1000, self.countdown, count - 1)
        else:
            self.button.invoke()

    def cancel(self, event=None):
        if self.after_id is not None:
            self.adaptor.after_cancel(self.after_id)
            self.after_id = None
            self.button.config(text=self.orig)
