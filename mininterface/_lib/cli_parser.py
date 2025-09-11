#
# CLI and config file parsing.
#
from dataclasses import asdict
import sys
from collections import deque
from contextlib import ExitStack
from typing import Optional, Sequence, Type, Union
from unittest.mock import patch


from .cli_flags import CliFlags

from ..cli import Command

from ..exceptions import Cancelled
from .auxiliary import (
    get_or_create_parent_dict,
    remove_empty_dicts,
    flatten,
)
from .dataclass_creation import (
    ChosenSubcommand,
    _unwrap_annotated,
    choose_subcommand,
    create_with_missing,
    to_kebab_case,
)
from .form_dict import EnvClass, TagDict, dataclass_to_tagdict, MissingTagValue, dict_added_main

try:
    from tyro import cli
    from tyro._argparse import _SubParsersAction, ArgumentParser
    from tyro._argparse_formatter import TyroArgumentParser
    from tyro._singleton import MISSING_NONPROP

    from .tyro_patches import (
        _crawling,
        custom_error,
        custom_init,
        custom_parse_known_args,
        failed_fields,
        patched_parse_known_args,
        subparser_call,
        argparse_init,
    )
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")


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
    m: "Mininterface",
    cf: Optional[CliFlags] = None,
    ask_for_missing: bool = True,
    args: Optional[Sequence[str]] = None,
    ask_on_empty_cli: Optional[bool] = None,
    _crawled=None,
    _req_fields=None,
) -> tuple[EnvClass, bool]:
    """Run the tyro parser to fetch program configuration from CLI

    Returns:
        EnvClass
        bool: Dialog raised? True if there were some wrong field the user dealed with.
    """
    # Xint: The depth we crawled into. The number of subcommands in args.
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
        env_classes[i] = _unwrap_annotated(candidate)

    # Mock parser, inject special options into
    patches = _apply_patches(cf, ask_for_missing, env_classes, kwargs)

    # Run the parser, with the mocks
    failed_fields.set([])
    _crawling.set(deque())
    final_call = _crawled is None
    """ This is the upmost parse_cli call.
    See the `_crawled` creation comment to know how to simulate nested parse_cli calls.
    """

    # Special CLI parsing
    if sys.modules.get("mininterface.tag.flag") is not None:
        from ..tag.flag import _custom_registry
    else: # run only if the user imported the flags. (Untested) performance reasons.
        _custom_registry = None

    try:
        with ExitStack() as stack:
            [stack.enter_context(p) for p in patches]  # apply just the chosen mocks
            try:
                env = cli(type_form, args=args, registry=_custom_registry, **kwargs)
            except BaseException:
                # Why this exception handling? Try putting this out and test_strange_error_mitigation fails.
                if len(env_classes) > 1 and kwargs.get("default"):
                    env = cli(kwargs["default"].__class__, args=args[1:], registry=_custom_registry, **kwargs)
                else:
                    raise
            # Why setting m.env instead of putting into into a constructor of a new get_interface() call?
            # 1. Getting the interface is a costly operation
            # 2. There is this bug so that we need to use single interface:
            #    TODO
            #    As this works badly, lets make sure we use single interface now
            #    and will not need the second one.
            #    get_interface("gui")
            #    m = get_interface("gui")
            #    m.select([1,2,3])
            m.env = env
    except BaseException as exception:
        if ask_for_missing and getattr(exception, "code", None) == 2 and failed_fields.get():
            env = _dialog_missing(env_classes, kwargs, m, cf, ask_for_missing, args, _crawled, _req_fields)

            if final_call:
                # Ask for the wrong fields
                # Why first_attempt? We display the wrong-fields-form only once.
                _ensure_command_init(env, m)

                try:
                    m.form(env)
                except Cancelled as e:
                    raise
                except SystemExit as e:
                    if sys.version_info < (3, 11):
                        raise
                    # Form did not work, cancelled or run through minadaptor.
                    # We use the original tyro exception message, caught in tyro_patches.custom_error
                    # instead of a validation error the minadaptor might produce.
                    # NOTE We might add minadaptor validation error. But it seems too similar to the better tyro's one.
                    # if str(e):
                    #     exception.add_note(str(e))
                    raise SystemExit("\n".join(exception.__notes__))

            return env, True

        # Parsing wrong fields failed. The program ends with a nice tyro message.
        raise
    else:
        dialog_raised = False
        if final_call:
            _ensure_command_init(env, m)

            # Subsequent validation
            # Do a subsequent validation as tyro cannot validate ie. annotated_types or our custom validators.
            # (This is not needed when we raise a wrong-fields-dialog as any dialog validates everything.)
            dc = dataclass_to_tagdict(m.env)
            for tag in flatten(dc):
                try:
                    tag._validate(tag.val)
                except Exception as e:
                    tag.set_error_text(str(e))
                    m.form(dc)
                    dialog_raised = True

            # Empty CLI → GUI edit
            subcommand_count = len(_crawling.get())
            if not dialog_raised and ask_on_empty_cli and len(sys.argv) <= 1 + subcommand_count:
                # Raise a dialog if the command line is empty.
                # This still means empty because 'run' and 'message' are just subcommands: `program.py run message`
                m.form()
                dialog_raised = True

        return env, dialog_raised


def _apply_patches(cf: Optional[CliFlags], ask_for_missing, env_classes, kwargs):
    patches = []

    patches.append(patch.object(_SubParsersAction, "__call__", subparser_call))
    patches.append(patch.object(TyroArgumentParser, "_parse_known_args", patched_parse_known_args))

    kw = {
        k: v for k, v in kwargs.items() if k != "default"
    }  # NOTE I might separate kwargs['default'] and do not do this filtering
    if kw:
        patches.append(patch.object(ArgumentParser, "__init__", argparse_init(kw)))

    if ask_for_missing:  # Get the missing flags from the parser
        patches.append(patch.object(TyroArgumentParser, "error", custom_error))
    if cf and cf.should_add(env_classes):
        # Mock parser to add some flags
        # Flags are added only if neither the env_class nor any of the subcommands have the same-name flag already
        patches.extend(
            (
                patch.object(
                    TyroArgumentParser,
                    "__init__",
                    custom_init(cf),
                ),
                patch.object(
                    TyroArgumentParser,
                    "parse_known_args",
                    custom_parse_known_args(cf),
                ),
            )
        )

    return patches


def _dialog_missing(
    env_classes,
    kwargs: dict,
    m: "Mininterface",
    cf: Optional[CliFlags],
    ask_for_missing: bool,
    args: Optional[Sequence[str]],
    crawled,
    req_fields: Optional[TagDict],
) -> EnvClass:
    """Some required arguments are missing. Determine which and ask for them.

    * kwargs["default"]. Struct (dataclass). The fields that must be filled are marked as MISSING_NONPROP.
        If marked directly with `tag._make_default_value()`, tyro would resolve CLI instantly with no further problem but we would never known which were missing CLI flags were missing.
    * failed_fields – Argparse Actions. Parser needs them filled. (It might not tell us about all of them. There is a use-case when superparser is resolved after subparser. And if whole subparser command is missing, its fields are not there either.)
    * req_fields – Tags. The same form as kwargs["default"]. Recursively all fields, needed to build up a dataclass for mininterface. The fields that must be filled are marked as MissingTagValue().
    * missing_req – Tags. Those req_fields which are missing from CLI. Merge of failed_fields and req_fields. (Subset of req_fields.)
        Their values are `tag._make_default_value()`.
        The default value is never seen, it's used just to build up `env`. Might have the same form as req_fields or a subset when we parse a subcommand.
        After resolving the class, we use missing_req to reset the `env` fields to MissingTagValue() so that the user must fill them in a raised form.
        (SelectTag has no value, nor in CLI. We give it a random value, build the struct through tyro (which enriches the kwargs["default"] with the CLI fields), then we reset the value to MissingTagValue() so that the user must choose. In the form, we see the SelectTag with no default value selected.)
    * env – Tyro's merge of CLI and kwargs["default"].

    """
    req_fields = req_fields or {}

    # There are multiple dataclasses, query which is chosen
    m, env_cl = _ensure_chosen_env(env_classes, args, m)

    if crawled is None:
        # This is the first correction attempt.
        # We create default instance etc.
        # It may fail for another reasons, ex. a super-parser claim:
        # 1. run inserts: `$ prog.py run message` ->  `$ prog.py run message MSG` (resolved 'message' subparser)
        # 2. run inserts: `$ prog.py run message MSG RUN-ID`. (resolved 'run' subparser)
        # So in further run, there is no need to rebuild the data. We just process new failed_fields reported by tyro.

        # Merge with the config file defaults.
        disk = d = asdict(dc) if (dc := kwargs.get("default")) else {}
        crawled = [None]
        for _, val, field_name in _crawling.get():
            # NOTE this might be ameliorated so that config file can define subcommands too, now we throw everything out
            subd = {}
            d[field_name] = ChosenSubcommand(val, subd)
            d = subd
            crawled.append(val)

        kwargs["default"] = create_with_missing(env_cl, disk, req_fields, m)

    missing_req = _fetch_currently_failed(req_fields)
    """ Fields required and missing from CLI """

    # These fields are known to be missing in the CLI.
    # Adds a temporary default value to the fields in the default_dataclass
    # so that tyro can join the rest from CLI.
    # Why we make a default values instead of putting None?
    # It would be good as Mininterface will ask for it as a missing value if None is not allowed by the field.
    # However, tyro produces 'UserWarning: The field (...) but the default value has type <class 'str'>.'
    # And pydantic model would fail.
    # As it serves only for tyro parsing and the field is marked wrong, the temporarily made up value is never used or seen.
    for tag in flatten(missing_req):
        tag._update_source(tag._make_default_value())

    # Merge CLI args with the defaults (and the temporary defaults)
    # Second attempt to parse CLI.
    # We have just put a default values for missing fields so that tyro will not fail.
    # If we succeeded (no exotic case), this will pass through.
    # Then, we impose the user to fill the missing values.
    env, _ = parse_cli(env_classes, kwargs, m, cf, ask_for_missing, args, None, crawled, req_fields)
    td = dataclass_to_tagdict(env, m)
    # Remove teporary defaults to be correctly displayed in the dialog form
    # so that user must fill them.
    _reset_missing_fields(td, missing_req)

    return env


def _ensure_chosen_env(env_classes, args, m):
    env = None
    if len(env_classes) == 1:
        env = env_classes[0]
    elif len(args):
        env = next(
            (env for env in env_classes if to_kebab_case(env.__name__) == args[0]),
            None,
        )
        if env:
            _crawling.get().popleft()
    elif len(env_classes):
        env = choose_subcommand(env_classes, m)
    if not env:
        raise NotImplementedError("This case of nested dataclasses is not implemented. Raise an issue please.")
    return m, env


def _fetch_currently_failed(requireds) -> TagDict:
    """Get missings.
    We get all fields from the dataclass and choose only those
    who pose problem for tyro (through implanted failed_fields)."""
    missing_req = {}
    for field in failed_fields.get():
        # ex: `_subcommands._nested_subcommands (positional)`
        fname = field.dest.replace(" (positional)", "").replace("-", "_")  # `_subcommands._nested_subcommands`
        fname_raw = fname.rsplit(".", 1)[-1]  # `_nested_subcommands`

        if isinstance(field, _SubParsersAction):
            # The function create_with_missing don't makes every encountered field a wrong field
            # (with the exception of the config fields, defined in the kwargs["default"] earlier).
            # The CLI options are unknown to it.
            # Here, we pick the field unknown to the CLI parser too.
            # As whole subparser was unknown here, we safely consider all its fields wrong fields.
            if fname:
                get_or_create_parent_dict(missing_req, fname, True)[fname_raw] = get_or_create_parent_dict(requireds, fname)
            else:
                # This is the default subparser, without a field name:
                # ex. `run([List, Run])`
                # Convert
                # {'bot_id': 'a', '_subcommands': {'my_int': 1}}
                #   into
                # {'': {'bot_id': 'a'}, {'_subcommands': {'my_int': 1}}}
                missing_req[""] = {}
                for k, v in requireds.items():
                    if isinstance(v, dict):
                        missing_req[k] = v
                    else:
                        missing_req[""][k] = v
        else:
            get_or_create_parent_dict(missing_req, fname, True)[fname_raw] = get_or_create_parent_dict(
                requireds, fname, True
            )[fname_raw]

    # We might have added a subsection with no fields in create_with_missing,
    # remove them so that no empty subgroup is displayed
    remove_empty_dicts(missing_req)

    # modify out to the same form as env_ derived tagdict
    # (adds the main "" section)
    return dict_added_main(missing_req)


def _reset_missing_fields(td: TagDict, missing_req: TagDict):
    """Those fields were given a temporary default value so that tyro
    can recover and join the rest of the CLI fields.
    Now, it's time to reset them so that in a dialog form,
    these fields are not pre-filled. (Ex. SelectTag must not have a chosen default.)
    """
    for key, val in missing_req.items():
        if isinstance(val, dict):
            _reset_missing_fields(td[key], val)
        else:
            tag = td[key]
            # Why we don't put None here? The only difference is
            # that when we use the bare Mininterface, val=MISSING is output instead of val=None
            # which is more meaningful.
            tag._set_val(MissingTagValue())
            # NOTE See the comment test_subcommands.Message.msg:
            # Even though this field is optional, tyro finds it as required
            # and we mark it as required when handling failed fields.
            # But if left empty, nothing happens.
            # If needed, we might detect whether it is optional and do not
            # mark it required.
            tag.set_error_text()


def _ensure_command_init(env: EnvClass, m: "Miniterface"):
    if isinstance(env, Command):
        # If dialog was raised in parse_cli, we are sure the init has been already called.
        env.facet = m.facet
        env.interface = m

        # Undocumented as I'm not sure whether I can recommend it or there might be a better design.
        # Init is launched before tagdict creation so that it can modify class __annotation__.
        env.init()
