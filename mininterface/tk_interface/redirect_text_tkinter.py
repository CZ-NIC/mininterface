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
        # NOTE: Since we do not call .join, the text is not only displayed in the GUI but also printed out after the program ends.
        # which is a bug. Deal with the special case when the text is written here but not displayed in the GUI.
        # with run...:
        #   print("Nothing happens")
        # quit() -> should be printed here

    def trim(self):
        lines = int(self.widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.widget.delete(1.0, f"{lines - self.max_lines}.0")

    def clear(self):
        self.widget.delete('1.0', END)
        super().clear()
