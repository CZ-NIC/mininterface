import re
import sys
from argparse import (SUPPRESS, Action, ArgumentParser, _AppendAction,
                      _AppendConstAction, _CountAction, _HelpAction,
                      _StoreConstAction, _StoreFalseAction, _StoreTrueAction,
                      _SubParsersAction, _VersionAction)
from collections import defaultdict
from dataclasses import MISSING, Field, dataclass, field, make_dataclass
from functools import cached_property
from typing import Annotated, Callable, Optional
from warnings import warn

from ..tag.alias import Options
from .form_dict import DataClass

try:
    from tyro.conf import DisallowNone, OmitSubcommandPrefixes, Positional
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")


class Property:
    def __init__(self):
        self._usages = []

    def add(self, callback: Callable):
        self._usages.append(callback)

    def generate_property(self):
        def _(this):
            for clb in self._usages:
                v = clb(this)
                if v is not None:
                    return v

        return property(_)


@dataclass
class ArgparseField:

    action: Action
    properties: dict[str, Property]

    @cached_property
    def name(self):
        if n := self.action.option_strings:
            # --get-one → get_one
            return re.sub(r"^--?", "", self.action.option_strings[0]).replace("-", "_")
        else:
            raise ValueError(f"Cannot load argparse, due to field {self.action}")

    def add(self, callback: Callable):
        if self.action.dest == self.name:
            raise NotImplementedError(
                f"Cannot load argparse, due to field {self.action}. It must be visible from CLI and cannot"
                "be read directly from the program. Solution: Do not use argparse or add a .dest parameter."
            )
        self.properties[self.action.dest].add(callback)

    @property
    def has_property(self):
        return self.action.dest in self.properties


def parser_to_dataclass(parser: ArgumentParser, name: str = "Args") -> tuple[DataClass | list[DataClass], Optional[str]]:
    """
    Note: Ex. parser.add_argument("--time", type=time) -> does work at all in argparse, here it works.

    Returns:
        DataClass | list[DataClass]
        Optional[str]: add_version flag
    """
    subparsers: list[_SubParsersAction] = []
    add_version = None

    normal_actions: list[Action] = []
    has_positionals = False
    for action in parser._actions:
        match action:
            case _HelpAction():
                continue
            case _SubParsersAction():
                if has_positionals:
                    warn(
                        "This CLI parser have a subcommand placed after positional arguments. The order of arguments changes, see --help."
                    )
                subparsers.append(action)
            case _VersionAction():
                # We do not want the version to be part of the dataclass (and appear in `m.form()`).
                add_version = action.version
            case _:
                if not action.option_strings:
                    has_positionals = True
                normal_actions.append(action)

    if subparsers:
        return [
            _make_dataclass_from_actions(
                normal_actions + subactions._actions,
                subname,
                help_,
                subactions.description,
            )
            for subparser in subparsers
            for subname, subactions, help_ in _loop_SubParsersAction(subparser)
        ], add_version
    else:
        return _make_dataclass_from_actions(normal_actions, name, None, parser.description), add_version


def _loop_SubParsersAction(subparser: _SubParsersAction):
    return [
        (subname, subactions, ch_act.help)
        for (subname, subactions), ch_act in zip(subparser.choices.items(), subparser._choices_actions)
    ]


def _make_dataclass_from_actions(
    actions: list[Action], name, helptext: str | None, description: str | None
) -> DataClass:
    const_actions = defaultdict(list[ArgparseField])
    normal_fields: list[tuple[str, type, Field]] = []
    pos_fields: list[tuple[str, type, Field]] = []
    properties = defaultdict(Property)
    """ Sometimes, the action.dest differs from the field name.
    Field name is exposed to the CLI, action.dest is used in the program.
    """
    subparser_fields: list[tuple[str, type]] = []

    for action in actions:
        af = ArgparseField(action, properties)
        opt = {}

        match action:
            case _HelpAction():
                continue
            case _SubParsersAction():
                # Note that there is only one _SubParsersAction in argparse
                # but to be sure, we allow multiple of them
                # This probably makes a different CLI output than the original argparse but should work.
                for subname, subparser, help_ in _loop_SubParsersAction(action):
                    sub_dc = _make_dataclass_from_actions(
                        subparser._actions,
                        subname.capitalize(),
                        help_,
                        subparser.description,
                    )
                    subparser_fields.append((subname, sub_dc))  # required, no default

                from functools import reduce

                union_type = reduce(lambda a, b: a | b, [aa[1] for aa in subparser_fields])

                result = OmitSubcommandPrefixes[Positional[union_type]]
                pos_fields.append(("_subparsers", result))
                subparser_fields.clear()
                continue
            case _AppendAction():
                arg_type = list[action.type or str]
                opt["default_factory"] = list
            case _AppendConstAction():
                # `--one --two` -> env.section = [one, two]
                arg_type = bool
                opt["default"] = False
                const_actions[af.action.dest].append(af)
                af.add(
                    lambda self, af=af: (
                        [_af.action.const for _af in const_actions[af.action.dest] if getattr(self, _af.name)]
                    )
                )
            case _StoreTrueAction():
                arg_type = bool
            case _StoreFalseAction():
                arg_type = bool
                opt["default"] = False
                af.add(lambda self, field_name=af.name: not getattr(self, field_name))
            case _StoreConstAction():
                arg_type = bool
                opt["default"] = False
                af.add(
                    lambda self, field_name=af.name, const=action.const: (const if getattr(self, field_name) else None)
                )
            case _CountAction():
                arg_type = int
            case _:
                if action.type:
                    arg_type = action.type
                elif action.default:
                    arg_type = type(action.default)
                else:
                    arg_type = str

        if "default" not in opt and "default_factory" not in opt:
            if action.choices:
                # With the drop of Python 3.10, use mere:
                # arg_type = Literal[*action.choices]
                if sys.version_info >= (3,11):
                    from .future_compatibility import literal
                    arg_type = literal(action.choices)
                else:
                    # we do not prefer this option as tyro does not understand it
                    # and won't display options in the help
                    arg_type = Annotated[arg_type, Options(*action.choices)]

            if not action.option_strings and action.default is None and action.nargs != "?":
                opt["default"] = MISSING
            else:
                if action.default is None:
                    # parser.add_argument("--path", type=Path) -> becomes None, not Path('.').
                    # By default, argparse put None if not used in the CLI.
                    # Which makes tyro output the warning: annotated with type `<class 'str'>`, but the default value `None`
                    # We either make None an option by `arg_type |= None`
                    # or else we default the value.
                    if arg_type is not None:
                        arg_type |= None
                opt["default"] = action.default if action.default != SUPPRESS else None

        # build a dataclass field, either optional, or positional
        opt["metadata"] = {"help": action.help}
        if action.option_strings:
            # normal_fields.append((action.dest, arg_type, field(**opt, **met)))
            # Annotated[arg_type, arg(metavar=metavar)]
            normal_fields.append((af.name, arg_type, field(**opt)))

            # Generate back-compatible property if dest != field_name
            if af.name != action.dest and not af.has_property:
                af.add(lambda self, field_name=af.name: getattr(self, field_name))
        else:
            pos_fields.append((action.dest, Positional[arg_type], field(**opt)))

    # Subparser can have the same field name as the parser. We use the latter.
    # Ex:
    #   parser.add_argument('--level', type=int, default=1)
    #   subparsers = parser.add_subparsers(dest='command')
    #   run_parser = subparsers.add_parser('run')
    #   run_parser.add_argument('--level', type=int, default=5)
    uniq_fields = []
    seen = set()
    # for f in reversed(subparser_fields + pos_fields + normal_fields):
    for f in reversed(pos_fields + normal_fields):
        if f[0] not in seen:
            seen.add(f[0])
            uniq_fields.append(f)

    # if subparser_fields:
    #     from functools import reduce
    #     union_type = reduce(lambda a, b: a | b, [aa[1] for aa in subparser_fields])
    #     result = OmitSubcommandPrefixes[Positional[union_type]]
    #     uniq_fields.append(("_subparsers",  result ))

    dc = make_dataclass(
        name,
        reversed(uniq_fields),
        namespace={k: prop.generate_property() for k, prop in properties.items()},
    )
    if helptext or description:
        trimmed = (helptext or "").strip()
        needs_colon = trimmed and description and trimmed[-1] not in (".", ":", "!", "?", "…")

        separator = ": " if needs_colon else ("\n" if trimmed else "")
        dc.__doc__ = trimmed + separator + (description or "")

    return DisallowNone[dc]
