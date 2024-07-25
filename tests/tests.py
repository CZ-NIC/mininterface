import sys
from unittest import TestCase, main
from unittest.mock import patch

from mininterface import Mininterface, TextInterface, run
from mininterface.FormField import FormField
from mininterface.Mininterface import Cancelled
from mininterface.FormDict import config_to_formdict, formdict_repr
from configs import OptionalFlagConfig, SimpleConfig, NestedDefaultedConfig, NestedMissingConfig
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

        m1: TextInterface = run(NestedDefaultedConfig, interface=TextInterface, prog="My application")
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
        data = {'': {'test': True, 'numb': 100, 'severity': '1', 'msg': 1}}
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

    def test_config_instance_dict_conversion(self):
        m: TextInterface = run(OptionalFlagConfig, interface=TextInterface, prog="My application")
        args1: OptionalFlagConfig = m.args

        self.assertIsNone(args1.severity)

        fd = config_to_formdict(args1, m.descriptions)
        ui = formdict_repr(fd)
        self.assertEqual({'': {'severity': '', 'msg': '', 'msg2': 'Default text'},
                          'further': {'deep': {'flag': False}, 'numb': 0}}, ui)
        self.assertIsNone(args1.severity)

        # do the same as if the tkinter_form was just submitted without any changes
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(args1.severity)

        # changes in the UI should not directly affect the original
        ui[""]["msg2"] = "Another"
        ui[""]["severity"] = 5
        ui["further"]["deep"]["flag"] = True
        self.assertEqual("Default text", args1.msg2)

        # on UI submit, the original is affected
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertEqual("Another", args1.msg2)
        self.assertEqual(5, args1.severity)
        self.assertTrue(args1.further.deep.flag)

        # Another UI changes, makes None from an int
        ui[""]["severity"] = ""  # UI is not able to write None, it does an empty string instead
        FormField.submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(args1.severity)

    def test_ask_form(self):
        m = TextInterface()
        dict1 = {"my label": FormField(True, "my description"), "nested": {"inner": "text"}}
        with patch('builtins.input', side_effect=["v['nested']['inner'] = 'another'", "c"]):
            m.ask_form(dict1)
        self.assertEqual({"my label": FormField(True, "my description"), "nested": {"inner": "another"}}, dict1)


if __name__ == '__main__':
    main()
