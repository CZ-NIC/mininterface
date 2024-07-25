import os
import re
from argparse import ArgumentParser
from typing import Iterable, TypeVar

try:
    # NOTE this should be clean up and tested on a machine without tkinter installable
    from tkinter import END, Entry, Text, Tk, Widget
    from tkinter.ttk import Checkbutton, Combobox
except ImportError:
    tkinter = None
    END, Entry, Text, Tk, Widget = (None,)*5



T = TypeVar("T")

def flatten(d: dict[str, T | dict]) -> Iterable[T]:
    """ Recursively traverse whole dict """
    for v in d.values():
        if isinstance(v, dict):
            yield from flatten(v)
        else:
            yield v


def get_terminal_size():
    try:
        # XX when piping the input IN, it writes
        # echo "434" | convey -f base64  --debug
        # stty: 'standard input': Inappropriate ioctl for device
        # I do not know how to suppress this warning.
        height, width = (int(s) for s in os.popen('stty size', 'r').read().split())
        return height, width
    except (OSError, ValueError):
        return 0, 0

def get_descriptions(parser: ArgumentParser) -> dict:
    """ Load descriptions from the parser. Strip argparse info about the default value as it will be editable in the form. """
    return {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help)
            for action in parser._actions}


class RedirectText:
    """ Helps to redirect text from stdout to a text widget. """

    def __init__(self, widget: Text, pending_buffer: list, window: Tk) -> None:
        self.widget = widget
        self.max_lines = 1000
        self.pending_buffer = pending_buffer
        self.window = window

    def write(self, text):
        self.widget.pack(expand=True, fill='both')
        self.widget.insert(END, text)
        self.widget.see(END)  # scroll to the end
        self.trim()
        self.window.update_idletasks()
        self.pending_buffer.append(text)

    def flush(self):
        pass  # required by sys.stdout

    def trim(self):
        lines = int(self.widget.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.widget.delete(1.0, f"{lines - self.max_lines}.0")


def recursive_set_focus(widget: Widget):
    for child in widget.winfo_children():
        if isinstance(child, (Entry, Checkbutton, Combobox)):
            child.focus_set()
            return True
        if recursive_set_focus(child):
            return True
