# Mininterface – access to GUI, TUI, CLI and config files

Write the program core, do not bother with the input/output.

![hello world example](asset/hello-world.png "A minimal use case")

Check out the code that displays such window, just the code you need. No lengthy blocks of code imposed by an external dependency.

```python
from dataclasses import dataclass
from mininterface import run

@dataclass
class Config:
    """Set of options."""
    test: bool = False
    """My testing flag"""
    important_number: int = 4
    """This number is very important"""

if __name__ == "__main__":
    args: Config = run(Config, prog="My application").get_args()
    print(args.important_number)    # suggested by the IDE with the hint text "This number is very important"
```

Or bound the interface to a `with` statement that redirects stdout directly to the window.

```python
with run(Config) as m:
    print(f"Your important number is {m}")
    boolean = m.is_yes("Is that alright?")
```

TODO img

Loading config file is a piece of cake. Alongside `program.py`, put `program.yaml`. Instantly loaded.

```yaml
important_number: 555
```

TODO img

- [Mininterface – GUI, TUI, CLI and config](#mininterface-gui-tui-cli-and-config)
- [Background](#background)
- [Docs](#docs)

# Background

Wrapper between the [tyro](https://github.com/brentyi/tyro) `argparse` replacement and [tkinter_form](https://github.com/JohanEstebanCuervo/tkinter_form/) that converts dicts into a GUI.

Writing a small and useful program might be a task that takes fifteen minutes. Adding a CLI to specify the parameters is not so much overhead. But building a simple GUI around it? HOURS! Hours spent on researching GUI libraries, wondering why the Python desktop app ecosystem lags so far behind the web world. All you need is a few input fields validated through a clickable window... You do not deserve to add hundred of lines of the code just to define some editable fields. `mininterface` is here to help.

The config variables needed by your program are kept in cozy dataclasses. Write less! The syntax of [tyro](https://github.com/brentyi/tyro) does not require any overhead (as its `argparse` alternatives do). You just annotate a class attribute, append a simple docstring and get a fully functional application:
* Call it as `program.py --help` to display full help.
* Use any flag in CLI: `program.py --test`  causes `args.test` be set to `True`.
* The main benefit: Launch it without parameters as `program.py` to get a full working window with all the flags ready to be edited.
* Running on a remote machine? Automatic regression to the text interface.

# Docs

TODO nested configuration