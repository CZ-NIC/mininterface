"""Patches/hooks for the native tyro CLI parser backend (tyro >= 1.0.14).

mininterface needs to know which required fields/subcommands are missing from the CLI
so that it can ask for them in a dialog instead of letting the program die with
a parsing error. tyro exposes this through `tyro._errors.on_parse_error` (added in
1.0.14 from our PR #478), so we register one hook there. The one remaining
monkeypatch is `TyroBackend.parse_args`, which we wrap to inject CliFlags arguments
(`--verbose`, ...) into the ParserSpecification and to harvest the subcommand passage
(`_crawling`) from the backend output on success.
"""

import sys
from collections import deque
from contextvars import ContextVar

from tyro import _arguments
from tyro._backends._tyro_backend import TyroBackend
from tyro._errors import MissingArgs, MissingSubcommand, on_parse_error
from tyro._parsers import ArgWithContext, SubparsersSpecification

from .cli_flags import CliFlags

failed_fields: ContextVar["list[ArgWithContext | SubparsersSpecification]"] = ContextVar(
    "failed_fields", default=[]
)
""" Required fields/subcommands the last parse found missing from the CLI. """

_crawling: ContextVar[deque] = ContextVar("_crawling", default=deque())
""" The subcommand passage: (chosen_name, field_name) tuples in selection order. """


def _harvest_crawl(output: dict, args=None) -> None:
    """Reconstruct the subcommand passage from the backend's output dict.

    Subparser selections are stored under keys like `'_subcommands._nested (positional)': 'run'`,
    in selection order. When `args` is given (the success path), default
    (not CLI-given) subcommands are filtered out by requiring the chosen name to
    be present in args – mininterface counts explicit selections only (ex. for
    the empty-CLI detection). On the error path `args` is None: the partial output
    holds only what was consumed from the CLI so far, so nothing needs filtering.
    """
    crawl = _crawling.get()
    crawl.clear()
    for key, val in output.items():
        if key.endswith(" (positional)") and isinstance(val, str):
            field_name = key[: -len(" (positional)")].rsplit(".", 1)[-1]
            if args is None or val in args:
                crawl.append((val, field_name))


def _raise_missing(message: str):
    """Raise a bare SystemExit(2) with the tyro message kept as a note.
    The note is used when the raised dialog cannot help (ex. the min interface)."""
    exc = SystemExit(2)
    if sys.version_info >= (3, 11):
        exc.add_note(message)
    raise exc


def missing_fields_hook(ask_for_missing: bool):
    """Register a tyro parse-error hook that records the missing required
    fields/subcommands (into failed_fields) and reconstructs the subcommand
    passage (_crawling) from the event's partial parse state.

    When ask_for_missing, we raise SystemExit(2) right away – caught by parse_cli
    to raise the dialog. Otherwise we return None and let tyro render its standard
    error. Returns the `on_parse_error` context manager to enter."""

    def hook(event):
        if isinstance(event, MissingArgs):
            failed_fields.get().extend(event.missing_arguments)
            _harvest_crawl(event.partial_output)
            if ask_for_missing:
                _raise_missing(
                    "the following arguments are required: "
                    + ", ".join(a.arg.lowered.name_or_flags[-1] for a in event.missing_arguments)
                )
        elif isinstance(event, MissingSubcommand) and ask_for_missing:
            failed_fields.get().append(event.subcommand_spec)
            _harvest_crawl(event.partial_output)
            _raise_missing(
                "the following arguments are required: {" + ",".join(event.subcommand_spec.parser_from_name) + "}"
            )

    return on_parse_error(hook)


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
