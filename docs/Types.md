# Types

Various types are supported:

* scalars
* functions
* well-known objects (`Path`, `datetime`)
* iterables (like `list[Path]`)
* custom classes (somewhat)
* union types (like `int | None`)

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


::: mininterface.types