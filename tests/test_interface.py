from mininterface import Mininterface
from mininterface._lib.run import run
from mininterface.exceptions import Cancelled
from mininterface.interfaces import TextInterface
from mininterface.tag import CallbackTag, DatetimeTag, SelectTag, Tag
from mininterface.tag.datetime_tag import date
from configs import (
    ColorEnum,
    ColorEnumSingle,
    EnumedEnv,
    FurtherEnv1,
    NestedDefaultedEnv,
    NestedUnion,
    SimpleEnv,
    callback_raw,
    callback_tag,
    callback_tag2,
)
from shared import TestAbstract, runm, mock_interactive_terminal, MISSING


from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch


class TestInterface(TestAbstract):

    @mock_interactive_terminal
    def test_ask(self):
        m0 = run(NestedDefaultedEnv, interface=Mininterface, prog="My application")
        self.assertEqual(0, m0.ask("Test input", int))

        m1: TextInterface = run(NestedDefaultedEnv, interface=TextInterface, prog="My application")
        with patch("builtins.input", return_value=5):
            self.assertEqual(5, m1.ask("Number", int))
        with patch("builtins.input", side_effect=["invalid", 1]):
            self.assertEqual(1, m1.ask("Number", int))
        with patch("builtins.input", side_effect=["invalid", EOFError]):
            with self.assertRaises(Cancelled):
                self.assertEqual(1, m1.ask("Number", int))

        with patch("builtins.input", side_effect=["", "", "y", "Y", "n", "n", "N", "y", "hello"]):
            self.assertTrue(m1.confirm(""))
            self.assertFalse(m1.confirm("", False))

            self.assertTrue(m1.confirm(""))
            self.assertTrue(m1.confirm(""))
            self.assertFalse(m1.confirm(""))

            self.assertFalse(m1.confirm("", False))
            self.assertFalse(m1.confirm("", False))
            self.assertTrue(m1.confirm("", False))

            self.assertEqual("hello", m1.ask(""))

    def test_ask_param(self):
        m0 = run(interface=Mininterface)
        self.assertEqual(datetime.now().date(), m0.ask("Test input", DatetimeTag(date=True)))
        # ignore microseconds
        self.assertEqual(str(datetime.now())[:20], str(m0.ask("Test input", DatetimeTag()))[:20])
        self.assertEqual(datetime.now().date(), m0.ask("Test input", date))

    @mock_interactive_terminal
    def test_ask_form(self):
        m = TextInterface()
        dict1 = {"my label": Tag(True, "my description"), "nested": {"inner": "text"}}
        with patch("builtins.input", side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.form(dict1)

        self.assertEqual(
            repr({"my label": Tag(True, "my description", label="my label"), "nested": {"inner": "another"}}),
            repr(dict1),
        )

        # Empty form invokes editing self.env, which is empty
        with patch("builtins.input", side_effect=["c"]):
            self.assertEqual(SimpleNamespace(), m.form())

        # Empty form invokes editing self.env, which contains a dataclass
        m2 = run(SimpleEnv, interface=TextInterface, prog="My application")
        self.assertFalse(m2.env.test)
        with patch("builtins.input", side_effect=["v.test = True", "c"]):
            self.assertEqual(m2.env, m2.form())
            self.assertTrue(m2.env.test)

        # Form accepts a dataclass type
        m3 = run(interface=Mininterface)
        self.assertEqual(SimpleEnv(), m3.form(SimpleEnv))

        # Form accepts a dataclass instance
        self.assertEqual(SimpleEnv(), m3.form(SimpleEnv()))

    def test_form_output(self):
        m = run(SimpleEnv, interface=Mininterface)
        d1 = {"test1": "str", "test2": Tag(True)}
        r1 = m.form(d1)
        self.assertEqual(dict, type(r1))
        # the original dict is not changed in the form
        self.assertEqual(True, d1["test2"].val)
        # and even, when it changes, the outputp dict is not altered
        d1["test2"].val = False
        self.assertEqual(True, r1["test2"])

        # when having empty form, it returns the env object
        self.assertIs(m.env, m.form())

        # putting a dataclass type
        self.assertIsInstance(m.form(SimpleEnv), SimpleEnv)

        # putting a dataclass instance
        self.assertIsInstance(m.form(SimpleEnv()), SimpleEnv)

    def test_form_enum(self):
        with self.assertForms( (
                {
                    "": {
                        "e1": SelectTag(
                            val=MISSING, description="", annotation=None, label="e1", options=ColorEnum
                        ),
                        "e2": SelectTag(
                            val=ColorEnum.RED, description="", annotation=None, label="e2", options=ColorEnum
                        ),
                    }
                } ,
                {"": {"e1": ColorEnum.GREEN, "e2": ColorEnum.BLUE}},
            )):
            out = runm().form(EnumedEnv)
            self.assertEqual(ColorEnum.GREEN, out.e1)
            self.assertEqual(ColorEnum.BLUE, out.e2)


    def test_select_single(self):
        m = run(interface=Mininterface)
        self.assertEqual(1, m.select([1]))
        self.assertEqual(1, m.select({"label": 1}))
        self.assertEqual(ColorEnumSingle.ORANGE, m.select(ColorEnumSingle))

    def test_select_multiple(self):
        m = run(interface=Mininterface)
        self.assertEqual([1], m.select([1], multiple=True))
        self.assertEqual([1], m.select({"label": 1}, multiple=True))
        self.assertEqual([ColorEnumSingle.ORANGE], m.select(ColorEnumSingle, multiple=True))

        self.assertEqual([1], m.select([1], default=[1]))
        self.assertEqual([1], m.select({"label": 1}, default=[1]))
        self.assertEqual([ColorEnumSingle.ORANGE], m.select(ColorEnumSingle, default=[ColorEnumSingle.ORANGE]))

    def test_select_callback(self):
        m = run(interface=Mininterface)
        form = """Asking the form {'My choice': SelectTag(val=None, description='', annotation=None, label=None, options=['callback_raw', 'callback_tag', 'callback_tag2'])}"""
        form2 = """Asking the form {'My choice': SelectTag(val=callback_raw, description='', annotation=None, label=None, options=['callback_raw', 'callback_tag', 'callback_tag2'])}"""
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            m.form(
                {
                    "My choice": SelectTag(
                        options=[
                            callback_raw,
                            CallbackTag(callback_tag),
                            # This case works here but is not supported as such form cannot be submit in GUI:
                            Tag(callback_tag2, annotation=CallbackTag),
                        ]
                    )
                }
            )

        # the default value causes no SystemExit is raised in Mininterface interface
        out = m.form(
            {
                "My choice": SelectTag(
                    callback_raw,
                    options=[
                        callback_raw,
                        CallbackTag(callback_tag),
                        # This case works here but is not supported as such form cannot be submit in GUI:
                        Tag(callback_tag2, annotation=CallbackTag),
                    ],
                )
            }
        )
        self.assertEqual(callback_raw, out["My choice"])

        options = {
            "My choice1": callback_raw,
            "My choice2": CallbackTag(callback_tag),
            # Not supported: "My choice3": Tag(callback_tag, annotation=CallbackTag),
        }

        form = """Asking the form {'Choose': SelectTag(val=None, description='', annotation=None, label=None, options=['My choice1', 'My choice2'])}"""
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            m.select(options)

        self.assertEqual(50, m.select(options, default=callback_raw))

        # NOTE This test does not work. We have to formalize the callback.
        # self.assertEqual(100, m.select(options, default=options["My choice2"]))

    def test_select_callback(self):
        def do_cmd1():
            return "cmd1"

        def do_cmd2():
            return "cmd2"

        m = runm()
        with self.assertRaises(SystemExit) as cm:
            m.select({"Open file...": do_cmd1, "Apply filter...": do_cmd2})
        self.assertEqual("Must be one of ['Open file...', 'Apply filter...']", str(cm.exception))

        ret = m.select({"Open file...": do_cmd1, "Apply filter...": do_cmd2}, default=do_cmd1)
        self.assertEqual("cmd1", ret)

        ret = m.select({"Open file...": do_cmd1, "Apply filter...": do_cmd2}, default=do_cmd1, launch=False)
        self.assertEqual(do_cmd1, ret)

        ret = m.select({"Apply filter...": do_cmd2})
        self.assertEqual("cmd2", ret)

        with self.assertRaises(SystemExit) as cm:
            m.select({"Apply filter...": do_cmd2}, skippable=False)

    def test_nested_union_from_cli(self):
        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Further env1 -", "Simple env   - Set of options."],
                    )
                },
                {"": SimpleEnv},
            ),
            (
                {
                    "": {},
                    "further": {
                        "test": Tag(val=False, description="My testing flag", annotation=bool, label="test"),
                        "important_number": Tag(
                            val=4,
                            description="This number is very important",
                            annotation=int,
                            label="important number",
                        ),
                    },
                },
                {"further": {"important_number": 12}},
            ),
        ):
            self.assertEqual(12, runm(NestedUnion).env.further.important_number)

        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Further env1 -", "Simple env   - Set of options."],
                    )
                },
                {"": FurtherEnv1},
            ),
            (
                {
                    "": {},
                    "further": {
                        "token": Tag(val="filled", description="", annotation=str, label="token"),
                        "host": Tag(val="example.org", description="", annotation=str, label="host"),
                    },
                },
                {},
            ),
        ):
            runm(NestedUnion)

    def test_nested_union_as_dialog(self):
        with self.assertForms(
            (
                {
                    "": SelectTag(
                        val=None,
                        description="",
                        annotation=None,
                        label=None,
                        options=["Further env1 -", "Simple env   - Set of options."],
                    )
                },
                {"": FurtherEnv1},
            ),
            {
                "": {},
                "further": {
                    "token": Tag(val="filled", description="", annotation=str, label="token"),
                    "host": Tag(val="example.org", description="", annotation=str, label="host"),
                },
            },
        ):
            runm().form(NestedUnion)
