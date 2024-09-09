from ast import literal_eval
from dataclasses import dataclass, fields
from types import FunctionType, MethodType, UnionType
from typing import TYPE_CHECKING, Callable, Iterable, Optional, TypeVar, get_args, get_type_hints

from .auxiliary import flatten

if TYPE_CHECKING:
    from .form_dict import FormDict
    from typing import Self  # remove the line as of Python3.11 and make `"Self" -> Self`

# Pydantic is not a project dependency, that is just an optional integration
try:  # Pydantic is not a dependency but integration
    from pydantic import ValidationError as PydanticValidationError
    from pydantic import create_model
    pydantic = True
except:
    pydantic = False
    PydanticValidationError = None
    create_model = None
try:   # Attrs is not a dependency but integration
    import attr
except:
    attr = None


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
PydanticFieldInfo = TypeVar("PydanticFieldInfo")
AttrsFieldInfo = TypeVar("AttrsFieldInfo")


@dataclass
class Tag:
    """ Wrapper around a value that encapsulates a description, validation etc.
        When you provide a value to an interface, you may instead use this object.

        Bridge between the input values and a UI widget. The widget is created with the help of this object,
        then transforms the value back (str to int conversion etc).

        (Ex: Merge the dict of dicts from the GUI back into the .env object holding the configuration.)
        """

    val: FieldValue = None
    """ The value wrapped by FormField.

    ```python
    tag = FormField(True, "", bool)
    m.form({"My boolean": tag})
    print(tag.val)  # True/False
    ```
    """
    description: str = ""
    """ The description displayed in the UI. """

    annotation: type | None = None
    """ Used for validation. To convert an empty '' to None.
        If not set, will be determined automatically from the `val` type.
    """
    name: str | None = None
    """ Name displayed in the UI. """

    validation: Callable[["Tag"], ValidationResult | tuple[ValidationResult,
                                                                 FieldValue]] | None = None
    """ When the user submits the form, the values are validated (and possibly transformed) with a callback function.
        If the validation fails, user is prompted to edit the value.
        Return True if validation succeeded or False or an error message when it failed.

        ```python
        def check(tag: FormField):
            if tag.val < 10:
                return "The value must be at least 10"
        m.form({"number", FormField(12, validation=check)})
        ```

        Either use a custom callback function or mininterface.validators.

        ```python
        from mininterface.validators import not_empty
        m.form({"number", FormField("", validation=not_empty)})
        # User cannot leave the field empty.
        ```

        You may use the validation in a type annotation.
        ```python
        from mininterface import FormField, Validation
        @dataclass
        class Env:
            my_text: Annotated[str, Validation(not_empty) = "will not be emtpy"

            # which is an alias for:
            # my_text: Annotated[str, FormField(validation=not_empty)] = "will not be emtpy"
        ```

    NOTE Undocumented feature, we can return tuple, while the [ValidationResult, FieldValue] to set the self.val.

    NOTE I am not sure where to validate. If I have a complex object in the form,
    would not annotation check spoil it before validation can transoform the value?
    I am not sure whether to store the transformed value in the ui_value or fixed_value.
    """

    choices: list[str] = None
    # TODO docs missing
    # TODO impementation in TextualInterface missing

    _src_dict: TD | None = None
    """ The original dict to be updated when UI ends."""

    _src_obj: TD | None = None
    """ The original object to be updated when UI ends.
        If not set earlier, fetches name, annotation, _pydantic_field from this class.
    """
    _src_key: str | None = None
    """ Key in the src object / src dict """
    _src_class: type | None = None
    """ If not set earlier, fetch name, annotation and _pydantic_field from this class. """

    #
    # Following attributes are not meant to be set externally.
    #
    original_val = None
    """ The original value, preceding UI change.  Handy while validating.

    ```python
    def check(tag.val):
        if tag.val != tag.original_val:
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
    _pydantic_field: PydanticFieldInfo = None
    _attrs_field: AttrsFieldInfo = None

    def __post_init__(self):
        # Fetch information from the parent object
        if self._src_obj and not self._src_class:
            self._src_class = self._src_obj
        if self._src_class:
            if not self.annotation:  # when we have _src_class, we must have _src_key too
                self.annotation = get_type_hints(self._src_class).get(self._src_key)
                field_type = self._src_class.__annotations__.get(self._src_key)
                if field_type and hasattr(field_type, '__metadata__'):
                    for metadata in field_type.__metadata__:
                        if isinstance(metadata, Tag):
                            self._fetch_from(metadata)  # NOTE might fetch from a pydantic model too
            if pydantic:  # Pydantic integration
                self._pydantic_field: dict | None = getattr(self._src_class, "model_fields", {}).get(self._src_key)
            if attr:  # Attrs integration
                try:
                    self._attrs_field: dict | None = attr.fields_dict(self._src_class.__class__).get(self._src_key)
                except attr.exceptions.NotAnAttrsClassError:
                    pass
        if not self.name and self._src_key:
            self.name = self._src_key

        if not self.annotation:
            self.annotation = type(self.val)
        self._original_desc = self.description
        self._original_name = self.name
        self.original_val = self.val

    def __repr__(self):
        field_strings = []
        for field in fields(self):
            field_value = getattr(self, field.name)
            # clean-up protected members
            if field.name.startswith("_"):
                continue

            # Display 'validation=not_empty' instead of 'validation=<function not_empty at...>'
            if field.name == 'validation' and (func_name := getattr(field_value, "__name__", "")):
                v = f"{field.name}={func_name}"
            else:
                v = f"{field.name}={field_value!r}"

            field_strings.append(v)
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def _fetch_from(self, tag: "Self"):
        """ Fetches public attributes from another instance. """
        for attr in ['val', 'description', 'annotation', 'name', 'validation', 'choices']:
            if getattr(self, attr) is None:
                setattr(self, attr, getattr(tag, attr))

    def _is_a_callable(self) -> bool:
        """ True, if the value is a callable function.
        Why not checking isinstance(self.annotation, Callable)?
        Because a str is a Callable too. We disburden the user when instructing them to write
            `my_var: Callable = x` instead of `my_var: FunctionType = x`
            but then, we need this check.
        """
        return isinstance(self.annotation, (FunctionType, MethodType)) \
            or isinstance(self.annotation, Callable) and isinstance(self.val, (FunctionType, MethodType))

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

    def _repr_annotation(self):
        if isinstance(self.annotation, UnionType):
            return repr(self.annotation)
        else:
            return self.annotation.__name__

    def _validate(self, out_value) -> FieldValue:
        """ Runs
            * self.validation callback
            * pydantic validation
            * annotation type validation

            If succeeded, return the (possibly transformed) value.
            If failed, raises ValueError.
        """
        if self.validation:
            last = self.val
            self.val = out_value
            res = self.validation(self)
            if isinstance(res, tuple):
                passed, out_value = res
                self.val = out_value
            else:
                passed = res
                self.val = last
            if passed is not True:  # we did not pass, there might be an error message in passed
                self.set_error_text(passed or f"Validation fail")
                raise ValueError

        # pydantic_check
        if self._pydantic_field:
            try:
                create_model('ValidationModel', check=(self.annotation, self._pydantic_field))(check=out_value)
            except PydanticValidationError as e:
                self.set_error_text(e.errors()[0]["msg"])
                raise ValueError
        # attrs check
        if self._attrs_field:
            try:
                attr.make_class(
                    'ValidationModel',
                    {"check": attr.ib(validator=self._attrs_field.validator)}
                )(check=out_value)
            except ValueError as e:
                self.set_error_text(str(e))
                raise

        # Type check
        if self.annotation and not isinstance(out_value, self.annotation):
            self.set_error_text(f"Type must be {self._repr_annotation()}!")
            raise ValueError
        return out_value

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

            try:
                seems_bad = not isinstance(out_value, self.annotation) and isinstance(out_value, str)
            except TypeError:
                # Why checking TypeError? Due to Pydantic.
                # class Inner(BaseModel):
                #     id: int
                # class Model(BaseModel):
                #     items1: List[Item] = []
                #          'TypeError: Subscripted generics cannot be used with class and instance checks'
                #     items2: list[Item] = []
                #           'TypeError: cannot be a parameterized generic'
                pass
            else:
                if seems_bad:
                    try:
                        # Textual ask_number -> user writes '123', this has to be converted to int 123
                        # NOTE: Unfortunately, type(list) looks awful here. @see TextualInterface.form comment.
                        out_value = self.annotation(ui_value)
                    except (TypeError, ValueError):
                        # Automatic conversion failed
                        pass

        # User and type validation check
        try:
            self.val = self._validate(out_value)   # checks succeeded, confirm the value
        except ValueError:
            return False

        # Store to the source user data
        if self._src_dict:
            self._src_dict[self._src_key] = out_value
        elif self._src_obj:
            setattr(self._src_obj, self._src_key, out_value)
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
    def submit_values(updater: Iterable[tuple["Tag", FFValue]]) -> bool:
        """ Returns whether the form is alright or whether we should revise it.
        Input is tuple of the FormFields and their new values from the UI.
        """
        # Why list? We need all the FormField values be updates from the UI.
        # If the revision is needed, the UI fetches the values from the FormField.
        # We need the keep the values so that the user does not have to re-write them.
        return all(list(tag.update(ui_value) for tag, ui_value in updater))

    @staticmethod
    def submit(fd: "FormDict", ui: dict):
        """ Returns whether the form is alright or whether we should revise it.
        Input is the FormDict and the UI dict in the very same form.
        """
        return Tag.submit_values(zip(flatten(fd), flatten(ui)))
