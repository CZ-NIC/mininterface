## All possible interfaces

Normally, you get an interface through [mininterface.run][]
but if you do not wish to parse CLI and config file, you can invoke one directly `from mininterface.interfaces import *`.

Apart from the default [`Mininterface`][mininterface.Mininterface], the base interface the others are fully compatible with, several interfaces exist:

How to invoke a specific interface.

```python
from mininterface.interfaces import TuiInterface

with TuiInterface("My program") as m:
    number = m.ask_number("Returns number")
```

Or you may use the `get_interface` function to ensure the interface is available.

::: mininterface.interfaces.get_interface

# `Mininterface`

When a GUI is not available (GuiInterface), nor the rich TUI is available (TextualInterface), nor the mere interactive TextInterface is available, the original non-interactive Mininterface is used. The ensures the program is still working in cron jobs etc.


# `GuiInterface` or `TkInterface` or 'gui'

A tkinter window.

It inherits from [`GuiOptions`][mininterface.options.GuiOptions]

# `TuiInterface` or 'tui'

An interactive terminal.

## `TextualInterface`

If [textual](https://github.com/Textualize/textual) installed, rich and mouse clickable interface is used.

## `TextInterface`

Plain text only interface with no dependency as a fallback. The non-interactive session becomes interactive if possible but there is no mouse support. Does not clear whole screen as TextualInterface if it suits better your program flow.

# `WebInterface` or 'web'

Exposed to a web.

```python
from dataclasses import dataclass
from mininterface import run

@dataclass
class Env:
    my_flag: bool = False
    my_number: int = 4

if __name__ == "__main__":
    m = run(Env, interface="web")
    m.form()  # Exposed on the web
```

Note that you can expose to the web any mininterface application, like this GUI:

```python
from dataclasses import dataclass
from mininterface import run

@dataclass
class Env:
    my_flag: bool = False
    my_number: int = 4

if __name__ == "__main__":
    m = run(Env, interface="gui")
    m.form()  # Seen in the GUI
```

We expose it to the web by invoking it through the `mininterface` program.

```bash
$ mininterface --web.cmd ./program.py --web.port 9997
```

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
