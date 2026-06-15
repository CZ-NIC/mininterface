We recommend using a dataclass and validating with the `Annotated` keyword. Here, we use the [Validation][mininterface.tag.alias.Validation] type.

```python
from typing import Annotated
from mininterface.validators import not_empty
from mininterface import Validation

@dataclass
class Env:
    test: Annotated[str, Validation(not_empty)] = "hello"
```

Under the hood, this is just a [`Tag`][mininterface.Tag].

```python
@dataclass
class Env:
    test: Annotated[str, Tag(validation=not_empty)] = "hello"
```

Why did we use it inside an `Annotated` statement? To preserve the data type.

::: mininterface.validators
