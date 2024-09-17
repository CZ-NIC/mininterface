from ast import literal_eval
from dataclasses import dataclass, fields
from datetime import datetime
from types import FunctionType, MethodType, UnionType
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, TypeVar, get_args, get_origin, get_type_hints
from warnings import warn

from .experimental import SubmitButton


from .auxiliary import flatten

if TYPE_CHECKING:
    from .facet import Facet
    from .form_dict import TagDict
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


UiValue = TypeVar("UiValue")
""" Candidate for the TagValue. """
TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """
TagValue = TypeVar("TagValue")
""" Any value. """
ErrorMessage = TypeVar("ErrorMessage")
""" A string, callback validation error message. """
ValidationResult = bool | ErrorMessage
""" Callback validation result is either boolean or an error message. """
PydanticFieldInfo = TypeVar("PydanticFieldInfo")
AttrsFieldInfo = TypeVar("AttrsFieldInfo")
common_iterables = list, tuple, set
ChoiceLabel = str
ChoicesType = list[TagValue] | tuple[TagValue] | set[TagValue] | dict[ChoiceLabel, TagValue]
""" You can denote the choices in many ways.
Either put options in an iterable or to a dict `{labels: value}`.
Values might be Tags as well.
"""


@dataclass
class Tag:
    """ Wrapper around a value that encapsulates a description, validation etc.
        When you provide a value to an interface, you may instead use this object.

        Bridge between the input values and a UI widget. The widget is created with the help of this object,
        then transforms the value back (str to int conversion etc).
        """

    val: TagValue = None
    """ The value wrapped by Tag.

    ```python
    from mininterface import run, Tag

    tag = Tag(True, "This is my boolean", bool)
    m = run()
    m.form({"My boolean": tag})
    print(tag.val)  # True/False
    print()
    ```

    ![Image title](asset/tag_val.avif)

    The encapsulated value is `True`, `tag.description` is 'This is my boolean',
    `tag.annotation` is `bool` and 'My boolean' is used as `tag.name`.
    """
    description: str = ""
    """ The description displayed in the UI. """

    annotation: type | None = None
    """ Used for validation (ex. to convert an empty string to None).
        If not set, will be determined automatically from the [val][mininterface.Tag.val] type.
    """
    name: str | None = None
    """ Name displayed in the UI. """

    validation: Callable[["Tag"], ValidationResult | tuple[ValidationResult,
                                                           TagValue]] | None = None
    """ When the user submits the form, the values are validated (and possibly transformed) with a callback function.
        If the validation fails, user is prompted to edit the value.
        Return True if validation succeeded or False or an error message when it failed.

    [ValidationResult][mininterface.tag.ValidationResult] is a bool or the error message (that implicitly means it has failed).


    ```python
    def check(tag: Tag):
        if tag.val < 10:
            return "The value must be at least 10"
    m.form({"number", Tag(12, validation=check)})
    ```

    Either use a custom callback function or mininterface.validators.

    ```python
    from mininterface.validators import not_empty
    m.form({"number", Tag("", validation=not_empty)})
    # User cannot leave the field empty.
    ```

    You may use the validation in a type annotation.
    ```python
    from mininterface import Tag, Validation
    @dataclass
    class Env:
        my_text: Annotated[str, Validation(not_empty) = "will not be emtpy"

        # which is an alias for:
        # my_text: Annotated[str, Tag(validation=not_empty)] = "will not be emtpy"
    ```

    NOTE Undocumented feature, we can return tuple [ValidationResult, FieldValue] to set the self.val.
    """

    choices: ChoicesType | None = None
    """ Print the radio buttons. Constraint the value.

    ```python
    from dataclasses import dataclass
    from typing import Annotated
    from mininterface import run, Choices

    @dataclass
    class Env:
        foo: Annotated["str", Choices("one", "two")] = "one"

        # `Choices` is an alias for `Tag(choices=)`

    m = run(Env)
    m.form()  # prompts a dialog
    ```
    """
    # NOTE we should support
    # * Enums: Tag(enum) # no `choice` param`
    # * more date types (now only str possible)
    # * mininterface.choice `def choice(choices=, guesses=)`

    on_change: Callable[["Tag"], Any] | None = None
    """ Accepts a callback that launches whenever the value changes (if the validation succeeds).
    The callback runs while the dialog is still running.
    The return value of the callback is currently not used.

    In the following example, we alter the heading title according to the chosen value.

    ```python
    from mininterface import run, Tag

    def callback(tag: Tag):
        tag.facet.set_title(f"Value changed to {tag.val}")

    m = run()
    m.facet.set_title("Click the checkbox")
    m.form({
        "My choice": Tag(choices=["one", "two"], on_change=callback)
    })
    ```

    ![Choice with on change callback](asset/on_change1.avif)
    ![Choice with on change callback chosen](asset/on_change2.avif)
    """

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
    facet: Optional["Facet"] = None
    """ Access to the UI [`facet`][mininterface.facet.Facet] from the front-end side.
    (Read [`Mininterface.facet`][mininterface.Mininterface.facet] to access from the back-end side.)

    Set the UI facet from within a callback, ex. a validator.

    ```python
    from mininterface import run, Tag

    def my_check(tag: Tag):
        tag.facet.set_title("My form title")
        return "Validation failed"

    with run(title='My window title') as m:
        m.form({"My form": Tag(1, validation=my_check)})
    ```

    This happens when you click ok.

    ![Facet front-end](asset/facet_frontend.avif)
    """

    original_val = None
    """ Meant to be read only in callbacks. The original value, preceding UI change. Handy while validating.

    ```python
    def check(tag.val):
        if tag.val != tag.original_val:
            return "You have to change the value."
    m.form({"number", Tag(8, validation=check)})
    ```
    """

    _error_text = None
    """ Meant to be read only. Error text if type check or validation fail and the UI has to be revised """

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
                            # The type of the Tag is another Tag
                            # Ex: `my_field: Validation(...) = 4`
                            self._fetch_from(metadata)  # NOTE might fetch from a pydantic model too
            if pydantic:  # Pydantic integration
                self._pydantic_field: dict | None = getattr(self._src_class, "model_fields", {}).get(self._src_key)
            if attr:  # Attrs integration
                try:
                    self._attrs_field: dict | None = attr.fields_dict(self._src_class.__class__).get(self._src_key)
                except attr.exceptions.NotAnAttrsClassError:
                    pass
        if not self.annotation and self.val is not None and not self.choices:
            # When having choices with None default self.val, this would impose self.val be of a NoneType,
            # preventing it to set a value.
            # Why checking self.val is not None? We do not want to end up with
            # annotated as a NoneType.
            self.annotation = type(self.val)

        if self.annotation is SubmitButton:
            self.val = False

        if not self.name and self._src_key:
            self.name = self._src_key
        self._original_desc = self.description
        self._original_name = self.name
        self.original_val = self.val
        self._last_ui_val = None
        """ This is the value as was in the current UI. Used by on_change. """

    def __repr__(self):
        field_strings = []
        for field in fields(self):
            field_value = getattr(self, field.name)
            # clean-up protected members
            if field.name.startswith("_"):
                continue
            if field.name not in ("val", "description", "annotation", "name"):
                continue

            # Display 'validation=not_empty' instead of 'validation=<function not_empty at...>'
            if field.name == 'validation' and (func_name := getattr(field_value, "__name__", "")):
                v = f"{field.name}={func_name}"
            else:
                v = f"{field.name}={field_value!r}"

            field_strings.append(v)
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def _fetch_from(self, tag: "Self") -> "Self":
        """ Fetches public attributes from another instance.
        (Skips the attributes that are already set.)
        """
        for attr in ['val', 'annotation', 'name', 'validation', 'choices', 'on_change']:
            if getattr(self, attr) is None:
                setattr(self, attr, getattr(tag, attr))
        if self.description == "":
            self.description = tag.description
        return self

    def _is_a_callable(self) -> bool:
        """ True, if the value is a callable function.
        Why not checking isinstance(self.annotation, Callable)?
        Because a str is a Callable too. We disburden the user when instructing them to write
            `my_var: Callable = x` instead of `my_var: FunctionType = x`
            but then, we need this check.
        """
        return self._is_a_callable_val(self.val, self.annotation)

    def _on_change_trigger(self, ui_val):
        """ Trigger on_change only if the value has changed and if the validation succeeds. """
        if self._last_ui_val != ui_val:
            # NOTE we should refresh the Widget when update fails. However, facet does not allow method for that yet.
            if self.update(ui_val) and self.on_change:
                self.on_change(self)
            self._last_ui_val = ui_val

    @staticmethod
    def _is_a_callable_val(val: TagValue, annot: type = None) -> bool:
        if annot is None:
            return isinstance(val, (FunctionType, MethodType))
        return isinstance(annot, (FunctionType, MethodType)) \
            or isinstance(annot, Callable) and isinstance(val, (FunctionType, MethodType))

    def _is_right_instance(self, val) -> bool:
        """ Check if the value conforms self.annotation.

        Like `isinstance` but able to parse complex annotation.

        class Env:
            items1: List[Item] = []
                 'TypeError: Subscripted generics cannot be used with class and instance checks'
            items2: list[Item] = []
                  'TypeError: cannot be a parameterized generic'

        """
        if self.annotation is None:
            return True
        elif self.annotation is SubmitButton:  # NOTE EXPERIMENTAL
            return val is True or val is False

        try:
            return isinstance(val, self.annotation)
        except TypeError:
            if complex_ := self._get_annotation_parametrized():
                origin, subtype = complex_
                return isinstance(val, origin) and all(isinstance(item, subtype) for item in val)

    def _is_subclass(self, class_type):
        print("350: self.annotation", self.annotation)  # TODO
        try:
            return issubclass(self.annotation, class_type)
        except TypeError:  # None, Union etc cast an error
            return False

    def _morph(self, class_type: "Self", morph_if: type):
        """ To be overrided by the subclasses.
        The user used a Path within a Tag and that will turn it into a PathTag when the UI needs it.
        """
        if self._is_subclass(morph_if):  # return a blank PathTag
            return class_type(self.val)

    def _get_annotation_parametrized(self):
        if origin := get_origin(self.annotation):  # list[str] -> list, list -> None
            if origin == UnionType:  # might be just `int | None`
                return
            subtype = get_args(self.annotation)  # list[str] -> (str,), list -> ()
            if (len(subtype) == 1):
                return origin, subtype[0]
            else:
                warn(f"This parametrized generic not implemented: {self.annotation}")
        return None

    def set_error_text(self, s):
        self._original_desc = o = self.description
        self._original_name = n = self.name

        self.description = f"{s} {o}"
        if self.name:
            # Why checking self.name?
            # If not set, we would end up with '* None'
            # `m.form({"my_text": Tag("", validation=validators.not_empty)})`
            self.name = f"* {n}"
        self._error_text = s

    def remove_error_text(self):
        self.description = self._original_desc
        self.name = self._original_name
        self._error_text = None

    def _repr_annotation(self):
        if isinstance(self.annotation, UnionType) or get_origin(self.annotation):
            # ex: `list[str]`
            return repr(self.annotation)
        # ex: `list`` (without name it would be <class list>)
        return self.annotation.__name__

    def _get_ui_val(self):
        """ Get values as suitable for UI.
        Some values are not expected to be parsed by any UI.
        But we will reconstruct them in self.update later.

        Ex: [Path("/tmp"), Path("/usr")] -> ["/tmp", "/usr"].
        We need the latter in the UI because in the first case, ast_literal would not not reconstruct it later.
        """
        if complex_ := self._get_annotation_parametrized():
            origin, _ = complex_
            return origin(str(v)for v in self.val)
        return self.val

    def _get_choices(self) -> dict[ChoiceLabel, TagValue]:
        """ Wherease self.choices might have different format, this returns a canonic dict. """
        def _edit(v):
            if self._is_a_callable_val(v):
                return v.__name__
            if isinstance(v, Tag):
                return v.name
            return v

        if self.choices is None:
            return {}
        if isinstance(self.choices, dict):
            return self.choices
        if isinstance(self.choices, common_iterables):
            return {_edit(v): v for v in self.choices}
        warn(f"Not implemented choices: {self.choices}")

    def _validate(self, out_value) -> TagValue:
        """ Runs
            * self.validation callback
            * pydantic validation
            * annotation type validation

        Returns:
            If succeeded, return the (possibly transformed) value.

        Raises:
            ValueError: If failed, raises ValueError.
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
        if not self._is_right_instance(out_value):
            self.set_error_text(f"Type must be {self._repr_annotation()}!")
            raise ValueError

        return out_value

    def update(self, ui_value: TagValue) -> bool:
        """ UI value → Tag value → original value. (With type conversion and checks.)

        Args:
            ui_value:
                The value as it has been updated in a UI.
                Update accordingly the value in the original linked dict/object
                the mininterface was invoked with.

                Validates the type and do the transformation.
                (Ex: Some values might be nulled from "".)

        Returns:
            bool, whether the value is alright or whether the revision is needed.
        """
        self.remove_error_text()
        out_value = ui_value  # The proposed value, with fixed type.

        # Choice check
        if (ch := self._get_choices()):
            if out_value in ch:
                out_value = ch[out_value]
            else:
                self.set_error_text(f"Must be one of {list(ch.keys())}")
                return False

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
            elif self.annotation in common_iterables:
                # basic support for iterables, however, it will not work for custom subclasses of these built-ins
                try:
                    out_value = literal_eval(ui_value)
                except SyntaxError:
                    self.set_error_text(f"Not a valid {self._repr_annotation()}")
                    return False
            elif self.annotation is datetime:
                try:
                    out_value = self.annotation.fromisoformat(ui_value)
                except ValueError:
                    pass

            if not self._is_right_instance(out_value) and isinstance(out_value, str):
                try:
                    if complex_ := self._get_annotation_parametrized():
                        origin, cast_to = complex_
                        # Textual ask_number -> user writes '123', this has to be converted to int 123
                        # NOTE: Unfortunately, type(list) looks awful here. @see TextualInterface.form comment.
                        # (Maybe that's better now.)
                        candidate = origin(cast_to(v) for v in literal_eval(ui_value))
                        if self._is_right_instance(candidate):
                            out_value = candidate
                    else:
                        out_value = self.annotation(ui_value)
                except (TypeError, ValueError, SyntaxError):
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
    def _submit_values(updater: Iterable[tuple["Tag", UiValue]]) -> bool:
        """ Returns whether the form is alright or whether we should revise it.
        Input is tuple of the Tags and their new values from the UI.
        """
        # Why list? We need all the Tag values be updates from the UI.
        # If the revision is needed, the UI fetches the values from the Tag.
        # We need the keep the values so that the user does not have to re-write them.
        return all(list(tag.update(ui_value) for tag, ui_value in updater))

    @staticmethod
    def _submit(fd: "TagDict", ui: dict):
        """ Returns whether the form is alright or whether we should revise it.
        Input is the TagDict and the UI dict in the very same form.
        """
        return Tag._submit_values(zip(flatten(fd), flatten(ui)))
