import sys
from contextlib import redirect_stderr
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Literal, Optional
from unittest import skipIf

from configs import (CommandWithInitedMissing, ParametrizedGeneric,
                     Subcommand1, Subcommand2)
from shared import MISSING, TestAbstract, runm
from tyro.conf import OmitSubcommandPrefixes, Positional

from mininterface import Tag
from mininterface._lib.auxiliary import get_description
from mininterface._lib.dataclass_creation import to_kebab_case
from mininterface._lib.form_dict import MissingTagValue
from mininterface.cli import Command, SubcommandPlaceholder
from mininterface.settings import CliSettings
from mininterface.tag import DatetimeTag, PathTag, SelectTag


@dataclass
class Subc1:
    pass


@dataclass
class Subc2:
    # NOTE Due to I suppose tyro error, this arg must have a default.
    # Instead, running
    #  `$./program.py run console  --rrr A  subc2   id-one`
    # when tyro gets its default, it claims
    # 'Unrecognized arguments: id-one', probably consumed by Subc2 parser.
    #
    # cli(env, args=subargs) correctly returns
    # ╭─ Required options ────────────────────────────────────╮
    # │ The following arguments are required: --bar           │
    # │ ───────────────────────────────────────────────────── │
    # │ Argument helptext:                                    │
    # │     --bar STR                                         │
    # │                                                       │
    # │         = "BAR" (required)                            │
    # │             in _debug.py console subc2 --help         │
    # │ ───────────────────────────────────────────────────── │
    # │ For full helptext, run _debug.py console subc2 --help │
    # ╰───────────────────────────────────────────────────────╯
    # whereas
    # cli(env, args=subargs, **kwargs)
    # kwargs = {'default': Run(bot_id='id-one', _subcommands=Console(my_subcommands=Subc2(bar=''), name='my-console', rrr='RRR'))}
    # ╭─ Parsing error ─────────────────────────╮
    # │ Unrecognized arguments: id-one          │
    # │ ─────────────────────────────────────── │
    # │ For full helptext, run _debug.py --help │
    # ╰─────────────────────────────────────────╯

    bar: str = "BAR"


@dataclass
class Console:
    my_subcommands: OmitSubcommandPrefixes[Subc1 | Subc2]

    my_int: int

    # NOTE Due to I suppose tyro error, this arg `name` cannot be changed from cli.
    # If the default value is removed, it can be.

    name: Positional[str] = "my-console"

    rrr: str = "RRR"


@dataclass
class Message:
    kind: Positional[Literal["get", "pop", "send"]]
    """ This is my help text """

    # NOTE even though this field is optional, tyro finds it as required
    # and we mark it as required when handling failed fields.
    # But if left empty, nothing happens.
    # See cli_parser.reset_missing_fields
    msg: Positional[Optional[str]]
    """My message"""

    foo: str = "hello"


@dataclass
class Run:
    bot_id: Positional[Literal["id-one", "id-two"]]
    """Choose a value"""

    _subcommands: OmitSubcommandPrefixes[Message | Console]


@dataclass
class List:
    kind: Positional[Literal["bots", "queues"]]


@dataclass
class UpperCommand2:
    command: Run | List


@dataclass
class UpperCommand1:
    command: OmitSubcommandPrefixes[UpperCommand2 | List]


@dataclass
class UpperCommandA:
    command: UpperCommand2 | List


@dataclass
class Cl1(Command):
    s: str


@dataclass
class Cl2(Cl1):

    def run(self):
        pass


@dataclass
class Cl0:
    subcommand: Optional[Cl1 | Cl2] = None
    """ Ignored text"""


@dataclass
class Message1:
    text: str


@dataclass
class Message2:
    text: str = "2"


@dataclass
class MessageA:
    msg: Message1 | Message2


@dataclass
class MessageB:
    msg: Message1


@dataclass
class MessageC:
    msg: MessageB | Message2


@skipIf(sys.version_info[:2] < (3, 11), "Ignored on Python 3.10 due to exc.add_note")
class TestSubcommands(TestAbstract):

    def subcommands(self, subcommands: list):
        def r(args):
            return runm(subcommands, args=args)

        # missing subcommand
        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Subcommand1 - Class inheriting from SharedArgs.", "Subcommand2 -"],
                    )
                },
                {"": Subcommand1},
            ),
            (
                {
                    "": {
                        "foo": Tag(val=MISSING, description="", annotation=int, label="foo"),
                        "a": Tag(val=1, description="", annotation=int, label="a"),
                    }
                },
                {"": {"foo": "foo"}},
            ),
        ), self.assertRaises(SystemExit) as cm:
            r([])
        # Even though we failed on "foo: Type must be int!" in the second form, the tyro's message from the first is displayed.
        # This is due to the testing case environment while we inject the first form response as if it is not a Minadaptor.
        # Normally, the user using the Minadaptor won't make it to the second form.
        subc = ",".join(to_kebab_case(s.__name__) for s in subcommands)  # ex. 'subcommand1,subcommand2,subcommand'
        self.assertEqual("the following arguments are required: {" + f"{subc}" + "}", cm.exception.code)

        # missing subcommand params (inherited --foo and proper --b)
        with self.assertForms(
            (
                {
                    "": {
                        "foo": Tag(val=MISSING, description="", annotation=int, label="foo"),
                        "b": Tag(val=MISSING, description="", annotation=int, label="b"),
                    }
                },
                {"": {"foo": 1, "b": 2}},
            )
        ):
            env = r(["subcommand2"]).env
            self.assertEqual(
                "Subcommand2(foo=1, b=2)",
                repr(env),
            )

        # calling a subcommand works
        m = r(["subcommand1", "--foo", "1"])
        self.assertEqual(1, m.env.foo)

        # missing subcommand param
        with self.assertRaises(SystemExit), redirect_stderr(StringIO()):
            r(["subcommand2", "--foo", "1"])

        # calling a subcommand with all the params works
        m = r(["subcommand2", "--foo", "1", "--b", "5"])
        self.assertEqual(5, m.env.b)

    def DISABLED_test_integrations(self):
        # NOTE Subcommand changed a bit. Now, it's a bigger task to test it.
        # NOTE test combination of Commands and plain dataclasses
        return
        # Guaranteed support for pydantic and attrs
        self.maxDiff = None
        form2 = "Asking the form {'SubcommandB1': {'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'a': Tag(val=1, description='', annotation=<class 'int'>, label='a'), 'SubcommandB1': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}, 'SubcommandB2': {'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'b': Tag(val=2, description='', annotation=<class 'int'>, label='b'), 'SubcommandB2': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}, 'PydModel': {'': {'test': Tag(val=False, description='My testing flag ', annotation=<class 'bool'>, label='test'), 'name': Tag(val='hello', description='Restrained name ', annotation=<class 'str'>, label='name'), 'PydModel': Tag(val='disabled', description='Subcommand PydModel does not inherit from the Command. Hence it is disabled.', annotation=<class 'str'>, label=None)}}, 'AttrsModel': {'': {'test': Tag(val=False, description='My testing flag ', annotation=<class 'bool'>, label='test'), 'name': Tag(val='hello', description='Restrained name ', annotation=<class 'str'>, label='name'), 'AttrsModel': Tag(val='disabled', description='Subcommand AttrsModel does not inherit from the Command. Hence it is disabled.', annotation=<class 'str'>, label=None)}}}"
        warn2 = """UserWarning: Subcommand dataclass PydModel does not inherit from the Command."""
        self.assertForms(
            [
                {
                    "SubcommandB1": {
                        "": {
                            "foo": Tag(val=7, description="", annotation=int, label="foo"),
                            "a": Tag(val=1, description="", annotation=int, label="a"),
                            "SubcommandB1": Tag(val=lambda: True, description=None, annotation=Callable, label=None),
                        }
                    },
                    "SubcommandB2": {
                        "": {
                            "foo": Tag(val=7, description="", annotation=int, label="foo"),
                            "b": Tag(val=2, description="", annotation=int, label="b"),
                            "SubcommandB2": Tag(val=lambda: True, description=None, annotation=Callable, label=None),
                        }
                    },
                    "PydModel": {
                        "": {
                            "test": Tag(val=False, description="My testing flag ", annotation=bool, label="test"),
                            "name": Tag(val="hello", description="Restrained name ", annotation=str, label="name"),
                            "PydModel": Tag(
                                val="disabled",
                                description="Subcommand PydModel does not inherit from the Command. Hence it is disabled.",
                                annotation=str,
                                label=None,
                            ),
                        }
                    },
                    "AttrsModel": {
                        "": {
                            "test": Tag(val=False, description="My testing flag ", annotation=bool, label="test"),
                            "name": Tag(val="hello", description="Restrained name ", annotation=str, label="name"),
                            "AttrsModel": Tag(
                                val="disabled",
                                description="Subcommand AttrsModel does not inherit from the Command. Hence it is disabled.",
                                annotation=str,
                                label=None,
                            ),
                        }
                    },
                }
            ]
        )
        with self.assertOutputs(form2), self.assertStderr(contains=warn2):
            runm([SubcommandB1, SubcommandB2, PydModel, AttrsModel], args=[])

        m = runm([SubcommandB1, SubcommandB2, PydModel, AttrsModel], args=["pyd-model", "--name", "me"])
        self.assertEqual("me", m.env.name)

    def test_subcommands(self):
        self.subcommands([Subcommand1, Subcommand2])

    def test_placeholder(self):
        subcommands = [Subcommand1, Subcommand2, SubcommandPlaceholder]

        def r(args):
            return runm(list(subcommands), args=args)

        self.subcommands(subcommands)

        # with the placeholder, the form is raised
        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Subcommand1 - Class inheriting from SharedArgs.", "Subcommand2 -"],
                    )
                },
                {"": Subcommand2},
            ),
            (
                {
                    "": {
                        "foo": Tag(val=MISSING, description="", annotation=int, label="foo"),
                        "b": Tag(val=MISSING, description="", annotation=int, label="b"),
                    }
                },
                {"": {"foo": 5, "b": 5}},
            ),
        ):

            r(["subcommand"])

        # calling a placeholder works for shared arguments of all subcommands
        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Subcommand1 - Class inheriting from SharedArgs.", "Subcommand2 -"],
                    )
                },
                {"": Subcommand2},
            ),
            (
                {
                    "": {
                        "foo": Tag(val=999, description="", annotation=int, label="foo"),
                        "b": Tag(val=MISSING, description="", annotation=int, label="b"),
                    }
                },
                {"": {"foo": 2, "b": 2}},
            ),
        ):

            r(["subcommand", "--foo", "999"])

        # main help works
        # with (self.assertOutputs("XUse this placeholder to choose the subcomannd via"), self.assertRaises(SystemExit)):
        with (
            self.assertOutputs(contains="Use this placeholder to choose the subcommand via"),
            self.assertRaises(SystemExit),
        ):
            r(["--help"])

        return
        # NOTE this stopped working when we removed SubcommandOverview.
        #   We might take its code to determine common attributes, create a dataclass model on-the-fly
        #   and give it to tyro to restore the behaviour.
        # placeholder help works and shows shared arguments of other subcommands
        with self.assertOutputs(contains="Class with a shared argument."), self.assertRaises(SystemExit):
            r(["subcommand", "--help"])

    def test_common_field_annotation(self):
        with self.assertForms(
            (
                {"": {"paths": PathTag(val=MISSING, description="", annotation=list[Path], label="paths")}},
                {"": {"paths": "['/tmp']"}},
            ),
            wizzard=False,
        ):
            runm([ParametrizedGeneric, ParametrizedGeneric])


@skipIf(sys.version_info[:2] < (3, 11), "Ignored on Python 3.10 due to exc.add_note")
class TestNested(TestAbstract):
    def test_no_args(self):

        with self.assertForms(
            (
                {"": SelectTag(val=None, annotation=None, label=None, options=["List", "Run"])},
                {"": List},
            ),
            (
                {
                    "": {
                        "kind": SelectTag(
                            val=MISSING, description="", annotation=None, label="kind", options=["bots", "queues"]
                        )
                    }
                },
                {"": {"kind": "bots"}},
            ),
        ):
            env = runm([List, Run], args=[]).env
            self.assertEqual(
                f"""List(kind='bots')""",
                repr(env),
            )

    def test_upper_command(self):
        args = (
            {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Message", "Console"])},
            {"": Message},
        ), (
            {
                "": {},
                "command": {
                    "command": {
                        "bot_id": SelectTag(
                            val=MISSING,
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        ),
                        "_subcommands": {
                            "kind": SelectTag(
                                val=MISSING,
                                description="This is my help text",
                                annotation=None,
                                label="kind",
                                options=["get", "pop", "send"],
                            ),
                            "msg": Tag(val=MISSING, description="My message", annotation=Optional[str], label="msg"),
                            "foo": Tag(val="hello", description="", annotation=str, label="foo"),
                        },
                    }
                },
            },
            {"command": {"command": {"bot_id": "id-two", "_subcommands": {"kind": "pop", "msg": None}}}},
        )

        with self.assertForms(*args):
            env = runm(UpperCommand1, args=["upper-command2", "run"]).env
            self.assertEqual(
                """UpperCommand1(command=UpperCommand2(command=Run(bot_id='id-two', _subcommands=Message(kind='pop', msg=None, foo='hello'))))""",
                repr(env),
            )

        # working with subcommand prefixes works identically
        with self.assertForms(*args):
            env = runm(UpperCommandA, args=["command:upper-command2", "command.command:run"]).env
            self.assertEqual(
                """UpperCommandA(command=UpperCommand2(command=Run(bot_id='id-two', _subcommands=Message(kind='pop', msg=None, foo='hello'))))""",
                repr(env),
            )

        # omitting the prefixes can be set via CLI
        # This does not work in Python3.10
        if sys.version_info[:2] >= (3, 11):
            with self.assertForms(*args):
                env = runm(UpperCommandA, args=["upper-command2", "run"], settings=CliSettings(omit_subcommand_prefixes=True)).env
                self.assertEqual(
                    """UpperCommandA(command=UpperCommand2(command=Run(bot_id='id-two', _subcommands=Message(kind='pop', msg=None, foo='hello'))))""",
                    repr(env),
                )
        else:
            with self.assertWarns(UserWarning) as cm:
                with self.assertForms(*args):
                    env = runm(UpperCommandA, args=["command:upper-command2", "command.command:run"], settings=CliSettings(omit_subcommand_prefixes=True)).env

            # # cm je context manager, můžeš zkontrolovat zprávu
            self.assertIn("Cannot apply", str(cm.warning))

    def test_run_arg(self):
        with self.assertForms(
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Message", "Console"])},
                {"": Message},
            ),
            (
                {
                    "": {
                        "bot_id": SelectTag(
                            val=MISSING,
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        )
                    },
                    "_subcommands": {
                        "kind": SelectTag(
                            val=MISSING,
                            description="This is my help text",
                            annotation=None,
                            label="kind",
                            options=["get", "pop", "send"],
                        ),
                        "msg": Tag(val=MISSING, description="My message", annotation=Optional[str], label="msg"),
                        "foo": Tag(val="hello", description="", annotation=str, label="foo"),
                    },
                },
                {"_subcommands": {"kind": "get", "msg": "hey"}, "": {"bot_id": "id-two"}},
            ),
        ):
            env = runm([List, Run], args=["run"]).env
            self.assertEqual(
                f"""Run(bot_id='id-two', _subcommands=Message(kind='get', msg='hey', foo='hello'))""",
                repr(env),
            )

    def test_run_message_args(self):
        with self.assertForms(
            (
                {
                    "": {
                        "bot_id": SelectTag(
                            val=MISSING,
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        )
                    },
                    "_subcommands": {
                        "kind": SelectTag(
                            val=MISSING,
                            description="This is my help text",
                            annotation=None,
                            label="kind",
                            options=["get", "pop", "send"],
                        ),
                        "msg": Tag(val=MISSING, description="My message", annotation=Optional[str], label="msg"),
                        "foo": Tag(val="hello", description="", annotation=str, label="foo"),
                    },
                },
                {"": {"bot_id": "id-two"}, "_subcommands": {"kind": "pop", "msg": "hey"}},
            ),
        ):
            env = runm([List, Run], args=["run", "message"]).env
            self.assertEqual(
                f"""Run(bot_id='id-two', _subcommands=Message(kind='pop', msg='hey', foo='hello'))""",
                repr(env),
            )

    def test_run_message_get_args(self):
        # Here, user writes get as the message positional arg,
        # but it's interpreted as a bot id.
        # NOTE It would be better if we could raise a bot id dialog instead of the error.
        with self.assertForms(), self.assertStderr(
            contains="invalid choice: 'get' (choose from 'id-one', 'id-two')"
        ), self.assertRaises(SystemExit):
            runm([List, Run], args=["run", "message", "get"])

    def test_full_args(self):
        env = runm([List, Run], args=["run", "message", "get", "None", "id-one"]).env
        self.assertEqual(
            f"""Run(bot_id='id-one', _subcommands=Message(kind='get', msg=None, foo='hello'))""",
            repr(env),
        )

    def test_optional_flag(self):
        """Message param is missing, hence the form is output. But we let it None."""
        with self.assertForms(
            (
                {
                    "": {
                        "bot_id": SelectTag(
                            val="id-one",
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        )
                    },
                    "_subcommands": {
                        "kind": SelectTag(
                            val="get",
                            description="This is my help text",
                            annotation=None,
                            label="kind",
                            options=["get", "pop", "send"],
                        ),
                        "msg": Tag(val=MISSING, description="My message", annotation=Optional[str], label="msg"),
                        "foo": Tag(val="my-foo", description="", annotation=str, label="foo"),
                    },
                },
                {"_subcommands": {"msg": None}},
            )
        ):
            env = runm([List, Run], args=["run", "message", "get", "--foo", "my-foo", "id-one"]).env
            self.assertIsNone(env._subcommands.msg)

    def test_full_args_including_optional(self):
        env = runm([List, Run], args=["run", "message", "get", "my-message", "--foo", "foo-set", "id-one"]).env
        self.assertEqual(
            f"""Run(bot_id='id-one', _subcommands=Message(kind='get', msg='my-message', foo='foo-set'))""",
            repr(env),
        )

    def test_choose__run_console_subc1(self):
        with self.assertForms(
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["List", "Run"])},
                {"": Run},
            ),
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Message", "Console"])},
                {"": Console},
            ),
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Subc1", "Subc2"])},
                {"": Subc1},
            ),
            (
                {
                    "": {
                        "bot_id": SelectTag(
                            val=MISSING,
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        )
                    },
                    "_subcommands": {
                        "my_subcommands": {},
                        "my_int": Tag(val=MISSING, description="", annotation=int, label="my int"),
                        "name": Tag(val="my-console", description="", annotation=str, label="name"),
                        "rrr": Tag(val="RRR", description="", annotation=str, label="rrr"),
                    },
                },
                {"": {"bot_id": "id-one"}, "_subcommands": {"my_int": 5, "rrr": "RRR2"}},
            ),
        ):
            runm([List, Run])

    def test_run__choose_console_subc1(self):
        with self.assertForms(
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Message", "Console"])},
                {"": Console},
            ),
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Subc1", "Subc2"])},
                {"": Subc1},
            ),
            (
                {
                    "": {
                        "bot_id": SelectTag(
                            val=MISSING,
                            description="Choose a value",
                            annotation=None,
                            label="bot id",
                            options=["id-one", "id-two"],
                        )
                    },
                    "_subcommands": {
                        "my_subcommands": {},
                        "my_int": Tag(val=MISSING, description="", annotation=int, label="my int"),
                        "name": Tag(val="my-console", description="", annotation=str, label="name"),
                        "rrr": Tag(val="RRR", description="", annotation=str, label="rrr"),
                    },
                },
                {"": {"bot_id": "id-one"}, "_subcommands": {"my_int": 5, "rrr": "RRR2"}},
            ),
        ):
            runm([List, Run], ["run"])

    def test_subc1(self):
        self.assertIsInstance(runm([Subc1, Subc2], ["subc1"]).env, Subc1)

    def test_subc2(self):
        self.assertEqual("BAR", runm([Subc1, Subc2], ["subc2"]).env.bar)

    def test_choose_subc1(self):
        """No surplus form created, because Subc1 is empty"""
        with self.assertForms(
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Subc1", "Subc2"])},
                {"": Subc1},
            ),
            end=True,
        ):
            runm([Subc1, Subc2])

    def test_choose_subc2(self):
        with self.assertForms(
            (
                {"": SelectTag(val=None, description="", annotation=None, label=None, options=["Subc1", "Subc2"])},
                {"": Subc2},
            ),
            ({"": {"bar": Tag(val="BAR", description="", annotation=str, label="bar")}}, {"": {"bar": "A"}}),
        ):

            self.assertEqual("A", runm([Subc1, Subc2]).env.bar)

    def test_strange_error_mitigation(self):
        """Seems like a tyro error."""
        with self.assertForms(
            ({"": {"s": Tag(val=MISSING, description="", annotation=str, label="s")}}, {"": {"s": "s"}})
        ):
            runm([Cl1, Cl2], ["cl2"])

    def test_optional_subcommands(self):
        with self.assertForms():
            runm(Cl0)

        # The docstring is not seen by tyro
        # but at least it won't fail on the positional state of the attribute
        self.assertEqual(get_description(Cl0, "subcommand"), "")

    def test_nested_config_exists(self):
        """The nested classes have the same behaviour
        whether or not there is a config file.
        """
        for cf in (None, "tests/empty.yaml"):
            with self.assertForms(
                (
                    {
                        "": SelectTag(
                            val=None, description="", annotation=None, label=None, options=["Message b", "Message2"]
                        )
                    },
                    {"": Message2},
                ),
                ({"": {}, "msg": {"text": Tag(val="2", description="", annotation=str, label="text")}}, {}),
            ):
                runm(MessageC, config_file=cf)

            with self.assertForms(
                (
                    {
                        "": SelectTag(
                            val=None, description="", annotation=None, label=None, options=["Message b", "Message2"]
                        )
                    },
                    {"": MessageB},
                ),
                (
                    {"": {}, "msg": {"msg": {"text": Tag(val=MISSING, description="", annotation=str, label="text")}}},
                    {"msg": {"msg": {"text": "8"}}},
                ),
            ):
                runm(MessageC, config_file=cf)

            with self.assertForms(
                (
                    {"": {}, "msg": {"text": Tag(val=MISSING, description="", annotation=str, label="text")}},
                    {"msg": {"text": ""}},
                )
            ):
                runm(MessageB, config_file=cf)

            with self.assertForms(
                (
                    {
                        "": SelectTag(
                            val=None, description="", annotation=None, label=None, options=["Message1", "Message2"]
                        )
                    },
                    {"": Message1},
                ),
                (
                    {"": {}, "msg": {"text": Tag(val=MISSING, description="", annotation=str, label="text")}},
                    {"msg": {"text": ""}},
                ),
            ):
                runm(MessageA, config_file=cf)


class TestCommand(TestAbstract):

    def test_missing_tag(self):
        v = MissingTagValue()
        self.assertFalse(v)

    def test_missing_init(self):
        with self.assertForms(
            {"": {"date_": DatetimeTag(val=date(2025, 9, 4), description="", annotation=date, label="date")}}
        ):
            runm(CommandWithInitedMissing)
