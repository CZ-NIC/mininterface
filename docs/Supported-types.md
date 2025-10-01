# Supported types

Various types are supported:

* scalars
* functions
* enums
* well-known objects (`Path`, `datetime`)
* iterables (like `list[Path]`)
* custom classes (somewhat)
* union types (like `int | None`)
* nested dataclasses
* union of nested dataclasses for subcommands

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

```python
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

![Scalars](asset/scalars.avif)

### Functions

Will appear as buttons.

```python
def my_callback():
    print("I'm here!")

@dataclass
class Env:
    my_file: Callable = my_callback

run(Env).form()
```

![Function](asset/examples-function.avif)

Or use the `with` statement to redirect the stdout into the mininterface.

```python
with run(Env) as m:
    m.form()
    m.alert("The text 'I'm here' is displayed in the window.")
```

![Function](asset/examples-function-with.avif)

!!! Warning
    When used in a form like this `m.form({'My callback': my_callback)`, the value is left intact. It still points to the function. This behaviour might reconsidered and changed. (It might make more sense to change it to the return value instead.)

### Constraining

To constraint a value, either pass an enum object, `typing.Literal`, or use handy additional type [SelectTag][mininterface.tag.SelectTag] that might speed you up a bit.

See the [OptionsType][mininterface.tag.select_tag.OptionsType] help for all the possibilities, here is just a quick hint:

#### Enums

CLI shows keys, UI shows values. Static values. The program:

```python
class Color(Enum):
    RED = "red"
    GREEN = "green"

@dataclass
class Env:
    val: Color

m = run(Env)
```

CLI shows keys.

```bash
$ ./program.py --help
usage: program.py [-h] [-v] --val {RED,GREEN}

╭─ options ───────────────────────────────────────────────────────────────────────╮
│ -h, --help              show this help message and exit                         │
│ -v, --verbose           verbosity level, can be used multiple times to increase │
│ --val {RED,GREEN}       (required)                                              │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

(Note: You may mark it with [a special flag](https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.EnumChoicesFromValues) to show the values in the CLI.)

UI shows values:

![Enum vals](asset/enum_vals.avif "UI shows enum values")

As both keys and values are displayed, should you need to bear an additional information, not displayed in CLI nor UI, you can tackle the Enum class.

```python
class Color(Enum):
    RED = "#ff0000"
    GREEN = "#00ff00"

    def __init__(self, payload):
        # mark '#ff0000' as payload, rather than the `.value`
        self.payload = payload

    @property
    def value(self):  # `.value` is seen from UI
        return self.name.lower()

@dataclass
class Env:
    val: Color

m = run(Env)
print(m.env.val.payload)  # ex. '#ff0000'
```

#### Literal

Built-in `Literal` is supported. Allows you to do a one-liner.

```python
from typing import Literal

@dataclass
class Env:
    val: Literal["one", "two"]

m = run(Env)
print(m.env.val)  # ex. 'one'
```

Should you need dynamic values, wrap it under `Annotated`:

```python
from typing import Annotated, Literal

variable = "one", "two"

@dataclass
class Env:
    val: Annotated[str, Literal[variable]] = "one"

m = run(Env)
print(m.env.val)  # ex. 'one'
```

#### [SelectTag][mininterface.tag.SelectTag]

Advanced adjustments, multiple choice, dynamic values, etc.

```python
@dataclass
class Env:
    val: Annotated[list[str], SelectTag(options=["one", "two"], multiple=True)]

run(Env)
```

![SelectTag multiple](asset/selecttag-multiple.avif)

### Nested dataclasses or their unions (subcommands)

You can nest the classes to create a subgroup:

```python
@dataclass
class Message:
    text: str

@dataclass
class Env:
    val: Message

run(Env)
```

![Nested dataclass](asset/nested-dataclass.avif)

You can union the classes to create subcommands:

```python
from typing import Literal
from tyro.conf import OmitSubcommandPrefixes

@dataclass
class ConsolePlain:
    pass

@dataclass
class ConsoleRich:
    color: Literal["red", "green"]

@dataclass
class Console:
    style: ConsolePlain | ConsoleRich
    bot_id: Literal["id-one", "id-two"]

@dataclass
class Message:
    text: str

@dataclass
class Env:
    val: Message | Console

m = run(OmitSubcommandPrefixes[Env])
```

First, we've chosen `Console`, then `Console rich`.

![Nested subcommands](asset/nested-subcommands-1.avif)
![Choosing Console rich](asset/nested-subcommands-2.avif)
![Fields from both Console and ConsoleRich](asset/nested-subcommands-3.avif)

??? Grouping
    Note fields from outer `Console` and inner `ConsoleRich` are displayed together in step 3. Why? You might start at arbitrary position.

    Starting at step 1:

    ```bash
    $ ./program.py --help
    usage: program.py [-h] [-v] {message,console}
    $ ./program.py
    ```

    ![Nested subcommands](asset/nested-subcommands-1.avif)

    Starting at step 2:

    ```bash
    $ ./program.py console --help
    usage: program.py console [-h] [-v] --bot-id {id-one,id-two} {console-plain,console-rich}
    $ ./program.py console
    ```

    ![Choosing Console rich](asset/nested-subcommands-2.avif)

    That way, you may start anywhere from CLI, yet be sure all the missing fields, if possible, are grouped in a single form dialog.

??? OmitSubcommandPrefixes
    Why using `OmitSubcommandPrefixes`? This will rend the inscription shorter.

    ```bash
    $ ./program.py --help
    usage: program.py [-h] [-v] {message,console}
    ```

    Without:
    ```bash
    $ ./program.py --help
    usage: program.py [-h] [-v] {val:message,val:console}
    ```

### Well-known objects

We've added extra functions for known objects like `Path` or `datetime` (file exists check etc.), see `Tag` subclasses in Custom types section ([PathTag][mininterface.tag.PathTag], [DatetimeTag][mininterface.tag.DatetimeTag], ...).

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

We've added some other useful custom types that can be imported mostly from `mininterface.tag`.

1. Tag subclasses – The descendants of the [`Tag`](Tag.md), the object for storing values. Normally, you don't need to use or know much about those but they can be helpful when you need to further specify the functionality, such as restricting a `Path` to directories only ([PathTag][mininterface.tag.PathTag]).
2. [Tag aliases](Tag-aliases.md) – Userful shortcuts.
3. [Prepared annotations](Prepared-annotations.md) – Useful types to be used for nifty CLI parsing.
