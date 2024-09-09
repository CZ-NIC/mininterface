## Basic usage
Use a common [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass), a Pydantic [BaseModel](https://brentyi.github.io/tyro/examples/04_additional/08_pydantic/) or an [attrs](https://brentyi.github.io/tyro/examples/04_additional/09_attrs/) model to store the configuration. Wrap it to the [run][mininterface.run] method that returns an interface `m`. Access the configuration via [`m.env`][mininterface.Mininterface.env] or use it to prompt the user [`m.is_yes("Is that alright?")`][mininterface.Mininterface.is_yes]. To do any advanced things, stick the value to a powerful [`Tag`][mininterface.Tag]. For a validation only, use its [`Validation alias`](#validation-alias).


## Supported types

Various types are supported: scalars, functions, well-known objects (Path), iterables, custom classes.

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

## Nested configuration
You can easily nest the configuration. (See also [Tyro Hierarchical Configs](https://brentyi.github.io/tyro/examples/02_nesting/01_nesting/)).

Just put another dataclass inside the config file:

```python3
@dataclass
class FurtherConfig:
    token: str
    host: str = "example.org"

@dataclass
class Config:
    further: FurtherConfig

...
print(config.further.host)  # example.org
```

A subset might be defaulted in YAML:

```yaml
further:
  host: example.com
```

Or by CLI:

```
$./program.py --further.host example.net
```



























