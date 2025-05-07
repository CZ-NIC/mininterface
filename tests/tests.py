import logging
import os
import sys
import warnings
from argparse import ArgumentParser
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import date, datetime, time
from importlib import import_module
from io import StringIO
from pathlib import Path, PosixPath
from types import NoneType, SimpleNamespace
from typing import Optional, Type, get_type_hints
from unittest import TestCase, main
from unittest.mock import DEFAULT, Mock, patch

from annotated_types import Gt, Lt
from attrs_configs import AttrsModel, AttrsNested, AttrsNestedRestraint
from configs import (AnnotatedClass, AnnotatedClass3, AnnotatedTypes,
                     AnnotatedTypesCombined, ColorEnum, ColorEnumSingle,
                     ConflictingEnv, ConstrainedEnv, DatetimeTagClass,
                     DynamicDescription, FurtherEnv2, InheritedAnnotatedClass,
                     MissingCombined, MissingNonscalar, MissingPositional,
                     MissingPositionalScalar, MissingUnderscore,
                     NestedDefaultedEnv, NestedMissingEnv, OptionalFlagEnv,
                     ParametrizedGeneric, PathTagClass, SimpleEnv, Subcommand1,
                     Subcommand2, SubcommandB1, SubcommandB2, callback_raw,
                     callback_tag, callback_tag2)
from dumb_settings import (GuiSettings, MininterfaceSettings, TextSettings,
                           TextualSettings, TuiSettings)
from dumb_settings import UiSettings as UiDumb
from dumb_settings import WebSettings
from pydantic_configs import PydModel, PydNested, PydNestedRestraint

from mininterface import ChooseSubcommandOverview, EnvClass, Mininterface, run
from mininterface._lib.auxiliary import (flatten, matches_annotation,
                                         subclass_matches_annotation)
from mininterface._lib.cli_parser import (_merge_settings, parse_cli,
                                          parse_config_file)
from mininterface.exceptions import Cancelled
from mininterface._lib.form_dict import (MissingTagValue, TagDict,
                                         dataclass_to_tagdict, dict_to_tagdict,
                                         formdict_resolve)
from mininterface.interfaces import TextInterface
from mininterface._mininterface import MinAdaptor
from mininterface.settings import UiSettings
from mininterface._lib.start import Start
from mininterface.cli import SubcommandPlaceholder
from mininterface.tag import CallbackTag, DatetimeTag, PathTag, Tag, SelectTag, SecretTag
from mininterface.tag.tag_factory import tag_assure_type, assure_tag
from mininterface.validators import limit, not_empty

from tyro.conf import FlagConversionOff, OmitArgPrefixes

SYS_ARGV = None  # To be redirected

MISSING = MissingTagValue(BaseException(), None)


def runm(env_class: Type[EnvClass] | list[Type[EnvClass]] | None = None, args=None, **kwargs) -> Mininterface[EnvClass]:
    return run(env_class, interface=Mininterface, args=args, **kwargs)


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

    @contextmanager
    def _assertRedirect(self, redirect, expected_output=None, contains: str | list[str] = None, not_contains: str | list[str] = None):
        f = StringIO()
        with redirect(f):
            yield
        actual_output = f.getvalue().strip()
        if expected_output is not None:
            self.assertEqual(expected_output, actual_output)
        if contains is not None:
            for comp in (contains if isinstance(contains, list) else [contains]):
                self.assertIn(comp, actual_output)
        if not_contains is not None:
            for comp in (not_contains if isinstance(not_contains, list) else [not_contains]):
                self.assertNotIn(comp, actual_output)

    def assertOutputs(self, expected_output=None, contains: str | list[str] = None, not_contains=None):
        return self._assertRedirect(redirect_stdout, expected_output, contains, not_contains)

    def assertStderr(self, expected_output=None, contains=None, not_contains=None):
        return self._assertRedirect(redirect_stderr, expected_output, contains, not_contains)

    @contextmanager
    def assertForms(self, check: list[dict | None | tuple[dict | None, dict | None]]):
        """ Intercepts every form call, checks it and possibly modify it (simulating the user input).

        Args:
            check: tuple of model and setter (or just model). (If the list is shorter then the form call count, it's okay.)
                Model is compared to the form call.
                Values from setter are taken and injected into the form call, simulating the user input.
        """
        # normalize - assure items are tuples
        check_ = iter(it if isinstance(it, tuple) else (it, None) for it in check)
        this = self

        class MockAdaptor(MinAdaptor):
            def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
                try:
                    model, setter = next(check_)
                    if model:
                        this.assertEqual(repr(form), repr(model))
                    if setter:
                        for k, v in setter.items():
                            form[k].val = v
                except StopIteration:
                    # further form calls are without checks
                    pass

                # if not submit:
                #     submit = True # I should have the mechanism to choose the Tag to be submitted.

                return super().run_dialog(form, title, submit)

        class MockInterface(Mininterface[EnvClass]):
            _adaptor: MockAdaptor

        original_interface = Mininterface
        try:
            globals()['Mininterface'] = MockInterface
            yield
        finally:
            globals()['Mininterface'] = original_interface

    def assertReprEqual(self, a, b):
        return self.assertEqual(repr(a), repr(b))


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
        return
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


def mock_interactive_terminal(func):
    # mock the session could be made interactive
    @patch("sys.stdin.isatty", new=lambda: True)
    @patch("sys.stdout.isatty", new=lambda: True)
    @patch.dict(sys.modules, {"ipdb": None})  # ipdb prevents vscode to finish test_ask_form
    def _(*args, **kwargs):
        return func(*args, **kwargs)
    return _


class TestInteface(TestAbstract):

    @mock_interactive_terminal
    def test_ask(self):
        m0 = run(NestedDefaultedEnv, interface=Mininterface, prog="My application")
        self.assertEqual(0, m0.ask("Test input", int))

        m1: TextInterface = run(NestedDefaultedEnv, interface=TextInterface, prog="My application")
        with patch('builtins.input', return_value=5):
            self.assertEqual(5, m1.ask("Number", int))
        with patch('builtins.input', side_effect=["invalid", 1]):
            self.assertEqual(1, m1.ask("Number", int))
        with patch('builtins.input', side_effect=["invalid", EOFError]):
            with self.assertRaises(Cancelled):
                self.assertEqual(1, m1.ask("Number", int))

        with patch('builtins.input', side_effect=["", "", "y", "Y", "n", "n", "N", "y", "hello"]):
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
        with patch('builtins.input', side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.form(dict1)

        self.assertEqual(repr({"my label": Tag(True, "my description", label="my label"),
                         "nested": {"inner": "another"}}), repr(dict1))

        # Empty form invokes editing self.env, which is empty
        with patch('builtins.input', side_effect=["c"]):
            self.assertEqual(SimpleNamespace(), m.form())

        # Empty form invokes editing self.env, which contains a dataclass
        m2 = run(SimpleEnv, interface=TextInterface, prog="My application")
        self.assertFalse(m2.env.test)
        with patch('builtins.input', side_effect=["v.test = True", "c"]):
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
            m.form({"My choice": SelectTag(options=[
                callback_raw,
                CallbackTag(callback_tag),
                # This case works here but is not supported as such form cannot be submit in GUI:
                Tag(callback_tag2, annotation=CallbackTag)
            ])})

        # the default value causes no SystemExit is raised in Mininterface interface
        out = m.form({"My choice": SelectTag(callback_raw, options=[
            callback_raw,
            CallbackTag(callback_tag),
            # This case works here but is not supported as such form cannot be submit in GUI:
            Tag(callback_tag2, annotation=CallbackTag)
        ])})
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
        self.assertEqual("Choose: Must be one of ['Open file...', 'Apply filter...']", str(cm.exception))

        ret = m.select({"Open file...": do_cmd1, "Apply filter...": do_cmd2}, default=do_cmd1)
        self.assertEqual("cmd1", ret)

        ret = m.select({"Open file...": do_cmd1, "Apply filter...": do_cmd2}, default=do_cmd1, launch=False)
        self.assertEqual(do_cmd1, ret)

        ret = m.select({"Apply filter...": do_cmd2})
        self.assertEqual("cmd2", ret)

        with self.assertRaises(SystemExit) as cm:
            m.select({"Apply filter...": do_cmd2}, skippable=False)


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
        tag2 = Tag(datetime.fromisoformat("2024-09-10 17:35:39.922044"))
        # The user might put datetime into Tag but we need to use DatetimeTag.
        # Calling a form will convert it automatically,
        # while the original Tag is being updated.
        d = dict_to_tagdict({"test": tag2})
        tag = d["test"]
        self.assertFalse(tag.update("fail"))
        self.assertTrue(tag.update(new_date))
        self.assertEqual(datetime.fromisoformat(new_date), tag.val)
        self.assertEqual(datetime.fromisoformat(new_date), tag2.val)

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
        m = run(OptionalFlagEnv, interface=Mininterface, prog="My application")
        env1: OptionalFlagEnv = m.env

        self.assertIsNone(env1.severity)

        fd = dataclass_to_tagdict(env1)
        ui = formdict_resolve(fd)
        self.assertEqual({'': {'severity': None, 'msg': None, 'msg2': 'Default text'},
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

    def test_tag_src_update(self):
        m = run(ConstrainedEnv, interface=Mininterface)
        d: TagDict = dataclass_to_tagdict(m.env)[""]

        # tagdict uses the correct reference to the original object
        # sharing a static annotation Tag is not desired:
        # self.assertIs(ConstrainedEnv.__annotations__.get("test").__metadata__[0], d["test"])

        # name is correctly determined from the dataclass attribute name
        self.assertEqual("test2", d["test2"].label)
        # but the tag in the annotation stays intact
        self.assertIsNone(ConstrainedEnv.__annotations__.get("test2").__metadata__[0].label)
        # name is correctly fetched from the dataclass annotation
        self.assertEqual("Better name", d["test"].label)

        # a change via set_val propagates
        self.assertEqual("hello", d["test"].val)
        self.assertEqual("hello", m.env.test)
        d["test"]._set_val("foo")
        self.assertEqual("foo", d["test"].val)
        self.assertEqual("foo", m.env.test)

        # direct val change does not propagate
        d["test"].val = "bar"
        self.assertEqual("bar", d["test"].val)
        self.assertEqual("foo", m.env.test)

        # a change via update propagates
        d["test"].update("moo")
        self.assertEqual("moo", d["test"].val)
        self.assertEqual("moo", m.env.test)

    def test_nested_tag(self):
        t0 = Tag(5)
        t1 = Tag(t0, label="Used name")
        t2 = Tag(t1, label="Another name")
        t3 = Tag(t1, label="Unused name")
        t4 = Tag()._fetch_from(t2)
        t5 = Tag(label="My name")._fetch_from(t2)

        self.assertEqual("Used name", t1.label)
        self.assertEqual("Another name", t2.label)
        self.assertEqual("Another name", t4.label)
        self.assertEqual("My name", t5.label)

        self.assertEqual(5, t1.val)
        self.assertEqual(5, t2.val)
        self.assertEqual(5, t3.val)
        self.assertEqual(5, t4.val)
        self.assertEqual(5, t5.val)

        t5._set_val(8)
        self.assertEqual(8, t0.val)
        self.assertEqual(8, t1.val)
        self.assertEqual(8, t2.val)
        self.assertEqual(5, t3.val)
        self.assertEqual(5, t4.val)
        self.assertEqual(8, t5.val)  # from t2, we inherited the hook to t1

        # update triggers the value propagation
        inner = Tag(2)
        outer = Tag(Tag(Tag(inner)))
        outer.update(3)
        self.assertEqual(3, inner.val)

    def test_fetch_from(self):
        t0 = Tag(5)
        t1 = Tag(t0, label="Used name")
        t2 = Tag(t1, label="Another name")
        t5 = Tag(label="My name")._fetch_from(t2, include_ref=True)

        t5._set_val(8)

        self.assertEqual(8, t0.val)
        self.assertEqual(8, t1.val)
        self.assertEqual(5, t2.val)  # the ref was fetches instead of the t2 object, hence it is not updated
        self.assertEqual(8, t5.val)

    def test_label(self):
        """ Dict labels do not have to be str,
        but Tag.labels have to. (Ex. TuiInterface would fail.) """
        self.assertReprEqual({1: Tag("a", label='1'),
                              45: Tag("b", label='45')},
                             dict_to_tagdict({1: "a", 45: "b"}))


class TestTag(TestAbstract):
    def test_get_ui_val(self):
        self.assertEqual([1, 2], Tag([1, 2])._get_ui_val())
        self.assertEqual(["/tmp"], Tag([Path("/tmp")])._get_ui_val())
        self.assertEqual([(1, "a")], Tag([(1, 'a')])._get_ui_val())


class TestAuxiliary(TestAbstract):
    def test_matches_annotation(self):
        annotation = Optional[list[int] | str | tuple[int, str]]
        self.assertTrue(matches_annotation(None, annotation))
        self.assertTrue(matches_annotation([1, 2], annotation))
        self.assertTrue(matches_annotation("hello", annotation))
        self.assertTrue(matches_annotation((42, "world"), annotation))
        self.assertFalse(matches_annotation(42, annotation))
        self.assertTrue(matches_annotation([(1, "a"), (2, "b")], list[tuple[int, str]]))
        self.assertFalse(matches_annotation([(1, 2)], list[tuple[int, str]]))

    def test_subclass_matches_annotation(self):
        annotation = Optional[list[int] | str | tuple[int, str]]
        self.assertTrue(subclass_matches_annotation(NoneType, annotation))
        self.assertTrue(subclass_matches_annotation(str, annotation))
        self.assertFalse(subclass_matches_annotation(int, annotation))

        # The subclass_matches_annotation is not almighty. Tag behaves better:
        self.assertTrue(Tag(annotation=annotation)._is_subclass(tuple[int, str]))
        # NOTE but this should work too
        # self.assertTrue(Tag(annotation=annotation)._is_subclass(list[int]))


class TestInheritedTag(TestAbstract):
    def test_inherited_path(self):
        PathType = type(Path(""))  # PosixPath on Linux
        m = runm()
        d = dict_to_tagdict({
            "1": Path("/tmp"),
            "2": Tag("", annotation=Path),
            "3": PathTag([Path("/tmp")], multiple=True),
            "4": PathTag([Path("/tmp")]),
            "5": PathTag(Path("/tmp")),
            "6": PathTag(["/tmp"]),
            "7": PathTag([]),
            # NOTE these should work
            # "7": Tag(Path("/tmp")),
            # "8": Tag([Path("/tmp")]),
        }, m)

        # every item became PathTag
        [self.assertEqual(type(v), PathTag) for v in d.values()]
        # val stayed the same
        self.assertEqual(d["1"].val, Path('/tmp'))
        # correct annotation
        self.assertEqual(d["1"].annotation, PathType)
        self.assertEqual(d["2"].annotation, Path)
        self.assertEqual(d["3"].annotation, list[Path])
        self.assertEqual(d["4"].annotation, list[PathType])
        self.assertEqual(d["5"].annotation, PathType)
        self.assertEqual(d["6"].annotation, list[Path])
        self.assertEqual(d["7"].annotation, list[Path])
        # PathTag specific attribute
        [self.assertTrue(v.multiple) for k, v in d.items() if k in ("3", "4", "6", "7")]
        [self.assertFalse(v.multiple) for k, v in d.items() if k in ("1", "2", "5")]

    def test_path_class(self):
        m = runm(PathTagClass, ["/tmp"])  # , "--files2", "/usr"])
        d: dict[str, PathTag | Tag] = dataclass_to_tagdict(m.env)[""]

        [self.assertEqual(PathTag, type(v)) for v in d.values()]
        self.assertEqual(d["files"].label, "files")
        self.assertTrue(d["files"].multiple)

        self.assertEqual(d["files2"].label, "Custom name")
        self.assertTrue(d["files2"].multiple)

        # self.assertEqual(d["files3"].label, "Custom name")
        # self.assertTrue(d["files3"].multiple)


class TestTypes(TestAbstract):
    def test_datetime_tag(self):
        m = runm(DatetimeTagClass)
        d: TagDict = dataclass_to_tagdict(m.env)[""]
        d["extern"] = dict_to_tagdict({"extern": date.fromisoformat("2024-09-10")})["extern"]

        for key, expected_date, expected_time in [("p1", True, True), ("p2", False, True), ("p3", True, False),
                                                  ("pAnnot", True, False),
                                                  ("extern", True, False)]:
            tag: DatetimeTag = d[key]
            self.assertIsInstance(tag, DatetimeTag)
            self.assertEqual(expected_date, tag.date)
            self.assertEqual(expected_time, tag.time)


class TestRun(TestAbstract):
    def test_run_ask_empty(self):
        with self.assertOutputs("Asking the form SimpleEnv(test=False, important_number=4)"):
            run(SimpleEnv, True, interface=Mininterface)
        with self.assertOutputs(""):
            run(SimpleEnv, interface=Mininterface)

    def test_run_ask_for_missing(self):
        form = """Asking the form {'token': Tag(val=MISSING, description='', annotation=<class 'str'>, label='token')}"""
        # Ask for missing, no interference with ask_on_empty_cli
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            run(FurtherEnv2, True, interface=Mininterface)
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            run(FurtherEnv2, False, interface=Mininterface)
        # Ask for missing does not happen, CLI fails with tyro message before the Mininterface log 'Asking the form...' is displayed
        with self.assertOutputs(""), self.assertRaises(SystemExit):
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
        form2 = """Asking the form {'token_underscore': Tag(val=MISSING, description='', annotation=<class 'str'>, label='token_underscore')}"""
        with self.assertOutputs(form2), self.assertRaises(SystemExit):
            run(MissingUnderscore, True, interface=Mininterface)

        self.sys("--token-underscore", "1")  # dash used instead of an underscore

        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(MissingUnderscore, True, ask_for_missing=True, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    def test_wrong_fields(self):
        kwargs, _ = parse_config_file(AnnotatedClass)
        _, wf = parse_cli(AnnotatedClass, kwargs, args=[])
        # NOTE yield_defaults instead of yield_annotations should be probably used in pydantic and attr
        # too to support default_factory,
        # ex: `my_complex: tuple[int, str] = field(default_factory=lambda: [(1, 'foo')])`
        self.assertEqual(["files2"], list(wf))

    def test_run_ask_for_missing_union(self):
        form = """Asking the form {'path': PathTag(val=MISSING, description='', annotation=str | pathlib._local.Path, label='path'), 'combined': Tag(val=MISSING, description='', annotation=int | tuple[int, int] | None, label='combined'), 'simple_tuple': Tag(val=MISSING, description='', annotation=tuple[int, int], label='simple_tuple')}"""
        if sys.version_info[:2] <= (3, 12):  # NOTE remove with Python 3.12
            form = form.replace("pathlib._local.Path", "pathlib.Path")

        with self.assertOutputs(form), self.assertRaises(SystemExit):
            runm(MissingNonscalar)

    def test_missing_required_fail(self):
        with self.assertRaises(SystemExit):
            run(MissingPositionalScalar, interface=Mininterface)

        # Since the positional is list, we infer an empty list
        # This might be not the desired behaviour, we might change it to fail too.
        m2 = run(MissingPositional, interface=Mininterface)
        m2.form()
        self.assertListEqual([], m2.env.files)

    def test_missing_combined(self):
        with self.assertRaises(SystemExit):
            run(MissingCombined, interface=Mininterface)

        _, wf = parse_cli(MissingCombined, {})
        r = {'file': PathTag(val=MISSING, description='file ', annotation=Path, label='file'),
             'foo': Tag(val=MISSING, description='', annotation=str, label='foo')}
        self.assertEqual(repr(r), repr(wf))

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

    def test_run_annotated(self):
        m = run(FlagConversionOff[OmitArgPrefixes[SimpleEnv]])
        self.assertEqual(4, m.env.important_number)

    def test_config_unknown(self):
        """ An unknown field in the config file should emit a warning. """

        def r(model):
            run(model, config_file="tests/unknown.yaml", interface=Mininterface)

        for model in (PydNested, SimpleEnv, AttrsNested):
            with warnings.catch_warnings(record=True) as w:
                r(model)
                self.assertIn("Unknown fields in the configuration file", str(w[0].message))

    def test_settings(self):
        # NOTE
        # The settings had little params at the moment of the test writing.
        # when there is more settings, use the actual objects instead of the dumb ones here.
        # Then, you might get rid of the dumb_settings.py and _def_fact factory parameter in _merge_settings.

        opt1 = MininterfaceSettings(gui=GuiSettings(combobox_since=1))
        opt2 = MininterfaceSettings(gui=GuiSettings(combobox_since=10))
        self.assertEqual(opt1, _merge_settings(None, {'gui': {'combobox_since': 1}}, MininterfaceSettings))

        # config file settings are superior to the program-given settings
        self.assertEqual(opt1, _merge_settings(opt2, {'gui': {'combobox_since': 1}}, MininterfaceSettings))

        opt3 = MininterfaceSettings(
            ui=UiDumb(foo=3, p_config=0, p_dynamic=0),
            gui=GuiSettings(foo=3, p_config=0, p_dynamic=0, combobox_since=5, test=False),
            tui=TuiSettings(foo=3, p_config=2, p_dynamic=0),
            textual=TextualSettings(foo=3, p_config=1, p_dynamic=0, foobar=74),
            text=TextSettings(foo=3, p_config=2, p_dynamic=0),
            web=WebSettings(foo=3, p_config=1, p_dynamic=0, foobar=74), interface=None)

        def conf():
            return {'textual': {'p_config': 1}, 'tui': {'p_config': 2}, 'ui': {'foo': 3}}
        self.assertEqual(opt3, _merge_settings(None, conf(), MininterfaceSettings))

        opt4 = MininterfaceSettings(text=TextSettings(p_dynamic=200),
                                    tui=TuiSettings(p_dynamic=100, p_config=100, foo=100))

        res4 = MininterfaceSettings(
            ui=UiDumb(foo=3, p_config=0, p_dynamic=0),
            gui=GuiSettings(foo=3, p_config=0, p_dynamic=0, combobox_since=5, test=False),
            tui=TuiSettings(foo=100, p_config=2, p_dynamic=100),
            textual=TextualSettings(foo=100, p_config=1, p_dynamic=100, foobar=74),
            text=TextSettings(foo=100, p_config=2, p_dynamic=200),
            web=WebSettings(foo=100, p_config=1, p_dynamic=100, foobar=74), interface=None)
        self.assertEqual(res4, _merge_settings(opt4, conf(), MininterfaceSettings))

    def test_settings_inheritance(self):
        """ The interface gets the relevant settings section, not whole MininterfaceSettings """
        opt1 = MininterfaceSettings(gui=GuiSettings(combobox_since=1))
        m = run(settings=opt1, interface=Mininterface)
        self.assertIsInstance(m, Mininterface)
        self.assertIsInstance(m._adaptor.settings, UiSettings)

    def test_argparse(self):
        parser = ArgumentParser(description="Test parser for dataclass generation.")
        # positional
        parser.add_argument("input_file", type=str, help="Path to the input file.")
        parser.add_argument("output_dir", type=str, help="Directory where output will be saved.")
        # optional with/out defaults
        parser.add_argument("--verbosity", type=int, default=1, help="Verbosity level.")
        # attention, an empty path will become Path('.'), not None
        parser.add_argument("--config", type=Path, help="Optional path to config file.")
        # action=store_true
        parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
        # action=store_false
        parser.add_argument("--no-color", dest="color", action="store_false", help="Disable colored output.")
        # append
        parser.add_argument("--tag", action="append", help="Add one or more tags.")
        # subparsers
        subparsers = parser.add_subparsers(dest="command", required=True)
        sub1 = subparsers.add_parser("build", help="Build something.")
        sub1.add_argument("--optimize", action="store_true", help="Enable optimizations.")
        sub1.add_argument("--target", type=str, help="Build target platform.")
        sub2 = subparsers.add_parser("deploy", help="Deploy something.")
        # NOTE handling missing values in subparsers is not implemented (we defer to tyro exception)
        # sub2.add_argument("host", type=str, help="Remote host.")
        sub2.add_argument("--port", type=int, default=22, help="SSH port.")
        sub2.add_argument("--user", type=str, default="root", help="SSH user.")

        with self.assertRaises(SystemExit) as cm:
            run(parser, interface=Mininterface)
        self.assertEqual("""input_file: Type must be str!
output_dir: Type must be str!
the following arguments are required: STR, STR""", cm.exception.code)

        env = run(parser, args=["/tmp/file", "/tmp"], interface=Mininterface).form()

        PathType = type(Path(""))  # PosixPath on Linux
        self.assertEqual(
            f"""Args(build=Build(optimize=False, target=''), deploy=Deploy(port=22, user='root'), input_file='/tmp/file', output_dir='/tmp', verbosity=1, config={PathType.__name__}('.'), debug=False, color=True, tag=[])""",
            repr(env))


class TestValidators(TestAbstract):
    def test_not_empty(self):
        t1 = Tag("", validation=not_empty)
        self.assertFalse(t1.update(""))
        self.assertTrue(t1.update("1"))

        t2 = Tag(validation=not_empty, annotation=Path)
        self.assertFalse(t2.update(b""))
        self.assertFalse(t2.update(b"wrong type"))
        self.assertFalse(t2.update(Path("")))
        self.assertFalse(t2.update(Path(".")))
        self.assertTrue(t2.update(Path("/tmp")))

        t3 = Tag(validation=not_empty, annotation=bytes)
        self.assertFalse(t3.update(b""))
        self.assertTrue(t3.update(b"true"))

        t4 = DatetimeTag(validation=not_empty, annotation=time)
        self.assertFalse(t4.update(""))
        self.assertTrue(t4.update("12:12"))
        self.assertTrue(t4.update(time(10, 10)))
        self.assertFalse(t4.update(""))
        # This would pass through (if it's not midnight), as the _make_default_value is currently the current time,
        # not `time()`. We might implement it other way.
        self.assertTrue(t4.update(time()))

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

    def test_assure_tag(self):
        t = assure_tag(int, Gt(1))
        for x in ("0", 0, 1, 2.5):
            self.assertFalse(t.update(x))
        for x in ("5", 5):
            self.assertTrue(t.update(x))

        t2 = assure_tag(Tag(annotation=float, validation=Gt(3)), Lt(100))
        for x in ("0", 0, 1, 2.5, 100.0):
            self.assertFalse(t2.update(x))
        for x in ("5", 5.0, 99.9):
            self.assertTrue(t2.update(x))

    def test_annotated_types(self):
        d: TagDict = dataclass_to_tagdict(AnnotatedTypes())[""]

        for i in ("19", 1000):
            self.assertTrue(d["age"].update(i))

        for i in (18, 18.0, "18.1", 19.5, False, "str"):
            self.assertFalse(d["age"].update(i))

        for i in (1, 2, 100):
            self.assertTrue(d["percent"].update(i))
        for i in (-1, 0, 101, 99.9):
            self.assertFalse(d["percent"].update(i))

        for i in (0.1, 1.0, "1", "2", "100", 99.9):
            self.assertTrue(d["percent_fl"].update(i), i)
        for i in (0.0, 1, 2):
            self.assertFalse(d["percent_fl"].update(i), i)

        for i in (0, 9, 10):
            self.assertTrue(d["my_list"].update([0]*i), i)

        for i in (11, 100):
            self.assertFalse(d["my_list"].update([0]*i), i)

    def test_annotated_types_combined(self):
        d: TagDict = dataclass_to_tagdict(AnnotatedTypesCombined())[""]

        for i in (-99, 0, 2, 40):
            self.assertTrue(d["combined1"].update(i), i)
            self.assertTrue(d["combined2"].update(i), i)
            self.assertTrue(d["combined3"].update(i), i)

        for i in (-1000, -100, 60, 90, 100):
            self.assertFalse(d["combined1"].update(i), i)
            self.assertFalse(d["combined2"].update(i), i)
            self.assertFalse(d["combined3"].update(i), i)

        # transforming funcion is before the annotated-types
        i = 49
        self.assertTrue(d["combined1"].update(i), i)
        self.assertTrue(d["combined2"].update(i), i)
        self.assertTrue(d["combined3"].update(i), i)
        self.assertFalse(d["combined4"].update(i), i)


class TestLog(TestAbstract):
    @staticmethod
    def log(object=SimpleEnv):
        run(object, interface=Mininterface)
        logger = logging.getLogger(__name__)
        logger.debug("debug level")
        logger.info("info level")
        logger.warning("warning level")
        logger.error("error level")

    @patch('logging.basicConfig')
    def test_run_verbosity0(self, mock_basicConfig):
        self.sys("-v")
        with self.assertRaises(SystemExit):
            run(SimpleEnv, add_verbose=False, interface=Mininterface)
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

    @patch('logging.basicConfig')
    def test_custom_verbosity(self, mock_basicConfig):
        """ We use an object, that has verbose attribute too. Which interferes with the one injected. """
        self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()

        self.sys("-v")
        with (self.assertStderr(contains="running-tests: error: unrecognized arguments: -v"), self.assertRaises(SystemExit)):
            self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()


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

        f: Tag = dataclass_to_tagdict(m.env)["inner"]["name"]
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

        f: Tag = dataclass_to_tagdict(m.env)["inner"]["name"]
        self.assertTrue(f.update("short"))
        self.assertEqual("Restrained name ", f.description)
        self.assertFalse(f.update("long words"))
        self.assertEqual("Length of 'check' must be <= 5: 10 Restrained name ", f.description)
        self.assertTrue(f.update(""))
        self.assertEqual("Restrained name ", f.description)


class TestAnnotated(TestAbstract):
    # NOTE some of the entries are not well supported
    # NOTE The same should be for pydantic and attrs.

    def test_annotated(self):
        m = run(ConstrainedEnv)
        d: TagDict = dataclass_to_tagdict(m.env)[""]
        self.assertFalse(d["test"].update(""))
        self.assertFalse(d["test2"].update(""))
        self.assertTrue(d["test"].update(" "))
        self.assertTrue(d["test2"].update(" "))

    def test_class(self):
        with self.assertRaises(SystemExit):
            m = run(AnnotatedClass, interface=Mininterface)

        m = run(AnnotatedClass, args=["[]", "--files2", "[]"], interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertEqual(list[Path], d["files1"].annotation)
        self.assertEqual(list[Path], d["files2"].annotation)
        self.assertEqual(list[Path], d["files3"].annotation)
        # self.assertEqual(list[Path], d["files4"].annotation)  # does not work
        self.assertEqual(list[Path], d["files5"].annotation)
        # This does not work, however I do not know what should be the result
        # self.assertEqual(list[Path], d["files6"].annotation)
        # self.assertEqual(list[Path], d["files7"].annotation)
        # self.assertEqual(list[Path], d["files8"].annotation)

    def test_positional(self):
        # all arguments passed well, positional, positional with default and required flag
        m = runm(AnnotatedClass3, args=["1", "True", "False", "--foo2", "--foo3", "/tmp"])
        self.assertEqual(AnnotatedClass3(foo1=1, foo2=[], foo3=[PosixPath('/tmp')], foo4=[True, False]),
                         m.env)

        # positional but defaulted argument not mentioned
        self.assertEqual(AnnotatedClass3(foo1=1, foo2=[], foo3=[PosixPath('/tmp')], foo4=[]),
                         runm(AnnotatedClass3, args=["1", "--foo2", "--foo3", "/tmp"]).env)

        # required positional missing
        with self.assertRaises(SystemExit):
            runm(AnnotatedClass3, args=["--foo2", "--foo3", "/tmp"])

        # missing required flag
        with self.assertRaises(SystemExit):
            runm(AnnotatedClass3, args=["1", "--foo2"])

        # In the current implementation,
        # the validation is done not at dataclass built, but on the form call.
        # Hence, missing --foo3 will not raise an issue on run,
        # but later on the form call.
        # I'm not sure that this is the best behaviour and thus might be changed.
        m.form()
        m2 = runm(AnnotatedClass3, args=["1", "--foo2", "--foo3"])
        with self.assertRaises(SystemExit):
            m2.form()

    def test_inherited_class(self):
        # Without _parse_cli / yield_annotations on inherited members, it produced
        # UserWarning: Could not find field files6 in default instance namespace()
        with self.assertStderr(not_contains="Could not find field"), self.assertRaises(SystemExit):
            m = run(InheritedAnnotatedClass, interface=Mininterface)
        m = run(InheritedAnnotatedClass, args=["--files1", "/tmp"], interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertEqual(list[Path], d["files1"].annotation)
        # self.assertEqual(list[Path], d["files2"].annotation) does not work
        self.assertEqual(list[Path], d["files3"].annotation)
        self.assertEqual(list[Path], d["files4"].annotation)
        self.assertEqual(list[Path], d["files5"].annotation)
        # This does not work, however I do not know what should be the result
        # self.assertEqual(list[Path], d["files6"].annotation)
        # self.assertEqual(list[Path], d["files7"].annotation)
        # self.assertEqual(list[Path], d["files8"].annotation)

    def test_missing_positional(self):
        m = run(MissingPositional, interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertReprEqual(
            {'files': PathTag(val=[], description='files ', annotation=list[Path], label='files')}, d)


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
        _([(list, str), (tuple, [int])], None | list[str] | tuple[int])
        _([(list, int), (tuple, [str]), (None, str)], list[int] | tuple[str] | str | None)

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
        _(tuple[int, int], tuple[int, int])
        _(Path, tuple[int, int], true=False)

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
        self.assertTrue(t.update(""))  # an empty input gets converted to an empty list
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
        with self.assertRaises(SystemExit):
            m = run(ParametrizedGeneric, interface=Mininterface, ask_for_missing=False)

        with self.assertRaises(SystemExit):
            m = run(ParametrizedGeneric, interface=Mininterface)
        env = ParametrizedGeneric([])
        f = dataclass_to_tagdict(env)[""]["paths"]
        self.assertEqual([], f.val)
        self.assertTrue(f.update("[]"))

        self.sys("--paths", "/usr", "/tmp")
        m = run(ParametrizedGeneric, interface=Mininterface)
        f = dataclass_to_tagdict(m.env)[""]["paths"]
        self.assertEqual([Path("/usr"), Path("/tmp")], f.val)
        self.assertEqual(['/usr', '/tmp'], f._get_ui_val())
        self.assertTrue(f.update("['/var']"))
        self.assertEqual([Path("/var")], f.val)
        self.assertEqual(['/var'], f._get_ui_val())

    def test_select_method(self):
        m = run(interface=Mininterface)
        with self.assertRaises(SystemExit):
            m.select((1, 2, 3))
        self.assertEqual(2, m.select((1, 2, 3), default=2))
        self.assertEqual(2, m.select((1, 2, 3), default=2))
        self.assertEqual(2, m.select({"one": 1, "two": 2}, default=2))
        self.assertEqual(2, m.select([Tag(1, label="one"), Tag(2, label="two")], default=2))

        # Enum type
        self.assertEqual(ColorEnum.GREEN, m.select(ColorEnum, default=ColorEnum.GREEN))

        # list of enums
        self.assertEqual(ColorEnum.GREEN, m.select([ColorEnum.BLUE, ColorEnum.GREEN], default=ColorEnum.GREEN))
        self.assertEqual(ColorEnum.BLUE, m.select([ColorEnum.BLUE]))
        with self.assertRaises(SystemExit):
            self.assertEqual(m.select([ColorEnum.RED, ColorEnum.GREEN]))

        # Enum instance signify the default
        self.assertEqual(ColorEnum.RED, m.select(ColorEnum.RED))

    def test_dynamic_description(self):
        """ This is an undocumented feature.
        When you need a dynamic text, you may use tyro's arg to set it.
        """
        m = run(DynamicDescription, interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        # tyro seems to add a space after the description in such case, I don't know why
        self.assertEqual("My dynamic str ", d["foo"].description)


class TestSubcommands(TestAbstract):

    form1 = "Asking the form {'foo': Tag(val=0, description='', annotation=<class 'int'>, label='foo'), "\
        "'Subcommand1': {'': {'a': Tag(val=1, description='', annotation=<class 'int'>, label='a'), "\
        "'Subcommand1': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}, "\
        "'Subcommand2': {'': {'b': Tag(val=0, description='', annotation=<class 'int'>, label='b'), "\
        "'Subcommand2': Tag(val=<lambda>, description=None, annotation=<class 'function'>, label=None)}}}"

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
        self.assertForms([
            {'SubcommandB1': {'':
                              {'foo': Tag(val=7, description='', annotation=int, label='foo'),
                               'a': Tag(val=1, description='', annotation=int, label='a'),
                               'SubcommandB1': Tag(val=lambda: True, description=None, annotation=Callable, label=None)}},
             'SubcommandB2': {'':
                              {'foo': Tag(val=7, description='', annotation=int, label='foo'), 'b': Tag(val=2, description='', annotation=int, label='b'), 'SubcommandB2': Tag(val=lambda: True, description=None, annotation=Callable, label=None)
                               }},
             'PydModel': {'':
                          {'test': Tag(val=False, description='My testing flag ', annotation=bool, label='test'), 'name': Tag(val='hello', description='Restrained name ', annotation=str, label='name'), 'PydModel': Tag(val='disabled', description='Subcommand PydModel does not inherit from the Command. Hence it is disabled.', annotation=str, label=None)}},
             'AttrsModel': {'':
                            {'test': Tag(val=False, description='My testing flag ', annotation=bool, label='test'), 'name': Tag(val='hello', description='Restrained name ', annotation=str, label='name'), 'AttrsModel': Tag(val='disabled', description='Subcommand AttrsModel does not inherit from the Command. Hence it is disabled.', annotation=str, label=None)}}}
        ])
        with self.assertOutputs(form2), self.assertStderr(contains=warn2):
            runm([SubcommandB1, SubcommandB2, PydModel, AttrsModel], args=[])

        m = runm([SubcommandB1, SubcommandB2, PydModel, AttrsModel], args=["pyd-model", "--name", "me"])
        self.assertEqual("me", m.env.name)

    def DISABLED_test_choose_subcommands(self):
        # NOTE Subcommand changed a bit. Now, it's a bigger task to test it. Do first self.DISABLED_test_integrations().
        return
        values = ["{'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'a': Tag(val=1, description='', annotation=<class 'int'>, label='a')}}",
                  "{'': {'foo': Tag(val=7, description='', annotation=<class 'int'>, label='foo'), 'b': Tag(val=2, description='', annotation=<class 'int'>, label='b')}}"]

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
        self.cli([Subcommand1, Subcommand2])

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

        self.cli(subcommands)

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
        with (self.assertOutputs(contains="Use this placeholder to choose the subcommand via"), self.assertRaises(SystemExit)):
            r(["--help"])

        # placeholder help works and shows shared arguments of other subcommands
        with (self.assertOutputs(contains="Class with a shared argument."), self.assertRaises(SystemExit)):
            r(["subcommand", "--help"])

    def test_common_field_annotation(self):
        with self.assertForms([
            ({'paths': PathTag(val=MISSING, description='', annotation=list[Path], label='paths')},
             {"paths": "['/tmp']"}
             )]), self.assertRaises(Cancelled):
            runm([ParametrizedGeneric, ParametrizedGeneric])


class TestSecretTag(TestAbstract):
    """Tests for SecretTag functionality"""

    def test_secret_masking(self):
        secret = SecretTag("mysecret")
        self.assertEqual("••••••••", secret._get_masked_val())

        self.assertFalse(secret.toggle_visibility())
        self.assertEqual("mysecret", secret._get_masked_val())

    def test_toggle_visibility(self):
        secret = SecretTag("test", show_toggle=False)
        self.assertTrue(secret._masked)
        self.assertFalse(secret.toggle_visibility())
        self.assertFalse(secret._masked)

    def test_repr_safety(self):
        secret = SecretTag("sensitive_data")
        self.assertEqual("SecretTag(masked_value)", repr(secret))

    def test_annotation_default(self):
        secret = SecretTag("test")
        self.assertEqual(str, secret.annotation)


class TestSelectTag(TestAbstract):
    def test_options_param(self):
        t = SelectTag("one", options=["one", "two"])
        t.update("two")
        self.assertEqual(t.val, "two")
        t.update("three")
        self.assertEqual(t.val, "two")

        m = run(ConstrainedEnv)
        d = dataclass_to_tagdict(m.env)
        self.assertFalse(d[""]["options"].update(""))
        self.assertTrue(d[""]["options"].update("two"))

        # dict is the input
        t = SelectTag(1, options={"one": 1, "two": 2})
        self.assertFalse(t.update("two"))
        self.assertEqual(1, t.val)
        self.assertTrue(t.update(2))
        self.assertEqual(2, t.val)
        self.assertFalse(t.update(3))
        self.assertEqual(2, t.val)
        self.assertTrue(t.update(1))
        self.assertEqual(1, t.val)
        self.assertFalse(t.multiple)

        # list of Tags are the input
        t1 = Tag(1, label="one")
        t2 = Tag(2, label="two")
        t = SelectTag(1, options=[t1, t2])
        self.assertTrue(t.update(2))
        self.assertEqual(t2.val, t.val)
        self.assertFalse(t.update(3))
        self.assertEqual(t2.val, t.val)
        self.assertTrue(t.update(1))
        self.assertEqual(t1.val, t.val)
        self.assertFalse(t.multiple)

    def test_select_enum(self):
        # Enum type supported
        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum)
        t1.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE, t1.val)

        # list of enums supported
        t2 = SelectTag(ColorEnum.GREEN, options=[ColorEnum.BLUE, ColorEnum.GREEN])
        self.assertEqual({str(v.value): v for v in [ColorEnum.BLUE, ColorEnum.GREEN]}, t2._build_options())
        t2.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE, t2.val)

        # Enum type supported even without explicit definition
        t3 = SelectTag(ColorEnum.GREEN)
        self.assertEqual(ColorEnum.GREEN.value, t3._get_ui_val())
        self.assertEqual({str(v.value): v for v in list(ColorEnum)}, t3._build_options())
        t3.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE.value, t3._get_ui_val())
        self.assertEqual(ColorEnum.BLUE, t3.val)

        # We pass the EnumType which does not include the default options.
        t4 = Tag(ColorEnum)
        # But the Tag itself does not work with the Enum, so it does not reset the value.
        self.assertIsNotNone(t4.val)
        # Raising a form will automatically invoke the SelectTag instead of the Tag.
        t5 = tag_assure_type(t4)
        # The SelectTag resets the value.
        self.assertIsNone(t5.val)

        [self.assertFalse(t.multiple) for t in (t1, t2, t3, t5)]

    def test_tips(self):
        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum)
        self.assertListEqual([
            ('1', ColorEnum.RED, False, ('1', )),
            ('2', ColorEnum.GREEN, False, ('2', )),
            ('3', ColorEnum.BLUE, False, ('3', )),
        ], t1._get_options())

        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum, tips=[ColorEnum.BLUE])
        self.assertListEqual([
            ('3', ColorEnum.BLUE, True, ('3', )),
            ('1', ColorEnum.RED, False, ('1', )),
            ('2', ColorEnum.GREEN, False, ('2', )),
        ], t1._get_options())

    def test_tupled_label(self):
        t1 = SelectTag(options={("one", "half"): 11, ("second", "half"): 22, ("third", "half"): 33})
        self.assertListEqual([
            ('one    - half', 11, False, ('one', 'half')),
            ('second - half', 22, False, ('second', 'half')),
            ('third  - half', 33, False, ('third', 'half')),
        ], t1._get_options())

    def test_label_resilience(self):
        """ Convert the labels to str. """
        # In this test, we are using a type as label.
        t1 = SelectTag(options={("one", ColorEnum): 11, ("second", "half"): 22, ("third", "half", "another"): 33})
        self.assertListEqual([("one - <enum 'ColorEnum'>", 11, False, ('one', "<enum 'ColorEnum'>")),
                              ('second - half', 22, False, ('second', 'half')),
                              ('third - half - another', 33, False, ('third', 'half', 'another'))],
                             t1._get_options())

    def test_multiple(self):
        options = {("one", "half"): 11, ("second", "half"): 22, ("third", "half"): 33}
        t1 = SelectTag(options=options)
        t2 = SelectTag(11, options=options)
        t3 = SelectTag([11], options=options)
        t4 = SelectTag([11, 33], options=options)
        t5 = SelectTag(options=options, multiple=True)

        [self.assertTrue(t.multiple) for t in (t3, t4, t5)]
        [self.assertFalse(t.multiple) for t in (t1, t2)]

        with self.assertRaises(TypeError), redirect_stderr(StringIO()):
            self.assertFalse(t3.update(22))

        self.assertListEqual([11], t3.val)
        self.assertTrue(t3.update([22]))
        self.assertListEqual([22], t3.val)

        self.assertListEqual([11, 33], t4.val)
        self.assertTrue(t4.update([22, 11]))
        self.assertListEqual([22, 11], t4.val)

    def test_build_options(self):
        t = SelectTag()
        self.assertDictEqual({}, t._build_options())

        t.options = {"one": 1}
        self.assertDictEqual({"one": 1}, t._build_options())

        t.options = {"one": Tag(1, label="one")}
        self.assertDictEqual({"one": 1}, t._build_options())

        t.options = [Tag(1, label="one"), Tag(2, label="two")]
        self.assertDictEqual({"one": 1, "two": 2}, t._build_options())

        t.options = {("one", "col2"): Tag(1, label="one"), ("three", "column3"): 3}
        self.assertDictEqual({("one", "col2"): 1, ("three", "column3"): 3}, t._build_options())

        t.options = [Tag(1, label='A')]
        self.assertDictEqual({"A": 1}, t._build_options())


if __name__ == '__main__':
    main()
