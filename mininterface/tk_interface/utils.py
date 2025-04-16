from tkinter import Button, Entry, TclError, Variable, Widget, Spinbox
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from tkinter.ttk import Checkbutton, Combobox, Frame, Radiobutton, Style
from typing import TYPE_CHECKING

try:
    from autocombobox import AutoCombobox
except ImportError:
    AutoCombobox = None

from tkinter_form.tkinter_form import FieldForm, Form


from ..types.internal import CallbackButtonWidget, FacetButtonWidget, SubmitButtonWidget

from ..auxiliary import flatten
from ..form_dict import TagDict
from ..tag import Tag
from ..types import DatetimeTag, PathTag, SecretTag, EnumTag
from .date_entry import DateEntryFrame
from .secret_entry import SecretEntryWrapper

if TYPE_CHECKING:
    from mininterface.tk_interface.adaptor import TkAdaptor

import os


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
    """Handler for file/directory selection on PathTag"""
    def _(*_):
        initialdir = os.getcwd()

        # Check whether this is a directory selection
        if tag.is_dir:
            # Directory selection using askdirectory
            kwargs = {"title": "Select Directory", "initialdir": initialdir}
            selected_dir = askdirectory(**kwargs)
            if not selected_dir:  # User cancelled
                return

            if tag.multiple:
                # Handle multiple selection for directories
                try:
                    current_val = variable.get()
                    if current_val and current_val.strip() and current_val != '[]':
                        # Parse existing list
                        import ast
                        try:
                            dirs_list = ast.literal_eval(current_val)
                            if not isinstance(dirs_list, list):
                                dirs_list = [dirs_list]  # Convert to list if not already

                            # Add the new directory if not already in list
                            if selected_dir not in dirs_list:
                                dirs_list.append(selected_dir)

                            variable.set(str(dirs_list))
                        except (SyntaxError, ValueError):
                            # If parsing fails, start a new list
                            variable.set(str([selected_dir]))
                    else:
                        # No current value, set a new list
                        variable.set(str([selected_dir]))
                except (TclError, TypeError):
                    # Fallback
                    variable.set(str([selected_dir]))
            else:
                # Simple single directory selection
                variable.set(selected_dir)
        else:
            # File selection
            if tag.multiple:
                # Multiple file selection
                try:
                    current_val = variable.get()
                    current_files = []
                    if current_val and current_val.strip() and current_val != '[]':
                        # Parse existing list
                        import ast
                        try:
                            current_files = ast.literal_eval(current_val)
                            if not isinstance(current_files, list):
                                current_files = [current_files]
                        except (SyntaxError, ValueError):
                            current_files = []

                    # Select new files with initial directory
                    kwargs = {"title": "Select Files", "initialdir": initialdir}
                    new_files = list(askopenfilenames(**kwargs))
                    if not new_files:  # User cancelled
                        return

                    # Add new files to existing list without duplicates
                    for new_file in new_files:
                        if new_file not in current_files:
                            current_files.append(new_file)

                    # Save updated list
                    variable.set(str(current_files))
                except (SyntaxError, ValueError, TclError, TypeError):
                    kwargs = {"title": "Select Files", "initialdir": initialdir}
                    files = list(askopenfilenames(**kwargs))
                    if files:
                        variable.set(str(files))
            else:
                # Single file selection
                kwargs = {"title": "Select File", "initialdir": initialdir}
                selected_file = askopenfilename(**kwargs)
                if selected_file:
                    variable.set(selected_file)

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

    # Prevent Enter key in an input field from submitting the form
    # But do not interfere with Tab navigation
    def prevent_submit(event):
        # Only prevent form submission, don't affect Tab navigation
        return "break"

    for tag, field_form in zip(flatten(form), flatten(nested_widgets)):
        tag: Tag
        field_form: FieldForm
        label1: Widget = field_form.label
        widget: Widget = field_form.widget
        variable = field_form.variable
        subwidgets = []
        master = widget.master

        # Prevent Enter key in any regular input field from submitting the form
        # But still allow Tab key to work normally
        if isinstance(widget, Entry):
            # Only bind the Enter key, not Tab key
            widget.bind('<Return>', prevent_submit)

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

                # Create button for file/directory selection with appropriate icon
                file_handler = choose_file_handler(variable, tag)
                button_text = "📁" if tag.is_dir else "…"  # Folder icon for directories
                widget2 = Button(master, text=button_text, command=file_handler)
                widget2.grid(row=grid_info['row'], column=grid_info['column']+1)

                # Bind Enter key to button to open file dialog when button is focused
                widget2.bind('<Return>', lambda event: file_handler())

                # For input field, just prevent form submission on Enter without opening file dialog
                widget.bind('<Return>', prevent_submit)
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
