# Config file
Any settings you see in the `--help` command can be modified via a YAML config file.

By default, we try to find one in the current working dir, whose name stem is the same as the program's. Ex: program.py will search for program.yaml. This behaviour can be changed via the [run][mininterface.run] method `config_file` or `add_config` parameters or via `MININTERFACE_CONFIG` environment variable.

!!! Tip
    You do not have to re-define all the settings in the config file, you can choose a few.

## Search order by highest priority

* `$ program.py --config PATH` with `run(add_config=True)` will load `PATH`
* `$ MININTERFACE_CONFIG=PATH program.py` will load `PATH`
* `$ program.py` with `run(config_file=PATH)` will load `PATH`
* `$ program.py` with `run(config_file=True)` will load `program.yaml`

## Basic example

We have this nested structure:

```python
# program.py
@dataclass
class FurtherConfig:
    token: str
    host: str = "example.org"

@dataclass
class Env:
    further: FurtherConfig

...
m = run(Env)
print(m.env.further.host)  # example.com
```

The config file being used:

```yaml
# program.yaml
further:
  host: example.com
```

## Complex example

Nested container structures are supported too.

```python
from mininterface import run
@dataclass
class ComplexEnv:
    a1: dict[int, str]
    a2: dict[int, tuple[str, int]]
    a3: dict[int, list[str]]
    a4: list[int]
    a5: tuple[str, int]
    a6: list[int | str]
    a7: list[tuple[str, float]]

m = run(ComplexEnv)
m.env
# ComplexEnv(
#  a1={1: 'a'},
#  a2={2: ('b', 22), 3: ('c', 33), 4: ('d', 44)},
#  a3={5: ['e', 'ee', 'eee']},
#  a4=[6, 7],
#  a5=('h', 8),
#  a6=['i', 9],
#  a7=[('j', 10.0), ('k', 11), ('l', 12)])
```

The YAML file used. (Note the various YAML syntax and the automatic YAML-list to Python-tuple conversion.)

```yaml
{% include-markdown '../tests/complex.yaml' %}
```