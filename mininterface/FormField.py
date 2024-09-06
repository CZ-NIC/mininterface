from ast import literal_eval
from dataclasses import dataclass, fields
from types import UnionType
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, TypeVar, get_args

from .auxiliary import flatten

if TYPE_CHECKING:
    from .FormDict import FormDict

FFValue = TypeVar("FFValue")
TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """
FieldValue = TypeVar("FieldValue")
""" value """
ErrorMessage = TypeVar("ErrorMessage")
""" Callback validation error message"""
ValidationResult = bool | ErrorMessage
""" Callback validation result is either boolean or an error message. """

# TODO rename to Field?


@dataclass
class FormField:
    """ Enrich a value with a description, validation etc.
        When you provide a value to an interface, you may instead use this object.

        Bridge between the input values and a UI widget. The widget is created with the help of this object,
        then transforms the value back (str to int conversion etc).

        (Ex: Merge the dict of dicts from the GUI back into the .env object holding the configuration.)
        """

    val: FieldValue
    """ The value wrapped by FormField.

    ```python
    ff = FormField(True, "", bool)
    m.form({"My boolean": ff})
    print(ff.val)  # True/False
    ```
    """
    description: str = ""
    """ The description displayed in the UI. """

    annotation: type | None = None
    """ Used for validation. To convert an empty '' to None.
        If not set, will be determined automatically from the `val` type.
    """
    name: str | None = None
    """ Name displayed in the UI.
        NOTE: Only TextualInterface uses this by now.
        GuiInterface reads the name from the dict.
        In the future, Textual should be able to do the same
        and both, Gui and Textual should use FormField.name as override.
    """

    validation: Callable[["FormField"], ValidationResult | tuple[ValidationResult,
                                                                FieldValue]] | None = None
    """ When the user submits the form, the values are validated (and possibly transformed) with a callback function.
        If the validation fails, user is prompted to edit the value.
        Return True if validation succeeded or False or an error message when it failed.

        ```python
        def check(ff: FormField):
            if ff.val < 10:
                return "The value must be at least 10"
        m.form({"number", FormField(12, validation=check)})
        ```

        Either use a custom callback function or mininterface.validators.

        ```python
        from mininterface.validators import not_empty
        m.form({"number", FormField("", validation=not_empty)})
        # User cannot leave the field empty.
        ```

    NOTE Undocumented feature, we can return tuple, while the [ValidationResult, FieldValue] to set the self.val.

    NOTE I am not sure where to validate. If I have a complex object in the form,
    would not annotation check spoil it before validation can transoform the value?
    I am not sure whether to store the transformed value in the ui_value or fixed_value.
    """

    _src_dict: tuple[TD, TK] | None = None
    """ The original dict to be updated when UI ends.
    """
    _src_obj: tuple[TD, TK] | None = None
    """ The original object to be updated when UI ends.
    NOTE might be merged to `src`
    """

    #
    # Following attributes are not meant to be set externally.
    #
    original_val = None
    """ The original value, preceding UI change.  Handy while validating.

    ```python
    def check(ff.val):
        if ff.val != ff.original_val:
            return "You have to change the value."
    m.form({"number", FormField(8, validation=check)})
    ```
    """

    error_text = None
    """ Error text if type check or validation fail and the UI has to be revised """

    # _has_ui_val = None
    # """ Distinguish _ui_val default None from the user UI input None """
    # _ui_val = None
    # """ Auxiliary variable. UI state → validation fails on a field, we need to restore """

    def __post_init__(self):
        if not self.annotation:
            self.annotation = type(self.val)
        self._original_desc = self.description
        self._original_name = self.name
        self.original_val = self.val

    def __repr__(self):
        field_strings = []
        for field in fields(self):
            field_value = getattr(self, field.name)
            # Display 'validation=not_empty' instead of 'validation=<function not_empty at...>'
            if field.name == 'validation' and (func_name := getattr(field_value, "__name__", "")):
                v = f"{field.name}={func_name}"
            else:
                v = f"{field.name}={field_value!r}"
            field_strings.append(v)
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def set_error_text(self, s):
        self._original_desc = o = self.description
        self._original_name = n = self.name

        self.description = f"{s} {o}"
        self.name = f"* {n}"
        self.error_text = s

    def remove_error_text(self):
        self.description = self._original_desc
        self.name = self._original_name
        self.error_text = None

    # NOTE remove
    # def _get_ui_val(self, allowed_types: tuple | None = None):
    #     """ Internal function used from within a UI only, not from the program.

    #     It returns the val, however the field was already displayed in the UI, it preferably
    #     returns the value as presented in the UI (self._ui_val). NOTE bad description

    #     :param allowed_types If the value is not their instance, convert to str.
    #         Because UIs are not able to process all types.
    #     """
    #     # NOTE remove
    #     # if self._has_ui_val and self._ui_val is not None:
    #     #     v = self._ui_val
    #     # else:
    #     v = self.val
    #     if allowed_types and not isinstance(v, allowed_types):
    #         v = str(v)
    #     return v

    def _repr_annotation(self):
        if isinstance(self.annotation, UnionType):
            return repr(self.annotation)
        else:
            return self.annotation.__name__

    def update(self, ui_value) -> bool:
        """ UI value → FormField value → original value. (With type conversion and checks.)

            The value has been updated in a UI.
            Update accordingly the value in the original linked dict/object
            the mininterface was invoked with.

            Validates the type and do the transformation.
            (Ex: Some values might be nulled from "".)

            Return bool, whether the value is alright or whether the revision is needed.
        """
        self.remove_error_text()
        out_value = ui_value  # The proposed value, with fixed type.
        # NOTE might be removed
        # self._ui_val = ui_value
        # self._has_ui_val = True

        # Type conversion
        # Even though GuiInterface does some type conversion (str → int) independently,
        # other interfaces does not guarantee that. Hence, we need to do the type conversion too.
        if self.annotation:
            if ui_value == "" and type(None) in get_args(self.annotation):
                # The user is not able to set the value to None, they left it empty.
                # Cast back to None as None is one of the allowed types.
                # Ex: `severity: int | None = None`
                out_value = None
            elif self.annotation == Optional[int]:
                try:
                    out_value = int(ui_value)
                except ValueError:
                    pass
            elif self.annotation in (list, tuple, set):
                # basic support for iterables, however, it will not work for custom subclasses of these built-ins
                try:
                    out_value = literal_eval(ui_value)
                except SyntaxError:
                    self.set_error_text(f"Not a valid {self._repr_annotation()}")
                    return False

            if not isinstance(out_value, self.annotation):
                if isinstance(out_value, str):
                    try:
                        # Textual ask_number -> user writes '123', this has to be converted to int 123
                        # NOTE: Unfortunately, type(list) looks awful here. @see TextualInterface.form comment.
                        out_value = self.annotation(ui_value)
                    except (TypeError, ValueError):
                        # Automatic conversion failed
                        pass

        # User validation check
        if self.validation:
            last = self.val
            self.val = out_value
            res = self.validation(self)
            if isinstance(res, tuple):
                passed, out_value = res
                self.val = ui_value = out_value
            else:
                passed = res
                self.val = last
            if passed is not True:  # we did not pass, there might be an error message in passed
                self.set_error_text(passed or f"Validation fail")
                # self.val = last
                return False

        # Type check
        if self.annotation and not isinstance(out_value, self.annotation):
            self.set_error_text(f"Type must be {self._repr_annotation()}!")
            # self.val = last
            return False  # revision needed

        # keep values if revision needed
        # We merge new data to the origin. If form is re-submitted, the values will stay there.
        self.val = out_value  # checks succeeded, confirm the value


        # Store to the source user data
        if self._src_dict:
            d, k = self._src_dict
            d[k] = out_value
        elif self._src_obj:
            d, k = self._src_obj
            setattr(d, k, out_value)
        else:
            # This might be user-created object. There is no need to update anything as the user reads directly from self.val.
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
