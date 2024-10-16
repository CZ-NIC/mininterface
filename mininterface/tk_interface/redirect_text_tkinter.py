from tkinter import END, Text, Tk

from ..redirectable import RedirectText


class RedirectTextTkinter(RedirectText):
    """ Helps to redirect text from stdout to a text widget. """

    def __init__(self, widget: Text, window: Tk) -> None:
        super().__init__()
        self.widget = widget
        self.window = window

    def write(self, text):
        self.widget.pack(expand=True, fill='both')
        self.widget.insert(END, text)
        self.widget.see(END)  # scroll to the end
        self.trim()
        self.window.update_idletasks()
        super().write(text)

    def trim(self):
        lines = int(self.widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.widget.delete(1.0, f"{lines - self.max_lines}.0")
