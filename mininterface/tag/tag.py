from ast import literal_eval
from collections import abc
from dataclasses import dataclass, fields
from datetime import date, time
from enum import Enum
from types import FunctionType, MethodType, NoneType, UnionType
from typing import (TYPE_CHECKING, Any, Callable, Generic, Iterable, Optional, TypeVar,
                    Union, get_args, get_origin)
from warnings import warn

from annotated_types import BaseMetadata, GroupedMetadata

from .._lib.auxiliary import (common_iterables, flatten, guess_type,
                              matches_annotation, serialize_structure,
                              subclass_matches_annotation, validate_annotated_type)
from ..experimental import FacetCallback, SubmitButton
from .internal import (BoolWidget, CallbackButtonWidget, FacetButtonWidget,
                       RecommendedWidget, SubmitButtonWidget)
from .type_stubs import TagCallback

if TYPE_CHECKING:
    from typing import \
        Self  # remove the line as of Python3.11 and make `"Self" -> Self`

    from ..facet import Facet
    from .._lib.form_dict import TagDict
else:
    # NOTE this is needed for tyro dataclass serialization (which still does not work
    # as Tag is not a frozen object, you cannot use it as an annotation)
    Facet = object

# Pydantic is not a project dependency, that is just an optional integration
try:  # Pydantic is not a dependency but integration
    from pydantic import ValidationError as PydanticValidationError
    from pydantic import create_model
    pydantic = True
except ImportError:
    pydantic = False
    PydanticValidationError = None
    create_model = None
try:   # Attrs is not a dependency but integration
    import attr
except ImportError:
    attr = None


TD = TypeVar("TD")
""" dict """
TK = TypeVar("TK")
""" dict key """
# Why TagValue bounded to Any? This might help in the future to allow a dataclass to have a Tag as the attribute value. (It is not frozen now.)
TagValue = TypeVar("TagValue", bound=Any)
""" Any value. It is being wrapped by a [Tag][mininterface.Tag]. """
UiValue = TagValue | str
""" Candidate for the TagValue. Produced by the UI. Might be of the same type as the target TagValue, or str
    (as the default input type for interfaces that do not implement the given type further)."""
ErrorMessage = TypeVar("ErrorMessage")
""" A string, callback validation error message. """
ValidationResult = bool | ErrorMessage
""" Being used at [Tag.validation][mininterface.Tag.validation].

A bool or the error message (that implicitly means the [ValidationCallback][mininterface.tag.tag.ValidationCallback] has failed) as shows the following table.
Optionally, you may add a second argument to specify the tag value (to ex. recommend a better value).

| return | description |
|--|--|
| bool | True if validation succeeded or False if validation failed. |
| str | Error message if the validation failed. |
| tuple[bool\\|str, TagVal] | The first argument is the same as above. The second is the value to be set. |

This example shows the str error message:

```python
def check(tag: Tag):
    if tag.val < 10:
        return "The value must be at least 10"
m.form({"number", Tag(12, validation=check)})
```

This example shows the value transformation. For `val=50+`, the validation fails.

```python
def check(tag: Tag):
    return True, tag.val * 2
m.form({"number", Tag(12, validation=(check, Lt(100)))})
```
"""
PydanticFieldInfo = TypeVar("PydanticFieldInfo", bound=Any)  # see why TagValue bounded to Any?
AttrsFieldInfo = TypeVar("AttrsFieldInfo", bound=Any)  # see why TagValue bounded to Any?
ValsType = Iterable[tuple["Tag", UiValue]]
ValidationCallback = Callable[["Tag"], ValidationResult |
                              tuple[ValidationResult, TagValue]] | BaseMetadata | GroupedMetadata
""" Being used at [Tag.validation][mininterface.Tag.validation].

Either use a custom callback function, a provided [validator][mininterface.validators], or an [annotated-types predicate](https://github.com/annotated-types/annotated-types?#documentation). (You can use multiple validation callbacks combined into an itarable.)

[ValidationResult][mininterface.tag.tag.ValidationResult] is a bool or the error message that implicitly means it has failed. Optionally, you may add a second argument to specify the tag value (to ex. recommend a better value).

# Custom function

Handles the Tag.

```python
from mininterface.tag import Tag

def my_validation(tag: Tag):
    return tag.val > 50

m.form({"number", Tag("", validation=my_validation)})
```

# Provided validators

Found in the [mininterface.validators][mininterface.validators] module.

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
    my_text: Annotated[str, Validation(not_empty)] = "will not be emtpy"

    # which is an alias for:
    # my_text: Annotated[str, Tag(validation=not_empty)] = "will not be emtpy"
```

# annotated-types predicate.

The [annotated-types](https://github.com/annotated-types/annotated-types?#documentation) are de-facto standard for types restraining.

Currently, `Gt, Ge, Lt, Le, MultipleOf and Len` are supported.

```python
from dataclasses import dataclass
from annotated_types import Ge
from mininterface import run

@dataclass
class AnnotatedTypes:
    age: Annotated[int, Ge(18)]

run(AnnotatedTypes).env.age  # guaranteed to be >= 18
```

!!! info
    The annotated-types from the Annotated are prepended to the Tag(validation=) iterable.

    ```python
    @dataclass
    class AnnotatedTypes:
        age: Annotated[int, Ge(18), Tag(validation=custom)]

    # -> age: Annotated[int, Tag(validation=[Ge(18), custom])]
    ```
"""


class MissingTagValue:
    """ The dataclass field has not received a value from the CLI, and this value is required.
    Before anything happens, run.ask_for_missing should re-ask for a real value instead of this placeholder.

    If we fail to fill a value (ex. in a CRON), the program ends.
    """

    def __init__(self, exception: BaseException, eavesdrop):
        self.exception = exception
        self.eavesdrop = eavesdrop

    def __repr__(self):
        return "MISSING"

    def fail(self):
        print(self.eavesdrop)
        raise self.exception


@dataclass
class Tag(Generic[TagValue]):
    """ Wrapper around a value that encapsulates a description, validation etc.

        Bridge between the input values and a UI widget. The widget is created with the help of this object,
        then transforms the value back (str to int conversion etc).

        For dataclasses, use in as an annotation:

        ```python
        from mininterface import run
        @dataclass
        class Env:
            my_str: Annotated[str, Tag(validation=not_empty)]

        m = run(Env)
        ```

        For dicts, use it as a value:

        ```python
        m.form({"My string": Tag(annotation=str, validation=not_empty)})
        ```
        """

    val: TagValue = None
    """ The value wrapped by Tag. It can be any value.

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
    `tag.annotation` is `bool` and 'My boolean' is used as `tag.label`.

    !!! tip
        If the Tag is nested, the info is fetched to the outer Tag.
        When updated, the inner Tag value updates accordingly.

        ```python
        tag = Tag(Tag(True))
        ```
    """
    description: str = ""
    """ The description displayed in the UI. """

    annotation: type[TagValue] | None = None
    """ Used for validation (ex. to convert an empty string to None).
        If not set, will be determined automatically from the [val][mininterface.Tag.val] type.
    """

    validation: Iterable[ValidationCallback] | ValidationCallback | None = None
    """ When the user submits the form, the values are validated (and possibly transformed) with a [ValidationCallback][mininterface.tag.tag.ValidationCallback] function (or several of them).
        If the validation fails, user is prompted to edit the value.

        The [ValidationResult][mininterface.tag.tag.ValidationResult] is either a boolean or an error message. Optionally, you may add a second argument to specify the tag value (to ex. recommend a better value).
    """

    label: str | None = None
    """ Name displayed in the UI. If not set, it is taken from the dict key or the field name.

    ```python
    m.form({"label": ...})
    ```

    ```python
    @dataclass
    class Form:
        my_field: str
    m.form(Form)  # label=my_field
    ```
    """

    on_change: Callable[["Tag"], Any] | None = None
    """ Accepts a callback that launches whenever the value changes (if the validation succeeds).
    The callback runs while the dialog is still running.
    The return value of the callback is currently not used.

    In the following example, we alter the heading title according to the chosen value.

    ```python
    from mininterface import run
    from mininterface.tag import SelectTag

    def callback(tag: Tag):
        tag.facet.set_title(f"Value changed to {tag.val}")

    m = run()
    m.facet.set_title("Click the checkbox")
    m.form({
        "My choice": SelectTag(options=["one", "two"], on_change=callback)
    })
    ```

    ![Choice with on change callback](asset/on_change1.avif)
    ![Choice with on change callback chosen](asset/on_change2.avif)
    """

    #
    # Following attributes are not meant to be set externally.
    #
    _src_dict: TD | None = None
    """ The original dict to be updated when UI ends."""

    _src_obj: TD | list[TD] | None = None
    """ The original object (or their list) to be updated when UI ends.
        If not set earlier, fetches name, annotation, _pydantic_field from this class.
        How come there might be multiple original objects? When dealing with subcommands,
        they can share the common ancester fields (like `--output-filename`).
    """
    _src_key: str | None = None
    """ Key in the src object / src dict """
    _src_class: type | None = None
    """ If not set earlier, fetch name, annotation and _pydantic_field from this class. """

    _facet: Optional["Facet"] = None

    @property
    def facet(self) -> Facet:
        """ Access to the UI [`facet`][mininterface._mininterface.Facet] from the front-end side.
        (Read [`Mininterface.facet`][mininterface.Mininterface.facet] to access from the back-end side.)

        Use the UI facet from within a callback, ex. from a validator.

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
        if self._facet is None:
            raise ValueError("Facet has not been set")
        return self._facet

    _original_val: TagValue = None

    @property
    def original_val(self) -> TagValue:
        """ Meant to be read only in callbacks. The original value, preceding UI change. Handy while validating.

        ```python
        def check(tag.val):
            if tag.val != tag.original_val:
                return "You have to change the value."
        m.form({"number", Tag(8, validation=check)})
        ```
        """
        return self._original_val

    _error_text = None
    """ Meant to be read only. Error text if type check or validation fail and the UI has to be revised """

    _pydantic_field: PydanticFieldInfo = None
    _attrs_field: AttrsFieldInfo = None
    _original_desc: Optional[str] = None
    _original_label: Optional[str] = None
    _last_ui_val: TagValue = None
    """ This is the value as was in the current UI. Used by on_change_trigger
        to determine whether the UI value changed. """

    def __post_init__(self):
        # Determine annotation and fetch other information.

        # Fetch information from the nested tag: `Tag(Tag(...))`
        if isinstance(self.val, Tag):
            if self._src_obj or self._src_key:
                raise ValueError("Wrong Tag inheritance, submit a bug report.")
            self._fetch_from(self.val)
            self.val = self.val.val

        # Fetch information from the parent object
        if self._src_class:
            if pydantic:  # Pydantic integration
                self._pydantic_field: dict | None = getattr(self._src_class, "model_fields", {}).get(self._src_key)
            if attr:  # Attrs integration
                try:
                    self._attrs_field: dict | None = attr.fields_dict(self._src_class).get(self._src_key)
                except attr.exceptions.NotAnAttrsClassError:
                    pass
        if not self.annotation and self.val is not None:
            if isinstance(self.val, Enum) or (isinstance(self.val, type) and issubclass(self.val, Enum)):
                self.annotation = Enum
            else:
                # When having options with None default self.val, this would impose self.val be of a NoneType,
                # preventing it to set a value.
                # Why checking self.val is not None? We do not want to end up with
                # annotated as a NoneType.
                self.annotation = guess_type(self.val)

        if self.annotation is SubmitButton:
            self.val = False

        if not self.label:
            if self._src_key:
                self.label = self._src_key
            # It seems to be it is better to fetch the name from the dict or object key than to use the function name.
            # We are using get_name() instead.
            # if self._is_a_callable():
                #     self.label = self.val.__name__
        if not self.description and self._is_a_callable():
            # NOTE does not work, do a test, there is `(fixed to` instead
            self.description = self.val.__doc__

        self._original_desc = self.description
        self._original_label = self.label
        self._original_val = self.val
        self._last_ui_val = None

    def __repr__(self):
        field_strings = []
        for field in fields(self):
            field_value = getattr(self, field.name)
            # clean-up protected members
            if field.name.startswith("_"):
                continue
            if field.name not in ("val", "description", "annotation", "label"):
                continue

            # Display 'validation=not_empty' instead of 'validation=<function not_empty at...>'
            if field.name == 'validation' and (func_name := getattr(field_value, "__name__", "")):
                v = func_name
            elif field.name == "val" and self._is_a_callable():
                v = self.val.__name__
            else:
                v = repr(field_value)

            field_strings.append(f"{field.name}={v}")
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def __hash__(self):
        # Once upon a time, github actions test stopped working with no hash function here.
        # The tests for commit c108a6d passed on 2024-10-16. But strangely, the very same commit failed on 2024-10-24.
        # Python patch version did not change. On the local machine, the tests work great with no obstacle.
        # Hence, I add a hash function with no intention yet.
        return hash(str(self))

    def _fetch_from(self, tag: Union["Tag", dict], name: str = "", include_ref=False) -> "Self":
        """ Fetches attributes from another instance. (Skips the attributes that are already set.)
        Register the fetched tag to be updated when we change.

        Note that without the parameters, __post_init__ might end up with a default and wrong annotation.
        Hence consider setting annotation on Tag init instead of fetching it later.
        ```python
        p = PathTag() .. -> annotation = Path
        p._fetch_from(PathTag(annotation=list[Path])) # still annotation = Path
        ```
        """
        use_as_src = True
        if isinstance(tag, dict):
            tag = Tag(**tag)
            use_as_src = False

        ignored = {'description', '_pydantic_field', '_attrs_field', '_last_ui_val'}
        if include_ref:
            use_as_src = False
        else:
            ignored |= {'_src_dict', '_src_obj', '_src_key', '_src_class'}
        for attr in tag.__dict__:
            if attr in ignored:
                continue
            if getattr(self, attr, None) is None:
                setattr(self, attr, getattr(tag, attr))
        if use_as_src:
            self._src_obj_add(tag)
        if self.description == "":
            self.description = tag.description
        if name and self.label is None:
            self._original_label = self.label = name
        return self

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_facet"] = None  # NOTE WebUi rather than deleting facet, try removing StdIO from it.
        state["_src_dict"] = None
        state["_src_obj"] = None
        state["_src_class"] = None
        return state

    def __setstate__(self, state):
        # NOTE check with WebUI. If not needed, remove.
        self.__dict__.update(state)
        self._update_source(self.val)

    def _is_a_callable(self) -> bool:
        """ True, if the value is a callable function.
        Why not checking isinstance(self.annotation, Callable)?
        Because a str is a Callable too. We disburden the user when instructing them to write
            `my_var: Callable = x` instead of `my_var: FunctionType = x`
            but then, we need this check.
        """
        return self._is_a_callable_val(self.val, self.annotation)

    def _run_callable(self):
        return self.val()

    def _on_change_trigger(self, ui_val):
        """ Trigger on_change only if the value has changed and if the validation succeeds. """
        if self._last_ui_val != ui_val:
            # NOTE we should refresh the Widget when update fails; see facet comment
            if self.update(ui_val) and self.on_change:
                self.on_change(self)
            self._last_ui_val = ui_val

    def _recommend_widget(self) -> RecommendedWidget | type["Self"] | None:
        """ Recommend a widget type.
        The tag should be handled this way:
        1. according to the inheritace (Tag children like PathTag)
        2. according to the result of this method
        3. Returning None means the type is scalar or unknown (like mixed) and thus might default to str handling.
        """
        v = self._get_ui_val()
        if self.annotation is bool:
            return BoolWidget()
        elif self.annotation is SubmitButton:  # NOTE EXPERIMENTAL
            return SubmitButtonWidget()
        elif self._is_a_callable():
            return CallbackButtonWidget()
        elif self.annotation is FacetCallback:
            return FacetButtonWidget()
        return None  # scalar or unknown -›

    @staticmethod
    def _is_a_callable_val(val: TagValue, annot: type = None) -> bool:
        # Note _is_a_callable_val(CallableTag(...)) -> False, as CallableTag is not a FunctionType
        detect = FunctionType, MethodType
        if annot is None:
            return isinstance(val, detect)
        return isinstance(annot, detect) or isinstance(annot, Callable) and isinstance(val, detect)

    def _is_right_instance(self, val) -> bool:
        """ Check if the value conforms self.annotation.

        Like `isinstance` but able to parse complex annotation.

        class Env:
            items1: List[Item] = []
                 'TypeError: Subscripted generics cannot be used with class and instance checks'
            items2: list[Item] = []
                  'TypeError: cannot be a parameterized generic'

        """
        if self.annotation is None:  # no annotation check, everything is fine then
            return True
        elif self.annotation is SubmitButton:  # NOTE EXPERIMENTAL
            return val is True or val is False

        return matches_annotation(val, self.annotation)
        # NOTE remove
        try:
            return isinstance(val, self.annotation)
        except TypeError:
            if val is None and NoneType in get_args(self.annotation):
                return True
            for origin, subtype in self._get_possible_types():
                if origin:
                    if isinstance(val, origin) and all(isinstance(item, subtype) for item in val):
                        return True
                else:
                    if isinstance(val, subtype):
                        return True
            return False

    def _is_subclass(self, class_type: type | tuple[type]):
        # if origin := get_origin(self.annotation):  # list[str] -> list, list -> None
        #     subtype = get_args(self.annotation)  # list[str] -> (str,), list -> ()
        #     if origin in [UnionType, Union]:  # ex: `int | None`, `list[int] | None`, `Optional[list[int]]`
        #         return any(subclass_matches_annotation(subt, class_type) for subt in subtype)
        # return subclass_matches_annotation(self.annotation, class_type)
        try:
            if issubclass(self.annotation, class_type):
                return True
            if issubclass(class_type, self.annotation):
                # Let me explain. DatetimeTag receives a date.
                # In __post_init__, it resolves, whether it is self._is_subclass(datetime)
                # to determine the time component.
                # Later on, we call subclass_matches_annotation which swaps class_type and self.annotation
                # in the 'scalar' part – I don't clearly see the use-case, we can identify it and limit it.
                # Until then, this reverse check will do.
                return False
        except TypeError:  # None, Union etc cast an error
            pass
        for origin, subtype in self._get_possible_types():
            # ex: checking that class_type=Path is subclass of annotation=list[Path] <=> subtype=Path
            if origin is tuple and isinstance(subtype, list):
                # ex. tuple[int, int] -> origin = tuple, subtype = [int, int]
                if get_origin(class_type) is tuple \
                        and all(subt1 is subt2 for subt1, subt2 in zip(get_args(class_type), subtype)):
                    return True
                continue
            elif get_origin(subtype):
                pass  # ex. tuple in `list[tuple[str, str]]`, not implemented
            elif isinstance(class_type, tuple):  # (PosixPath, Path)
                if any(subclass_matches_annotation(ct, subtype) for ct in class_type):
                    return True
            elif subclass_matches_annotation(class_type, subtype):  # tuple
                return True
        return False

    def _get_possible_types(self) -> list[tuple[type | None, type | list[type]]]:
        """ Possible types we can cast the value to.
        For annotation `list[int] | tuple[str] | str | None`,
        it returns `[(list,int), (tuple,str), (None,str)]`.

        Filters out None.
        """
        def _(annot):
            if origin := get_origin(annot):  # list[str] -> list, list -> None
                if origin is abc.Callable:
                    # I found no usecase for checking Callable, hence I return None.
                    # This statement is here for handling cases like this. That checks whether there is ex. `date` to get the DatetimeTag
                    # but there is nothing like that.
                    # @dataclass
                    # class Env:
                    #     foo: Callable = fn
                    return None, None
                subtype = get_args(annot)  # list[str] -> (str,), list -> ()
                if origin in [UnionType, Union]:  # ex: `int | None`, `list[int] | None`, `Optional[list[int]]`
                    return [_(subt) for subt in subtype]
                if origin is tuple:
                    return origin, list(subtype)
                elif (len(subtype) == 1):
                    return origin, subtype[0]
                else:
                    warn(f"This parametrized generic not implemented: {annot}")
            elif annot is not None and annot is not NoneType:
                # from UnionType, we get a NoneType
                return None, annot
            return False  # to be filtered out
        out = _(self.annotation)
        return [x for x in (out if isinstance(out, list) else [out]) if x is not False]

    def _src_obj_add(self, src):
        if self._src_obj is None:
            self._src_obj = [src]
        elif not isinstance(self._src_obj, list):
            self._src_obj = [self._src_obj, src]
        else:
            self._src_obj.append(src)
        return self

    def set_error_text(self, s):
        self.description = f"{s} {self._original_desc}"
        if n := self._original_label:
            # Why checking self._original_label?
            # If for any reason (I do not know the use case) is not set, we would end up with '* None'
            self.label = f"* {n}"
        self._error_text = s

    def remove_error_text(self):
        self.description = self._original_desc
        self.label = self._original_label
        self._error_text = None

    def _get_name(self, make_effort=False):
        """ It is not always wanted to set the callable name to the name.
        When used as a form button, we prefer to use the dict key.
        However, when used as a choice, this might be the only way to get the name.
        """
        if make_effort and not self.label and self._is_a_callable():
            return self.val.__name__
        return self.label

    def _repr_annotation(self):
        if isinstance(self.annotation, UnionType) or get_origin(self.annotation):
            # ex: `list[str]`
            return repr(self.annotation)
        # ex: `list` (without name it would be <class list>)
        return self.annotation.__name__

    def _make_default_value(self):
        # NOTE: Works bad for var: tuple[str]
        if get_origin(self.annotation) in (UnionType, Union):
            # for cases `int|None` and `Optional[int]``
            if NoneType in get_args(self.annotation):
                return None
            return get_args(self.annotation)[0]()
        elif origin := get_origin(self.annotation):  # list[Path]
            if isinstance(origin, type) and issubclass(origin, tuple):
                # tuple of scalars, ex. tuple[str, str]
                # Whereas `[]` is a valid list[str], an empty `()` is not a valid tuple[str].
                return tuple(subt() for subt in get_args(self.annotation))
            return self.annotation()
        else:
            return self.annotation()

    def _add_validation(self, validators: Iterable[ValidationCallback] | ValidationCallback):
        """ Prepend validators to the current validator. """
        if not isinstance(validators, list):
            validators = list(validators) if isinstance(validators, Iterable) else [validators]

        if self.validation is None:
            self.validation = validators
        elif isinstance(self.validation, Iterable):
            validators.extend(self.validation)
            self.validation = validators
        else:
            validators.append(self.validation)
            self.validation = validators

    def _get_ui_val(self):
        """ Get values as suitable for UI. Adaptor should not read the value directly.
        Some values are not expected to be parsed by any UI.
        But we will reconstruct them in self.update later.

        Ex: [Path("/tmp"), Path("/usr")] -> ["/tmp", "/usr"].
        We need the latter in the UI because in the first case, ast_literal would not not reconstruct it later.
        """
        if self.val is None:
            return ""
        if isinstance(self.val, MissingTagValue):
            # this is a missing wrong field, the user has to decide about the value
            return ""
        if isinstance(self.val, Enum):
            return self.val.value
        return serialize_structure(self.val)
        for origin, _ in self._get_possible_types():
            try:
                if origin:
                    return origin(str(v) for v in self.val)
            except (TypeError, ValueError):
                # Ex. tolerate_hour: int | tuple[int, int] | bool = False
                continue
        return self.val

    def _validate(self, out_value: TagValue) -> TagValue:
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

            validation = self.validation
            if not isinstance(validation, Iterable):
                validation = (validation,)

            for vald in validation:
                if isinstance(vald, (BaseMetadata, GroupedMetadata)):
                    try:
                        res = validate_annotated_type(vald, out_value)
                    except TypeError:
                        # Ex. putting "2.0" into an int.
                        # It would generate type problem later here in the method,
                        # but even now comparison failed Ex. TypeError("2.0" > 0)
                        self.set_error_text(f"Type must be {self._repr_annotation()}!")
                        raise ValueError
                else:
                    res = vald(self)
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

    def _set_val(self, val: TagValue) -> "Self":
        """ Sets the value without any checks. Updates the sources. """
        self.val = val
        self._update_source(val)
        return self

    def update(self, ui_value: UiValue | str) -> bool:
        """ Update the tag value with type conversion and checks.

        UI → Tag → the object of origin.

        Args:
            ui_value:
                The value as it has been updated in a UI.
                Update accordingly the value in the original linked dict/object
                the mininterface was invoked with.

                Validates the type and do the transformation.
                (Ex: Some values might be nulled from "".)

        Returns: bool
            Whether the value was succesfully changed or whether the revision is needed.
        """
        self.remove_error_text()
        out_value = ui_value  # The proposed value, with fixed type.

        # Type conversion
        # Even though an interface might do some type conversion (str → int) independently,
        # other interfaces does not guarantee that. Hence, we need to do the type conversion too.
        # When the ui_value is not a str, it seems the interface did retain the original type
        # and no conversion is needed.
        if self.annotation and isinstance(ui_value, str):
            if self.annotation == TagCallback:
                return True  # NOTE, EXPERIMENTAL
            if ui_value == "" and NoneType in get_args(self.annotation):
                # The user is not able to set the value to None, they left it empty.
                # Cast back to None as None is one of the allowed types.
                # Ex: `severity: int | None = None`
                out_value = None
            elif self.annotation == Optional[int]:
                try:
                    out_value = int(ui_value)
                except (ValueError, TypeError):
                    pass
            elif self.annotation in common_iterables:
                # basic support for iterables, however, it will not work for custom subclasses of these built-ins
                try:
                    out_value = literal_eval(ui_value)
                except (SyntaxError, ValueError):
                    self.set_error_text(f"Not a valid {self._repr_annotation()}")
                    return False

            if not self._is_right_instance(out_value) and isinstance(out_value, str):
                try:
                    for origin, cast_to in self._get_possible_types():
                        try:
                            if origin:
                                # Textual ask_number -> user writes '123', this has to be converted to int 123
                                # NOTE: Unfortunately, type(list) looks awful here. @see TextualInterface.form comment.
                                # (Maybe that's better now.)
                                if isinstance(cast_to, list):
                                    # this is a tuple, tuple returns a list, each value is converted to another type
                                    candidate = origin(cast_to_(v)
                                                       for cast_to_, v in zip(cast_to, literal_eval(ui_value)))
                                else:
                                    candidate = origin(cast_to(v) for v in literal_eval(ui_value))
                            else:
                                candidate = cast_to(ui_value)
                        except (TypeError, ValueError, SyntaxError):
                            continue
                        if self._is_right_instance(candidate):
                            out_value = candidate
                            break
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
        self._update_source(out_value)
        return True

    def _update_source(self, out_value):
        # Store to the source user data
        if self._src_obj:
            _src_objs = [self._src_obj] if not isinstance(self._src_obj, list) else self._src_obj
            for src in _src_objs:
                if isinstance(src, Tag):
                    # this helps to propagate the modification to possible other nested tags
                    src._set_val(out_value)
                else:
                    setattr(src, self._src_key, out_value)
        elif self._src_dict:
            self._src_dict[self._src_key] = out_value
        else:
            # This might be user-created object. There is no need to update anything as the user reads directly from self.val.
            pass

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
    def _submit_values(updater: ValsType) -> bool:
        """ Returns whether the form is alright or whether we should revise it.
        Input is tuple of the Tags and their new values from the UI.
        """
        # Why list? We need all the Tag values be updated from the UI.
        # If the revision is needed, the UI fetches the values from the Tag.
        # We need the keep the values so that the user does not have to re-write them.
        return all(list(tag.update(ui_value) for tag, ui_value in updater))

    @staticmethod
    def _submit(fd: "TagDict", ui: dict):
        """ Returns whether the form is alright or whether we should revise it.
        Input is the TagDict and the UI dict in the very same form.
        """
        return Tag._submit_values(zip(flatten(fd), flatten(ui)))
