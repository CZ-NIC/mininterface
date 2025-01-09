# The purpose of the file is to put the descriptions to the bottom of the widgets
# as it was in the former version of the tkinter_form and to limit their width.
from tkinter import ttk

from tkinter_form import Form, Value, FieldForm

orig = Form._Form__create_widgets


def __create_widgets_monkeypatched(
    self, form_dict: dict, name_config: str, button_command: callable
) -> None:
    """
    Create form widgets

    Args:
        form_dict (dict): form dict base
        name_config (str): name_config
        button (bool): button_config
    """

    index = 0
    for _, (name_key, value) in enumerate(form_dict.items()):
        index += 1
        description = None
        if isinstance(value, Value):
            value, description = value.val, value.description

        self.rowconfigure(index, weight=1)

        if isinstance(value, dict):
            widget = Form(self, name_key, value)
            widget.grid(row=index, column=0, columnspan=3, sticky="nesw")

            self.fields[name_key] = widget
            last_index = index
            continue

        variable = self._Form__type_vars[type(value)]()
        widget = self._Form__type_widgets[type(value)](self)

        self.columnconfigure(1, weight=1)
        widget.grid(row=index, column=1, sticky="nesw", padx=2, pady=2)
        label = ttk.Label(self, text=name_key)
        self.columnconfigure(0, weight=1)
        label.grid(row=index, column=0, sticky="nes", padx=2, pady=2)

        # Add a further description to the row below the widget
        description_label = None
        if not description is None:
            index += 1
            description_label = ttk.Label(self, text=description, wraplength=1000)
            description_label.grid(row=index, column=1, columnspan=2, sticky="nesw", padx=2, pady=2)

        self.fields[name_key] = FieldForm(
            master=self,
            label=label,
            widget=widget,
            variable=variable,
            value=value,
            description=description_label,
        )

        last_index = index

    if button_command:
        self._Form__command = button_command
        self.button = ttk.Button(
            self, text=name_config, command=self._Form__command_button
        )
        self.button.grid(row=last_index + 1, column=0, columnspan=3, sticky="nesw")


Form._Form__create_widgets = __create_widgets_monkeypatched
