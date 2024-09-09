"""
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
from typing import overload
from .tag import Tag


def not_empty(tag: Tag):
    """ Assures that Tag the user has written a value and did not let the field empty.

    ```python
    from mininterface import Tag, validators, run

    m = run()
    m.form({"my_text": Tag("", validation=validators.not_empty)})
    # User cannot leave the string field empty.
    ```

    When submitting an empty value, a warning appears:

    ![Not empty window](asset/not_empty.avif "Not empty warning")


    Note that for Path, an empty string is converted to an empty Path('.'),
    hence '.' too is considered as an empty input and the user
    is not able to set '.' as a value.
    This does not seem to me as a bad behaviour as in CLI you clearly see the CWD,
    whereas in a UI the CWD is not evident.

    Args:
        tag:
    """
    v = tag.val
    if v == "":
        return "Cannot be empty"
    elif v is False:
        return True
    try:
        if not v != tag.annotation():
            return "Fill in the value"
    except:
        pass
    return True


@overload
def limit(maximum: int, lt: float | None = None, gt: float | None = None, transform=False):
    ...


@overload
def limit(minimum: int, maximum: int, lt: float | None = None, gt: float | None = None, transform=False):
    ...


def limit(maxOrMin: int | None = None, max_: int | None = None, lt: float | None = None, gt: float | None = None, transform:bool=False):
    """ Limit a number range or a string length.

    Either use as `limit(maximum)` or `limit(minimum, maximum)`.

    Args:
        maximum int: `limit(maximum)` – from zero (including) to maximum (including)
        minimum int: `limit(minimum, maximum)` – From minimum (including) to maximum (including)
        lt: lesser than
        gt: greater than
        transform: If the value is not withing the limit, transform it to a boundary.
            ```python
            from mininterface import run, Tag
            from mininterface.validators import limit

            m = run()
            m.form({"my_number": Tag(2, validation=limit(1, 10, transform=True))})
            # Put there '50' → transformed to 10 and dialog reappears
            # with 'Value must be between 1 and 10.'
            ```

            ![Validator limit](asset/validators_limit_transform.avif)
    """
    minimum = maximum = None
    if max_ is None:
        minimum = 0
        maximum = maxOrMin
    elif maxOrMin is not None:
        minimum = maxOrMin
        maximum = max_
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
