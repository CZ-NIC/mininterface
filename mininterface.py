#!/usr/bin/env python3

import re
import sys
from tkinter import Tk

from simple_parsing import ArgumentParser as AP
from simple_parsing.help_formatter import TEMPORARY_TOKEN
from tkinter_form import Form, Value
from tktooltip import ToolTip


class ArgumentParser(AP):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = _GuiEditWindow()
        self.args = None

    def parse_args(self):
        self.args = super().parse_args()

        # Empty CLI → GUI edit
        if len(sys.argv) <= 1:
            return self.ask_args()
        return self.args

    def ask_args(self):
        # Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form.
        descriptions = {action.dest: re.sub(r"\(default.*\)", "", action.help)
                        for action in self._actions if not action.help.startswith(TEMPORARY_TOKEN)}
        # Convert the namespace of dataclasses into dict of dicts. Fetching the description from the parser.
        params_ = {group: {param: Value(val, descriptions.get(f"{group}.{param}"))
                           for param, val in vars(dataclass).items()}
                   for group, dataclass in vars(self.args).items()}


        # fetch the dict of dicts values from the form back to the namespace of the dataclasses
        data = self.window.run_dialog(self.prog, params_)
        for group, params in data.items():
            for key, val in params.items():
                setattr(getattr(self.args, group), key, val)
        return self.args



class _GuiEditWindow(Tk):
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
        self.form.button.config(command=self.ok)
        ToolTip(self.form.button, msg="Ctrl+Enter")
        self.bind('<Control-Return>', self.ok)
        self.bind('<Escape>', lambda _: sys.exit(0))
        self.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        # focus the first element and run
        self.winfo_children()[0].winfo_children()[0].winfo_children()[0].focus_set()
        self.mainloop()
        return self.form.get()

    def ok(self, _=None):
        self.destroy()
