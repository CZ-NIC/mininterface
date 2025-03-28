# Mininterface – access to GUI, TUI, CLI and config files
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Build Status](https://github.com/CZ-NIC/mininterface/actions/workflows/run-unittest.yml/badge.svg)](https://github.com/CZ-NIC/mininterface/actions)
[![Downloads](https://static.pepy.tech/badge/mininterface)](https://pepy.tech/project/mininterface)

Write the program core, do not bother with the input/output.

![Hello world example: GUI window](asset/hello-gui.avif "A minimal use case – GUI")
![Hello world example: TUI fallback](asset/hello-tui.avif "A minimal use case – TUI fallback")

Check out the code, which is surprisingly short, that displays such a window or its textual fallback.

```python
from dataclasses import dataclass
from mininterface import run

@dataclass
class Env:
    """ This calculates something. """

    my_flag: bool = False
    """ This switches the functionality """

    my_number: int = 4
    """ This number is very important """

if __name__ == "__main__":
    m = run(Env, prog="My application")
    m.form()
    # Attributes are suggested by the IDE
    # along with the hint text 'This number is very important'.
    print(m.env.my_number)
```

# Contents
- [You got CLI](#you-got-cli)
- [You got config file management](#you-got-config-file-management)
- [You got dialogues](#you-got-dialogues)
- [Background](#background)
- [Installation](#installation)
- [Docs](#docs)
- [Gallery](#gallery)
- [Examples](#examples)

## You got CLI
It was all the code you need. No lengthy blocks of code imposed by an external dependency. Besides the GUI/TUI, you receive powerful YAML-configurable CLI parsing.


```bash
$ ./program.py --help
usage: My application [-h] [-v] [--my-flag | --no-my-flag] [--my-number INT]

This calculates something.

╭─ options ───────────────────────────────────────────────────────────────╮
│ -h, --help             show this help message and exit                  │
│ -v, --verbose          Verbosity level. Can be used twice to increase.  │
│ --my-flag, --no-my-flag                                                 │
│                        This switches the functionality (default: False) │
│ --my-number INT        This number is very important (default: 4)       │
╰─────────────────────────────────────────────────────────────────────────╯
```

## You got config file management
Loading config file is a piece of cake. Alongside `program.py`, put `program.yaml` and put there some of the arguments. They are seamlessly taken as defaults.

```yaml
my_number: 555
```

```bash
$ program.py --help
...
│ --my-number INT        This number is very important (default: 555)     │
```

## You got dialogues
Check out several useful methods to handle user dialogues. Here we bound the interface to a `with` statement that redirects stdout directly to the window.

```python
with run(Env) as m:
    print(f"Your important number is {m.env.my_number}")
    boolean = m.is_yes("Is that alright?")
```

![Small window with the text 'Your important number'](asset/hello-with-statement.webp "With statement to redirect the output")
![The same in terminal'](asset/hello-with-statement-tui.avif "With statement in TUI fallback")

# Background

Wrapper between the [tyro](https://github.com/brentyi/tyro) `argparse` replacement and [tkinter_form](https://github.com/JohanEstebanCuervo/tkinter_form/) that converts dicts into a GUI.

Writing a small and useful program might be a task that takes fifteen minutes. Adding a CLI to specify the parameters is not so much overhead. But building a simple GUI around it? HOURS! Hours spent on researching GUI libraries, wondering why the Python desktop app ecosystem lags so far behind the web world. All you need is a few input fields validated through a clickable window... You do not deserve to add hundred of lines of the code just to define some editable fields. `Mininterface` is here to help.

The config variables needed by your program are kept in cozy dataclasses. Write less! The syntax of [tyro](https://github.com/brentyi/tyro) does not require any overhead (as its `argparse` alternatives do). You just annotate a class attribute, append a simple docstring and get a fully functional application:
* Call it as `program.py --help` to display full help.
* Use any flag in CLI: `program.py --my-flag`  causes `env.my_flag` be set to `True`.
* The main benefit: Launch it without parameters as `program.py` to get a full working window with all the flags ready to be edited.
* Running on a remote machine? Automatic regression to the text interface.

# Installation

Install with a single command from [PyPi](https://pypi.org/project/mininterface/).

```bash
pip install mininterface[all]  # GPLv3 and compatible
```

## Minimal installation

Should you need just the CLI part and you are happy with basic text dialogs, use these commands instead:

```bash
pip install --no-dependencies mininterface
pip install tyro typing_extensions pyyaml simple_term_menu
```

## MacOS GUI

If the GUI does not work on MacOS, you might need to launch: `brew install python-tk`

# Docs
See the docs overview at [https://cz-nic.github.io/mininterface/](https://cz-nic.github.io/mininterface/Overview/).

# Gallery

These projects have the code base reduced thanks to the mininterface:

* **[deduplidog](https://github.com/CZ-NIC/deduplidog/)** – Find duplicates in a scattered directory structure
* **[touch-timestamp](https://github.com/CZ-NIC/touch-timestamp/)** – A powerful dialog to change the files' timestamp

# Examples

A powerful [`m.form`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.form) dialog method accepts either a dataclass or a dict. Take a look on both.

## A complex dataclass.

```python3
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
