import tkinter as tk
from tkinter import Button, Entry
from ..tag.secret_tag import SecretTag
from .._lib.shortcuts import convert_to_tkinter_shortcut


class SecretEntryWrapper:
    def __init__(self, master, tag: SecretTag, variable: tk.Variable, grid_info, adaptor):
        self.tag = tag
        self.entry = Entry(master, text=variable, show="•")
        # Add more hints here as needed
        self.entry._shortcut_hints = [
            f"{adaptor.options.toggle_widget}: Toggle visibility of password field"
        ]
        row = grid_info['row']
        col = grid_info['column']
        self.entry.grid(row=row, column=col, sticky="we")

        # Add binding using the shortcut from settings
        tk_shortcut = convert_to_tkinter_shortcut(adaptor.options.toggle_widget)
        self.entry.bind(tk_shortcut, self._on_toggle)

        if tag.show_toggle:
            self.button = Button(master, text='👁', command=self.toggle_show)
            self.button.grid(row=row, column=col + 1)

    def _on_toggle(self, event=None):
        """Handle toggle key event"""
        self.toggle_show()
        return "break"  # Prevent event propagation

    def toggle_show(self):
        if self.tag.toggle_visibility():
            self.entry.config(show='•')
            self.button.config(text="👁")
        else:
            self.entry.config(show='')
            self.button.config(text="🙈")
