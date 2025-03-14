import tkinter as tk
from tkinter import Button, Entry
from ..types import SecretTag
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tk_window import TkWindow


class SecretEntryWrapper:
    def __init__(self, master, variable: tk.Variable, grid_info):
        self.entry = Entry(master, text=variable, show="*")
        self.entry.grid(row=grid_info['row'], column=grid_info['column'])

        self.button = Button(master, text='👁', command=self.toggle_show)
        self.button.grid(row=grid_info['row'], column=grid_info['column']+1)

    def toggle_show(self):
        if self.entry.cget('show') == '*':
            self.entry.config(show='')
            self.button.config(text="🙈")
        else:
            self.entry.config(show='*')
            self.button.config(text="👁")
