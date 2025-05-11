# Examples

A powerful [`m.form`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.form) dialog method accepts either a dataclass or a dict. Take a look on both.

## A complex dataclass.

```python
from typing import Annotated
from dataclasses import dataclass
from mininterface.validators import not_empty
from mininterface import run, Tag, Validation

@dataclass
class NestedEnv:
  another_number: int = 7
  """ This field is nested """

@dataclass
class Env:
  nested_config: NestedEnv

  mandatory_str: str
  """ As there is no default value, you will be prompted automatically to fill up the field """

  my_number: int | None = None
  """ This is not just a dummy number, if left empty, it is None. """

  my_string: str = "Hello"
  """ A dummy string """

  my_flag: bool = False
  """ Checkbox test """

  my_validated: Annotated[str, Validation(not_empty)] = "hello"
  """ A validated field """

m = run(Env, title="My program")
# See some values
print(m.env.nested_config.another_number)  # 7
print(m.env)
# Env(nested_config=NestedEnv(another_number=7), my_number=5, my_string='Hello', my_flag=False, my_validated='hello')

# Edit values in a dialog
m.form()
```

As the attribute `mandatory_str` requires a value, a prompt appears automatically:

![Complex example missing field](asset/complex_example_missing_field.avif)

Then, full form appears:

![Complex example](asset/complex_example.avif)

## Form with paths

We have a dict with some paths. Here is how it looks.

```python
from pathlib import Path
from mininterface import run, Tag

m = run(title="My program")
my_dictionary = {
  "paths": Tag("", annotation=list[Path]),
  "default_paths": Tag([Path("/tmp"), Path("/usr")], annotation=list[Path])
  }

# Edit values in a dialog
m.form(my_dictionary)
```

![List of paths](asset/list_of_paths.avif)
