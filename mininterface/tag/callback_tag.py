from .tag import Tag, TagValue, UiValue


from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CallbackTag(Tag[TagValue | Callable]):
    ''' Callback function is guaranteed to receive the [Tag][mininterface.Tag] as a parameter.

    !!! warning
        Experimental. May change into a CallableTag.

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
        "My choice": Tag(options=[callback_raw, CallbackTag(callback_tag)])
    })
    print(out)  # {'My choice': <function callback_raw at 0x7ae5b3e74ea0>}
    ```

    Via choice, we receive the function output:

    ```python
    out = m.select({
        "My choice1": callback_raw,
        "My choice2": CallbackTag(callback_tag),
        # Not supported: "My choice3": Tag(callback_tag, annotation=CallbackTag),
    })
    print(out)  # output of callback0 or callback_tag, ex:
    #    Printing <class 'mininterface.tag.CallbackTag'>
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
    val: Callable[[Tag], Any]

    def _run_callable(self):
        return self.val(self)

    def __hash__(self):
        return super().__hash__()
