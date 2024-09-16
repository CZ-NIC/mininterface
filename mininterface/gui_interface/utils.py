from tkinter import Button, Entry, Variable, Widget
from tkinter.ttk import Checkbutton, Combobox, Frame, Radiobutton, Widget
from typing import Literal
from warnings import warn

from ..auxiliary import flatten
# from ..experimental import SubmitToTrue # NOTE EXPERIMENTAL
from ..form_dict import TagDict
from ..tag import Tag


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
        # super().__init__()
        self._name = str(val)
        self.val = val

    def set(self, val):
        self.val = val

    def get(self):
        return self.val


def ready_to_replace(widget: Widget,
                     name,
                     tag: "Tag",
                     variable: Variable) -> tuple[Widget, dict]:
    if widget.winfo_manager() == 'grid':
        grid_info = widget.grid_info()
        widget.grid_forget()

        master = widget.master
        # master._Form__vars[name] = variable = Variable(tag.val)  # the chosen default
        master._Form__vars[name] = variable

        return master, grid_info
    else:
        raise ValueError(f"GuiInterface: Cannot tackle the form, unknown winfo_manager {widget.winfo_manager()}.")


def replace_widgets(nested_widgets, form: TagDict):
    def _fetch(variable):
        return ready_to_replace(widget1, tag._original_name or label1.cget("text"), tag, variable)

    # NOTE tab order broken, injected to another position
    # TODO should the button receive tag or directly the whole facet (to change the current form).
    #   Implement to textual. Docs.
    # TODO Not able to choose 'x': "My choice2": Choices("tri", x)

    nested_widgets = widgets_to_dict(nested_widgets)
    for tag, (label1, widget1) in zip(flatten(form), flatten(nested_widgets)):
        tag: Tag
        label1: Widget
        widget1: Widget

        if tag.choices:
            variable = Variable(value=tag.val)
            master, grid_info = _fetch(variable)

            nested_frame = Frame(master)
            nested_frame.grid(row=grid_info['row'], column=grid_info['column'])

            for i, (choice_label, choice_val) in enumerate(tag._get_choices().items()):
                widget2 = Radiobutton(nested_frame, text=choice_label, variable=variable, value=choice_val)
                widget2.grid(row=i, column=1)

        # elif tag.annotation is SubmitToTrue:  # NOTE EXPERIMENTAL
        #     def _set_true(variable):
        #         variable.set(True)
        #         tag.facet.submit()
        #     variable = AnyVariable(tag.val)
        #     master, grid_info = _fetch(variable)
        #     widget2 = Button(master, text=tag.name, command=lambda variable=variable:_set_true(variable))
        #     widget2.grid(row=grid_info['row'], column=grid_info['column'])
        #     label1.grid_forget()
        #     variable = False

        elif tag._is_a_callable():
            variable = AnyVariable(tag.val)
            master, grid_info = _fetch(variable)
            # widget2 = Button(master, text=tag.name, command=lambda tag=tag: tag.val(tag.facet)) NOTE how to receive the facet?
            widget2 = Button(master, text=tag.name, command=tag.val)
            widget2.grid(row=grid_info['row'], column=grid_info['column'])
            label1.grid_forget()

        # Change label name as the field name might have changed (ex. highlighted by an asterisk)
        # But we cannot change the dict key itself
        # as the user expects the consistency – the original one in the dict.
        if tag.name:
            label1.config(text=tag.name)


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
