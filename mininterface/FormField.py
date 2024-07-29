from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Optional, TypeVar, get_args

from .auxiliary import flatten

if TYPE_CHECKING:
    from .FormDict import FormDict

try:
    from tkinter_form import Value
except ImportError:
    # TODO put into GuiInterface create_ui(ff: FormField)
    @dataclass
    class Value:
        """ This class helps to enrich the field with a description. """
        val: Any
        description: str


FFValue = TypeVar("FFValue")
TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """


@dataclass
class FormField(Value):
    """ Bridge between the input values and a UI widget.
        Helps to creates a widget from the input value (includes description etc.),
        then transforms the value back (str to int conversion etc).

        (Ex: Merge the dict of dicts from the GUI back into the object holding the configuration.)
        """

    annotation: Any | None = None
    """ Used for validation. To convert an empty '' to None. """
    name: str | None = None  # NOTE: Only TextualInterface uses this by now.

    src: tuple[TD, TK] | None = None
    """ The original dict to be updated when UI ends. """
    src2: tuple[TD, TK] | None = None
    """ The original object to be updated when UI ends.
    NOTE should be merged to `src`
    """

    def __post_init__(self):
        self._original_desc = self.description

    def set_error_text(self, s):
        self.description = f"{s} {self._original_desc}"

    def update(self, ui_value):
        """ UI value → FormField value → original value. (With type conversion and checks.)

            The value has been updated in a UI.
            Update accordingly the value in the original linked dict
            the mininterface was invoked with.

            Validates the type and do the transformation.
            (Ex: Some values might be nulled from "".)
        """
        fixed_value = ui_value
        if self.annotation:
            if ui_value == "" and type(None) in get_args(self.annotation):
                # The user is not able to set the value to None, they left it empty.
                # Cast back to None as None is one of the allowed types.
                # Ex: `severity: int | None = None`
                fixed_value = None
            elif self.annotation == Optional[int]:
                try:
                    fixed_value = int(ui_value)
                except ValueError:
                    pass

            if not isinstance(fixed_value, self.annotation):
                self.set_error_text(f"Type must be `{self.annotation}`!")
                return False  # revision needed

        # keep values if revision needed
        # We merge new data to the origin. If form is re-submitted, the values will stay there.
        self.val = ui_value

        # Store to the source user data
        if self.src:
            d, k = self.src
            d[k] = fixed_value
        elif self.src2:
            d, k = self.src2
            setattr(d, k, fixed_value)
        else:
            # This might be user-created object. The user reads directly from this. There is no need to update anything.
            pass
        return True
        # Fixing types:
        # This code would support tuple[int, int]:
        #
        #     self.types = get_args(self.annotation) \
        #     if isinstance(self.annotation, UnionType) else (self.annotation, )
        # "All possible types in a tuple. Ex 'int | str' -> (int, str)"
        #
        #
        # def convert(self):
        #     """ Convert the self.value to the given self.type.
        #         The value might be in str due to CLI or TUI whereas the programs wants bool.
        #     """
        #     # if self.value == "True":
        #     #     return True
        #     # if self.value == "False":
        #     #     return False
        #     if type(self.val) is str and str not in self.types:
        #         try:
        #             return literal_eval(self.val)  # ex: int, tuple[int, int]
        #         except:
        #             raise ValueError(f"{self.name}: Cannot convert value {self.val}")
        #     return self.val

    @staticmethod
    def submit_values(updater: Iterable[tuple["FormField", FFValue]]) -> bool:
        """ Returns whether the form is alright or whether we should revise it.
        Input is tuple of the FormFields and their new values from the UI.
        """
        # Why list? We need all the FormField values be updates from the UI.
        # If the revision is needed, the UI fetches the values from the FormField.
        # We need the keep the values so that the user does not have to re-write them.
        return all(list(ff.update(ui_value) for ff, ui_value in updater))

    @staticmethod
    def submit(fd: "FormDict", ui: dict):
        """ Returns whether the form is alright or whether we should revise it.
        Input is the FormDict and the UI dict in the very same form.
        """
        return FormField.submit_values(zip(flatten(fd), flatten(ui)))