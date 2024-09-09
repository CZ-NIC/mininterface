::: mininterface.mininterface.Mininterface

# All possible interfaces
Several interfaces exist:

* [`Mininterface`][mininterface.Mininterface] – The base interface. Does not require any user input and hence is suitable for headless testing.
* `GuiInterface` – A tkinter window.
* `TuiInterface` – An interactive terminal.
  * `TextualInterface` – If [textual](https://github.com/Textualize/textual) installed, rich interface is used.
  * `TextInterface` – Plain text only interface with no dependency as a fallback.
* `ReplInterface` – A debug terminal. Invokes a breakpoint after every dialog.

Normally, you get an interface through [mininterface.run](#run) but if you do not wish to parse CLI and config file, you can invoke one directly.

```python
with TuiInterface("My program") as m:
    number = m.ask_number("Returns number")
```
