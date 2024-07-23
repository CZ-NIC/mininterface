from argparse import Namespace
from dataclasses import dataclass
from io import StringIO
import sys
from unittest import TestCase, main
from unittest.mock import patch

from mininterface import Mininterface, TuiInterface, run
from mininterface.Mininterface import Cancelled

# NOTE then add [![Build Status](https://github.com/CZ-NIC/mininterface/actions/workflows/run-unittest.yml/badge.svg)](https://github.com/CZ-NIC/mininterface/actions)


@dataclass
class Config:
    """Set of options."""
    test: bool = False
    """My testing flag"""
    important_number: int = 4
    """This number is very important"""


@dataclass
class FurtherConfig1:
    token: str = "filled"
    host: str = "example.org"


@dataclass
class RootConfig1:
    further: FurtherConfig1


@dataclass
class FurtherConfig2:
    token: str
    host: str = "example.org"


@dataclass
class RootConfig2:
    further: FurtherConfig2


SYS_ARGV = None  # To be redirected


class TestAbstract(TestCase):
    @classmethod
    def setUpClass(cls):
        global SYS_ARGV
        SYS_ARGV = sys.argv
        cls.sys()

    @classmethod
    def tearDownClass(cls):
        global SYS_ARGV
        sys.argv = SYS_ARGV

    @classmethod
    def sys(cls, *args):
        sys.argv = ["running-tests", *args]

    def test_basic(self):
        def go(*_args) -> Config:
            self.sys(*_args)
            return run(Config, interface=Mininterface, prog="My application").get_args()

        self.assertEqual(4, go().important_number)
        self.assertEqual(False, go().test)
        self.assertEqual(5, go("--important-number", "5").important_number)
        self.assertEqual(6, go("--important-number=6").important_number)
        self.assertEqual(7, go("--important_number=7").important_number)

        self.sys("--important_number='8'")
        self.assertRaises(SystemExit, lambda: run(Config, interface=Mininterface, prog="My application"))

    def test_cli_complex(self):
        def go(*_args) -> RootConfig1:
            self.sys(*_args)
            return run(RootConfig1, interface=Mininterface, prog="My application").get_args()

        self.assertEqual("example.org", go().further.host)
        self.assertEqual("example.com", go("--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go("--further.host='example.net'").further.host)
        self.assertEqual("example.org", go("--further.host", 'example.org').further.host)
        self.assertEqual("example org", go("--further.host", 'example org').further.host)

        def go2(*_args) -> RootConfig2:
            self.sys(*_args)
            return run(RootConfig2, interface=Mininterface, prog="My application").get_args()
        self.assertEqual("example.org", go2("--further.token=1").further.host)
        self.assertEqual("example.com", go2("--further.token=1", "--further.host=example.com").further.host)
        self.assertEqual("'example.net'", go2("--further.token=1", "--further.host='example.net'").further.host)
        self.sys("--further.host='example.net'")
        self.assertRaises(SystemExit, lambda: run(Config, interface=Mininterface, prog="My application"))

    def test_ask(self):
        m0 = run(RootConfig1, interface=Mininterface, prog="My application")
        self.assertEqual(0, m0.ask_number("Test input"))

        m1: TuiInterface = run(RootConfig1, interface=TuiInterface, prog="My application")
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


if __name__ == '__main__':
    main()
