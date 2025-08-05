Be aware that in contrast to the argparse:

* We create default values. This does make sense for most values but might pose a confusion for ex. `parser.add_argument("--path", type=Path)` which becomes `Path('.')`, not `None`.
* When storing multiple `store_const` action to the same `dest`, order does not matter.
* When using positional arguments before the subcommands, the order changes

Argparse:

```bash
$ ./program.py --help
usage: program.py [-h] input_file {deploy,build} ...

Test parser for dataclass generation.

positional arguments:
  input_file      Path to the input file.
  {deploy,build}
    deploy        Deploy something
    build         Build something

options:
  -h, --help      show this help message and exit

# Using the command `deploy`
$ ./program.py ./file.txt deploy  --help
usage: program.py input_file deploy [-h] [--port PORT]

My thorough description.

options:
  -h, --help   show this help message and exit
  --port PORT  SSH port.
```


Mininterface changes the order and produces a warning:

```bash
$ ./program.py --help
UserWarning: This CLI parser have a subcommand placed after positional arguments. The order of arguments changes, see --help.
usage: program.py [-h] [-v] {deploy,build}

Test parser for dataclass generation.

╭─ options ─────────────────────────────────────────────────────────────╮
│ -h, --help            show this help message and exit                 │
│ -v, --verbose         Verbosity level. Can be used twice to increase. │
╰───────────────────────────────────────────────────────────────────────╯
╭─ subcommands ─────────────────────────────────────────────────────────╮
│ {deploy,build}                                                        │
│     deploy            Deploy something: My thorough description.      │
│     build             Build something                                 │
╰───────────────────────────────────────────────────────────────────────╯

# Using the command `deploy`
$ ./program.py deploy --help
UserWarning: This CLI parser have a subcommand placed after positional arguments. The order of arguments changes, see --help.
usage: program.py deploy [-h] [-v] [--port INT] STR

Deploy something: My thorough description.

╭─ positional arguments ───────────────────────────────────────────────╮
│ STR                  Path to the input file. (required)              │
╰──────────────────────────────────────────────────────────────────────╯
╭─ options ────────────────────────────────────────────────────────────╮
│ -h, --help           show this help message and exit                 │
│ -v, --verbose        Verbosity level. Can be used twice to increase. │
│ --port INT           SSH port. (default: 22)                         │
╰──────────────────────────────────────────────────────────────────────╯
```

The code

```python
from argparse import ArgumentParser
from mininterface import run

parser = ArgumentParser(description="Test parser for dataclass generation.")
parser.add_argument("input_file", type=str, help="Path to the input file.")
subs = parser.add_subparsers(dest="command", required=True)
sub2 = subs.add_parser(
    "deploy", help="Deploy something", description="My thorough description."
)
sub1 = subs.add_parser("build", help="Build something")
sub2.add_argument("--port", type=int, default=22, help="SSH port.")

if True:
    env = parser.parse_args()
else:
    env = run(parser).env
```