from tkinter import BooleanVar, Variable, Widget
from tkinter.ttk import Checkbutton, Frame, Label, Radiobutton, Style
from typing import TYPE_CHECKING, Generic, TypeVar


from ..tag.select_tag import SelectTag, OptionsReturnType

try:
    from autocombobox import AutoCombobox
except ImportError:
    AutoCombobox = None

if TYPE_CHECKING:
    from . import TkAdaptor

T = TypeVar("T", bound=str)
V = TypeVar("V")


class VariableAnyWrapper(Generic[T, V]):
    """ Since tkinter is not able to hold objects as values, keep a mapping.
    You can use this object as a standard Variable (which is underlying and you can still access it).
    """

    def __init__(self, variable: Variable, mapping: dict[T, V]):
        self.variable = variable
        self.mapping = mapping

    # def add(self, key: T, value: V) -> T:
    #     self.mapping[key] = value
    #     return key

    def get(self) -> V | None:
        key = self.variable.get()
        return self.mapping.get(key, None)

    def set(self, key: T):
        self.variable.set(key)

    def trace_add(self, *args, **kwargs):
        return self.variable.trace_add(*args, **kwargs)


class SetVar(set):
    def get(self):
        # casting to list, as multiple=True claims it returns a list
        return list(self)

    def set(self):
        raise NotImplemented("Was not meant to be used.")


class SelectInputWrapper:

    def __init__(self, master, tag: SelectTag, grid_info, widget: Widget, adaptor: "TkAdaptor"):
        # Replace with radio buttons
        self.tag = tag
        self.adaptor = adaptor
        self.options: OptionsReturnType = tag._get_options()
        self.variable = Variable()
        self.widget = widget

        self.frame = nested_frame = Frame(master)
        nested_frame.grid(row=grid_info['row'], column=grid_info['column'], sticky='w')

        # highlight style
        style = Style()
        style.configure("Highlight.TRadiobutton", background="lightyellow")
        style.configure("Highlight.TCheckbutton", background="lightyellow")

        bg = style.lookup('TRadioButton', 'background')
        self.init_phase = True
        """ Becomes False few ms after mainloop """

        if tag.multiple:
            self.variable_wrapper = SetVar()
            self.checkboxes(bg)
        else:
            self.variable_wrapper = VariableAnyWrapper(self.variable, {k: v for k, v, *_ in self.options})
            if len(self.options) >= adaptor.settings.combobox_since and AutoCombobox:
                self.widget = self.combobox()
            else:
                self.radio(bg)

        # if radio_select_on_focus is True, we want to ignore the first FocusIn event
        nested_frame.after(200, self.end_init_phase)

    def checkboxes(self, bg):
        options = self.options
        tag = self.tag
        nested_frame = self.frame

        vw = self.variable_wrapper

        for i, (choice_label, choice_val, tip, tupled_key) in enumerate(options):
            var = BooleanVar(value=choice_val in tag.val)

            def on_toggle(val=choice_val, var=var):
                if var.get():
                    vw.add(val)
                else:
                    vw.remove(val)
                tag._last_ui_val = False
                return tag._on_change_trigger(vw.get())

            button = Checkbutton(nested_frame,
                                 text=choice_label,
                                 variable=var,
                                 command=on_toggle,
                                 style="Highlight.TCheckbutton" if tip else "",
                                 #    takefocus=True
                                 )

            button.pack(anchor="w")

    def radio(self, bg):
        options = self.options
        tag = self.tag
        adaptor = self.adaptor
        nested_frame = self.frame
        buttons = []

        for i, (choice_label, choice_val, tip, tupled_key) in enumerate(options):
            is_selected = choice_val is tag.val
            rb = Radiobutton(nested_frame,
                             text="",
                             variable=self.variable,
                             value=choice_label,
                             style="Highlight.TRadiobutton" if tip else "",
                             takefocus=is_selected)
            if adaptor.settings.radio_select_on_focus:
                rb.bind("<FocusIn>",
                        lambda _, var=self.variable, val=choice_label: self.select_on_focus(var, val),
                        add='+')

                # Set the Tab to refocus the currently selected button when getting back to widget
                # The default tkinter behaviour is that Tab iterates over all radio buttons
                # which does not make sense.
            rb.bind("<FocusIn>",
                    lambda _, rb=rb, buttons=buttons: self.change_takefocus(rb, buttons),
                    add='+')
            rb.grid(row=i, column=1, sticky="w")
            buttons.append(rb)

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
            self.variable_wrapper.set(k)
            return True
        return False

    def combobox(self):
        options = self.options
        widget = AutoCombobox(self.frame, textvariable=self.variable)
        widget['values'] = [k for k, *_ in options]
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
