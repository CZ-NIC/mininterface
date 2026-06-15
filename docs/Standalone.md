When invoked directly, the bundled `mininterface` program creates simple GUI/TUI dialogs.

```bash
$ mininterface --help
usage: Mininterface [-h] [-v] {alert,ask,confirm,select,integrate,showcase,web}

Simple GUI/TUI dialog toolkit. Contains:
* dialog commands to output the value the user entered
* commands to operate and test programs using mininterface as a Python library

 options
 -----------------------------------------------------------------------
  -h, --help     show this help message and exit
  -v, --verbose  verbosity level, can be used multiple times to increase

 subcommands
 -----------------------------------------------------------------------
  (required)
    • alert      Dialog: Display the OK dialog with text.
    • ask        Dialog: Prompt the user to input a value.
    • confirm    Dialog: Display confirm box. Returns 0 / 1.
    • select     Dialog: Prompt the user to select.
    • integrate  Integrate to the system. Generates bash completion.
    • showcase   Prints various forms to show what's possible.
    • web        Expose a program using mininterface to the web.
```

You can fetch a value into e.g. a bash script.

```bash
$ mininterface ask "What's your age?" int  # GUI or TUI window invoked
18
```

![Standalone number](asset/standalone_number.avif)
![Standalone number in terminal](asset/standalone_number_textual.avif)

## Dialog commands

**`ask`** prompts the user for a value. The default type is `str`; the second positional argument imposes a type: `int`, `float`, `Path`, `date`, `datetime`, `time`, `file` (an existing file) or `dir` (an existing directory).

```bash
$ mininterface ask "Give me a folder" dir
/tmp
```

**`confirm`** displays a yes/no box and prints `1` or `0`. The second positional argument sets the focused button (`yes` or `no`).

```bash
$ mininterface confirm "Continue?" no
1
```

**`select`** outputs the chosen item.

```bash
$ mininterface select one two
```

![Select dialog](asset/choices_labels.avif)

## Other commands

* `mininterface integrate ./program` – install [bash completion](Overview.md#bash-completion) for a program using mininterface
* `mininterface web ./program.py` – expose a program [to the web](Interfaces.md#webinterface-or-web)
* `mininterface showcase [1|2]` – display example forms to preview what's possible; see [Showcase](#showcase)

## Showcase

The `showcase` command prints various forms to let you explore what mininterface looks like before writing any code. Choose the interface with the environment variable.

```bash
$ mininterface showcase          # showcase 1: a complex form with many field types
$ MININTERFACE_INTERFACE=tui mininterface showcase 2  # showcase 2: subcommand selection
```
