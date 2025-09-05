import re
import warnings
from dataclasses import MISSING, dataclass, fields, is_dataclass
from types import UnionType
from typing import Annotated, Optional, Type, Union, get_args, get_origin

try:
    from tyro._singleton import MISSING_NONPROP

    from ..cli import SubcommandPlaceholder
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")


from ..tag import Tag
from ..tag.tag_factory import tag_factory
from ..validators import not_empty
from .auxiliary import _get_origin, _get_parser, get_description
from .form_dict import DataClass, EnvClass, MissingTagValue

# Pydantic is not a project dependency, that is just an optional integration
try:  # Pydantic is not a dependency but integration
    from pydantic import BaseModel

    pydantic = True
except ImportError:
    pydantic = False
    BaseModel = False
try:  # Attrs is not a dependency but integration
    import attr
except ImportError:
    attr = None


@dataclass(slots=True)
class ChosenSubcommand:
    name: str
    subdict: dict


def coerce_type_to_annotation(value, annotation):
    """
    Coerce value (e.g. list) to expected type (e.g. tuple[int, int]).
    Only handles basic cases: tuple[...] from list, and recurses if needed.
    """
    if annotation is None:
        return value

    annotation = _unwrap_annotated(annotation)  # NOTE might be superfluous, called before
    origin = get_origin(annotation)

    # Handle tuple[...] conversion
    if origin is tuple and isinstance(value, list):
        args = get_args(annotation)
        if args and len(args) == len(value):
            return tuple(coerce_type_to_annotation(v, arg) for v, arg in zip(value, args))
        return tuple(value)

    # Handle list[...] conversion
    if origin is list and isinstance(value, list):
        args = get_args(annotation)
        if args:
            return [coerce_type_to_annotation(v, args[0]) for v in value]
        return value

    # Handle dict[...] conversion
    if origin is dict and isinstance(value, dict):
        key_type, val_type = get_args(annotation)
        return {
            coerce_type_to_annotation(k, key_type): coerce_type_to_annotation(v, val_type) for k, v in value.items()
        }

    # For nested dataclass or BaseModel etc.
    return value


def _get_wrong_field(
    env_class: EnvClass,
    field_name: str,
    annotation=None,
) -> Tag:
    desc = get_description(env_class, field_name)
    if desc == field_name:
        desc = ""
    return tag_factory(
        MissingTagValue(),
        desc,
        annotation,
        validation=not_empty,
        _src_class=env_class,
        _src_key=field_name,
    )


def _unwrap_annotated(tp):
    """
    Annotated[Annotated[Inner, ...], ...] -> `Inner`,
    """
    if _get_origin(tp) is Annotated:
        inner, *_ = get_args(tp)
        return inner
    return tp


def create_with_missing(env, disk: dict, wf: Optional[dict] = None, mint: Optional["Mininterface"] = None):
    """
    Create a default instance of an Env object. This is due to provent tyro to spawn warnings about missing fields.
    Nested dataclasses have to be properly initialized. YAML gave them as dicts only.

    The result contains MISSING_NONPROP on the places the original Env object must have a value.

    And such fields are put into the wf (wrong_fields) dict.
    """
    # NOTE a test is missing
    # @dataclass
    # class Test:
    #     foo: str = "NIC"
    # @dataclass
    # class Env:
    #     test: Test
    #     mod: OmitArgPrefixes[EnablingModules]
    # config.yaml:
    # test:
    #     foo: five
    # mod:
    #     whois: False
    # m = run(FlagConversionOff[Env], config_file=...) would fail with
    # `TypeError: issubclass() arg 1 must be a class` without _unwrap_annotated

    # Determine model
    if pydantic and issubclass(_unwrap_annotated(env), BaseModel):
        proc_method = _process_pydantic
    elif attr and attr.has(env):
        proc_method = _process_attr
    else:  # dataclass
        proc_method = _process_dataclass

    # Fill default fields with the config file values or leave the defaults.
    # Unfortunately, we have to fill the defaults, we cannot leave them empty
    # as the default value takes the precedence over the hard coded one, even if missing.
    out = {}
    missings: list[Tag] = []
    for name, v in proc_method(env, disk, wf, mint):
        out[name] = v
        if v == MISSING_NONPROP and wf is not None:
            # For building config file, the MISSING_NONPROP is alright as we expect tyro to fail
            # if the value is not taken from the CLI.
            tag = wf[name] = _get_wrong_field(env, name)
            missings.append(tag)
        disk.pop(name, None)

    # Check for unknown fields
    if disk:
        warnings.warn(f"Unknown fields in the configuration file: {', '.join(disk)}")

    # Safely initialize the model
    model = env(**out)
    for tag in missings:
        tag._src_obj = model
    return model


def _process_pydantic(env, disk, wf: Optional[dict], m: Optional["Mininterface"] = None):
    for name, f in env.model_fields.items():
        if name in disk:
            default_value = f.default if f.default is not None else MISSING
            v = _process_field(name, f.annotation, disk[name], wf, m, default_value)
        elif f.default is not None:
            v = f.default
        else:
            v = _process_field(name, f.annotation, MISSING, wf, m, default_value=MISSING)
        yield name, v


def _process_attr(env, disk, wf: Optional[dict], m: Optional["Mininterface"] = None):
    for f in attr.fields(env):
        has_default = f.default is not attr.NOTHING
        default_val = f.default if has_default else MISSING
        if f.name in disk:
            v = _process_field(f.name, f.type, disk[f.name], wf, m, default_val)
        elif has_default:
            v = f.default
        else:
            v = _process_field(f.name, f.type, MISSING, wf, m, default_val)
        yield f.name, v


def _is_struct_type(t) -> bool:
    """True for dataclass / attrs / pydantic model classes."""
    try:
        if is_dataclass(t):
            return True
        if attr and attr.has(t):
            return True
        if pydantic and isinstance(t, type) and issubclass(t, BaseModel):
            return True
    except TypeError:  # ex. parametrized annotation
        pass
    return False


def _resolve_ftype(ftype, default_value):
    ftype = _unwrap_annotated(ftype)
    if default_value is not MISSING and default_value is not None:
        if is_dataclass(default_value):
            return default_value.__class__
        if attr and attr.has(default_value):
            return default_value.__class__
        if pydantic and isinstance(default_value, BaseModel):
            return default_value.__class__
    return ftype


def _init_struct_value(ftype, disk_value, wf, fname, m):
    """Init structural type (dataclass/attrs/pydantic)."""
    if wf is not None:
        subwf = wf[fname] = {}
    else:
        subwf = None
    v = create_with_missing(ftype, disk_value, subwf, m)
    if wf and not subwf:  # prevent having an empty section to edit
        del wf[fname]
    return v


def _process_field(fname, ftype, disk_value, wf, m, default_value=MISSING):
    ftype = _resolve_ftype(ftype, default_value)
    origin = _get_origin(ftype)

    # the subcommand has been already chosen by CLI parser
    if isinstance(disk_value, ChosenSubcommand):  # `(class Message | class Console)`
        for _subcomm in get_args(_unwrap_annotated(ftype)):
            if disk_value.name == getattr(_subcomm, "__name__", "").casefold():
                ftype = _subcomm  # `class Message` only
                disk_value = disk_value.subdict
                break
        else:
            raise ValueError(f"Type {disk_value} not found in {ftype}")

    if disk_value is not MISSING:
        if _is_struct_type(ftype):
            return _init_struct_value(ftype, disk_value, wf, fname, m)
        return coerce_type_to_annotation(disk_value, ftype)

    # We must handle the case when there are multiple subcommands possible.
    # The user decides now which way to go (choose a subcommand).
    if (origin is Union or origin is UnionType) and all(_is_struct_type(cl) for cl in get_args(ftype)):
        if not m:  # we should not come here
            raise RuntimeError("Missing interface, report the issue please.")
        ftype = choose_subcommand(get_args(ftype), m)
        return _init_struct_value(ftype, {}, wf, fname, m)

    return MISSING_NONPROP


def _process_dataclass(env, disk, wf: Optional[dict], m: Optional["Mininterface"] = None):
    for f in fields(_unwrap_annotated(env)):

        if f.name.startswith("__"):
            continue
        elif f.name in disk:
            v = _process_field(f.name, f.type, disk[f.name], wf, m, f.default)
        elif f.default_factory is not MISSING:
            v = f.default_factory()
        elif f.default is not MISSING:
            v = f.default
        else:
            v = _process_field(f.name, f.type, MISSING, wf, m)
        yield f.name, v


def choose_subcommand(env_classes: list[Type[DataClass]], m: "Mininterface[EnvClass]"):
    # NOTE make select display buttons if there is a little amount of options.
    env = m.select({(to_kebab_case(cl.__name__).replace("-", " ").capitalize(), _get_parser(cl).description): cl for cl in env_classes  if cl is not SubcommandPlaceholder})
    return env

def to_kebab_case(name: str) -> str:
    """MyClass -> my-class"""
    # I did not find where tyro does it. If I find it, I might use its function instead.
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
