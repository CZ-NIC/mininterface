# Supported types

Various types are supported:

* scalars
* functions
* enums
* well-known objects (`Path`, `datetime`)
* iterables (like `list[Path]`)
* custom classes (somewhat)
* union types (like `int | None`)

## Basic usage

### Usage in a dataclass

Take a look how it works with the variables organized in a dataclass:

```python
from dataclasses import dataclass
from pathlib import Path

from mininterface import run


@dataclass
class Env:
    my_number: int = 1
    """ A dummy number """
    my_boolean: bool = True
    """ A dummy boolean """
    my_conditional_number: int | None = None
    """ A number that can be null if left empty """
    my_path: Path = Path("/tmp")
    """ A dummy path """


m = run(Env)  # m.env contains an Env instance
m.form()  # Prompt a dialog; m.form() without parameter edits m.env
print(m.env)
# Env(my_number=1, my_boolean=True, my_path=PosixPath('/tmp'),
#  my_point=<__main__.Point object at 0x7ecb5427fdd0>)
```

![GUI window](asset/supported_types_1.avif "A prompted dialog")


### Usage in a dict

Variables organized in a dict:

Along scalar types, there is (basic) support for common iterables or custom classes.

```python
from mininterface import run

class Point:
    def __init__(self, i: int):
        self.i = i

    def __str__(self):
        return str(self.i)


values = {"my_number": 1,
          "my_list": [1, 2, 3],
          "my_point": Point(10)
          }

m = run()
m.form(values)  # Prompt a dialog
print(values)  # {'my_number': 2, 'my_list': [2, 3], 'my_point': <__main__.Point object...>}
print(values["my_point"].i)  # 100
```

![GUI window](asset/supported_types_2.avif "A prompted dialog after editation")

## Examples

All the examples need some imports:

```
from dataclasses import dataclass, field
from pathlib import Path
from mininterface import run
```

### Scalars
```python
@dataclass
class Env:
    my_file: str
    """ This is my help text """

    my_flag: bool = False
    """ My checkbox """

    my_number: float = 1.1
    """ Any scalar possible """

run(Env).form()
```

### Functions

```python
def my_callback():
    print("I'm here!")

@dataclass
class Env:
    my_file: Callable = my_callback

run(Env).form()
```

Or use the `with` statement to redirect the stdout into the mininterface.

```
with run(Env) as m:
    m.form()
    m.alert("The text 'I'm here' is displayed in the window.")
```

### Enums

To constraint a value, either pass an enum object or use handy additional type [EnumTag](Types.md#mininterface.types.EnumTag) that might speed you up a bit.

### Well-known objects

We've added extra function for known objects like `Path` or `datetime` (file exists check etc.), see [types](Types.md).

### Iterables

```python
from pathlib import Path

@dataclass
class Env:
    my_file: list[int] = field(default_factory=lambda: [1, 2, 3])
    my_paths: list[Path] = field(default_factory=lambda: [])
run(Env).form()
```
### Union types

An enormously useful feature is to let the user not set a variable.

```python
@dataclass
class Env:
    my_var: int | None = None
    """ Left empty for None """
```

### Additional

We've added some other useful [types](Types.md).