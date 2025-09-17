from pathlib import Path
from types import NoneType, UnionType
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeVar, Union, get_args


from .._lib.auxiliary import _get_origin
from .path_tag import PathTag

try:
    from tyro.constructors import ConstructorRegistry, PrimitiveConstructorSpec, PrimitiveTypeInfo
    from tyro.conf._markers import _Marker
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")

File = Annotated[Path, PathTag(is_file=True)]
""" An existing file.
from mininterface import run
from mininterface.tag.flag import File

```python
@dataclass
class Env:
    my_file: File

m = run(Env)
m.env.my_file  # guaranteed to be an existing dir
```

!!! Warning
    EXPERIMENTAL.
"""
# NOTE missing test
Dir = Annotated[Path, PathTag(is_dir=True)]
""" An existing directory.
from mininterface import run
from mininterface.tag.flag import Dir

```python
@dataclass
class Env:
    my_dir: Dir

m = run(Env)
m.env.my_dir  # guaranteed to be an existing dir
```

!!! Warning
    EXPERIMENTAL.
"""
# NOTE missing test

_blank_error = (
    "Unrecognised value '{}'. Allowed values are blank for True/1/on / False/0/off"
    " (case insensitive). Should the value be considered a positional parameter,"
    " move the parameter behind."
)


def _assure_blank_or_bool(args):
    match len(args):
        case 0:
            return True
        case 1:
            if args[0].lower() in ["0", "false", "off"]:
                return False
            elif args[0].lower() in ["1", "true", "on"]:
                return True
            raise TypeError(_blank_error.format(args[0]))
        case _:
            raise ValueError(_blank_error.format(args[0]))


BlankTrue = Annotated[
    bool | None,
    PrimitiveConstructorSpec(
        nargs=(0,1),  # TODO test should be probably = (0,1)
        metavar="blank=True|BOOL",
        instance_from_str=_assure_blank_or_bool,
        is_instance=lambda instance: True,  # NOTE not sure
        str_from_instance=lambda instance: [instance],
    ),
]
"""
When left blank, this flag produces True.


Returns:
    bool: for `0/false/off/1/true/on` in the parameter
    True: When parameter is left blank.

Raises:
    ValueError: Raised on an unknown parameter.

!!! Warning
    Experimental.

"""
# NOTE untested
# NOTE Works good with static type checking.


T = TypeVar("T")

_custom_registry = ConstructorRegistry()

Blank = Annotated[T | None, None]
"""
This marker specifies:

1. The default value can also be None (for the case the flag is omitted).
2. A different behavior when the flag is provided without a value.

If the flag is left blank, it evaluates to `True` (or to the value specified by a `Literal`).
If the flag is omitted entirely from the CLI, it returns the default value.


```python
from dataclasses import dataclass
from mininterface import run
from mininterface.tag.flag import Blank

@dataclass
class Env:
    test: Blank[int] = None

print(run(Env).env.test)
```

Let's try:

```bash
$ program.py --help
usage: program.py [-h] [-v] [--test BLANK|int]

╭─ options ───────────────────────────────────────────────────────────────────────╮
│ -h, --help              show this help message and exit                         │
│ -v, --verbose           verbosity level, can be used multiple times to increase │
│ --test BLANK|int        (default: 'None / or if left blank: True')              │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

```bash
$ program.py           # None
$ program.py  --test   # True
$ program.py  --test 5 # 5
```

The default blank value might be specified by a `Literal` in the `Annotated` statement.

```python
@dataclass
class Env
    test: Annotated[Blank[int], Literal[2]] = None

print(run(Env).env.test)
```

Let's try:

```bash
$ program.py           # None
$ program.py  --test   # 2
$ program.py  --test 5 # 5
```

You can use multiple types together:

```python
@dataclass
class Env:
    test: Blank[int|bool] = 0

print(run(Env).env.test)
```

Note that you can not use 'True' or 'False' for values, as the parameter becomes a bool.

Let's try:

```bash
$ program.py               # 0
$ program.py  --test       # True
$ program.py  --test False # False
```



!!! Warning
    Experimental.

    ??? Discussion
        The design is working but syntax `Annotated[str, Blank(True)]` might be a cleaner design. Do you have an opinion? Let us know.
    """

# NOTE untested
# NOTE Should we move rather to mininterface.cli?

# NOTE Python 3.13 would allow
# type Blank[T, U = None] = Optional[T]
# so maybe
# `Blank[int, Literal[2]]` will become an alternative
# for `Annotated[Blank4[int], Literal[fn()]]` for static literal values


if not TYPE_CHECKING:
    # In runtime, flag must not be an Annotated but a full class.
    # When type checking, flag must not be a full class otherwise
    # the value would needed to be instance of Blank (instead of ex. a str)

    class _Blank(_Marker):
        def __getitem__(self, key):
            return Annotated[(key | None, self)]

        def __init__(self, description: str):
            self.description = description
            self.default_val = None

        def __repr__(self):
            return self.description

    globals().update({"Blank": _Blank("Blank")})


@_custom_registry.primitive_rule
def _(
    type_info: PrimitiveTypeInfo,
) -> PrimitiveConstructorSpec | None:
    if Blank in type_info.markers:
        default_val = True
        import inspect

        frame = inspect.currentframe()
        try:
            try:
                annotation = frame.f_back.f_back.f_locals["type"]
            except:
                annotation = frame.f_back.f_back.f_locals["arg"].field.type
        except:
            # ex. `threads: Blank[int] | Literal["auto"] = "auto"
            raise ValueError("Cannot determine the default blank value. Check the mininterface.tag.flag.Blank annotation or raise a project issue please.")

        type_, *metadata = get_args(annotation)
        for m in metadata:
            if _get_origin(m) is Literal:
                default_val, *_ = get_args(m)

        type_ = type_info.type
        if type_info.type_origin is Union or type_info.type_origin is UnionType:
            types = get_args(type_info.type)
            type_ = types[0]
        else:
            types = (type_,)

        if len(types) == 1:
            metavar = getattr(type_, "__name__", repr(type_))
        else:
            metavar = "|".join(getattr(s, "__name__", repr(s)) for s in types if s is not NoneType)

        def instance_from_str(args):
            if not args:
                return default_val
            val = args[0]
            if bool in types:
                if val == "True":
                    return True
                elif val == "False":
                    return False
            e = None
            for t in types:
                if t is not bool:
                    try:
                        return t(val)
                    except Exception:
                        continue
            raise ValueError("Don't know how to make an instance")

        return PrimitiveConstructorSpec(
            nargs=(0, 1),
            metavar=f"[{metavar}]",
            instance_from_str=lambda args: instance_from_str(args),
            is_instance=lambda ins: ins is None or isinstance(ins, types),
            str_from_instance=lambda ins: [str(ins) + f" / or if left blank: {default_val}"],
        )
