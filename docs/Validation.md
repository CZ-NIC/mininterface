We recommend to use the dataclass and validate with the `Annotated` keyword. We use a [Validation][mininterface.types.Validation] type here.

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

```python3
@dataclass
class Env:
    my_string: Tag = Tag("hello", validation=not_empty)

m = run(Env)
print(type(m.env.my_string))  # Tag
print(m.env.my_string.val)  # hello
```

::: mininterface.validators
