# NOTE should be split into separate files


from mininterface import Mininterface
from configs import NestedDefaultedEnv, SimpleEnv
from mininterface._lib.run import run
from shared import TestAbstract


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
