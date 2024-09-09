from typing import overload
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


@overload
def limit(maximum: int, lt: float | None = None, gt: float | None = None, transform=False):
    ...


@overload
def limit(minimum: int, maximum: int, lt: float | None = None, gt: float | None = None, transform=False):
    ...


def limit(arg1: int | None = None, arg2: int | None = None, lt: float | None = None, gt: float | None = None, transform=False):
    """ Limit a number range or a string length.

        Two options:
        * limit(maximum): from zero (including) to maximum (including)
        * limit(minimum, maximum): From minimum (including) to maximum (including)
        Use gt like 'greater than' or lt like 'lesser than'.

        * transform: If the value is not withing the limit, transform it to a boundary.
    """
    # TODO docs missing
    minimum = maximum = None
    if arg2 is None:
        minimum = 0
        maximum = arg1
    elif arg1 is not None:
        minimum = arg1
        maximum = arg2
    elif gt is None and lt is None:
        raise ValueError("Specify minimum, maximum, lt or gt.")

    def error(transformed):
        msg = "Value must be " + ", ".join(filter(None, (
            f"between {minimum} and {maximum}" if minimum is not None and maximum is not None else None,
            f"greater than {gt}" if gt is not None else None,
            f"lesser than {lt}" if lt is not None else None))) + "."
        if transform:
            return msg, transformed
        else:
            return msg

    def limiter(tag: Tag) -> bool | str | tuple[str, int]:
        """ Limit value to the numerical range (or string length) with optional error message and transformation. """
        if isinstance(tag.val, str):
            value = len(tag.val)
            n = False  # we are dealing with string, which is not transformed
        else:
            value = tag.val
            n = True

        if minimum is not None and value < minimum:
            return error(minimum if n else value)
        if maximum is not None and value > maximum:
            return error(maximum if n else value)
        if lt is not None and value >= lt:
            return error(lt if n else value)
        if gt is not None and value <= gt:
            return error(gt if n else value)
        return True

    return limiter
