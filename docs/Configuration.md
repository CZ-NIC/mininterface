## Special section
In a YAML config file, use a special section 'mininterface' to set up the UI. For example, this stub will enforce your program to use the Tui interface.

```yaml
mininterface:
    interface: tui
```

## Complete example

Source of `program.py`, we have one single attribute `foo`:

```python
from typing import Annotated
from dataclasses import dataclass
from mininterface import run, Choices

@dataclass
class Env:
    foo: Annotated["str", Choices("one", "two")] = "one"

m = run(Env)
m.form()
```

Source of `program.yaml` will enforce the comboboxes:

```yaml
number: 5
mininterface:
    gui:
        combobox_since: 1
```

The difference when using such configuration file.

![Configuration not used](asset/configuration-not-used.avif) ![Configuration used](asset/configuration-used.avif)

::: mininterface.config
    options:
        members:
            - MininterfaceConfig
            - Gui
            - Tui