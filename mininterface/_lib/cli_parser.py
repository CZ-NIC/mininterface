#
# CLI and config file parsing.
#
import re
import sys
import warnings
from collections import deque
from contextlib import ExitStack
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import (Annotated, Callable, Optional, Sequence, Type, Union,
                    get_args, get_origin)
from unittest.mock import patch

from ..exceptions import Cancelled
from ..settings import MininterfaceSettings
from ..tag import Tag
from .auxiliary import (dataclass_asdict_no_defaults, get_nested_class,
                        get_or_create_parent_dict, merge_dicts,
                        remove_empty_dicts)
from .dataclass_creation import (ChosenSubcommand, choose_subcommand,
                                 create_with_missing)
from .form_dict import EnvClass

try:
    import yaml
    from tyro import cli
    from tyro._argparse import _SubParsersAction
    from tyro._argparse_formatter import TyroArgumentParser
    from tyro._singleton import MISSING_NONPROP

    from .tyro_patches import (_crawling, custom_error, custom_init,
                               custom_parse_known_args, failed_fields,
                               patched_parse_known_args, subparser_call)
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")


WrongFields = dict[str, Tag]


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


def parse_cli(
    env_or_list: Type[EnvClass] | list[Type[EnvClass]],
    kwargs: dict,
    add_verbose: bool = True,
    ask_for_missing: bool = True,
    args: Optional[Sequence[str]] = None,
    # as getting the interface is a costly operation and it is not always needed, we can wrap it in a lambda
    m: "Mininterface" | Callable[[], "Mininterface"] | None = None,
    _crawled=None,
    _wf=None,
) -> tuple[EnvClass, bool]:
    """Run the tyro parser to fetch program configuration from CLI

    Returns:
        EnvClass
        bool: True if there were some wrong field the user dealed with.
    """
    # NOTE ask_on_empty_cli might reveal all fields (in cli_parser), not just wrongs. Eg. when using a subparser `$ prog run`, reveal all subparsers.

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

    patches.append(patch.object(_SubParsersAction, "__call__", subparser_call))  # TODO
    patches.append(patch.object(TyroArgumentParser, "_parse_known_args", patched_parse_known_args))

    if ask_for_missing:  # Get the missing flags from the parser
        patches.append(patch.object(TyroArgumentParser, "error", custom_error))
    if add_verbose:  # Mock parser to add verbosity
        # The verbose flag is added only if neither the env_class nor any of the subcommands have the verbose flag already
        if all("verbose" not in cl.__annotations__ for cl in env_classes):
            patches.extend(
                (
                    patch.object(TyroArgumentParser, "__init__", custom_init),
                    patch.object(
                        TyroArgumentParser,
                        "parse_known_args",
                        custom_parse_known_args,
                    ),
                )
            )

    # Run the parser, with the mocks
    failed_fields.set([])
    _crawling.set(deque())
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
            return res, False
    except BaseException as exception:
        if ask_for_missing and getattr(exception, "code", None) == 2 and failed_fields.get():
            # Some required arguments are missing. Determine which.
            wf: dict[str, Tag] = _wf or {}
            _wf = wf

            # # There are multiple dataclasses, query which is chosen
            env = None
            if len(env_classes) == 1:
                env = env_classes[0]
                # parser: ArgumentParser = get_parser(type_form, **kwargs)
                # subargs = args
            elif len(args):
                env = next(
                    (env for env in env_classes if to_kebab_case(env.__name__) == args[0]),
                    None,
                )
                if env:
                    # parser: ArgumentParser = get_parser(env)
                    # subargs = args[1:]
                    _crawling.get().popleft()
            elif len(env_classes):
                m = assure_m(m)
                env = choose_subcommand(env_classes, m)
            if not env:
                raise NotImplementedError("This case of nested dataclasses is not implemented. Raise an issue please.")

            if _crawled is None:
                # This is the first correction attempt.
                # We create default instance etc.
                # It may fail for another reasons, ex. a super-parser claim:
                # 1. run inserts: `$ prog.py run message` ->  `$ prog.py run message MSG` (resolved 'message' subparser)
                # 2. run inserts: `$ prog.py run message MSG RUN-ID`. (resolved 'run' subparser)
                # So in further run, there is no need to rebuild the data. We just process new failed_fields reported by tyro.
                disk = d = kwargs.get("default", {})
                _crawled = [None]
                for _, val, field_name in _crawling.get():
                    # NOTE this might be ameliorated so that config file can define subcommands too, now we throw everything out
                    subd = {}
                    d[field_name] = ChosenSubcommand(val, subd)
                    d = subd
                    _crawled.append(val)
                m = assure_m(m)

                defaulted_class = create_with_missing(env, disk, wf, m)
                kwargs["default"] = defaulted_class

            wfi = {}
            for field in failed_fields.get():
                # ex: `_subcommands._nested_subcommands (positional)`
                fname = field.dest.replace(" (positional)", "").replace("-", "_")  # `_subcommands._nested_subcommands`
                fname_raw = fname.rsplit(".", 1)[-1]  # `_nested_subcommands`

                if isinstance(field, _SubParsersAction):
                    # The function _create_with_missing don't makes every encountered field a wrong field
                    # (with the exception of the config fields, defined in the kwargs["default"] earlier).
                    # The CLI options are unknown to it.
                    # Here, we pick the field unknown to the CLI parser too.
                    # As whole subparser was unknown here, we safely consider all its fields wrong fields.
                    if fname:
                        wfi_ = get_or_create_parent_dict(wf, fname)
                        if wfi_:
                            # there might not be any wrong fields in the subparsers,
                            # empty dict would raise an empty form
                            wfi[fname_raw] = wfi_
                    else:
                        # This is the default subparser, without a field name:
                        # ex. `run([List, Run])`
                        wfi[""] = wf
                else:
                    wfi_ = get_or_create_parent_dict(wf, fname, True)
                    tag = wfi[fname_raw] = wfi_[fname_raw]
                    tag._src_obj = get_nested_class(kwargs["default"], fname, True)

            # Ask for the wrong fields

            # We might have added a subsection with no fields in _create_with_missing,
            # remove them so that no empty subgroup is displayed
            remove_empty_dicts(wfi)
            if wfi:
                try:
                    m.form(wfi)
                except Cancelled as e:
                    raise
                except SystemExit as e:
                    # Form did not work, cancelled or run through minadaptor.
                    # We use the original tyro exception message, caught in tyro_patches.custom_error
                    # instead of a validation error the minadaptor might produce.
                    # NOTE We might add minadaptor validation error. But it seems too similar to the better tyro's one.
                    # if str(e):
                    #     exception.add_note(str(e))
                    raise SystemExit("\n".join(exception.__notes__))

            env_, _ = parse_cli(env_classes, kwargs, add_verbose, ask_for_missing, args, m, _crawled, _wf)
            return env_, True

            # # Second attempt to parse CLI.
            # # We have just put a default values for missing fields so that tyro will not fail.
            # # If we succeeded (no exotic case), this will pass through.
            # # Then, we impose the user to fill the missing values.
            # #
            # # Why catching warnings? All the meaningful warnings
            # # have been produces during the first attempt.
            # # Now, when we defaulted all the missing fields with None,
            # # tyro produces 'UserWarning: The field (...) but the default value has type <class 'str'>.'
            # # (This is not true anymore; to support pydantic we put a default value of the type,
            # # so there is probably no more warning to be caught.)
            # with warnings.catch_warnings():
            #     warnings.simplefilter("ignore")
            #     try:
            #         env = cli(env, args=subargs, **kwargs)
            #     except AssertionError:
            #         # Since it is a labyrinth of subcommands, required flags and positional arguments,
            #         # and something is messed up, raise the original tyro message.
            #         # When the user fulfills the error message,
            #         # the program will still work (even without our UI wizzard).
            #         raise reraise()
            #     return env, bool(wfi)

        # Parsing wrong fields failed. The program ends with a nice tyro message.
        raise


# NOTE Remove when we are sure this is not needed, see test_run_message_args comment.
# def register_wrong_field(
#     env_class: EnvClass,
#     kwargs: dict,
#     wf: dict,
#     argument: Action,
#     exception: BaseException,
#     eavesdrop,
# ):
#     """The field is missing.
#     We prepare it to the list of wrong fields to be filled up
#     and make a temporary default value so that tyro will not fail.
#     """
#     field_name = argument_to_field_name(env_class, argument)
#     # NOTE: We put MissingTagValue to the UI to clearly state that the value is missing.
#     # However, the UI then is not able to use ex. the number filtering capabilities.
#     # Putting there None is not a good idea as dataclass_to_tagdict fails if None is not allowed by the annotation.
#     tag = wf[field_name] = _get_wrong_field(env_class, argument, exception, eavesdrop, field_name)
#     # Why `_make_default_value`? We need to put a default value so that the parsing will not fail.
#     # A None would be enough because Mininterface will ask for the missing values
#     # promply, however, Pydantic model would fail.
#     # As it serves only for tyro parsing and the field is marked wrong, the made up value is never used or seen.
#     set_default(kwargs, field_name, tag._make_default_value())


def set_default(kwargs, field_name, val):
    if "default" not in kwargs:
        kwargs["default"] = SimpleNamespace()
    setattr(kwargs["default"], field_name, val)


def parse_config_file(
    env_or_list: Type[EnvClass] | list[Type[EnvClass]],
    config_file: Path | None = None,
    settings: Optional[MininterfaceSettings] = None,
    **kwargs,
) -> tuple[dict, MininterfaceSettings | None]:
    """Fetches the config file into the program defaults kwargs["default"] and UI settings.

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
        warnings.warn(
            f"Config file {config_file} is ignored because subcommands are used."
            " It is not easy to set how this should work."
            " Describe the developer your usecase so that they might implement this."
        )

    if "default" not in kwargs and not subcommands and config_file:
        # Undocumented feature. User put a namespace into kwargs["default"]
        # that already serves for defaults. We do not fetch defaults yet from a config file.
        disk = yaml.safe_load(config_file.read_text()) or {}  # empty file is ok
        try:
            if confopt := disk.pop("mininterface", None):
                # Section 'mininterface' in the config file.
                settings = _merge_settings(settings, confopt)

            kwargs["default"] = create_with_missing(env, disk)
        except TypeError:
            raise SyntaxError(f"Config file parsing failed for {config_file}")

    return kwargs, settings


def _merge_settings(
    runopt: MininterfaceSettings | None, confopt: dict, _def_fact=MininterfaceSettings
) -> MininterfaceSettings:
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
    for sources in [
        ("ui", "gui"),
        ("ui", "tui"),
        ("ui", "tui", "textual"),
        ("ui", "tui", "text"),
        ("ui", "tui", "textual", "web"),
    ]:
        target = sources[-1]
        confopt[target] = {
            **{k: v for s in sources for k, v in confopt.get(s, {}).items()},
            **confopt.get(target, {}),
        }

    for key, value in vars(create_with_missing(_def_fact, confopt)).items():
        if value is not MISSING_NONPROP:
            setattr(runopt, key, value)
    return runopt


def to_kebab_case(name: str) -> str:
    """MyClass -> my-class"""
    # I did not find where tyro does it. If I find it, I might use its function instead.
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def assure_m(m) -> "Mininterface":
    if isinstance(m, FunctionType):
        m = m()
    elif not m:  # we should never come here
        raise ValueError("Interface missing so that I can choose a subcommand")
    return m
