from tkinter import Variable, Widget
from tkinter.ttk import Frame, Label, Radiobutton, Style
from typing import TYPE_CHECKING, Generic, TypeVar

from .. import Optional


from ..types.rich_tags import ChoicesReturnType, EnumTag

try:
    from autocombobox import AutoCombobox
except ImportError:
    AutoCombobox = None

if TYPE_CHECKING:
    from . import TkAdaptor

T = TypeVar("T", bound=str)
V = TypeVar("V")


class VariableDictWrapper(Generic[T, V]):
    """ Since tkinter is not able to hold objects as values, keep a mapping.
    You can use this object as a standard Variable (which is underlying and you can still access it).
    """

    def __init__(self, variable: Variable):
        self.variable = variable
        self.mapping = {}

    def add(self, key: T, value: V) -> T:
        self.mapping[key] = value
        return key

    def get(self) -> V | None:
        key = self.variable.get()
        # if not key:
        # return None
        # return self.mapping[key]
        return self.mapping.get(key, None)

    def set(self, key: T):
        self.variable.set(key)

    def trace_add(self, *args, **kwargs):
        return self.variable.trace_add(*args, **kwargs)


class SelectInputWrapper:

    def __init__(self, master, tag: EnumTag, grid_info, widget: Widget, adaptor: "TkAdaptor"):
        # Replace with radio buttons
        self.tag = tag
        self.adaptor = adaptor
        self.choices: ChoicesReturnType = tag._get_choices()
        self.variable = Variable()
        self.variable_dict = VariableDictWrapper(self.variable)
        [self.variable_dict.add(k, v) for k, v, *_ in self.choices]
        self.widget = widget

        self.frame = nested_frame = Frame(master)
        nested_frame.grid(row=grid_info['row'], column=grid_info['column'], sticky='w')

        # highlight style
        style = Style()
        style.configure("Highlight.TRadiobutton", background="lightyellow")

        bg = style.lookup('TRadioButton', 'background')
        self.init_phase = True
        """ Becomes False few ms after mainloop """

        if tag.multiple:
            raise NotImplementedError  # TODO
        else:
            if len(self.choices) >= adaptor.options.combobox_since and AutoCombobox:
                self.widget = self.combobox()
            else:
                self.radio(bg)

        # if radio_select_on_focus is True, we want to ignore the first FocusIn event
        nested_frame.after(200, self.end_init_phase)

    def radio(self, bg):
        choices = self.choices
        tag = self.tag
        adaptor = self.adaptor
        nested_frame = self.frame
        buttons = []

        for i, (choice_label, choice_val, tip, tupled_key) in enumerate(choices):
            is_selected = choice_val is tag.val
            widget2 = Radiobutton(nested_frame,
                                  text="",
                                  variable=self.variable,
                                  value=choice_label,
                                  style="Highlight.TRadiobutton" if tip else "",
                                  takefocus=is_selected)
            if adaptor.options.radio_select_on_focus:
                widget2.bind("<FocusIn>",
                             lambda _, var=self.variable, val=choice_label: self.select_on_focus(var, val),
                             add='+')

                # Set the Tab to refocus the currently selected button when getting back to widget
                # The default tkinter behaviour is that Tab iterates over all radio buttons
                # which does not make sense.
            widget2.bind("<FocusIn>",
                         lambda _, rb=widget2, buttons=buttons: self.change_takefocus(rb, buttons),
                         add='+')
            widget2.grid(row=i, column=1, sticky="w")
            buttons.append(widget2)

            # display labels
            labs = []
            for i2, col in enumerate(tupled_key):
                lab = Label(nested_frame, text=col + " " * 5)
                lab.grid(row=i, column=1+1+i2, sticky="w")
                lab.bind("<Button-1>", lambda _, v=self.variable, ch=choice_label: v.set(ch))
                # highlight whole line on hover
                lab.bind('<Enter>', lambda _, labs=labs: [
                    lab.config(background='lightblue')for lab in labs])

                lab.bind('<Leave>', lambda _, labs=labs: [lab.config(background=bg) for lab in labs])
                labs.append(lab)

        if not self.set_default_label() and buttons:
            # allow Tab entry (that we disabled on button creation) even if no radio in group is checked
            buttons[0].configure(takefocus=1)

    def set_default_label(self):
        if k := self.tag._get_selected_key():
            self.variable_dict.set(k)
            return True
        return False

    def combobox(self):
        choices = self.choices
        widget = AutoCombobox(self.frame, textvariable=self.variable)
        widget['values'] = [k for k, *_ in choices]
        widget.pack()
        widget.bind('<Return>', lambda _: "break")  # override default enter that submits the form

        self.set_default_label()
        return widget

    def end_init_phase(self):
        self.init_phase = False

    def change_takefocus(self, rb: Radiobutton, buttons: list[Radiobutton]):
        """ Tab will jump on the next form element (not on the next radiobutton). """
        [b.configure(takefocus=0) for b in buttons]
        rb.configure(takefocus=1)

    def select_on_focus(self, var, val):
        if not self.init_phase:
            # We never want to select the radiobutton in the initial phase
            # as this might trigger on_change action (not caused by the user)
            var.set(val)
