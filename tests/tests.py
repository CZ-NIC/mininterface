from io import StringIO
import logging
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from mininterface import Mininterface, TextInterface, run
from mininterface.FormField import FormField
from mininterface.Mininterface import Cancelled
from mininterface.FormDict import dataclass_to_formdict, formdict_repr
from configs import OptionalFlagEnv, SimpleEnv, NestedDefaultedEnv, NestedMissingEnv
from mininterface.auxiliary import flatten

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


class TestBasic(TestAbstract):
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

    def test_run_ask_empty(self):
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(SimpleEnv, True, interface=Mininterface)
            self.assertEqual("Asking the form  None", stdout.getvalue().strip())
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run(SimpleEnv, interface=Mininterface)
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

    def test_normalize_types(self):
        """ Conversion str("") to None and back.
        When using GUI interface, we input an empty string and that should mean None
        for annotation `int | None`.
        """
        origin = {'': {'test': FormField(False, 'Testing flag ', annotation=None),
                       'numb': FormField(4, 'A number', annotation=None),
                       'severity': FormField('', 'integer or none ', annotation=int | None),
                       'msg': FormField('', 'string or none', annotation=str | None)}}
        data = {'': {'test': False, 'numb': 4, 'severity': 'fd', 'msg': ''}}

        self.assertFalse(FormField.submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': ''}}
        self.assertTrue(FormField.submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '', 'msg': ''}}
        self.assertTrue(FormField.submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': 'Text'}}
        self.assertTrue(FormField.submit(origin, data))

        # check value is kept if revision needed
        self.assertEqual(False, origin[""]["test"].val)
        data = {'': {'test': True, 'numb': 100, 'severity': '1', 'msg': 1}}  # ui put a wrong 'msg' type
        self.assertFalse(FormField.submit(origin, data))
        self.assertEqual(True, origin[""]["test"].val)
        self.assertEqual(100, origin[""]["numb"].val)

        # Check flat FormDict
        origin = {'test': FormField(False, 'Testing flag ', annotation=None),
                  'severity': FormField('', 'integer or none ', annotation=int | None),
                  'nested': {'test2': FormField(4, '')}}
        #   'nested': {'test2': 4}} TODO, allow combined FormDict
        data = {'test': True, 'severity': "", 'nested': {'test2': 8}}
        self.assertTrue(FormField.submit(origin, data))
        data = {'test': True, 'severity': "str", 'nested': {'test2': 8}}
        self.assertFalse(FormField.submit(origin, data))

    def test_env_instance_dict_conversion(self):
        m: TextInterface = run(OptionalFlagEnv, interface=TextInterface, prog="My application")
        env1: OptionalFlagEnv = m.env

        self.assertIsNone(env1.severity)

        fd = dataclass_to_formdict(env1, m._descriptions)
        ui = formdict_repr(fd)
        self.assertEqual({'': {'severity': '', 'msg': '', 'msg2': 'Default text'},
                          'further': {'deep': {'flag': False}, 'numb': 0}}, ui)
        self.assertIsNone(env1.severity)

        # do the same as if the tkinter_form was just submitted without any changes
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

        # changes in the UI should not directly affect the original
        ui[""]["msg2"] = "Another"
        ui[""]["severity"] = 5
        ui["further"]["deep"]["flag"] = True
        self.assertEqual("Default text", env1.msg2)

        # on UI submit, the original is affected
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertEqual("Another", env1.msg2)
        self.assertEqual(5, env1.severity)
        self.assertTrue(env1.further.deep.flag)

        # Another UI changes, makes None from an int
        ui[""]["severity"] = ""  # UI is not able to write None, it does an empty string instead
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

    def test_ask_form(self):
        m = TextInterface()
        dict1 = {"my label": FormField(True, "my description"), "nested": {"inner": "text"}}
        with patch('builtins.input', side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.form(dict1)
        self.assertEqual({"my label": FormField(True, "my description"), "nested": {"inner": "another"}}, dict1)

        # Empty form invokes editing self.env, which is empty
        with patch('builtins.input', side_effect=["c"]):
            self.assertEqual(SimpleNamespace(), m.form())

        # Empty form invokes editing self.env, which contains a dataclass
        m2 = run(SimpleEnv, interface=TextInterface, prog="My application")
        self.assertFalse(m2.env.test)
        with patch('builtins.input', side_effect=["v.test = True", "c"]):
            self.assertEqual(m2.env, m2.form())
            self.assertTrue(m2.env.test)


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


if __name__ == '__main__':
    main()
