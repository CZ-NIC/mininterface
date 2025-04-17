import tkinter as tk
from tkinter import Button, Entry
from ..tag.secret_tag import SecretTag


class SecretEntryWrapper:
    def __init__(self, master, tag: SecretTag, variable: tk.Variable, grid_info):
        self.tag = tag
        self.entry = Entry(master, text=variable, show="•")
        # Add more hints here as needed
        self.entry._shortcut_hints = [
            "Ctrl+T: Toggle visibility of password field"
        ]
        row = grid_info['row']
        col = grid_info['column']
        self.entry.grid(row=row, column=col, sticky="we")

        # Add Ctrl+T binding to the entry widget
        self.entry.bind('<Control-t>', self._on_toggle)

        if tag.show_toggle:
            self.button = Button(master, text='👁', command=self.toggle_show)
            self.button.grid(row=row, column=col + 1)

    def _on_toggle(self, event=None):
        """Handle Ctrl+T key event"""
        self.toggle_show()
        return "break"  # Prevent event propagation

    def toggle_show(self):
        if self.tag.toggle_visibility():
            self.entry.config(show='•')
            self.button.config(text="👁")
        else:
            self.entry.config(show='')
            self.button.config(text="🙈")
