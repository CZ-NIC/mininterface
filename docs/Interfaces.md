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

# `GuiInterface` = `TkInterface`

A tkinter window.

# `TuiInterface`

An interactive terminal.

## `TextualInterface`

If [textual](https://github.com/Textualize/textual) installed, rich and mouse clickable interface is used.

## `TextInterface`

Plain text only interface with no dependency as a fallback.

When used in a with statement, the non-interactive session becomes interactive if possible, see the Mininterface [enter][mininterface.Mininterface.__enter__] method.

# `ReplInterface`

A debug terminal. Invokes a breakpoint after every dialog.
