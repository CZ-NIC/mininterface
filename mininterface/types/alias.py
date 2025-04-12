from .tags import SelectTag
from ..tag import Tag, TagValue, ValidationResult

from typing import Callable


def Validation(check: Callable[["Tag"], ValidationResult | tuple[ValidationResult, TagValue]]):
    """ Alias to [`Tag(validation=...)`][mininterface.Tag.validation]

    ```python
    from mininterface import Tag, Validation
    @dataclass
    class Env:
        my_text: Annotated[str, Validation(not_empty) = "will not be emtpy"

        # which is an alias for:
        # my_text: Annotated[str, Tag(validation=not_empty)] = "will not be emtpy"
    ```

    Args:
        check: Callback function.
    """
    return Tag(validation=check)


def Options(*options: list[str]):
    """ An alias, see [`SelectTag.options`][mininterface.types.tags.SelectTag.options]
    """
    return SelectTag(options=options)
