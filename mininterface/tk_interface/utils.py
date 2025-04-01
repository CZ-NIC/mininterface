from tkinter import LEFT, Button, Entry, TclError, Variable, Widget, Spinbox
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter.ttk import Checkbutton, Combobox, Frame, Radiobutton, Style, Widget
from typing import TYPE_CHECKING

try:
    from autocombobox import AutoCombobox
except ImportError:
    AutoCombobox = None

from tkinter_form.tkinter_form import FieldForm, Form

from ..types.rich_tags import EnumTag

from ..types.internal import CallbackButtonWidget, FacetButtonWidget, SubmitButtonWidget

from ..auxiliary import flatten
from ..experimental import FacetCallback, SubmitButton
from ..form_dict import TagDict
from ..tag import Tag
from ..types import DatetimeTag, PathTag, SecretTag, EnumTag
from .date_entry import DateEntryFrame
from .external_fix import __create_widgets_monkeypatched
from .secret_entry import SecretEntryWrapper

if TYPE_CHECKING:
    from mininterface.tk_interface.adaptor import TkAdaptor


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
                     variable: Variable,
                     field_form: FieldForm) -> tuple[Widget, dict]:
    if widget.winfo_manager() == 'grid':
        grid_info = widget.grid_info()
        widget.grid_forget()
        field_form.variable = variable
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


def replace_widgets(adaptor: "TkAdaptor", nested_widgets, form: TagDict):
    def _fetch(variable):
        return ready_to_replace(widget, variable, field_form)

    # NOTE tab order broken, injected to another position
    # NOTE should the button receive tag or directly
    #   the whole facet (to change the current form)? Specifiable by experimental.FacetCallback.
    nested_widgets = widgets_to_dict(nested_widgets)
    for tag, field_form in zip(flatten(form), flatten(nested_widgets)):
        tag: Tag
        field_form: FieldForm
        label1: Widget = field_form.label
        widget: Widget = field_form.widget
        variable = field_form.variable
        subwidgets = []
        master = widget.master

        # We implement some of the types the tkinter_form don't know how to handle
        match tag._recommend_widget():
            case EnumTag():
                # Replace with radio buttons
                chosen_val = tag._get_ui_val()
                variable = Variable()
                grid_info = _fetch(variable)

                nested_frame = Frame(master)
                nested_frame.grid(row=grid_info['row'], column=grid_info['column'])

                # highlight style
                style = Style()
                style.configure("Custom.TRadiobutton", background="lightyellow")

                choices = tag._get_choices()
                if len(choices) >= adaptor.options.combobox_since and AutoCombobox:
                    widget = AutoCombobox(nested_frame, textvariable=variable)
                    widget['values'] = [k for k, *_ in choices]
                    widget.pack()
                    widget.bind('<Return>', lambda _: "break")  # override default enter that submits the form
                    if chosen_val is not None:
                        variable.set(chosen_val)

                else:
                    for i, (choice_label, choice_val, tip) in enumerate(choices):
                        widget2 = Radiobutton(nested_frame, text=choice_label, variable=variable,
                                              value=choice_label, style="Custom.TRadiobutton" if tip else None)
                        widget2.grid(row=i, column=1, sticky="w")
                        subwidgets.append(widget2)
                        if choice_val is tag.val:
                            variable.set(choice_label)

            case PathTag():
                grid_info = widget.grid_info()

                widget2 = Button(master, text='…', command=choose_file_handler(variable, tag))
                widget2.grid(row=grid_info['row'], column=grid_info['column']+1)
            case DatetimeTag():
                grid_info = widget.grid_info()
                widget.grid_forget()
                nested_frame = DateEntryFrame(master, adaptor, tag, variable)
                nested_frame.grid(row=grid_info['row'], column=grid_info['column'])
                widget = nested_frame.spinbox
            case SecretTag():
                grid_info = widget.grid_info()
                widget.grid_forget()
                # Create wrapper and store it in the widget list
                wrapper = SecretEntryWrapper(master, tag, variable, grid_info)
                widget = wrapper.entry
                # Add shortcut to the central shortcuts set
                adaptor.shortcuts.add("Ctrl+T: Toggle visibility of password field")

            # Special type: Submit button
            case SubmitButtonWidget():  # NOTE EXPERIMENTAL
                variable, widget = create_button(master, _fetch, tag, label1)
                widget.config(command=_set_true(variable, tag))
            case FacetButtonWidget():  # NOTE EXPERIMENTAL
                # Special type: FacetCallback button
                variable, widget = create_button(master, _fetch, tag, label1, lambda tag=tag: tag.val(tag.facet))

            case CallbackButtonWidget():
                # Replace with a callback button
                def inner(tag: Tag):
                    tag.facet.submit(_post_submit=tag._run_callable)
                variable, widget = create_button(master, _fetch, tag, label1, lambda tag=tag: inner(tag))

        # Add event handler
        tag._last_ui_val = variable.get()
        for w in subwidgets + [widget]:
            h = on_change_handler(variable, tag)
            if isinstance(w, Combobox):
                w.bind("<<ComboboxSelected>>", h)
            elif isinstance(w, (Entry, Spinbox)):
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


def widgets_to_dict(widgets_dict) -> dict[str, dict | FieldForm]:
    """ Convert tkinter_form.widgets to a dict """
    result = {}
    for key, value in widgets_dict.items():
        if isinstance(value, dict):
            result[key] = widgets_to_dict(value)
        elif isinstance(value, Form):
            # this is another tkinter_form.Form, recursively parse
            result[key] = widgets_to_dict(value.fields)
        else:  # value is a tuple of (Label, Widget (like Entry))
            result[key] = value
    return result
