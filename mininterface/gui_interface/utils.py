from typing import TYPE_CHECKING
from autocombobox import AutoCombobox
from pathlib import Path, PosixPath
from tkinter import Button, Entry, TclError, Variable, Widget
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter.ttk import Checkbutton, Combobox, Frame, Radiobutton, Widget


from ..types import PathTag
from ..auxiliary import flatten, flatten_keys
from ..experimental import MININTERFACE_CONFIG, FacetCallback, SubmitButton
from ..form_dict import TagDict
from ..tag import Tag

if TYPE_CHECKING:
    from tk_window import TkWindow


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
    def _(*_):
        try:
            return tag._on_change_trigger(variable.get())
        except TclError:
            # Ex: putting there an empty value to an input entry,
            # self._tk.getdouble(value))
            # _tkinter.TclError: expected floating-point number but got ""
            # NOTE we should refresh the Widget; see facet comment
            pass
    return _


def _set_true(variable: Variable, tag: Tag):
    def _(*_):
        variable.set(True)
        tag.facet.submit()
    return _


def replace_widgets(tk_app: "TkWindow", nested_widgets, form: TagDict):
    def _fetch(variable):
        return ready_to_replace(widget, var_name, tag, variable)

    # NOTE tab order broken, injected to another position
    # NOTE should the button receive tag or directly
    #   the whole facet (to change the current form)? Specifiable by experimental.FacetCallback.
    nested_widgets = widgets_to_dict(nested_widgets)
    for (var_name, tag), (label1, widget) in zip(flatten_keys(form), flatten(nested_widgets)):
        tag: Tag
        label1: Widget
        widget: Widget
        variable = widget.master._Form__vars[var_name]
        subwidgets = []
        master = widget.master

        # Replace with radio buttons
        if tag.choices:
            chosen_val = tag._get_ui_val()
            variable = Variable()
            grid_info = _fetch(variable)

            nested_frame = Frame(master)
            nested_frame.grid(row=grid_info['row'], column=grid_info['column'])

            if len(tag._get_choices()) > MININTERFACE_CONFIG["gui"]["combobox_since"]:
                widget = AutoCombobox(nested_frame, textvariable=variable)
                widget['values'] = list(tag._get_choices())
                widget.pack()
                widget.bind('<Return>', lambda _: "break")  # override default enter that submits the form
                variable.set(chosen_val)

            else:
                for i, (choice_label, choice_val) in enumerate(tag._get_choices().items()):
                    widget2 = Radiobutton(nested_frame, text=choice_label, variable=variable, value=choice_label)
                    widget2.grid(row=i, column=1, sticky="w")
                    subwidgets.append(widget2)
                    if choice_val is chosen_val:
                        variable.set(choice_label)
                        # TODO does this works in textual too?

        # File dialog
        elif path_tag := tag._morph(PathTag, (PosixPath, Path)):
            # TODO this probably happens at ._factoryTime, get rid of _morph. I do not know, touch-timestamp uses nested Tag.
            grid_info = widget.grid_info()

            widget2 = Button(master, text='…', command=choose_file_handler(variable, path_tag))
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
            def inner(tag: Tag):
                tk_app._post_submit_action = tag._run_callable
                tag.facet.submit()
            variable, widget = create_button(master, _fetch, tag, label1, lambda tag=tag: inner(tag))

        # Add event handler
        tag._last_ui_val = variable.get()
        for w in subwidgets + [widget]:
            h = on_change_handler(variable, tag)
            if isinstance(w, Combobox):
                w.bind("<<ComboboxSelected>>", h)
            elif isinstance(w, Entry):
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
