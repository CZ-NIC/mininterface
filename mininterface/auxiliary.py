import os
import re
from argparse import ArgumentParser
from tkinter import Button, Label, StringVar, Variable
from tkinter.ttk import Frame, Radiobutton
from types import SimpleNamespace
from typing import TYPE_CHECKING, Iterable, Literal, TypeVar
from warnings import warn

if TYPE_CHECKING:
    from .tag import Tag

try:
    from tkinter import Entry, Widget
    from tkinter.ttk import Checkbutton, Combobox
except ImportError:
    pass


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
    return {action.dest.replace("-", "_"): re.sub(r"\(default.*\)", "", action.help or "")
            for action in parser._actions}


def recursive_set_focus(widget: Widget):
    for child in widget.winfo_children():
        if isinstance(child, (Entry, Checkbutton, Combobox, Radiobutton)):
            child.focus_set()
            return True
        if recursive_set_focus(child):
            return True


class AnyVariable(Variable):
    """ Original Variable is not able to hold lambdas. """

    def __init__(self, val):
        self.val = val

    def set(self, val):
        self.val = val

    def get(self):
        return self.val


def replace_widget_with(target: Literal["button"] | Literal["radio"], widget: Widget, name, tag: "Tag") -> Widget:
    if widget.winfo_manager() == 'grid':
        grid_info = widget.grid_info()
        widget.grid_forget()

        master = widget.master

        # NOTE tab order broken, injected to another position
        match target:
            case "radio":
                choices = tag._get_choices()
                master._Form__vars[name] = variable = Variable(value=tag.val)  # the chosen default
                nested_frame = Frame(master)
                nested_frame.grid(row=grid_info['row'], column=grid_info['column'])


                for i, (label, val) in enumerate(choices.items()):
                    radio = Radiobutton(nested_frame, text=label, variable=variable, value=val)
                    radio.grid(row=i, column=1)
            case "button":
                # TODO should the button receive tag or directly the whole facet (to change the current form).
                #   Implement to textual. Docs.
                master._Form__vars[name] = AnyVariable(tag.val)
                radio = Button(master, text=name, command=lambda tag=tag: tag.val(tag.facet))
                radio.grid(row=grid_info['row'], column=grid_info['column'])
    else:
        warn(f"GuiInterface: Cannot tackle the form, unknown winfo_manager {widget.winfo_manager()}.")


def widgets_to_dict(widgets_dict) -> dict:
    """ Convert tkinter_form.widgets to a dict """
    result = {}
    for key, value in widgets_dict.items():
        if isinstance(value, dict):
            result[key] = widgets_to_dict(value)
        elif hasattr(value, 'widgets'):
            # this is another tkinter_form.Form, recursively parse
            result[key] = widgets_to_dict(value.widgets)
        else:  # value is a tuple of (Label, Widget (like Entry))
            result[key] = value
    return result
