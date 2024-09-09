from .tag import Tag

__doc__ = """
Functions suitable for Tag validation. When the user submits a value whose validation fails,
they are prompted to edit the value.

```python
m = run()
my_dict = m.form({"my_text", Tag("", validation=validators.not_empty)})
my_dict["my_text"]  # You can be sure the value is not empty here.
```

Note that alternatively to this module, you may validate with Pydantic or an attrs model.

```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    restrained: str = Field(default="hello", max_length=5)
```

```python
import attr
from attr.validators import max_len

@attr.s
class AttrsModel:
    restrained: str = attr.ib(default="hello", validator=max_len(5))
```
"""

def not_empty(tag: Tag):
    """ Assures that Tag the user has written a value and did not let the field empty.

    ```python
    from mininterface import Tag, validators

    m.form({"my_text", Tag("", validation=validators.not_empty)})
    # User cannot leave the string field empty.
    ```

    Note that for Path, an empty string is converted to an empty Path('.'),
    hence '.' too is considered as an empty input and the user
    is not able to set '.' as a value.
    This does not seem to me as a bad behaviour as in CLI you clearly see the CWD,
    whereas in a UI the CWD is not evident.
    """
    v = tag.val
    if v == "":
        return False
    elif v is False:
        return True
    try:
        return v != tag.annotation()
    except:
        pass
    return True

# @overload
# def limit(max:int)
# def limit(min_inclusive:int)
# Negative numbers?
# TODO