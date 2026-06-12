"""Mocking patches for the native tyro CLI parser backend (tyro >= 1.0).

mininterface needs to know which required fields/subcommands are missing from the CLI
so that it can ask for them in a dialog instead of letting the program die with
a parsing error. Tyro has no official hook for that, hence we monkeypatch three
choke points:

* _tyro_help_formatting.required_args_error – fires with the list of missing ArgWithContext
* _tyro_help_formatting.error_and_exit – fires on "Missing subcommand" (we pick the
  SubparsersSpecification from the caller frame)
* TyroBackend.parse_args – lets us inject CliFlags arguments into the ParserSpecification
  and harvest the subcommand passage (_crawling) from the backend's output dict

NOTE A PR to tyro adding an official missing-fields hook would make
the first two patches disappear.
"""

import sys
from collections import deque
from contextvars import ContextVar

from tyro import _arguments
from tyro._backends import _tyro_help_formatting
from tyro._backends._tyro_backend import TyroBackend
from tyro._parsers import ArgWithContext, SubparsersSpecification

from .cli_flags import CliFlags

failed_fields: ContextVar["list[ArgWithContext | SubparsersSpecification]"] = ContextVar(
    "failed_fields", default=[]
)
""" Required fields/subcommands the last parse found missing from the CLI. """

_crawling: ContextVar[deque] = ContextVar("_crawling", default=deque())
""" The subcommand passage: (chosen_name, field_name) tuples in selection order. """


def _harvest_crawl(output: dict, args) -> None:
    """Reconstruct the subcommand passage from the backend's output dict.

    Subparser selections are stored under keys like `'_subcommands._nested (positional)': 'run'`,
    in selection order. Default (not CLI-given) subcommands are filtered out
    by requiring the chosen name to be present in args – mininterface counts
    explicit selections only (ex. for the empty-CLI detection).
    """
    crawl = _crawling.get()
    crawl.clear()
    for key, val in output.items():
        if key.endswith(" (positional)") and isinstance(val, str):
            field_name = key[: -len(" (positional)")].rsplit(".", 1)[-1]
            if args is None or val in args:
                crawl.append((val, field_name))


def _harvest_crawl_from_frame() -> None:
    """On parsing failure, the output dict lives in a frame of TyroBackend._parse_args_recursive."""
    f = sys._getframe(2)
    while f is not None and "output" not in f.f_locals:
        f = f.f_back
    if f is not None:
        _harvest_crawl(f.f_locals["output"], f.f_locals.get("args"))


def tyro_required_args_error(ask_for_missing: bool):
    """Collect missing required arguments (ArgWithContext) into failed_fields,
    then raise a bare SystemExit(2) with the message attached as a note.
    The note is used when the raised dialog cannot help (ex. min interface)."""
    orig = _tyro_help_formatting.required_args_error

    def _(prog, required_args, unrecognized_args_and_progs, console_outputs, add_help):
        failed_fields.get().extend(required_args)
        _harvest_crawl_from_frame()
        if not ask_for_missing:
            return orig(
                prog=prog,
                required_args=required_args,
                unrecognized_args_and_progs=unrecognized_args_and_progs,
                console_outputs=console_outputs,
                add_help=add_help,
            )
        message = "the following arguments are required: " + ", ".join(
            a.arg.lowered.name_or_flags[-1] for a in required_args
        )
        exc = SystemExit(2)
        if sys.version_info >= (3, 11):
            exc.add_note(message)
        raise exc

    return _


def tyro_error_and_exit(ask_for_missing: bool):
    """Catch the "Missing subcommand" error: collect the failed SubparsersSpecification
    (found in the caller frame) so that a subcommand-chooser dialog can be raised."""
    orig = _tyro_help_formatting.error_and_exit

    def _(title, *contents, prog, console_outputs, add_help):
        if ask_for_missing and title == "Missing subcommand":
            f = sys._getframe(1)
            spec = f.f_locals.get("subparser_spec")
            if spec is not None:
                failed_fields.get().append(spec)
                _harvest_crawl(f.f_locals.get("output", {}), f.f_locals.get("args"))
                message = "the following arguments are required: {" + ",".join(spec.parser_from_name) + "}"
                exc = SystemExit(2)
                if sys.version_info >= (3, 11):
                    exc.add_note(message)
                raise exc
        return orig(title, *contents, prog=prog, console_outputs=console_outputs, add_help=add_help)

    return _


def _expand_abbrevs(parser_spec, args):
    """argparse's allow_abbrev: expand an unambiguous flag prefix (--im → --important-number).
    NOTE Only the root parser flags are taken into account; flags of (lazily evaluated)
    subparsers are not expanded."""
    flags = set()
    for arg_ctx in parser_spec.get_args_including_children():
        if not arg_ctx.arg.is_positional():
            flags.update(arg_ctx.arg.lowered.name_or_flags)
    out = []
    args_iter = iter(args)
    for token in args_iter:
        if token == "--":  # end-of-options marker
            out.append(token)
            out.extend(args_iter)
            break
        if token.startswith("--") and len(token) > 2:
            key, eq, val = token.partition("=")
            if key not in flags:
                matches = [f for f in flags if f.startswith(key)]
                if len(matches) == 1:
                    token = matches[0] + eq + val
        out.append(token)
    return out


def tyro_parse_args(cf: "CliFlags | None", allow_abbrev=False):
    """Wrap TyroBackend.parse_args:
    * inject CliFlags arguments (--verbose, --quiet, ...) into the ParserSpecification
    * handle --version early (like the argparse version action, before required-args checks)
    * expand abbreviated flags when the argparse-compatible allow_abbrev is requested
    * on success, harvest the subcommand passage and consume the CliFlags outputs
    """
    orig = TyroBackend.parse_args

    def _(self, parser_spec, args, prog, return_unknown_args, console_outputs, add_help, compact_help=False):
        if cf:
            cf.setup()
            if cf.add_version and "--version" in args:
                print(cf.version)
                raise SystemExit(0)
            for field in reversed(cf.field_list):
                # intern_prefix must stay empty: lowered.dest = make_field_name([intern_prefix, intern_name])
                parser_spec.args.insert(
                    0,
                    _arguments.ArgumentDefinition(
                        intern_prefix="",
                        extern_prefix="",
                        subcommand_prefix="",
                        field=field,
                    ),
                )
        if allow_abbrev:
            args = _expand_abbrevs(parser_spec, args)
        out, unknown = orig(self, parser_spec, args, prog, return_unknown_args, console_outputs, add_help, compact_help)
        _harvest_crawl(out, args)
        if cf:
            cf.consume_output(out)
        return out, unknown

    return _
