We recommend to use the dataclass and validate with the `Annotated` keyword. We use a [Validation][mininterface.tag.alias.Validation] type here.

```python3
from typing import Annotated
from mininterface.validators import not_empty
from mininterface import Validation

@dataclass
class Env:
    test: Annotated[str, Validation(not_empty)] = "hello"
```

Under the hood, this is just a [`Tag`][mininterface.Tag].

```python3
@dataclass
class Env:
    test: Annotated[str, Tag(validation=not_empty)] = "hello"
```

Why we used it in an Annotated statement? To preserve the date type.

::: mininterface.validators
