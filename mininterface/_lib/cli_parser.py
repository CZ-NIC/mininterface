#
# CLI and config file parsing.
#
import argparse
import logging
import re
import sys
import warnings
from argparse import Action, ArgumentParser
from contextlib import ExitStack
from dataclasses import (MISSING, Field, asdict, dataclass, field, fields,
                         is_dataclass, make_dataclass)
from pathlib import Path
from types import SimpleNamespace
from typing import (Annotated, Any, Callable, Optional, Sequence, Type, Union, get_args,
                    get_origin)
from unittest.mock import patch

from .auxiliary import (dataclass_asdict_no_defaults, merge_dicts,
                        yield_annotations)
from .form_dict import DataClass, EnvClass, MissingTagValue
from ..settings import MininterfaceSettings
from ..tag import Tag
from ..tag.tag_factory import tag_factory
from ..validators import not_empty

try:
    import yaml
    from tyro import cli
    from tyro._argparse_formatter import TyroArgumentParser
    from tyro._singleton import MISSING_NONPROP
    from tyro.conf import Positional
    from tyro.extras import get_parser
except ImportError:
    from ..exceptions import DependencyRequired
    raise DependencyRequired("basic")


# Pydantic is not a project dependency, that is just an optional integration
try:  # Pydantic is not a dependency but integration
    from pydantic import BaseModel
    pydantic = True
except ImportError:
    pydantic = False
    BaseModel = False
try:   # Attrs is not a dependency but integration
    import attr
except ImportError:
    attr = None


WrongFields = dict[str, Tag]

eavesdrop = ""
""" Used to intercept an error message from tyro """
reraise: Optional[Callable] = None
""" Reraise the intercepted tyro error message """


class Patches:
    """ Various mocking patches. """

    @staticmethod
    def custom_error(self: TyroArgumentParser, message: str):
        """ Fetch missing required options in GUI.
        On missing argument, tyro fail. We cannot determine which one was missing, except by intercepting
        the error message function. Then, we reconstruct the missing options.
        Thanks to this we will be able to invoke a UI dialog with the missing options only.
        """
        global eavesdrop, reraise
        if not message.startswith("the following arguments are required:"):
            return super(TyroArgumentParser, self).error(message)
        eavesdrop = message
        def reraise(): return super(TyroArgumentParser, self).error(message)
        raise SystemExit(2)  # will be catched

    @staticmethod
    def custom_init(self: TyroArgumentParser, *args, **kwargs):
        super(TyroArgumentParser, self).__init__(*args, **kwargs)
        default_prefix = '-' if '-' in self.prefix_chars else self.prefix_chars[0]
        self.add_argument(default_prefix+'v', default_prefix*2+'verbose', action='count', default=0,
                          help="Verbosity level. Can be used twice to increase.")

    @staticmethod
    def custom_parse_known_args(self: TyroArgumentParser, args=None, namespace=None):
        namespace, args = super(TyroArgumentParser, self).parse_known_args(args, namespace)
        # NOTE We may check that the Env does not have its own `verbose``
        if hasattr(namespace, "verbose"):
            if namespace.verbose > 0:
                log_level = {
                    1: logging.INFO,
                    2: logging.DEBUG,
                    3: logging.NOTSET
                }.get(namespace.verbose, logging.NOTSET)
                logging.basicConfig(level=log_level, format='%(levelname)s - %(message)s')
            delattr(namespace, "verbose")
        return namespace, args


def assure_args(args: Optional[Sequence[str]] = None):
    if args is None:
        # Set env to determine whether to use sys.argv.
        # Why settings env? Prevent tyro using sys.argv if we are in an interactive shell like Jupyter,
        # as sys.argv is non-related there.
        try:
            # Note wherease `"get_ipython" in globals()` returns True in Jupyter, it is still False
            # in a script a Jupyter cell runs. Hence we must put here this lengthty statement.
            global get_ipython
            get_ipython()
        except:
            args = sys.argv[1:]  # Fetch from the CLI
        else:
            args = []
    return args


def parse_cli(env_or_list: Type[EnvClass] | list[Type[EnvClass]],
              kwargs: dict,
              add_verbose: bool = True,
              ask_for_missing: bool = True,
              args: Optional[Sequence[str]] = None) -> tuple[EnvClass, WrongFields]:
    """ Run the tyro parser to fetch program configuration from CLI """
    if isinstance(env_or_list, list):
        # We have to convert the list of possible classes (subcommands) to union for tyro.
        # We have to accept the list and not an union directly because we are not able
        # to type hint a union type, only a union instance.
        # def sugg(a: UnionType[EnvClass]) -> EnvClass: ...
        # sugg(Subcommand1 | Subcommand2). -> IDE will not suggest anything
        type_form = Union[tuple(env_or_list)]  # Union[*env_or_list] not supported in Python3.10
        env_classes = env_or_list
    else:
        type_form = env_or_list
        env_classes = [env_or_list]

    # unwrap annotated
    # ex: `run(FlagConversionOff[OmitArgPrefixes[Env]])` -> Env
    for i, candidate in enumerate(env_classes):
        while get_origin(candidate) is Annotated:
            candidate = get_args(candidate)[0]
        env_classes[i] = candidate

    # Mock parser, inject special options into
    patches = []
    if ask_for_missing:  # Get the missing flags from the parser
        patches.append(patch.object(TyroArgumentParser, 'error', Patches.custom_error))
    if add_verbose:  # Mock parser to add verbosity
        # The verbose flag is added only if neither the env_class nor any of the subcommands have the verbose flag already
        if all("verbose" not in cl.__annotations__ for cl in env_classes):
            patches.extend((
                patch.object(TyroArgumentParser, '__init__', Patches.custom_init),
                patch.object(TyroArgumentParser, 'parse_known_args', Patches.custom_parse_known_args)
            ))

    # Run the parser, with the mocks
    try:
        with ExitStack() as stack:
            [stack.enter_context(p) for p in patches]  # apply just the chosen mocks
            res = cli(type_form, args=args, **kwargs)
            if res is MISSING_NONPROP:
                # NOTE not true any more, I've implemented and might go furhter:
                # NOTE tyro does not work if a required positional is missing tyro.cli()
                # returns just NonpropagatingMissingType (MISSING_NONPROP).
                # If this is supported, I might set other attributes like required (date, time).
                # Fail if missing:
                #   files: Positional[list[Path]]
                # Works if missing but imposes following attributes are non-required (have default values):
                #   files: Positional[list[Path]] = field(default_factory=list)
                pass
            return res, {}
    except BaseException as exception:
        if ask_for_missing and getattr(exception, "code", None) == 2 and eavesdrop:
            # Some required arguments are missing. Determine which.
            wf: dict[str, Tag] = {}

            # There are multiple dataclasses, query which is chosen
            if len(env_classes) == 1:
                env = env_classes[0]
                parser: ArgumentParser = get_parser(type_form, **kwargs)
                subargs = args
            elif len(args):
                env = next((env for env in env_classes if to_kebab_case(env.__name__) == args[0]), None)
                if env:
                    parser: ArgumentParser = get_parser(env)
                    subargs = args[1:]
            if not env:
                raise NotImplemented("This case of nested dataclasses is not implemented. Raise an issue please.")

            # Determine missing argument of the given dataclass
            positionals = (p for p in parser._actions if p.default != argparse.SUPPRESS)
            for arg in _fetch_eavesdrop_args():
                # We handle both Positional and required arguments
                # Ex: `The following arguments are required: PATH, --foo`
                if "--" not in arg:
                    # Positional
                    # Ex: `The following arguments are required: PATH, INT, STR`
                    argument = next(positionals)
                    register_wrong_field(env, kwargs, wf, argument, exception, eavesdrop)
                else:
                    # required arguments
                    # Ex: `the following arguments are required: --foo, --bar`
                    if argument := identify_required(parser,  arg):
                        register_wrong_field(env, kwargs, wf, argument, exception, eavesdrop)

            # Second attempt to parse CLI.
            # We have just put a default values for missing fields so that tyro will not fail.
            # If we succeeded (no exotic case), this will pass through.
            # Then, we impose the user to fill the missing values.
            #
            # Why catching warnings? All the meaningful warnings
            # have been produces during the first attempt.
            # Now, when we defaulted all the missing fields with None,
            # tyro produces 'UserWarning: The field (...) but the default value has type <class 'str'>.'
            # (This is not true anymore; to support pydantic we put a default value of the type,
            # so there is probably no more warning to be caught.)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                try:
                    env = cli(env, args=subargs, **kwargs)
                except AssertionError:
                    # Since it is a labyrinth of subcommands, required flags and positional arguments,
                    # and something is messed up, raise the original tyro message.
                    # When the user fulfills the error message,
                    # the program will still work (even without our UI wizzard).
                    raise reraise()

                # register all wrong fields to the object
                # so that the object updated automatically while the wrong field is set
                for f in wf.values():
                    f._src_obj = env
                return env, wf

        # Parsing wrong fields failed. The program ends with a nice tyro message.
        raise


def identify_required(parser: ArgumentParser, arg: str) -> None | Action:
    """
    Identifies the original field_name as it was edited by tyro.

    See the [mininterface.cli.SubcommandPlaceholder] for CLI expectation.
    """
    if arg.startswith("{"):
        # we should never come here, as treating missing subcommand should be treated by run/start.choose_subcommand
        return
    try:
        argument: Action = next(iter(p for p in parser._actions if arg in p.option_strings))
    except:
        # missing subcommand flag not implemented (correction: might be implemented and we never come here anymore)
        return
    argument.default = "DEFAULT"  # NOTE I do not know whether used
    if "." in argument.dest:
        # missing nested required argument handler not implemented, we let the CLI fail
        # (with a graceful message from tyro)
        return
    else:
        return argument


def argument_to_field_name(env_class: EnvClass, argument: Action):
    # get the original attribute name (argparse uses dash instead of underscores)
    # Why using mro? Find the field in the dataclass and all of its parents.
    # Useful when handling subcommands, they share a common field.
    field_name = argument.dest
    if not any(field_name in ann for ann in yield_annotations(env_class)):
        field_name = field_name.replace("-", "_")
    if not any(field_name in ann for ann in yield_annotations(env_class)):
        raise ValueError(f"Cannot find {field_name} in the configuration object")
    return field_name


def register_wrong_field(env_class: EnvClass, kwargs: dict,  wf: dict, argument: Action, exception: BaseException, eavesdrop):
    """ The field is missing.
    We prepare it to the list of wrong fields to be filled up
    and make a temporary default value so that tyro will not fail.
    """
    field_name = argument_to_field_name(env_class, argument)
    # NOTE: We put MissingTagValue to the UI to clearly state that the value is missing.
    # However, the UI then is not able to use ex. the number filtering capabilities.
    # Putting there None is not a good idea as dataclass_to_tagdict fails if None is not allowed by the annotation.
    tag = wf[field_name] = tag_factory(MissingTagValue(exception, eavesdrop),
                                       (argument.help or "").replace("(required)", ""),
                                       validation=not_empty,
                                       _src_class=env_class,
                                       _src_key=field_name
                                       )
    # Why `_make_default_value`? We need to put a default value so that the parsing will not fail.
    # A None would be enough because Mininterface will ask for the missing values
    # promply, however, Pydantic model would fail.
    # As it serves only for tyro parsing and the field is marked wrong, the made up value is never used or seen.
    set_default(kwargs, field_name, tag._make_default_value())


def _fetch_eavesdrop_args():
    return eavesdrop.partition(":")[2].strip().split(", ")


def set_default(kwargs, field_name, val):
    if "default" not in kwargs:
        kwargs["default"] = SimpleNamespace()
    setattr(kwargs["default"], field_name, val)


def parse_config_file(env_or_list: Type[EnvClass] | list[Type[EnvClass]],
                      config_file: Path | None = None,
                      settings: Optional[MininterfaceSettings] = None,
                      **kwargs) -> tuple[dict, MininterfaceSettings | None]:
    """ Fetches the config file into the program defaults kwargs["default"] and UI settings.

    Args:
        env_class: Class with the configuration.
        config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
        settings: Used to complement the 'mininterface' config file section-
    Kwargs:
        The same as for argparse.ArgumentParser.

    Returns:
        Tuple of kwargs and settings.
    """
    if isinstance(env_or_list, list):
        subcommands, env = env_or_list, None
    else:
        subcommands, env = None, env_or_list

    # Load config file
    if config_file and subcommands:
        # Reading config files when using subcommands is not implemented.
        kwargs.pop("default", None)
        warnings.warn(f"Config file {config_file} is ignored because subcommands are used."
                      " It is not easy to set how this should work."
                      " Describe the developer your usecase so that they might implement this.")

    if "default" not in kwargs and not subcommands and config_file:
        # Undocumented feature. User put a namespace into kwargs["default"]
        # that already serves for defaults. We do not fetch defaults yet from a config file.
        disk = yaml.safe_load(config_file.read_text()) or {}  # empty file is ok
        if confopt := disk.pop("mininterface", None):
            # Section 'mininterface' in the config file.
            settings = _merge_settings(settings, confopt)

        kwargs["default"] = _create_with_missing(env, disk)

    return kwargs, settings


def _merge_settings(runopt: MininterfaceSettings | None, confopt: dict, _def_fact=MininterfaceSettings) -> MininterfaceSettings:
    # Settings inheritance:
    # Config file > program-given through run(settings=) > the default settings (original dataclasses)

    # Assure the default settings
    # Either the program-given or create fresh defaults
    if runopt:
        # Merge the program-given settings to the config file settings if not yet present.
        confopt = merge_dicts(dataclass_asdict_no_defaults(runopt), confopt)
    else:
        runopt = _def_fact()

    # Merge option sections.
    # Ex: TextSettings will derive from both Tui and Ui. You may specify a Tui default value, common for all Tui interfaces.
    for sources in [("ui", "gui"),
                    ("ui", "tui"),
                    ("ui", "tui", "textual"),
                    ("ui", "tui", "text"),
                    ("ui", "tui", "textual", "web"),
                    ]:
        target = sources[-1]
        confopt[target] = {**{k: v for s in sources for k, v in confopt.get(s, {}).items()}, **confopt.get(target, {})}

    for key, value in vars(_create_with_missing(_def_fact, confopt)).items():
        if value is not MISSING_NONPROP:
            setattr(runopt, key, value)
    return runopt


def _unwrap_annotated(tp):
    """
    Annotated[Inner, ...] -> `Inner`,
    """
    if get_origin(tp) is Annotated:
        inner, *_ = get_args(tp)
        return inner
    return tp


def _create_with_missing(env, disk: dict):
    """
    Create a default instance of an Env object. This is due to provent tyro to spawn warnings about missing fields.
    Nested dataclasses have to be properly initialized. YAML gave them as dicts only.

    The result contains MISSING_NONPROP on the places the original Env object must have a value.
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
        m = _process_pydantic
    elif attr and attr.has(env):
        m = _process_attr
    else:  # dataclass
        m = _process_dataclass

    # Fill default fields with the config file values or leave the defaults.
    # Unfortunately, we have to fill the defaults, we cannot leave them empty
    # as the default value takes the precedence over the hard coded one, even if missing.
    out = {}
    for name, v in m(env, disk):
        out[name] = v
        disk.pop(name, None)

    # Check for unknown fields
    if disk:
        warnings.warn(f"Unknown fields in the configuration file: {', '.join(disk)}")

    # Safely initialize the model
    return env(**out)


def _process_pydantic(env, disk):
    for name, f in env.model_fields.items():
        if name in disk:
            if isinstance(f.default, BaseModel):
                v = _create_with_missing(f.default.__class__, disk[name])
            else:
                v = disk[name]
        elif f.default is not None:
            v = f.default
        yield name, v


def _process_attr(env, disk):
    for f in attr.fields(env):
        if f.name in disk:
            if attr.has(f.default):
                v = _create_with_missing(f.default.__class__, disk[f.name])
            else:
                v = disk[f.name]
        elif f.default is not attr.NOTHING:
            v = f.default
        else:
            v = MISSING_NONPROP
        yield f.name, v


def _process_dataclass(env, disk):
    for f in fields(_unwrap_annotated(env)):
        if f.name.startswith("__"):
            continue
        elif f.name in disk:
            if is_dataclass(_unwrap_annotated(f.type)):
                v = _create_with_missing(f.type, disk[f.name])
            else:
                v = disk[f.name]
        elif f.default_factory is not MISSING:
            v = f.default_factory()
        elif f.default is not MISSING:
            v = f.default
        else:
            v = MISSING_NONPROP
        yield f.name, v


def parser_to_dataclass(parser: ArgumentParser, name: str = "Args") -> DataClass:
    """ Note that in contrast to the argparse, we create default values.
    When an optional flag is not used, argparse put None, we have a default value.

    This does make sense for most values and should not pose problems for truthy-values.
    Ex. checking `if namespace.my_int` still returns False for both argparse-None and our-0.

    Be aware that for Path this might pose a big difference:
    parser.add_argument("--path", type=Path) -> becomes Path('.'), not None!
    """
    subparser_fields: list[tuple[str, type]] = []
    normal_fields: list[tuple[str, type, Field]] = []
    pos_fields: list[tuple[str, type, Field]] = []

    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue

        if isinstance(action, argparse._SubParsersAction):
            for subname, subparser in action.choices.items():
                sub_dc = parser_to_dataclass(subparser, name=subname.capitalize())
                subparser_fields.append((subname, sub_dc))  # required, no default
            continue

        opt = {}
        if isinstance(action, argparse._AppendAction):
            arg_type = list[action.type or str]
            opt["default_factory"] = list
        else:
            if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
                arg_type = bool
            elif isinstance(action, argparse._StoreConstAction):
                arg_type = type(action.const)
            elif isinstance(action, argparse._CountAction):
                arg_type = int
            else:
                arg_type = action.type or str
                if action.default is None:
                    # parser.add_argument("--path", type=Path) -> becomes Path('.'), not None!
                    # By default, argparse put None if not used in the CLI.
                    # Which makes tyro output the warning: annotated with type `<class 'str'>`, but the default value `None`
                    # We either make None an option by `arg_type |= None`
                    # or else we default the value.
                    # This creates a slightly different behaviour, however, the behaviour is slightly different
                    # nevertheless.
                    # Ex. parser.add_argument("--time", type=time) -> does work poorly in argparse.
                    action.default = Tag(annotation=arg_type)._make_default_value()
            opt["default"] = action.default if action.default != argparse.SUPPRESS else None

        # build a dataclass field, either optional, or positional
        met = {"metadata": {"help": action.help}}
        if action.option_strings:
            normal_fields.append((action.dest, arg_type, field(**opt, **met)))
        else:
            pos_fields.append((action.dest, Positional[arg_type], field(**met)))

    return make_dataclass(name, subparser_fields + pos_fields + normal_fields)


def to_kebab_case(name: str) -> str:
    """ MyClass -> my-class """
    # I did not find where tyro does it. If I find it, I might use its function instead.
    return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
