"""Various mocking patches."""

import logging
from collections import deque
from contextvars import ContextVar
from gettext import gettext as _
import sys
from typing import Optional, Callable

from tyro import _argparse as argparse
from tyro._argparse import Action, _SubParsersAction, ArgumentParser
from tyro._argparse_formatter import TyroArgumentParser

from .cli_flags import CliFlags

failed_fields: ContextVar[list[Action]] = ContextVar("failed_fields", default=[])
_orig_call = _SubParsersAction.__call__
_crawling = ContextVar("_crawling", default=deque())

_orig_init = ArgumentParser.__init__


# NOTE This function is too long to monkeypatch. I'd be great we do a PR to tyro
# so that it refactors to a smaller method it would be easier to monkeypatch & maintain.
#
# The only line changed: failed_fields
#
def patched_parse_known_args(self, arg_strings, namespace):  # type: ignore  # pragma: no cover
    """We override _parse_known_args() to improve error messages in the presence of
    subcommands. Difference is marked with <new>...</new> below."""

    # <new>
    # Reset the unused argument list in the root parser.
    # Subparsers will have spaces in self.prog.
    if " " not in self.prog:
        global global_unrecognized_arg_and_prog
        global_unrecognized_arg_and_prog = []
    # </new>

    # replace arg strings that are file references
    if self.fromfile_prefix_chars is not None:
        arg_strings = self._read_args_from_files(arg_strings)

    # map all mutually exclusive arguments to the other arguments
    # they can't occur with
    action_conflicts = {}
    for mutex_group in self._mutually_exclusive_groups:
        group_actions = mutex_group._group_actions
        for i, mutex_action in enumerate(mutex_group._group_actions):
            conflicts = action_conflicts.setdefault(mutex_action, [])
            conflicts.extend(group_actions[:i])
            conflicts.extend(group_actions[i + 1 :])

    # find all option indices, and determine the arg_string_pattern
    # which has an 'O' if there is an option at an index,
    # an 'A' if there is an argument, or a '-' if there is a '--'
    option_string_indices = {}
    arg_string_pattern_parts = []
    arg_strings_iter = iter(arg_strings)
    for i, arg_string in enumerate(arg_strings_iter):
        # all args after -- are non-options
        if arg_string == "--":
            arg_string_pattern_parts.append("-")
            for arg_string in arg_strings_iter:
                arg_string_pattern_parts.append("A")

        # otherwise, add the arg to the arg strings
        # and note the index if it was an option
        else:
            option_tuple = self._parse_optional(arg_string)
            if option_tuple is None:
                pattern = "A"
            else:
                option_string_indices[i] = option_tuple
                pattern = "O"
            arg_string_pattern_parts.append(pattern)

    # join the pieces together to form the pattern
    arg_strings_pattern = "".join(arg_string_pattern_parts)

    # converts arg strings to the appropriate and then takes the action
    seen_actions = set()
    seen_non_default_actions = set()

    def take_action(action, argument_strings, option_string=None):
        seen_actions.add(action)
        argument_values = self._get_values(action, argument_strings)

        # error if this argument is not allowed with other previously
        # seen arguments, assuming that actions that use the default
        # value don't really count as "present"
        if argument_values is not action.default:
            seen_non_default_actions.add(action)
            for conflict_action in action_conflicts.get(action, []):
                if conflict_action in seen_non_default_actions:
                    msg = _("not allowed with argument %s")
                    action_name = argparse._get_action_name(conflict_action)
                    raise argparse.ArgumentError(action, msg % action_name)

        # take the action if we didn't receive a SUPPRESS value
        # (e.g. from a default)
        if argument_values is not argparse.SUPPRESS:
            action(self, namespace, argument_values, option_string)

    # function to convert arg_strings into an optional action
    def consume_optional(start_index):
        # get the optional identified at this index
        option_tuple = option_string_indices[start_index]
        action, option_string, sep, explicit_arg = option_tuple

        # identify additional optionals in the same arg string
        # (e.g. -xyz is the same as -x -y -z if no args are required)
        match_argument = self._match_argument
        action_tuples = []
        while True:
            # if we found no optional action, skip it
            if action is None:
                # <new>
                # Manually track unused arguments to assist with error messages
                # later.
                if not self._parsing_known_args:
                    global_unrecognized_arg_and_prog.append((option_string, self.prog))
                # </new>
                extras.append(arg_strings[start_index])
                return start_index + 1

            # if there is an explicit argument, try to match the
            # optional's string arguments to only this
            if explicit_arg is not None:
                arg_count = match_argument(action, "A")

                # if the action is a single-dash option and takes no
                # arguments, try to parse more single-dash options out
                # of the tail of the option string
                chars = self.prefix_chars
                if arg_count == 0 and option_string[1] not in chars and explicit_arg != "":
                    if sep or explicit_arg[0] in chars:
                        msg = _("ignored explicit argument %r")
                        raise argparse.ArgumentError(action, msg % explicit_arg)
                    action_tuples.append((action, [], option_string))
                    char = option_string[0]
                    option_string = char + explicit_arg[0]
                    optionals_map = self._option_string_actions
                    if option_string in optionals_map:
                        action = optionals_map[option_string]
                        explicit_arg = explicit_arg[1:]
                        if not explicit_arg:
                            sep = explicit_arg = None
                        elif explicit_arg[0] == "=":
                            sep = "="
                            explicit_arg = explicit_arg[1:]
                        else:
                            sep = ""
                    else:
                        extras.append(char + explicit_arg)
                        stop = start_index + 1
                        break
                # if the action expect exactly one argument, we've
                # successfully matched the option; exit the loop
                elif arg_count == 1:
                    stop = start_index + 1
                    args = [explicit_arg]
                    action_tuples.append((action, args, option_string))
                    break

                # error if a double-dash option did not use the
                # explicit argument
                else:
                    msg = _("ignored explicit argument %r")
                    raise argparse.ArgumentError(action, msg % explicit_arg)

            # if there is no explicit argument, try to match the
            # optional's string arguments with the following strings
            # if successful, exit the loop
            else:
                start = start_index + 1
                selected_patterns = arg_strings_pattern[start:]
                arg_count = match_argument(action, selected_patterns)
                stop = start + arg_count
                args = arg_strings[start:stop]
                action_tuples.append((action, args, option_string))
                break

        # add the Optional to the list and return the index at which
        # the Optional's string args stopped
        assert action_tuples
        for action, args, option_string in action_tuples:
            take_action(action, args, option_string)
        return stop

    # the list of Positionals left to be parsed; this is modified
    # by consume_positionals()
    positionals = self._get_positional_actions()

    # function to convert arg_strings into positional actions
    def consume_positionals(start_index):
        # match as many Positionals as possible
        match_partial = self._match_arguments_partial
        selected_pattern = arg_strings_pattern[start_index:]
        arg_counts = match_partial(positionals, selected_pattern)

        # slice off the appropriate arg strings for each Positional
        # and add the Positional and its args to the list
        for action, arg_count in zip(positionals, arg_counts):
            args = arg_strings[start_index : start_index + arg_count]
            start_index += arg_count
            take_action(action, args)

        # slice off the Positionals that we just parsed and return the
        # index at which the Positionals' string args stopped
        positionals[:] = positionals[len(arg_counts) :]
        return start_index

    # consume Positionals and Optionals alternately, until we have
    # passed the last option string
    extras = []
    start_index = 0
    if option_string_indices:
        max_option_string_index = max(option_string_indices)
    else:
        max_option_string_index = -1
    while start_index <= max_option_string_index:
        # consume any Positionals preceding the next option
        next_option_string_index = min([index for index in option_string_indices if index >= start_index])
        if start_index != next_option_string_index:
            positionals_end_index = consume_positionals(start_index)

            # only try to parse the next optional if we didn't consume
            # the option string during the positionals parsing
            if positionals_end_index > start_index:
                start_index = positionals_end_index
                continue
            else:
                start_index = positionals_end_index

        # if we consumed all the positionals we could and we're not
        # at the index of an option string, there were extra arguments
        if start_index not in option_string_indices:
            strings = arg_strings[start_index:next_option_string_index]
            extras.extend(strings)
            start_index = next_option_string_index

        # consume the next optional and any arguments for it
        start_index = consume_optional(start_index)

    # consume any positionals following the last Optional
    stop_index = consume_positionals(start_index)

    # if we didn't consume all the argument strings, there were extras
    extras.extend(arg_strings[stop_index:])

    # make sure all required actions were present and also convert
    # action defaults which were not given as arguments
    required_actions = []
    for action in self._actions:
        if action not in seen_actions:
            if action.required:
                failed_fields.get().append(action)  # WE ADDED THIS LINE
                required_actions.append(argparse._get_action_name(action))
            else:
                # Convert action default now instead of doing it before
                # parsing arguments to avoid calling convert functions
                # twice (which may fail) if the argument was given, but
                # only if it was defined already in the namespace
                if (
                    action.default is not None
                    and isinstance(action.default, str)
                    and hasattr(namespace, action.dest)
                    and action.default is getattr(namespace, action.dest)
                ):
                    setattr(
                        namespace,
                        action.dest,
                        self._get_value(action, action.default),
                    )

    if required_actions:
        self.error(_("the following arguments are required: %s") % ", ".join(required_actions))

    # make sure all required groups had one option present
    for group in self._mutually_exclusive_groups:
        if group.required:
            for action in group._group_actions:
                if action in seen_non_default_actions:
                    break

            # if no actions were used, report the error
            else:
                names = [
                    argparse._get_action_name(action)
                    for action in group._group_actions
                    if action.help is not argparse.SUPPRESS
                ]
                msg = _("one of the arguments %s is required")
                self.error(msg % " ".join(names))  # type: ignore

    # return the updated namespace and the extra arguments
    return namespace, extras


def custom_error(self: TyroArgumentParser, message: str):
    """Fetch missing required options in GUI.
    On missing argument, tyro fail. We cannot determine which one was missing, except by intercepting
    the error message function. Then, we reconstruct the missing options.
    Thanks to this we will be able to invoke a UI dialog with the missing options only.
    """
    if not message.startswith("the following arguments are required:"):
        return super(TyroArgumentParser, self).error(message)

    exc = SystemExit(2)
    if sys.version_info >= (3, 11):
        exc.add_note(message)
    raise exc  # will be catched


def custom_init(cf:CliFlags):
    def _(self: TyroArgumentParser, *args, **kwargs):
        super(TyroArgumentParser, self).__init__(*args, **kwargs)
        default_prefix = "-" if "-" in self.prefix_chars else self.prefix_chars[0]
        if cf.add_verbose:
            self.add_argument(
                default_prefix + "v",
                default_prefix * 2 + "verbose",
                action="count",
                default=0,
                help="verbosity level, can be used multiple times to increase",
            )

        if cf.add_version:
            self.add_argument(
                default_prefix * 2 + "version",
                # NOTE We use the native version, but it inserts a blank line
                action="version",
                version=cf.version,
                # Our custom version works bad with subcommands, we have to first resolve subcommands,
                # than it comes to the version
                # action="store_const",
                # const=cf.version,
                help=f"show program's version number ({cf.version}) and exit",
            )

        if cf.add_quiet:
            self.add_argument(
                default_prefix + "q",
                default_prefix * 2 + "quiet",
                action="store_true",
                help="suppress warnings, display only errors",
            )

        if cf.add_config:
            self.add_argument(
                default_prefix * 2 + "config",
                help=f"path to config file to fetch the defaults from",
                metavar="PATH"
            )

    return _


def custom_parse_known_args(cf:CliFlags):
    def _(self: TyroArgumentParser, args=None, namespace=None):
        namespace, args = super(TyroArgumentParser, self).parse_known_args(args, namespace)
        # NOTE We may check that the Env does not have its own `verbose``
        # NOTE I do not like much tests need force=True here as they are run in paralel.
        if cf.add_verbose and hasattr(namespace, "verbose"):
            if namespace.verbose > 0:
                logging.basicConfig(level=cf.get_log_level(namespace.verbose), format="%(message)s", force=True)
            else:
                logging.basicConfig(level=cf.default_verbosity, format="%(message)s", force=True)
            delattr(namespace, "verbose")

        # This code is now not used, see `custom_init`
        # if cf.add_verbose and hasattr(namespace, "version"):
        #     if namespace.version:
        #         print(namespace.version)
        #         raise SystemExit(0)
        #     delattr(namespace, "version")

        # Note that we do not parse --config here as it is parsed at `run.py`, before CLI parsing.
        # Since config file serves as default fo CLI parsing.
        if cf.add_config and hasattr(namespace, "config"):
            delattr(namespace, "config")

        if cf.add_quiet and hasattr(namespace, "quiet"):
            if namespace.quiet:
                logging.basicConfig(level=cf.get_log_level(-1), format="%(message)s", force=True)
            delattr(namespace, "quiet")
        return namespace, args

    return _


def subparser_call(self, parser, namespace, values, option_string=None):
    # '_subcommands._subcommandsNested (positional)' -> '_subcommandsNested'
    field_name = self.dest.replace(" (positional)", "").rsplit(".", 1)[-1]

    _crawling.get().append((self, values[0], field_name))
    _orig_call(self, parser, namespace, values, option_string)
    # I cannot use, I don't know why  super(_SubParsersAction, self).__call__


def argparse_init(kw) -> None:
    """ Restore ArgumentParser parameters that tyro considers useless
    as we tend to have backwards compatibility with argparse
    to facilitate usage.
    """
    def _(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        for k, v in kw.items():
            # Ex. self.allow_abbrev = True
            setattr(self, k, v)
    return _