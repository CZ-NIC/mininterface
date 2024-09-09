from typing import Callable
from .tag import Tag, ValidationResult, FieldValue


def Validation(check: Callable[["Tag"], ValidationResult | tuple[ValidationResult, FieldValue]]):
    """ Alias to `Tag(validation=...)`

    ```python
    from mininterface import Tag, Validation
    @dataclass
    class Env:
        my_text: Annotated[str, Validation(not_empty) = "will not be emtpy"

        # which is an alias for:
        # my_text: Annotated[str, Tag(validation=not_empty)] = "will not be emtpy"
    ```

    :param check: Callback function.
    """
    return Tag(validation=check)