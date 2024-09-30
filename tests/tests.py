from datetime import datetime
import logging
import os
import sys
from io import StringIO
from pathlib import Path, PosixPath
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from attrs_configs import AttrsModel, AttrsNested, AttrsNestedRestraint
from configs import (ColorEnum, ConstrainedEnv, FurtherEnv2, MissingUnderscore, NestedDefaultedEnv, NestedMissingEnv,
                     OptionalFlagEnv, ParametrizedGeneric, SimpleEnv)
from pydantic_configs import PydModel, PydNested, PydNestedRestraint

from mininterface import Mininterface, TextInterface, run
from mininterface.validators import not_empty, limit
from mininterface.auxiliary import flatten
from mininterface.form_dict import dataclass_to_tagdict, formdict_resolve
from mininterface.tag import Tag
from mininterface.common import Cancelled

SYS_ARGV = None  # To be redirected


class TestAbstract(TestCase):
    def setUp(self):
        global SYS_ARGV
        SYS_ARGV = sys.argv
        self.sys()

    def tearDown(self):
        global SYS_ARGV
        sys.argv = SYS_ARGV

    @classmethod
    def sys(cls, *args):
        sys.argv = ["running-tests", *args]


class TestCli(TestAbstract):
    def test_basic(self):
        def go(*_args) -> SimpleEnv:
            self.sys(*_args)
            return run(SimpleEnv, interface=Mininterface, prog="My application").env

        self.assertEqual(4, go().important_number)
        self.assertEqual(False, go().test)
        self.assertEqual(5, go("--important-number", "5").important_number)
        self.assertEqual(6, go("--important-number=6").important_number)
        self.assertEqual(7, go("--important_number=7").important_number)

        self.sys("--important_number='8'")
        self.assertRaises(SystemExit, lambda: run(SimpleEnv, interface=Mininterface, prog="My application"))

    def test_cli_complex(self):
        def go(*_args) -> NestedDefaultedEnv:
            self.sys(*_args)
            return run(NestedDefaultedEnv, interface=Mininterface, prog="My application").env

        self.assertEqual("example.org", go().further.host)
        self.assertEqual("example.com", go("--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go("--further.host='example.net'").further.host)
        self.assertEqual("example.org", go("--further.host", 'example.org').further.host)
        self.assertEqual("example org", go("--further.host", 'example org').further.host)

        def go2(*_args) -> NestedMissingEnv:
            self.sys(*_args)
            return run(NestedMissingEnv, interface=Mininterface, prog="My application").env
        self.assertEqual("example.org", go2("--further.token=1").further.host)
        self.assertEqual("example.com", go2("--further.token=1", "--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go2("--further.token=1", "--further.host='example.net'").further.host)
        self.sys("--further.host='example.net'")
        self.assertRaises(SystemExit, lambda: run(SimpleEnv, interface=Mininterface, prog="My application"))


class TestInteface(TestAbstract):
    def test_ask(self):
        m0 = run(NestedDefaultedEnv, interface=Mininterface, prog="My application")
        self.assertEqual(0, m0.ask_number("Test input"))

        m1: TextInterface = run(NestedDefaultedEnv, interface=TextInterface, prog="My application")
        with patch('builtins.input', return_value=5):
            self.assertEqual(5, m1.ask_number("Number"))
        with patch('builtins.input', side_effect=["invalid", 1]):
            self.assertEqual(1, m1.ask_number("Number"))
        with patch('builtins.input', side_effect=["invalid", EOFError]):
            with self.assertRaises(Cancelled):
                self.assertEqual(1, m1.ask_number("Number"))

        with patch('builtins.input', side_effect=["", "", "y", "Y", "n", "n", "N", "y", "hello"]):
            self.assertTrue(m1.is_yes(""))
            self.assertTrue(m1.is_no(""))

            self.assertTrue(m1.is_yes(""))
            self.assertTrue(m1.is_yes(""))
            self.assertFalse(m1.is_yes(""))

            self.assertTrue(m1.is_no(""))
            self.assertTrue(m1.is_no(""))
            self.assertFalse(m1.is_no(""))

            self.assertEqual("hello", m1.ask(""))

    def test_ask_form(self):
        m = TextInterface()
        dict1 = {"my label": Tag(True, "my description"), "nested": {"inner": "text"}}
        with patch('builtins.input', side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.form(dict1)
        self.assertEqual({"my label": Tag(True, "my description"), "nested": {"inner": "another"}}, dict1)

        # Empty form invokes editing self.env, which is empty
        with patch('builtins.input', side_effect=["c"]):
            self.assertEqual(SimpleNamespace(), m.form())

        # Empty form invokes editing self.env, which contains a dataclass
        m2 = run(SimpleEnv, interface=TextInterface, prog="My application")
        self.assertFalse(m2.env.test)
        with patch('builtins.input', side_effect=["v.test = True", "c"]):
            self.assertEqual(m2.env, m2.form())
            self.assertTrue(m2.env.test)

    def test_form_output(self):
        m = run(SimpleEnv, interface=Mininterface)
        d1 = {"test1": "str", "test2": Tag(True)}
        r1 = m.form(d1)
        # the original dict is not changed in the form
        self.assertEqual(True, d1["test2"].val)
        # and even, when it changes, the output dict is not altered
        d1["test2"].val = False
        self.assertEqual(True, r1["test2"])

        # when having empty form, it returns the env object
        self.assertIs(m.env, m.form())


class TestConversion(TestAbstract):
    def test_tagdict_resolve(self):
        self.assertEqual({"one": 1}, formdict_resolve({"one": 1}))
        self.assertEqual({"one": 1}, formdict_resolve({"one": Tag(1)}))
        self.assertEqual({"one": 1}, formdict_resolve({"one": Tag(Tag(1))}))
        self.assertEqual({"": {"one": 1}}, formdict_resolve({"": {"one": Tag(Tag(1))}}))
        self.assertEqual({"one": 1}, formdict_resolve({"": {"one": Tag(Tag(1))}}, extract_main=True))

    def test_normalize_types(self):
        """ Conversion str("") to None and back.
        When using GUI interface, we input an empty string and that should mean None
        for annotation `int | None`.
        """
        origin = {'': {'test': Tag(False, 'Testing flag ', annotation=None),
                       'numb': Tag(4, 'A number', annotation=None),
                       'severity': Tag('', 'integer or none ', annotation=int | None),
                       'msg': Tag('', 'string or none', annotation=str | None)}}
        data = {'': {'test': False, 'numb': 4, 'severity': 'fd', 'msg': ''}}

        self.assertFalse(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': ''}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '', 'msg': ''}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': 'Text'}}
        self.assertTrue(Tag._submit(origin, data))

        # check value is kept if revision needed
        self.assertEqual(False, origin[""]["test"].val)
        data = {'': {'test': True, 'numb': 100, 'severity': '1', 'msg': 1}}  # ui put a wrong 'msg' type
        self.assertFalse(Tag._submit(origin, data))
        self.assertEqual(True, origin[""]["test"].val)
        self.assertEqual(100, origin[""]["numb"].val)

        # Check nested TagDict
        origin = {'test': Tag(False, 'Testing flag ', annotation=None),
                  'severity': Tag('', 'integer or none ', annotation=int | None),
                  'nested': {'test2': Tag(4, '')}}
        data = {'test': True, 'severity': "", 'nested': {'test2': 8}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'test': True, 'severity': "str", 'nested': {'test2': 8}}
        self.assertFalse(Tag._submit(origin, data))

    def test_non_scalar(self):
        tag = Tag(Path("/tmp"), '')
        origin = {'': {'path': tag}}
        data = {'': {'path': "/usr"}}  # the input '/usr' is a str
        self.assertTrue(Tag._submit(origin, data))
        self.assertEqual(Path("/usr"), tag.val)  # the output is still a Path

    def test_datetime(self):
        new_date = "2020-01-01 17:35"
        tag = Tag(datetime.fromisoformat("2024-09-10 17:35:39.922044"))
        self.assertFalse(tag.update("fail"))
        self.assertTrue(tag.update(new_date))
        self.assertEqual(datetime.fromisoformat(new_date), tag.val)

    def test_validation(self):
        def validate(tag: Tag):
            val = tag.val
            if 10 < val < 20:
                return "Number must be between 0 ... 10 or 20 ... 100", 20
            if val < 0:
                return False, 30
            if val > 100:
                return "Too high"
            return True

        tag = Tag(100, 'Testing flag', validation=validate)
        origin = {'': {'number': tag}}
        # validation passes
        self.assertTrue(Tag._submit(origin, {'': {'number': 100}}))
        self.assertIsNone(tag._error_text)
        # validation fail, value set by validion
        self.assertFalse(Tag._submit(origin, {'': {'number': 15}}))
        self.assertEqual("Number must be between 0 ... 10 or 20 ... 100", tag._error_text)
        self.assertEqual(20, tag.val)  # value set by validation
        # validation passes again, error text restored
        self.assertTrue(Tag._submit(origin, {'': {'number': 5}}))
        self.assertIsNone(tag._error_text)
        # validation fails, default error text
        self.assertFalse(Tag._submit(origin, {'': {'number': -5}}))
        self.assertEqual("Validation fail", tag._error_text)  # default error text
        self.assertEqual(30, tag.val)
        # validation fails, value not set by validation
        self.assertFalse(Tag._submit(origin, {'': {'number': 101}}))
        self.assertEqual("Too high", tag._error_text)
        self.assertEqual(30, tag.val)

    def test_env_instance_dict_conversion(self):
        m: TextInterface = run(OptionalFlagEnv, interface=TextInterface, prog="My application")
        env1: OptionalFlagEnv = m.env

        self.assertIsNone(env1.severity)

        fd = dataclass_to_tagdict(env1, m._descriptions)
        ui = formdict_resolve(fd)
        self.assertEqual({'': {'severity': '', 'msg': '', 'msg2': 'Default text'},
                          'further': {'deep': {'flag': False}, 'numb': 0}}, ui)
        self.assertIsNone(env1.severity)

        # do the same as if the tkinter_form was just submitted without any changes
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

        # changes in the UI should not directly affect the original
        ui[""]["msg2"] = "Another"
        ui[""]["severity"] = 5
        ui["further"]["deep"]["flag"] = True
        self.assertEqual("Default text", env1.msg2)

        # on UI submit, the original is affected
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertEqual("Another", env1.msg2)
        self.assertEqual(5, env1.severity)
        self.assertTrue(env1.further.deep.flag)

        # Another UI changes, makes None from an int
        ui[""]["severity"] = ""  # UI is not able to write None, it does an empty string instead
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

    def test_choice(self):
        t = Tag("one", choices=["one", "two"])
        t.update("two")
        self.assertEqual(t.val, "two")
        t.update("three")
        self.assertEqual(t.val, "two")

        m = run(ConstrainedEnv)
        d = dataclass_to_tagdict(m.env, m._descriptions)
        self.assertFalse(d[""]["choices"].update(""))
        self.assertTrue(d[""]["choices"].update("two"))

        # dict is the input
        t = Tag(1, choices={"one": 1, "two": 2})
        self.assertTrue(t.update("two"))
        self.assertEqual(2, t.val)
        self.assertFalse(t.update("three"))
        self.assertEqual(2, t.val)
        self.assertTrue(t.update("one"))
        self.assertEqual(1, t.val)

        # list of Tags are the input
        t1 = Tag(1, name="one")
        t2 = Tag(2, name="two")
        t = Tag(1, choices=[t1, t2])
        self.assertTrue(t.update("two"))
        self.assertEqual(t2, t.val)
        self.assertFalse(t.update("three"))
        self.assertEqual(t2, t.val)
        self.assertTrue(t.update("one"))
        self.assertEqual(t1, t.val)

        # self.assertEqual(m.choice(["one", "two"]), "two")

    def test_choice_enum(self):
        # Enum type supported
        t1 = Tag(ColorEnum.GREEN, choices=ColorEnum)
        t1.update(str(ColorEnum.BLUE.value))
        self.assertEqual(ColorEnum.BLUE, t1.val)

        # list of enums supported
        t2 = Tag(ColorEnum.GREEN, choices=[ColorEnum.BLUE, ColorEnum.GREEN])
        self.assertEqual({str(v.value): v for v in [ColorEnum.BLUE, ColorEnum.GREEN]}, t2._get_choices())
        t2.update(str(ColorEnum.BLUE.value))
        self.assertEqual(ColorEnum.BLUE, t2.val)

        # Enum type supported even without explicit definition
        t3 = Tag(ColorEnum.GREEN)
        self.assertEqual(ColorEnum.GREEN.value, t3._get_ui_val())
        self.assertEqual({str(v.value): v for v in list(ColorEnum)}, t3._get_choices())
        t3.update(str(ColorEnum.BLUE.value))
        self.assertEqual(ColorEnum.BLUE.value, t3._get_ui_val())
        self.assertEqual(ColorEnum.BLUE, t3.val)
        t4 = Tag(ColorEnum)
        self.assertIsNone(t4.val)
        t4.update(str(ColorEnum.BLUE.value))
        self.assertEqual(ColorEnum.BLUE, t4.val)


class TestRun(TestAbstract):
    def test_run_ask_empty(self):
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(SimpleEnv, True, interface=Mininterface)
            self.assertEqual("Asking the form SimpleEnv(test=False, important_number=4)", stdout.getvalue().strip())
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(SimpleEnv, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    def test_run_ask_for_missing(self):
        form = """Asking the form {'token': Tag(val='', description='', annotation=<class 'str'>, name='token')}"""
        # Ask for missing, no interference with ask_on_empty_cli
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(FurtherEnv2, True, interface=Mininterface)
            self.assertEqual(form, stdout.getvalue().strip())
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(FurtherEnv2, False, interface=Mininterface)
            self.assertEqual(form, stdout.getvalue().strip())
        # Ask for missing does not happen, CLI fails
        with self.assertRaises(SystemExit):
            run(FurtherEnv2, True, ask_for_missing=False, interface=Mininterface)

        # No missing field
        self.sys("--token", "1")
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(FurtherEnv2, True, ask_for_missing=True, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())
            run(FurtherEnv2, True, ask_for_missing=False, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    def test_run_ask_for_missing_underscored(self):
        # Treating underscores
        form2 = """Asking the form {'token_underscore': Tag(val='', description='', annotation=<class 'str'>, name='token_underscore')}"""
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(MissingUnderscore, True, interface=Mininterface)
            self.assertEqual(form2, stdout.getvalue().strip())
        self.sys("--token-underscore", "1")  # dash used instead of an underscore

        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(MissingUnderscore, True, ask_for_missing=True, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    def test_run_config_file(self):
        os.chdir("tests")
        sys.argv = ["SimpleEnv.py"]
        self.assertEqual(10, run(SimpleEnv, config_file=True, interface=Mininterface).env.important_number)
        self.assertEqual(4, run(SimpleEnv, config_file=False, interface=Mininterface).env.important_number)
        self.assertEqual(20, run(SimpleEnv, config_file="SimpleEnv2.yaml", interface=Mininterface).env.important_number)
        self.assertEqual(20, run(SimpleEnv, config_file=Path("SimpleEnv2.yaml"),
                         interface=Mininterface).env.important_number)
        self.assertEqual(4, run(SimpleEnv, config_file=Path("empty.yaml"), interface=Mininterface).env.important_number)
        with self.assertRaises(FileNotFoundError):
            run(SimpleEnv, config_file=Path("not-exists.yaml"), interface=Mininterface)


class TestValidators(TestAbstract):
    def test_not_empty(self):
        f = Tag("", validation=not_empty)
        self.assertFalse(f.update(""))
        self.assertTrue(f.update("1"))

    def test_bare_limit(self):
        def f(val):
            return Tag(val)
        self.assertTrue(all(limit(1, 10)(f(v)) is True for v in (1, 2, 9, 10)))
        self.assertTrue(any(limit(1, 10)(f(v)) is not True for v in (-1, 0, 11)))
        self.assertTrue(all(limit(5)(f(v)) is True for v in (0, 2, 5)))
        self.assertTrue(any(limit(5)(f(v)) is not True for v in (-1, 6)))
        self.assertTrue(all(limit(1, 10, gt=2)(f(v)) is True for v in (9, 10)))
        self.assertTrue(all(limit(1, 10, gt=2)(f(v)) is not True for v in (1, 2, 11)))
        self.assertTrue(all(limit(1, 10, lt=3)(f(v)) is True for v in (1, 2)))
        self.assertTrue(all(limit(1, 10, lt=2)(f(v)) is not True for v in (3, 11)))

        # valid for checking str length
        self.assertTrue(all(limit(1, 10)(f("a"*v)) is True for v in (1, 2, 9, 10)))
        self.assertTrue(any(limit(1, 10)(f(v)) is not True for v in (-1, 0, 11)))

    def test_limited_field(self):
        t1 = Tag(1, validation=limit(1, 10))
        self.assertTrue(t1.update(2))
        self.assertEqual(2, t1.val)
        self.assertFalse(t1.update(11))
        self.assertEqual(2, t1.val)
        t2 = Tag(1, validation=limit(1, 10, transform=True))
        self.assertTrue(t2.update(2))
        self.assertEqual(2, t2.val)
        self.assertFalse(t2.update(11))
        self.assertEqual(10, t2.val)


class TestLog(TestAbstract):
    @staticmethod
    def log():
        run(SimpleEnv, interface=Mininterface)
        logger = logging.getLogger(__name__)
        logger.debug("debug level")
        logger.info("info level")
        logger.warning("warning level")
        logger.error("error level")

    @patch('logging.basicConfig')
    def test_run_verbosity0(self, mock_basicConfig):
        self.sys("-v")
        with self.assertRaises(SystemExit):
            run(SimpleEnv, add_verbosity=False, interface=Mininterface)
        mock_basicConfig.assert_not_called()

    @patch('logging.basicConfig')
    def test_run_verbosity1(self, mock_basicConfig):
        self.log()
        mock_basicConfig.assert_not_called()

    @patch('logging.basicConfig')
    def test_run_verbosity2(self, mock_basicConfig):
        self.sys("-v")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format='%(levelname)s - %(message)s')

    @patch('logging.basicConfig')
    def test_run_verbosity2b(self, mock_basicConfig):
        self.sys("--verbose")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format='%(levelname)s - %(message)s')

    @patch('logging.basicConfig')
    def test_run_verbosity3(self, mock_basicConfig):
        self.sys("-vv")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.DEBUG, format='%(levelname)s - %(message)s')


class TestPydanticIntegration(TestAbstract):
    def test_basic(self):
        m = run(PydModel, interface=Mininterface)
        self.assertEqual("hello", m.env.name)

    def test_nested(self):
        m = run(PydNested, interface=Mininterface)
        self.assertEqual(-100, m.env.number)

        self.sys("--number", "-200")
        m = run(PydNested, interface=Mininterface)
        self.assertEqual(-200, m.env.number)
        self.assertEqual(4, m.env.inner.number)

    def test_config(self):
        m = run(PydNested, config_file="tests/pydantic.yaml", interface=Mininterface)
        self.assertEqual(100, m.env.number)
        self.assertEqual(0, m.env.inner.number)
        self.assertEqual("hello", m.env.inner.text)

    def test_nested_restraint(self):
        m = run(PydNestedRestraint, interface=Mininterface)
        self.assertEqual("hello", m.env.inner.name)

        f = dataclass_to_tagdict(m.env, m._descriptions)["inner"]["name"]
        self.assertTrue(f.update("short"))
        self.assertEqual("Restrained name ", f.description)
        self.assertFalse(f.update("long words"))
        self.assertEqual("String should have at most 5 characters Restrained name ", f.description)
        self.assertTrue(f.update(""))
        self.assertEqual("Restrained name ", f.description)

    # NOTE
    # def test_run_ask_for_missing(self):
    #   Might be a mess. Seems that missing fields are working better
    #   when nested than directly.


class TestAttrsIntegration(TestAbstract):
    def test_basic(self):
        m = run(AttrsModel, interface=Mininterface)
        self.assertEqual("hello", m.env.name)

    def test_nested(self):
        m = run(AttrsNested, interface=Mininterface)
        self.assertEqual(-100, m.env.number)

        self.sys("--number", "-200")
        m = run(AttrsNested, interface=Mininterface)
        self.assertEqual(-200, m.env.number)
        self.assertEqual(4, m.env.inner.number)

    def test_config(self):
        m = run(AttrsNested, config_file="tests/pydantic.yaml", interface=Mininterface)
        self.assertEqual(100, m.env.number)
        self.assertEqual(0, m.env.inner.number)
        self.assertEqual("hello", m.env.inner.text)

    def test_nested_restraint(self):
        m = run(AttrsNestedRestraint, interface=Mininterface)
        self.assertEqual("hello", m.env.inner.name)

        f = dataclass_to_tagdict(m.env, m._descriptions)["inner"]["name"]
        self.assertTrue(f.update("short"))
        self.assertEqual("Restrained name ", f.description)
        self.assertFalse(f.update("long words"))
        self.assertEqual("Length of 'check' must be <= 5: 10 Restrained name ", f.description)
        self.assertTrue(f.update(""))
        self.assertEqual("Restrained name ", f.description)


class TestAnnotated(TestAbstract):
    def test_annotated(self):
        m = run(ConstrainedEnv)
        d = dataclass_to_tagdict(m.env, m._descriptions)
        self.assertFalse(d[""]["test"].update(""))
        self.assertFalse(d[""]["test2"].update(""))
        self.assertTrue(d[""]["test"].update(" "))
        self.assertTrue(d[""]["test2"].update(" "))


class TestTagAnnotation(TestAbstract):
    """ Tests tag annotation. """
    # The class name could not be 'TestAnnotation', nor 'TestAnnotation2'. If so, another test on github failed with
    # StopIteration / During handling of the above exception, another exception occurred:
    # File "/opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/unittest/result.py", line 226, in _clean_tracebacks
    #     value.__traceback__ = tb
    # /opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/unittest/result.py", line 226
    #   File "<string>", line 4, in __setattr__
    # dataclasses.FrozenInstanceError: cannot assign to field '__traceback__'
    # On local machine, all the tests went fine.

    def test_type_guess(self):
        def _(type_, val):
            self.assertEqual(type_, Tag(val).annotation)

        _(int, 1)
        _(str, "1")
        _(list, [])
        _(list[PosixPath], [PosixPath("/tmp")])
        _(list, [PosixPath("/tmp"), 2])
        _(set[PosixPath], set((PosixPath("/tmp"),)))

    def test_type_discovery(self):
        def _(compared, annotation):
            self.assertListEqual(compared, Tag(annotation=annotation)._get_possible_types())

        _([], None)
        _([(None, str)], str)
        _([(None, str)], None | str)
        _([(None, str)], str | None)
        _([(list, str)], list[str])
        _([(list, str)], list[str] | None)
        _([(list, str)], None | list[str])
        _([(list, str), (tuple, int)], None | list[str] | tuple[int])
        _([(list, int), (tuple, str), (None, str)], list[int] | tuple[str] | str | None)

    def test_subclass_check(self):
        def _(compared, annotation, true=True):
            getattr(self, "assertTrue" if true else "assertFalse")(Tag(annotation=annotation)._is_subclass(compared))

        _(int, int)
        _(list, list)
        _(Path, Path)
        _(Path, list[Path])
        _(PosixPath, list[Path])
        _(Path, list[PosixPath], False)
        _(PosixPath, list[PosixPath])
        _((Path, PosixPath), list[Path])

    def test_generic(self):
        t = Tag("", annotation=list)
        t.update("")
        self.assertEqual("", t.val)
        t.update("[1,2,3]")
        self.assertEqual([1, 2, 3], t.val)
        t.update("['1',2,3]")
        self.assertEqual(["1", 2, 3], t.val)

    def test_parametrized_generic(self):
        t = Tag("", annotation=list[str])
        self.assertFalse(t.update(""))  # NOTE we should consider this as an empty list instead and return True
        t.update("[1,2,3]")
        self.assertEqual(["1", "2", "3"], t.val)
        t.update("[1,'2',3]")
        self.assertEqual(["1", "2", "3"], t.val)

    def test_single_path_union(self):
        t = Tag("", annotation=Path | None)
        t.update("/tmp/")
        self.assertEqual(Path("/tmp"), t.val)
        t.update("")
        self.assertIsNone(t.val)

    def test_path(self):
        t = Tag("", annotation=list[Path])
        t.update("['/tmp/','/usr']")
        self.assertEqual([Path("/tmp"), Path("/usr")], t.val)
        self.assertFalse(t.update("[1,2,3]"))
        self.assertFalse(t.update("[/home, /usr]"))  # missing parenthesis

    def test_path_union(self):
        t = Tag("", annotation=list[Path] | None)
        t.update("['/tmp/','/usr']")
        self.assertEqual([Path("/tmp"), Path("/usr")], t.val)
        self.assertFalse(t.update("[1,2,3]"))
        self.assertFalse(t.update("[/home, /usr]"))  # missing parenthesis
        self.assertTrue(t.update("[]"))
        self.assertEqual([], t.val)
        self.assertTrue(t.update(""))
        self.assertIsNone(t.val)

    def test_path_cli(self):
        m = run(ParametrizedGeneric, interface=Mininterface)
        f = dataclass_to_tagdict(m.env, m._descriptions)[""]["paths"]
        self.assertEqual("", f.val)
        self.assertTrue(f.update("[]"))

        self.sys("--paths", "/usr", "/tmp")
        m = run(ParametrizedGeneric, interface=Mininterface)
        f = dataclass_to_tagdict(m.env, m._descriptions)[""]["paths"]
        self.assertEqual([Path("/usr"), Path("/tmp")], f.val)
        self.assertEqual(['/usr', '/tmp'], f._get_ui_val())
        self.assertTrue(f.update("['/var']"))
        self.assertEqual([Path("/var")], f.val)
        self.assertEqual(['/var'], f._get_ui_val())

    def test_choice_method(self):
        m = run(interface=Mininterface)
        self.assertIsNone(None, m.choice((1, 2, 3)))
        self.assertEqual(2, m.choice((1, 2, 3), default=2))
        self.assertEqual(2, m.choice((1, 2, 3), default=2))
        self.assertEqual(2, m.choice({"one": 1, "two": 2}, default=2))
        self.assertEqual(2, m.choice([Tag(1, name="one"), Tag(2, name="two")], default=2))

        # Enum type
        self.assertEqual(ColorEnum.GREEN, m.choice(ColorEnum, default=ColorEnum.GREEN))

        # list of enums
        self.assertEqual(ColorEnum.GREEN, m.choice([ColorEnum.BLUE, ColorEnum.GREEN], default=ColorEnum.GREEN))
        self.assertEqual(ColorEnum.BLUE, m.choice([ColorEnum.BLUE]))


if __name__ == '__main__':
    main()
