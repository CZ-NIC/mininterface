from argparse import (
    SUPPRESS,
    _AppendAction,
    _AppendConstAction,
    _CountAction,
    _HelpAction,
    _StoreConstAction,
    _StoreFalseAction,
    _StoreTrueAction,
    _SubParsersAction,
    Action,
    ArgumentParser,
)
from collections import defaultdict
from dataclasses import Field, dataclass, field, make_dataclass
from functools import cached_property
import re
from typing import Callable
from warnings import warn

from .form_dict import DataClass
from ..tag import Tag


try:
    from tyro.conf import Positional
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


def parser_to_dataclass(
    parser: ArgumentParser, name: str = "Args"
) -> DataClass | list[DataClass]:
    """Note that in contrast to the argparse, we create default values.
    When an optional flag is not used, argparse put None, we have a default value.

    This does make sense for most values and should not pose problems for truthy-values.
    Ex. checking `if namespace.my_int` still returns False for both argparse-None and our-0.

    Be aware that for Path this might pose a big difference:
    parser.add_argument("--path", type=Path) -> becomes Path('.'), not None!
    """
    subparsers: list[_SubParsersAction] = []

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
        ]
    else:
        return _make_dataclass_from_actions(
            normal_actions, name, None, parser.description
        )


def _loop_SubParsersAction(subparser: _SubParsersAction):
    return [
        (subname, subactions, ch_act.help)
        for (subname, subactions), ch_act in zip(
            subparser.choices.items(), subparser._choices_actions
        )
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
                        [
                            _af.action.const
                            for _af in const_actions[af.action.dest]
                            if getattr(self, _af.name)
                        ]
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
                    lambda self, field_name=af.name, const=action.const: (
                        const if getattr(self, field_name) else None
                    )
                )
            case _CountAction():
                arg_type = int
            case _:
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
        if "default" not in opt and "default_factory" not in opt:
            opt["default"] = action.default if action.default != SUPPRESS else None

        # build a dataclass field, either optional, or positional
        met = {"metadata": {"help": action.help}}
        if action.option_strings:
            # normal_fields.append((action.dest, arg_type, field(**opt, **met)))
            normal_fields.append((af.name, arg_type, field(**opt, **met)))

            # Generate back-compatible property if dest != field_name
            if af.name != action.dest and not af.has_property:
                af.add(lambda self, field_name=af.name: getattr(self, field_name))

        else:
            pos_fields.append((action.dest, Positional[arg_type], field(**met)))

    dc = make_dataclass(
        name,
        subparser_fields + pos_fields + normal_fields,
        namespace={k: prop.generate_property() for k, prop in properties.items()},
    )
    if helptext or description:
        trimmed = (helptext or "").strip()
        needs_colon = (
            trimmed and description and trimmed[-1] not in (".", ":", "!", "?", "…")
        )

        separator = ": " if needs_colon else ("\n" if trimmed else "")
        dc.__doc__ = trimmed + separator + (description or "")

    return dc
