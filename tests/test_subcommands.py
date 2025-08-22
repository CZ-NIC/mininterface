from dataclasses import dataclass
from typing import Literal, Optional

from tyro.conf import OmitSubcommandPrefixes, Positional
from mininterface import Tag
from mininterface.cli import SubcommandPlaceholder
from mininterface.exceptions import Cancelled
from mininterface.tag import PathTag, SelectTag
from configs import ParametrizedGeneric, Subcommand1, Subcommand2
from shared import MISSING, TestAbstract, runm


from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


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
    # kwargs = {'default': Run(bot_id='id-one', _subcommands=Console(_subcommandsTODO=Subc2(bar=''), name='my-console', rrr='RRR'))}
    # ╭─ Parsing error ─────────────────────────╮
    # │ Unrecognized arguments: id-one          │
    # │ ─────────────────────────────────────── │
    # │ For full helptext, run _debug.py --help │
    # ╰─────────────────────────────────────────╯


    bar: str = "BAR"
@dataclass
class Console:
    _subcommandsTODO: OmitSubcommandPrefixes[Subc1 | Subc2]

    # NOTE Due to I suppose tyro error, this arg cannot be changed from cli.
    # If the default value is removed, it can be.

    name: Positional[str] = "my-console"

    rrr: str = "RRR"

@dataclass
class Message:
    kind: Positional[Literal["get", "pop", "send"]]
    msg: Positional[Optional[str]]
    foo: str = "hello"


@dataclass
class Run:
    bot_id: Positional[Literal["id-one", "id-two"]]
    _subcommands: OmitSubcommandPrefixes[Message | Console]


@dataclass
class List:
    kind: Positional[Literal["bots", "queues"]]


class TestSubcommands(TestAbstract):

    form1 = (
        "Asking the form {'foo': Tag(val=0, description='', annotation=<class 'int'>, label='foo'), "
        "'Subcommand1': {'': {'a': Tag(val=1, description='', annotation=<class 'int'>, label='a'), "
        "'Subcommand1': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}, "
        "'Subcommand2': {'': {'b': Tag(val=0, description='', annotation=<class 'int'>, label='b'), "
        "'Subcommand2': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}}"
    )

    wf1 = "Asking the form {'foo': Tag(val=MISSING, description='', annotation=<class 'int'>, label='foo')}"
    wf2 = "Asking the form {'b': Tag(val=MISSING, description='', annotation=<class 'int'>, label='b')}"

    def subcommands(self, subcommands: list):
        def r(args):
            return runm(subcommands, args=args)

        # # missing subcommand
        # with self.assertOutputs(self.form1): <- wrong fields dialog appear instead of the whole form
        with self.assertOutputs(self.wf1), self.assertRaises(SystemExit):
            r([])

        # NOTE we should implement this better, see Command comment
        # missing subcommand params (inherited --foo and proper --b)
        with self.assertRaises(SystemExit), redirect_stderr(StringIO()):
            r(["subcommand2"])

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

    def DISABLED_test_choose_subcommands(self):
        # NOTE Subcommand changed a bit. Now, it's a bigger task to test it. Do first self.DISABLED_test_integrations().
        return
        values = [
            "{'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'a': Tag(val=1, description='', annotation=<class 'int'>, label='a')}}",
            "{'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'b': Tag(val=2, description='', annotation=<class 'int'>, label='b')}}",
        ]

        def check_output(*args):
            ret = dataclass_to_tagdict(*args)
            self.assertEqual(values.pop(0), str(ret))
            return ret

        with self.assertForms(["ADD HERE"]):
            # with patch('mininterface._lib.start.dataclass_to_tagdict', side_effect=check_output) as mocked, \
            #         redirect_stdout(StringIO()), redirect_stderr(StringIO()), self.assertRaises(Cancelled):
            ChooseSubcommandOverview([SubcommandB1, SubcommandB2], Mininterface(), [])
            # self.assertEqual(2, mocked.call_count)

    def test_subcommands(self):
        self.subcommands([Subcommand1, Subcommand2])

    def test_command_methods(self):
        # NOTE I need a mechanism to determine the subcommand chosen Subcommand1
        return
        # env = runm([Subcommand1, Subcommand2])
        # self.assertIsInstance(env, Subcommand1)
        # self.assertListEqual(env._trace, [1] ...)

    def test_placeholder(self):
        subcommands = [Subcommand1, Subcommand2, SubcommandPlaceholder]

        def r(args):
            return runm(subcommands, args=args)

        self.subcommands(subcommands)

        # with the placeholder, the form is raised
        # with self.assertOutputs(self.form1):   <- wrong fields dialog appear instead of the whole form
        with self.assertOutputs(self.wf1), self.assertRaises(SystemExit):
            r(["subcommand"])

        # calling a placeholder works for shared arguments of all subcommands
        # with self.assertOutputs(self.form1.replace("'foo': Tag(val=0", "'foo': Tag(val=999")):
        # <- wrong fields dialog appear instead of the whole form
        with self.assertOutputs(self.wf2), self.assertRaises(SystemExit):
            r(["subcommand", "--foo", "999"])

        # main help works
        # with (self.assertOutputs("XUse this placeholder to choose the subcomannd via"), self.assertRaises(SystemExit)):
        with (
            self.assertOutputs(contains="Use this placeholder to choose the subcommand via"),
            self.assertRaises(SystemExit),
        ):
            r(["--help"])

        # placeholder help works and shows shared arguments of other subcommands
        with self.assertOutputs(contains="Class with a shared argument."), self.assertRaises(SystemExit):
            r(["subcommand", "--help"])

    def test_common_field_annotation(self):
        with self.assertForms(
            [
                (
                    {"paths": PathTag(val=MISSING, description="", annotation=list[Path], label="paths")},
                    {"paths": "['/tmp']"},
                )
            ]
        ), self.assertRaises(Cancelled):
            runm([ParametrizedGeneric, ParametrizedGeneric])

    def test_complicated(self):
        # TODO these all use cases should display nice form
        # env = runm([List, Run], args=[]).env

        with self.assertForms(
            [
               ( {
                    "message": {
                        "kind": SelectTag(
                            val=MISSING, description="", annotation=None, label="kind", options=["get", "pop", "send"]
                        ),
                        "msg": Tag(val=MISSING, description="", annotation=Optional[str], label="msg"),
                    },
                    "bot_id": SelectTag(
                        val=MISSING,
                        description="bot-id ",
                        annotation=None,
                        label="bot_id",
                        options=["id-one", "id-two"],
                    ),
                },
                {"message": {"kind": "get", "msg": "hey"}, "bot_id" : "id-two"}
                )
            ]
        ):
            env = runm([List, Run], args=["run"]).env
            self.assertEqual(
                f"""Run(bot_id='id-two', _subcommands=Message(kind='get', msg='hey', foo='hello'))""",
                repr(env),
            )
        return

        # TODO test this
        # env = runm([List, Run], args=["run", "message"]).env

        with self.assertStderr(contains="The following arguments are required: {None}|STR"), self.assertRaises(
            SystemExit
        ) as cm:
            runm([List, Run], args=["run", "message", "get"])

        env = runm([List, Run], args=["run", "message", "get", "None", "id-one"]).env
        self.assertEqual(
            f"""Run(bot_id='id-one', _subcommands=Message(kind='get', msg=None, foo='hello'))""",
            repr(env),
        )
