"""Useful objects meaningful for CLI handling only."""
from ._lib.cli_utils import Command, SubcommandPlaceholder

try:
    from tyro.conf import Positional
except ImportError:
    from .exceptions import DependencyRequired

    raise DependencyRequired("basic")

Positional = Positional
"""
Annotate the dataclass field with `Positional` to make it behave like a positional argument in the CLI.

```python
from dataclasses import dataclass
from mininterface import run
from mininterface.cli import Positional

@dataclass
class Env:
    flag1: Positional[str] = "default"
    flag2: str = "flag"

run(Env)
```

```bash
$ ./program.py --help
usage: program.py [-h] [-v] [--flag2 STR] [STR]

╭─ positional arguments ───────────────────────────────────────────────╮
│ [STR]                flag1 (default: default)                        │
╰──────────────────────────────────────────────────────────────────────╯
╭─ options ────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                 │
│ -v, --verbose        Verbosity level. Can be used twice to increase. │
│ --flag2 STR          (default: flag)                                 │
╰──────────────────────────────────────────────────────────────────────╯
```

This is just a link from `tyro.conf` package which comes bundled. You will find much more useful features there.
https://brentyi.github.io/tyro/api/tyro/conf/#tyro.conf.Positional
"""

__all__ = ["Command", "SubcommandPlaceholder", "Positional"]