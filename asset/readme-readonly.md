# Mininterface – access to GUI, TUI, web, CLI and config files
[![Build Status](https://github.com/CZ-NIC/mininterface/actions/workflows/run-unittest.yml/badge.svg?branch=main)](https://github.com/CZ-NIC/mininterface/actions)
[![Downloads](https://static.pepy.tech/badge/mininterface)](https://pepy.tech/project/mininterface)

Write the program core, do not bother with the input/output.

![Hello world example: GUI window](asset/hello-gui.avif "A minimal use case – GUI")
![Hello world example: TUI fallback](asset/hello-tui.avif "A minimal use case – TUI fallback")

Check out the surprisingly short code that displays such a window – or its textual fallback.

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
    m = run(Env, title="My application")
    m.form()
    # Attributes are suggested by the IDE
    # along with the hint text 'This number is very important'.
    print(m.env.my_number)
```

# Contents
- [You got CLI](#you-got-cli)
- [You got config file management](#you-got-config-file-management)
- [You got dialogs](#you-got-dialogs)
- [Background](#background)
- [Installation](#installation)
- [Docs](#docs)
- [Gallery](#gallery)
- [Examples](#examples)
    * [Hello world](#hello-world)
    * [Goodbye argparse world](#goodbye-argparse-world)

## You got CLI
That was all the code you need. No lengthy blocks of code imposed by an external dependency. Besides the GUI/TUI/web, you receive powerful YAML-configurable CLI parsing.


```bash
$ ./program.py --help
usage: program.py [-h] [-v] [--my-flag | --no-my-flag] [--my-number INT]

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
Loading a config file is a piece of cake. Alongside `program.py`, write some of its arguments into `program.yaml`. They are seamlessly taken as defaults.

```yaml
my_number: 555
```

```bash
$ program.py --help
...
│ --my-number INT        This number is very important (default: 555)     │
```

## You got dialogs
Check out several useful methods for handling user dialogs. Here we bind the interface to a `with` statement that redirects stdout directly to the window.

```python
with run(Env) as m:
    print(f"Your important number is {m.env.my_number}")
    boolean = m.confirm("Is that alright?")
```

![Small window with the text 'Your important number'](asset/hello-with-statement.webp "With statement to redirect the output")
![The same in terminal'](asset/hello-with-statement-tui.avif "With statement in TUI fallback")

# Background

Wrapper between various libraries that provide a user interface.

It allows you to focus on writing the program's core logic without worrying about input/output. It generates CLI arguments, parses the config file, and shows a UI. Depending on the environment, the dialogs automatically use either a GUI, a mouse-clickable TUI, a lightweight terminal text interface, or become available via HTTP — all while maintaining exactly the same functionality.

Writing a small and useful program might be a task that takes fifteen minutes. Adding a CLI to specify the parameters is not so much overhead. But building a simple GUI around it? HOURS! Hours spent on researching GUI libraries, wondering why the Python desktop app ecosystem lags so far behind the web world. All you need is a few input fields validated through a clickable window... You should not have to add hundreds of lines of code just to define a few editable fields. *Mininterface* is here to help.

The config variables needed by your program are kept in cozy dataclasses. Write less! The [tyro](https://github.com/brentyi/tyro) syntax requires no overhead (unlike its `argparse` alternatives). You just annotate a class attribute, append a simple docstring, and get a fully functional application:

* Call it as `program.py --help` to display full help.
* Use any flag in CLI: `program.py --my-flag`  causes `env.my_flag` to be set to `True`.
* The main benefit: Launch it without parameters as `program.py` to get a fully working window with all the flags ready to be edited.
* Running on a remote machine? It automatically falls back to the text interface.
* Or access your program via [web browser](Interfaces.md#webinterface-or-web).

# Installation

Install with a single command from [PyPi](https://pypi.org/project/mininterface/).

```bash
pip install "mininterface[all]<2"  # GPLv3 and compatible
```

## Bundles

There are various bundles. We mark the least permissive licence in the bundle.

| bundle | size | licence | description |
| ------ | ---- | ----------- | ---- |
| mininterface | 1 MB | LGPL | minimal – only text dialogs |
| mininterface[basic] | 25 MB | LGPL | CLI, GUI, TUI |
| mininterface[web] | 40 MB | LGPL | including [WebInterface](Interfaces.md#webinterface-or-web) |
| mininterface[img] | 40 MB | LGPL | image support (GUI and TUI) |
| mininterface[tui] | 40 MB | LGPL | TUI with image support |
| mininterface[gui] | 70 MB | GPL | images, combobox, calendar |
| mininterface[ui] | 90 MB | GPL | full installation |
| mininterface[all] | 90 MB | GPL | full installation, same as `ui`, reserved for future use (big dependencies, optional interfaces) |

Apart from the minimal bundle (which lacks CLI and dataclass support), they have the same functionality, differing only in the user experience.

!!! tip
    For automated testing (e.g., in CI environments), the `mininterface[basic]` bundle is sufficient.

## MacOS GUI

If the GUI does not work on MacOS, you might need to launch: `brew install python-tk`

# Docs
See the docs overview at [https://cz-nic.github.io/mininterface/](https://cz-nic.github.io/mininterface/Overview/).

# Gallery

These projects have the code base reduced thanks to the mininterface:

* **[deduplidog](https://github.com/CZ-NIC/deduplidog/)** – Find duplicates in a scattered directory structure
* **[touch-timestamp](https://github.com/CZ-NIC/touch-timestamp/)** – A powerful dialog to change the files' timestamp

# Examples
## Hello world

Take a look at the following example.

1. We define an Env class.
2. Then, we initialize mininterface with [`run(Env)`](https://cz-nic.github.io/mininterface/run/) – the missing fields will be prompted for
3. Then, we use various dialog methods, like [`confirm`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.confirm), [`select`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.select) or [`form`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.form).

Below, you can find screenshots of how the program looks in various environments ([graphic](Interfaces.md#guiinterface-or-tkinterface-or-gui) interface, [web](Interfaces.md#webinterface-or-web) interface...).

```python
from dataclasses import dataclass
from pathlib import Path
from mininterface import run

@dataclass
class Env:
  my_file: Path  # This is my help text
  my_flag: bool = False
  my_number: int = 4

if __name__ == "__main__":
    # Here, the user will be prompted
    # for missing parameters (`my_file`) automatically
    with run(Env) as m:

      # You can lean on the typing
      # Ex. directly read from the file object:
      print("The file contents:", m.env.my_file.read_text())

      # You can use various dialog methods,
      # like `confirm` for bool
      if m.confirm("Do you want to continue?"):

        # or `select` for choosing a value
        fruit = m.select(("apple", "banana", "sirup"), "Choose a fruit")

        if fruit == "apple":
          # or `form` for arbitrary values
          m.form({
            "How many": 0,
            "Choose another file": m.env.my_file
          })
```

Launch with `./program.py`:

![Tutorial](asset/tutorial_tk1.avif)
![Tutorial](asset/tutorial_tk2.avif)
![Tutorial](asset/tutorial_tk3.avif)
![Tutorial](asset/tutorial_tk4.avif)

Or on a remote machine `MININTERFACE_INTERFACE=tui ./program.py`:

![Tutorial](asset/tutorial_textual1.avif)
![Tutorial](asset/tutorial_textual2.avif)
![Tutorial](asset/tutorial_textual3.avif)
![Tutorial](asset/tutorial_textual4.avif)

Or via the plain text `MININTERFACE_INTERFACE=text ./program.py`:

![Tutorial](asset/tutorial_text.avif)

Or via web browser `MININTERFACE_INTERFACE=web ./program.py`:

![Tutorial](asset/tutorial_web.avif)

You can always set the Env via the CLI or a config file:

```bash
$ ./program.py --help
usage: program.py [-h] [OPTIONS]

╭─ options ──────────────────────────────────────────────────────────────╮
│ -h, --help             show this help message and exit                 │
│ -v, --verbose          Verbosity level. Can be used twice to increase. │
│ --my-file PATH         This is my help text (required)                 │
│ --my-flag, --no-my-flag                                                │
│                        (default: False)                                │
│ --my-number INT        (default: 4)                                    │
╰────────────────────────────────────────────────────────────────────────╯
```

## Goodbye argparse world

Do you want to try out Mininterface with your current [`ArgumentParser`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser)?

You're using positional arguments, subparsers, types in the ArgumentParser... Mininterface will give you an immediate benefit. Just wrap it in the [`run`](https://cz-nic.github.io/mininterface/run/) method.

```python
#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import time
from pathlib import Path

from mininterface import run

parser = ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=True)
sub1 = subparsers.add_parser("build", help="Build something.")
sub1.add_argument("--optimize", action="store_true", help="Enable optimizations.")
parser.add_argument("input_file", type=Path, help="Path to the input file.")
parser.add_argument("--time", type=time, help="Given time")

# Old version
# env = parser.parse_args()
# env.input_file  # a Path object

# New version
m = run(parser)
m.env.input_file  # a Path object

# Live edit of the fields
m.form()
```

Now, the help text looks much better. Try it in the terminal to see the colours.

```
$ ./program.py --help
usage: program.py [-h] [OPTIONS] PATH

╭─ positional arguments ──────────────────────────────────────────────────╮
│ PATH                    Path to the input file. (required)              │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ options ───────────────────────────────────────────────────────────────╮
│ -h, --help              show this help message and exit                 │
│ -v, --verbose           Verbosity level. Can be used twice to increase. │
│ --time HH:MM[:SS[…]]    Given time (default: 00:00:00)                  │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ build options ─────────────────────────────────────────────────────────╮
│ --build.optimize, --build.no-optimize                                   │
│                         Enable optimizations. (default: False)          │
╰─────────────────────────────────────────────────────────────────────────╯
```

And what happens when you launch the program? First, *Mininterface* asks you to provide the missing required arguments. Note the button that opens a file picker dialog.

![Positional fields](asset/argparse_required.avif)

Then, a `.form()` call will create a dialog with all the fields.

![Whole form](asset/argparse_form.avif)

You then access the arguments through [`m.env`](https://cz-nic.github.io/mininterface/Mininterface/#mininterface.Mininterface.env):

```python
print(m.env.time)  # -> 14:21
```

Once you decide to adopt *Mininterface*, convert the argparse definition into a dataclass. Then, the IDE will auto-complete the hints as you type.

!!! warning
    The argparse support is meant mostly for evaluation, as there are some [differences](Argparse-caveats.md) for advanced argparse CLI interfaces.
