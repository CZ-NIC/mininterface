# Dialog methods

Mininterface provides five dialog methods for prompting the user. They all work the same way across every backend (GUI, TUI, web, text).

See the full API reference in [`Mininterface`](Mininterface.md).

---

## `m.form()` — edit a form

```python
m.form(form=None, title="", *, submit=True)
```

Displays an editable form. Pass:

* **nothing** (or `None`) → edit `m.env` in place
* a **dataclass type** → instantiate and return it
* a **dataclass instance** → edit in place and return it
* a **dict** → edit in place and return it

```python
# Edit the main env
m.form()

# Edit an arbitrary dict
result = m.form({"count": 0, "label": "hello"})

# Instantiate a dataclass
from dataclasses import dataclass

@dataclass
class Options:
    retries: int = 3
    verbose: bool = False

opts = m.form(Options)
print(opts.retries)
```

The `submit` parameter controls the submit button label (`True` = default label, `False` = no submit button, a string = custom label).

---

## `m.ask()` — typed input

```python
m.ask(text, annotation=str, validation=None)
```

Prompts the user for a single value of the given type.

```python
name = m.ask("Your name")                 # str
age  = m.ask("Your age", int)             # int
path = m.ask("Pick a file", PathTag(is_file=True))
```

Pass a [`Tag`](Tag.md) as `annotation` for extra control (file picker, validation, …). Pass a callable (or list of callables) as `validation` for inline validation.

---

## `m.confirm()` — yes/no

```python
m.confirm(text, default=True, *, timeout=0)
```

Displays a yes/no confirmation box. Returns `True`/`False`.

```python
if m.confirm("Delete all files?", default=False):
    ...
```

`timeout` (seconds): auto-confirms with the default value when it expires (`0` = no timeout).

---

## `m.alert()` — informational message

```python
m.alert(text, *, timeout=0)
```

Displays a message with an OK button. Returns `None`.

```python
m.alert("Done! Files processed.")
```

`timeout` (seconds): auto-dismisses when it expires (`0` = no timeout).

---

## `m.select()` — choose from options

```python
m.select(options, title="", default=None, tips=None,
         multiple=None, skippable=True, launch=True)
```

Displays a selection dialog. Returns the chosen value (or a list when `multiple=True`).

```python
fruit = m.select(["apple", "banana", "cherry"])

# Multi-select
fruits = m.select(["apple", "banana", "cherry"], multiple=True)

# With a default
fruit = m.select(["apple", "banana"], default="banana")
```

Key parameters:

| parameter | meaning |
| --------- | ------- |
| `multiple` | `True` = multi-select, inferred automatically from `default` being a list |
| `tips` | secondary list of hint texts shown alongside the options |
| `skippable` | allow the dialog to be dismissed without selecting |
| `launch` | immediately call the selected item if it is callable |

See [Supported types – Constraining](Supported-types.md#constraining) for `Enum`, `Literal`, and `SelectTag` alternatives.

---

## Using `with run() as m:`

Wrapping your code in a `with` statement turns the mininterface into a **persistent window** that stays open across all dialogs:

```python
with run(Env) as m:
    print(f"Your number is {m.env.my_number}")  # printed inside the window
    boolean = m.confirm("Is that alright?")
```

Two additional effects:

* **`print()` is redirected** into the UI window instead of the terminal.
* **Non-interactive TTY** (e.g. a script started from a desktop launcher) becomes interactive where possible (TextInterface).

When the `with` block exits, stdout is restored and any buffered output not yet shown to the user is reprinted to the real terminal.
