import sys
from tkinter import Tk

from tktooltip import ToolTip

from tkinter_form import Form

from .HeadlessInterface import HeadlessInterface


class GuiInterface(Tk, HeadlessInterface):
    """ An editing window. """
    def __init__(self):
        super().__init__()
        self.params = None

    def run_dialog(self, title, form_dict: dict) -> dict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """

        # Init the GUI
        self.title(title)
        self.form = Form(self,
                         name_form="",
                         form_dict=form_dict,
                         name_config="Ok",
                         )
        self.form.pack()

        # Set the enter and exit options
        self.form.button.config(command=self._ok)
        ToolTip(self.form.button, msg="Ctrl+Enter")
        self.bind('<Control-Return>', self._ok)
        self.bind('<Escape>', lambda _: sys.exit(0))
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        self.winfo_children()[0].winfo_children()[0].winfo_children()[0].focus_set()
        self.mainloop()
        return self.form.get()

    def _ok(self, _=None):
        self.destroy()