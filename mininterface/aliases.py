from typing import Callable
from .FormField import FormField, ValidationResult, FieldValue


def Validation(check: Callable[["FormField"], ValidationResult | tuple[ValidationResult, FieldValue]]):
    """ Alias to `FormField(validation=...)`

    ```python
    from mininterface import FormField, Validation
    @dataclass
    class Env:
        my_text: Annotated[str, Validation(not_empty) = "will not be emtpy"

        # which is an alias for:
        # my_text: Annotated[str, FormField(validation=not_empty)] = "will not be emtpy"
    ```

    :param check: Callback function.
    """
    return FormField(validation=check)