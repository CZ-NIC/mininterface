from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from typing_extensions import Self
from .tag import Tag, ValidationResult, TagValue


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


def Choices(*choices: list[str]):
    """ An alias, see [`Tag.choices`][mininterface.Tag.choices] """
    return Tag(choices=choices)


@dataclass
class PathTag(Tag):
    """
    Use this helper object to select files.

    In the following example, we see that it is not always needed to use this object.

    * File 1 – plain detection, button to a file picker appeared.
    * File 2 – the same.
    * File 3 – we specified multiple paths can be selected.

    ```python
    from pathlib import Path
    from mininterface import run, Tag
    from mininterface.aliases import PathTag

    m = run()
    out = m.form({
        "File 1": Path("/tmp"),
        "File 2": Tag("", annotation=Path),
        "File 3": PathTag([Path("/tmp")], multiple=True),
    })
    print(out)
    # {'File 1': PosixPath('/tmp'), 'File 2': PosixPath('.'), 'File 3': [PosixPath('/tmp')]}
    ```

    ![File picker](asset/file_picker.avif)
    """
    # NOTE turn SubmitButton into a Tag too and turn this into a types module.
    # NOTE Missing in textual. Might implement file filter and be used for validation.
    # NOTE Path multiple is not recognized: "File 4": Tag([], annotation=list[Path])
    multiple: str = False
    """ The user can select multiple files. """

    def __post_init__(self):
        super().__post_init__()
        self.annotation = list[Path] if self.multiple else Path

    def _morph(self, *_):
        return self
