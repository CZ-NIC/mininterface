import tkinter as tk
from tkinter import Button, Entry
from ..types import SecretTag
from typing import TYPE_CHECKING
from tkinter.ttk import Frame

if TYPE_CHECKING:
    from tk_window import TkWindow


class SecretEntryWrapper:
    def __init__(self, master, tag: SecretTag, variable: tk.Variable, grid_info):
        self.tag = tag
        self.entry = Entry(master, text=variable, show="•")
        self.entry.grid(row=grid_info['row'], column=grid_info['column'])

        if tag.show_toggle:
            self.button = Button(master, text='👁', command=self.toggle_show)
            self.button.grid(row=grid_info['row'], column=grid_info['column']+1)

    def toggle_show(self):
        if self.tag.toggle_visibility():
            self.entry.config(show='•')
            self.button.config(text="👁")
        else:
            self.entry.config(show='')
            self.button.config(text="🙈")
