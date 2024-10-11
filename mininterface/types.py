from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from typing_extensions import Self, override

from .auxiliary import common_iterables
from .tag import Tag, ValidationResult, TagValue


from .type_stubs import TagCallback, TagType # Allow import from the module

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
class CallbackTag(Tag):
    ''' Callback function is guaranteed to receives the [Tag][mininterface.Tag] as a parameter.

    For the following examples, we will use these custom callback functions:
    ```python
    from mininterface import run

    def callback_raw():
        """ Dummy function """
        print("Priting text")
        return 50

    def callback_tag(tag: Tag):
        """ Receives a tag """
        print("Printing", type(tag))
        return 100

    m = run()
    ```

    Use as buttons in a form:
    ```
    m.form({"Button": callback_raw})
    m.form({"Button": CallbackTag(callback_tag)})
    ```

    ![Callback button](asset/callback_button.avif)

    Via form, we receive the function handler:
    ```python
    out = m.form({
        "My choice": Tag(choices=[callback_raw, CallbackTag(callback_tag)])
    })
    print(out)  # {'My choice': <function callback_raw at 0x7ae5b3e74ea0>}
    ```

    Via choice, we receive the function output:

    ```python
    out = m.choice({
        "My choice1": callback_raw,
        "My choice2": CallbackTag(callback_tag),
        # Not supported: "My choice3": Tag(callback_tag, annotation=CallbackTag),
    })
    print(out)  # output of callback0 or callback_tag, ex:
    #    Printing <class 'mininterface.types.CallbackTag'>
    #    100
    ```

    ![Callback choice](asset/callback_choice.avif)


    You may use callback in a dataclass.
    ```python
    @dataclass
    class Callbacks:
        p1: Callable = callback0
        p2: Annotated[Callable, CallbackTag(description="Foo")] = callback_tag
        # Not supported: p3: CallbackTag = callback_tag
        # Not supported: p4: CallbackTag = field(default_factory=CallbackTag(callback_tag))
        # Not supported: p5: Annotated[Callable, Tag(description="Bar", annotation=CallbackTag)] = callback_tag

    m = run(Callbacks)
    m.form()
    ```
    '''
    val: Callable[[str], Any]

    def _run_callable(self):
        return self.val(self)


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
    # NOTE Missing in textual. Might implement file filter and be used for validation. (ex: file_exist, is_dir)
    # NOTE Path multiple is not recognized: "File 4": Tag([], annotation=list[Path])
    multiple: str = False
    """ The user can select multiple files. """

    def __post_init__(self):
        super().__post_init__()
        if not self.annotation:
            self.annotation = list[Path] if self.multiple else Path
        else:
            for origin, _ in self._get_possible_types():
                if origin in common_iterables:
                    self.multiple = True
                    break

    @override
    def _morph(self, class_type: "Self", morph_if: type | tuple[type]):
        if class_type == PathTag:
            return self
