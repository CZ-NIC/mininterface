import tkinter as tk
from tkinter import Button, Entry
from ..types import SecretTag


class SecretEntryWrapper:
    def __init__(self, master, tag: SecretTag, variable: tk.Variable, grid_info):
        self.tag = tag
        self.entry = Entry(master, text=variable, show="•")
        self.entry._secret_wrapper = self  # Store reference to wrapper

        row = grid_info['row']
        col = grid_info['column']
        self.entry.grid(row=row, column=col)

        if tag.show_toggle:
            self.button = Button(master, text='👁', command=self.toggle_show)
            self.button.grid(row=row, column=col + 1)

    def toggle_show(self):
        if self.tag.toggle_visibility():
            self.entry.config(show='•')
            self.button.config(text="👁")
        else:
            self.entry.config(show='')
            self.button.config(text="🙈")
