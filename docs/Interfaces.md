## All possible interfaces

Apart from the default [`Mininterface`][mininterface.Mininterface], the base interface the others are fully compatible with, several interfaces exist at `mininterface.interfaces`.

| shortcut | full name |
| -- | -- |
| min | [Mininterface](#mininterface) |
| gui | [GuiInterface](#guiinterface-or-tkinterface-or-gui) \| TkInterface |
| tui \| textual | [TuiInterface](#tuiinterface-or-tui) |
| text \| tui | [TextInterface](#textinterface) |
| web | [WebInterface](#webinterface-or-web) |

### Ordering

We try to obtain the best interface available. By preference, it is **gui** , then **> tui** (textual or at least **> text**), then the original non-interactive **> Mininterface** is used. The ensures the program to still work in cron jobs etc.

### Getting one

Normally, you get an interface through [mininterface.run][]
but if you do not wish to parse CLI and config file, you can invoke one directly through `from mininterface.interfaces import *`. You may as well use the [`get_interface`][mininterface.interfaces.get_interface] function to ensure the interface is available or invoke the program with [`MININTERFACE_INTERFACE`](#environment-variable-mininterface_interface) environment variable.

!!! info
    Performance boost: Only interfaces that are being used are loaded into memory for faster start.

### Direct invocation

How to invoke a specific interface directly?

```python
from mininterface.interfaces import TuiInterface

with TuiInterface("My program") as m:
    number = m.ask("Returns number", int)
```

::: mininterface.interfaces.get_interface
    options:
        show_signature: false
        show_root_full_path: false

### Environment variable `MININTERFACE_INTERFACE`

From outside, you may override the default interface choice by the environment variable.

`$ MININTERFACE_INTERFACE=web program.py`

# `Mininterface`

The base interface.

# `GuiInterface` or `TkInterface` or 'gui'

A tkinter window. It inherits from [`GuiSettings`][mininterface.settings.GuiSettings].

```bash
$ MININTERFACE_INTERFACE=gui ./program.py
```

![Hello world example: GUI window](asset/hello-gui.avif "A minimal use case – GUI")
<br>*The code for generating screenshots is taken from the [Introduction](index.md).*

# `TuiInterface` or 'tui'

An interactive terminal. Will try to get `TextualInterface` and `TextInterface` as a fallback.

## `TextualInterface`

If [textual](https://github.com/Textualize/textual) installed, rich and mouse clickable interface is used.

```bash
$ MININTERFACE_INTERFACE=tui ./program.py
```

![Hello world example: TUI fallback](asset/hello-tui.avif "A minimal use case – TUI fallback")

## `TextInterface`

Plain text only interface with no dependency as a fallback. The non-interactive session becomes interactive if possible but there is no mouse support. Does not clear whole screen as TextualInterface if it suits better your program flow.

```bash
$ MININTERFACE_INTERFACE=text ./program.py
```
![Hello world example: text fallback](asset/hello-text.avif "A minimal use case – text fallback")

# `WebInterface` or 'web'

Exposed to a web.

You can expose any script to the web by invoking it through the bundled `mininterface` program.


```bash
$ mininterface web ./program.py --port 9997
```

But still, you have the possibility to invoke the web by preference in the `run` or `get_interface` method, direct invocation through importing `WebInterface` from `mininterface.interfaces`, or through the environment variable.

```bash
$ MININTERFACE_INTERFACE=web ./program.py
Serving './program.py' on http://localhost:64646

Press Ctrl+C to quit
```
![Hello world example: web](asset/hello-web.avif "A minimal use case – web")



!!! Caveat
    Should you plan to use the WebInterface, we recommend invoking it be the first thing your program do. All the statements before invoking it run multiple times!

    ```python
    hello = "world"  # This line would run thrice!
    with run(interface="web") as m:
        m.form({"one": 1})
        m.form({"two": 2})
    ```

!!! Warning
    Still in beta. We appreciate help with testing etc.

# `ReplInterface`

A debug terminal. Invokes a breakpoint after every dialog.
