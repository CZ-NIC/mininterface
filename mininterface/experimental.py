
# SubmitButton = TypeVar("SubmitButton")

from types import FunctionType


class SubmitButton:
    """ Create a button. When clicked, the form submits.
            If submission succeeds (validation checks pass), its value becomes True.

    ```python
    from pathlib import Path
    from mininterface import run, Tag
    from mininterface.experimental import SubmitButton

    m = run()
    out = m.form({
        "File name": Tag("/tmp", annotation=Path),
        "Append text": {
            "My text": "",
            "Append now": SubmitButton()
        },
        "Duplicate": {
            "Method": Tag("twice", choices=["twice", "thrice"]),
            "Duplicate now": SubmitButton()
        }
    })
    # Clicking on 'Append now' button
    print(out)
    # {'File name': PosixPath('/tmp'),
    # 'Append text': {'My text': '', 'Append now': True},
    # 'Duplicate': {'Method': 'twice', 'Duplicate now': False}}
    ```

    ![Submit button](asset/submitButton.avif)
    """
    pass
    # NOTE I would prefer this is Xa mere type , not a class.
    # a SubmitTag, inherited from the Tag.
    # If the val is fn, launch it. The name is the button text. The description would work.


# class Foo:
#     def test(self):
#         if isinstance(self, Bar):

# class Bar(Foo):

# FunctionType is not acceptable base type
class FacetCallback():
    """ This type denotes the Tag value is a function.
    A button should be created. When clicked, it gets the facet as the argument.
    """
    pass
    # NOTE, just a stub. Deprecated, use CallbackTag instead.


# NOTE should we use the dataclasses, isn't that slow?
MININTERFACE_CONFIG = {"gui": {"combobox_since": 5}}
