import sys
from unittest import TestCase, main
from unittest.mock import patch

from mininterface import Mininterface, TuiInterface, Value, run
from mininterface.Mininterface import Cancelled
from mininterface.auxiliary import config_from_dict, config_to_dict, normalize_types
from configs import OptionalFlagConfig, SimpleConfig, NestedDefaultedConfig, NestedMissingConfig

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

    def test_basic(self):
        def go(*_args) -> SimpleConfig:
            self.sys(*_args)
            return run(SimpleConfig, interface=Mininterface, prog="My application").get_args()

        self.assertEqual(4, go().important_number)
        self.assertEqual(False, go().test)
        self.assertEqual(5, go("--important-number", "5").important_number)
        self.assertEqual(6, go("--important-number=6").important_number)
        self.assertEqual(7, go("--important_number=7").important_number)

        self.sys("--important_number='8'")
        self.assertRaises(SystemExit, lambda: run(SimpleConfig, interface=Mininterface, prog="My application"))

    def test_cli_complex(self):
        def go(*_args) -> NestedDefaultedConfig:
            self.sys(*_args)
            return run(NestedDefaultedConfig, interface=Mininterface, prog="My application").get_args()

        self.assertEqual("example.org", go().further.host)
        self.assertEqual("example.com", go("--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go("--further.host='example.net'").further.host)
        self.assertEqual("example.org", go("--further.host", 'example.org').further.host)
        self.assertEqual("example org", go("--further.host", 'example org').further.host)

        def go2(*_args) -> NestedMissingConfig:
            self.sys(*_args)
            return run(NestedMissingConfig, interface=Mininterface, prog="My application").get_args()
        self.assertEqual("example.org", go2("--further.token=1").further.host)
        self.assertEqual("example.com", go2("--further.token=1", "--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go2("--further.token=1", "--further.host='example.net'").further.host)
        self.sys("--further.host='example.net'")
        self.assertRaises(SystemExit, lambda: run(SimpleConfig, interface=Mininterface, prog="My application"))

    def test_ask(self):
        m0 = run(NestedDefaultedConfig, interface=Mininterface, prog="My application")
        self.assertEqual(0, m0.ask_number("Test input"))

        m1: TuiInterface = run(NestedDefaultedConfig, interface=TuiInterface, prog="My application")
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
        origin = {'': {'test': Value(False, 'Testing flag ', annotation=None),
                       'numb': Value(4, 'A number', annotation=None),
                       'severity': Value('', 'integer or none ', annotation=int | None),
                       'msg': Value('', 'string or none', annotation=str | None)}}
        data = {'': {'test': False, 'numb': 4, 'severity': 'fd', 'msg': ''}}
        self.assertFalse(normalize_types(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': ''}}
        self.assertTrue(normalize_types(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '', 'msg': ''}}
        self.assertTrue(normalize_types(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': 'Text'}}
        self.assertTrue(normalize_types(origin, data))

        # check value is kept if revision needed
        self.assertEqual(False, origin[""]["test"].val)
        data = {'': {'test': True, 'numb': 100, 'severity': '1', 'msg': 1}}
        self.assertFalse(normalize_types(origin, data))
        self.assertEqual(True, origin[""]["test"].val)
        self.assertEqual(100, origin[""]["numb"].val)

        # Check flat FormDict
        origin = {'test': Value(False, 'Testing flag ', annotation=None),
                  'severity': Value('', 'integer or none ', annotation=int | None),
                  'nested': {'test2': 4}}
        data = {'test': True, 'severity': "", 'nested': {'test2': 8}}
        self.assertTrue(normalize_types(origin, data))
        data = {'test': True, 'severity': "str", 'nested': {'test2': 8}}
        self.assertFalse(normalize_types(origin, data))

    def test_config_instance_dict_conversion(self):
        m: TuiInterface = run(OptionalFlagConfig, interface=TuiInterface, prog="My application")
        args1: OptionalFlagConfig = m.args

        self.assertIsNone(args1.further.severity)

        dict1 = config_to_dict(args1, m.descriptions)
        self.assertEqual({'': {'msg': Value('', '', str | None),
                               'msg2': Value('Default text', '', None)},
                          'further': {'severity': Value('', '', int | None)}}, dict1)
        self.assertIsNone(args1.further.severity)

        # do the same as if the tkinter_form was just submitted without any changes
        dict1 = normalize_types(dict1, {'': {'msg': "",
                                             'msg2': 'Default text'},
                                        'further': {'severity': ''}})

        config_from_dict(args1, dict1)
        self.assertIsNone(args1.further.severity)
        dict1[""]["msg2"] = "Another"
        dict1["further"]["severity"] = 5
        self.assertEqual("Default text", args1.msg2)

        config_from_dict(args1, dict1)
        self.assertEqual("Another", args1.msg2)
        self.assertEqual(5, args1.further.severity)

    def test_ask_form(self):
        m = TuiInterface()
        dict1 = {"my label": Value(True, "my description"), "nested": {"inner": "text"}}
        with patch('builtins.input', side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.ask_form(dict1)
        self.assertEqual({"my label": Value(True, "my description"), "nested": {"inner": "another"}}, dict1)


if __name__ == '__main__':
    main()
