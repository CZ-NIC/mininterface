from pathlib import Path
from tkinter import Button, Entry, Variable, Widget
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter.ttk import Checkbutton, Combobox, Frame, Radiobutton, Widget

from ..types import PathTag
from ..auxiliary import flatten
from ..experimental import FacetCallback, SubmitButton
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
        widget.master._Form__vars[name] = variable
        return grid_info
    else:
        raise ValueError(f"GuiInterface: Cannot tackle the form, unknown winfo_manager {widget.winfo_manager()}.")


def choose_file_handler(variable: Variable, tag: PathTag):
    def _(*_):
        if tag.multiple:
            out = str(list(askopenfilenames(title="Choose files")))
        else:
            out = askopenfilename(title="Choose a file")
        variable.set(out)
    return _


def on_change_handler(variable: Variable, tag: Tag):
    """ Closure handler """
    return lambda *_: tag._on_change_trigger(variable.get())


def _set_true(variable: Variable, tag: Tag):
    def _(*_):
        variable.set(True)
        tag.facet.submit()
    return _


def replace_widgets(nested_widgets, form: TagDict):
    def _fetch(variable):
        return ready_to_replace(widget, var_name, tag, variable)

    # NOTE tab order broken, injected to another position
    # NOTE should the button receive tag or directly
    #   the whole facet (to change the current form)? Specifiable by experimental.FacetCallback.
    nested_widgets = widgets_to_dict(nested_widgets)
    for tag, (label1, widget) in zip(flatten(form), flatten(nested_widgets)):
        tag: Tag
        label1: Widget
        widget: Widget
        var_name = tag._original_name or label1.cget("text")
        variable = widget.master._Form__vars[var_name]
        subwidgets = []
        master = widget.master

        # Replace with radio buttons
        if tag.choices:
            variable = Variable(value=tag.val)
            grid_info = _fetch(variable)

            nested_frame = Frame(master)
            nested_frame.grid(row=grid_info['row'], column=grid_info['column'])

            for i, choice_label in enumerate(tag._get_choices()):
                widget2 = Radiobutton(nested_frame, text=choice_label, variable=variable, value=choice_label)
                widget2.grid(row=i, column=1)
                subwidgets.append(widget2)

        # File dialog
        if path_tag := tag._morph(PathTag, Path):
            grid_info = widget.grid_info()
            master.grid(row=grid_info['row'], column=grid_info['column'])

            widget2 = Button(master, text='👓', command=choose_file_handler(variable, path_tag))
            widget2.grid(row=grid_info['row'], column=grid_info['column']+1)

        # Special type: Submit button
        elif tag.annotation is SubmitButton:  # NOTE EXPERIMENTAL
            variable, widget = create_button(master, _fetch, tag, label1)
            widget.config(command=_set_true(variable, tag))

        # Special type: FacetCallback button
        elif tag.annotation is FacetCallback:  # NOTE EXPERIMENTAL
            variable, widget = create_button(master, _fetch, tag, label1, lambda tag=tag: tag.val(tag.facet))

        # Replace with a callback button
        elif tag._is_a_callable():
            variable, widget = create_button(master, _fetch, tag, label1, tag.val)

        # Add event handler
        tag._last_ui_val = variable.get()
        for w in subwidgets + [widget]:
            h = on_change_handler(variable, tag)
            if isinstance(w, (Entry, Combobox)):
                w.bind("<FocusOut>", h)
            elif isinstance(w, Checkbutton):
                w.configure(command=h)
            elif isinstance(w, Radiobutton):
                variable.trace_add("write", h)

        # Change label name as the field name might have changed (ex. highlighted by an asterisk)
        # But we cannot change the dict key itself
        # as the user expects the consistency – the original one in the dict.
        if tag.name:
            label1.config(text=tag.name)


def create_button(master, _fetch, tag, label1, command=None):
    variable = AnyVariable(tag.val)
    grid_info = _fetch(variable)
    widget2 = Button(master, text=tag.name, command=command)
    widget2.grid(row=grid_info['row'], column=grid_info['column'])
    label1.grid_forget()
    return variable, widget2


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
