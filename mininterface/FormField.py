from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Optional, TypeVar, get_args

from .auxiliary import flatten

if TYPE_CHECKING:
    from .FormDict import FormDict

FFValue = TypeVar("FFValue")
TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """


@dataclass
class FormField:
    """ This class helps to enrich the field with a description.
        Bridge between the input values and a UI widget.
        Helps to creates a widget from the input value (includes description etc.),
        then transforms the value back (str to int conversion etc).

        (Ex: Merge the dict of dicts from the GUI back into the object holding the configuration.)
        """

    val: Any
    """ The value being enriched by this object. """
    description: str
    """ The description. """

    annotation: Any | None = None
    """ Used for validation. To convert an empty '' to None.
        If not set, will be determined automatically from the `val` type.
    """
    name: str | None = None
    """ NOTE: Only TextualInterface uses this by now.
        GuiInterface reads the name from the dict.
        In the future, Textual should be able to do the same
        and both, Gui and Textual should use FormField.name as override.
    """

    src_dict: tuple[TD, TK] | None = None
    """ The original dict to be updated when UI ends.
        The processed value is in the self.processed_value too.
    """
    src_obj: tuple[TD, TK] | None = None
    """ The original object to be updated when UI ends.
        The processed value is in the self.processed_value too.
    NOTE should be merged to `src`
    """

    processed_value = None
    """ The value set while processed through the UI. """

    def __post_init__(self):
        if not self.annotation:
            self.annotation = type(self.val)
        self._original_desc = self.description

    def set_error_text(self, s):
        self.description = f"{s} {self._original_desc}"

    def remove_error_text(self):
        self.description = self._original_desc

    def update(self, ui_value):
        """ UI value → FormField value → original value. (With type conversion and checks.)

            The value has been updated in a UI.
            Update accordingly the value in the original linked dict
            the mininterface was invoked with.

            Validates the type and do the transformation.
            (Ex: Some values might be nulled from "".)
        """
        fixed_value = ui_value
        self.remove_error_text()
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
                if isinstance(fixed_value, str):
                    try:
                        # Textual ask_number -> user writes '123', this has to be converted to int 123
                        # NOTE: Unfortunately, type(list) looks awful here. @see TextualInterface.form comment.
                        fixed_value = self.annotation(ui_value)
                    except (TypeError, ValueError):
                        # Automatic conversion failed
                        pass

            if not isinstance(fixed_value, self.annotation):
                self.set_error_text(f"Type must be `{self.annotation}`!")
                return False  # revision needed

        # keep values if revision needed
        # We merge new data to the origin. If form is re-submitted, the values will stay there.
        # NOTE: We might store `self.val = fixed_value`.
        # This would help when the user defines FormField themselves
        # because there is no other way to access fixed_value from outside (we try self.processed_value).
        # However `self.val = fixed_value`` looks awful when TextualInterface have a list of strings
        # and the form is recreated, strings split to letters, @see TextualInterface.form comment.
        self.val = ui_value
        self.processed_value = fixed_value

        # Store to the source user data
        if self.src_dict:
            d, k = self.src_dict
            d[k] = fixed_value
        elif self.src_obj:
            d, k = self.src_obj
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