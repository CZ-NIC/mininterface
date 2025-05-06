from tkinter import LEFT, Button, Entry, TclError, Variable, Spinbox
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter.ttk import Checkbutton, Combobox, Radiobutton, Widget
from typing import TYPE_CHECKING


from tkinter_form.tkinter_form import FieldForm, Form

from ..tag.datetime_tag import DatetimeTag

from ..tag.path_tag import PathTag

from ..tag.select_tag import SelectTag

from ..tag.internal import CallbackButtonWidget, FacetButtonWidget, SubmitButtonWidget

from .._lib.auxiliary import flatten
from .._lib.form_dict import TagDict
from ..tag import Tag
from ..tag.secret_tag import SecretTag
from .select_input import SelectInputWrapper, VariableAnyWrapper
from .date_entry import DateEntryFrame
from .external_fix import __create_widgets_monkeypatched
from .secret_entry import SecretEntryWrapper

if TYPE_CHECKING:
    from mininterface._tk_interface.adaptor import TkAdaptor


def recursive_set_focus(widget: Widget):
    for child in widget.winfo_children():
        if not child.winfo_manager():
            # This is a hidden widget. Ex. Tkinter_form generates Entry for SelectTag
            # which we hide and put our own SelectTag widget over its place.
            continue
        if isinstance(child, (Entry, Checkbutton, Combobox, Radiobutton)):
            if isinstance(child, Radiobutton) and child.cget("takefocus") == 0:
                # NOTE the takefocus solution is not good.
                # We've set takefocus=0 to all radios that are not selected.
                # But proper way would be to compare the real value, if the radio box is checked.
                # If no radio in group is checked, focus the first.
                # But attention, if adaptor.settings.radio_select_on_focus,
                # the focusing must not trigger the var setting – radio box should stay unchecked.
                continue
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


def choose_file_handler(variable: Variable, tag: PathTag):
    def _(*_):
        if tag.multiple:
            out = str(list(askopenfilenames(title="Choose files")))
        else:
            out = askopenfilename(title="Choose a file")
        variable.set(out)
    return _


def on_change_handler(variable: Variable | VariableAnyWrapper, tag: Tag):
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
        tag._facet.submit()
    return _


def replace_widgets(adaptor: "TkAdaptor", nested_widgets, form: TagDict):
    def replace_variable(variable):
        """ On form submit, tkinter_form will return the output of this variable. """
        if widget.winfo_manager() == 'grid':
            grid_info = widget.grid_info()
            widget.grid_forget()
            field_form.variable = variable
            return grid_info
        else:
            raise ValueError(f"GuiInterface: Cannot tackle the form, unknown winfo_manager {widget.winfo_manager()}.")

    # NOTE should the button receive tag or directly
    #   the whole facet (to change the current form)? Specifiable by experimental.FacetCallback.
    nested_widgets = widgets_to_dict(nested_widgets)
    for tag, field_form in zip(flatten(form), flatten(nested_widgets)):
        tag: Tag
        field_form: FieldForm
        label1: Widget = field_form.label
        widget: Widget = field_form.widget
        variable = field_form.variable
        master = widget.master
        widget.pack_forget()
        process_change_handler = True
        """ If False, you process _last_ui_val and launch _on_change_trigger. """
        select_tag = False
        # NOTE this variable exists due to poor design

        # We implement some of the types the tkinter_form don't know how to handle
        match tag:
            case SelectTag():
                grid_info = widget.grid_info()
                wrapper = SelectInputWrapper(master, tag, grid_info, widget, adaptor)
                select_tag = True
                variable = wrapper.variable_wrapper
                # since tkinter variables do not allow objects,
                # and choice values can be objects (ex. callbacks)
                # we use out special variable_dict instead
                replace_variable(variable)
                widget.grid_forget()
                widget = wrapper.widget
                if tag.multiple:
                    process_change_handler = False

            case PathTag():
                grid_info = widget.grid_info()

                widget2 = Button(master, text='…', command=choose_file_handler(variable, tag))
                widget2.grid(row=grid_info['row'], column=grid_info['column']+1)
            case DatetimeTag():
                grid_info = widget.grid_info()
                widget.grid_forget()
                nested_frame = DateEntryFrame(master, adaptor, tag, variable)
                nested_frame.grid(row=grid_info['row'], column=grid_info['column'], sticky="w")
                widget = nested_frame.spinbox
            case SecretTag():
                grid_info = widget.grid_info()
                widget.grid_forget()
                # Create wrapper and store it in the widget list
                wrapper = SecretEntryWrapper(master, tag, variable, grid_info)
                widget = wrapper.entry
                # Add shortcut to the central shortcuts set
                adaptor.shortcuts.add("Ctrl+T: Toggle visibility of password field")
            case _:
                match tag._recommend_widget():
                    # Special type: Submit button
                    case SubmitButtonWidget():  # NOTE EXPERIMENTAL
                        variable, widget = create_button(master, replace_variable, tag, label1)
                        widget.config(command=_set_true(variable, tag))
                    case FacetButtonWidget():  # NOTE EXPERIMENTAL
                        # Special type: FacetCallback button
                        variable, widget = create_button(master, replace_variable, tag, label1,
                                                         lambda tag=tag: tag.val(tag._facet))

                    case CallbackButtonWidget():
                        # Replace with a callback button
                        def inner(tag: Tag):
                            tag._facet.submit(_post_submit=tag._run_callable)
                        variable, widget = create_button(master, replace_variable, tag,
                                                         label1, lambda tag=tag: inner(tag))
                    case _:
                        grid_info = replace_variable(variable)
                        # Reposition to the grid so that the Tab order is restored.
                        # (As we replace some widgets with ex. custom DateEntry, these new would have Tab order broken.)
                        widget.grid(row=grid_info['row'], column=grid_info['column'], sticky="we")

        # Add event handler
        if process_change_handler:
            tag._last_ui_val = variable.get()
            h = on_change_handler(variable, tag)
            if select_tag:
                variable.trace_add("write", h)
            elif isinstance(widget, Combobox):
                widget.bind("<<ComboboxSelected>>", h)
            elif isinstance(widget, (Entry, Spinbox)):
                widget.bind("<FocusOut>", h)
            elif isinstance(widget, Checkbutton):
                widget.configure(command=h)

        # Change label name as the field name might have changed (ex. highlighted by an asterisk)
        # But we cannot change the dict key itself
        # as the user expects the consistency – the original one in the dict.
        if tag.label:
            label1.config(text=tag.label)


def create_button(master, _fetch, tag: Tag, label1, command=None):
    variable = AnyVariable(tag.val)
    grid_info = _fetch(variable)
    widget2 = Button(master, text=tag.label, command=command)
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
