import warnings
from mininterface import Mininterface, run
from shared import TestAbstract, runm

from argparse import ArgumentParser
from pathlib import Path


class TestArgparse(TestAbstract):

    def test_argparse(self):
        parser = ArgumentParser(description="Test parser for dataclass generation.")
        # positional
        subparsers = parser.add_subparsers(dest="command", required=True)
        parser.add_argument("input_file", type=str, help="Path to the input file.")
        parser.add_argument(
            "output_dir", type=str, help="Directory where output will be saved."
        )
        # optional with/out defaults
        parser.add_argument("--verbosity", type=int, default=1, help="Verbosity level.")
        # attention, an empty path will become Path('.'), not None
        parser.add_argument("--config", type=Path, help="Optional path to config file.")
        # action=store_true
        parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
        # action=store_false
        parser.add_argument(
            "--no-color",
            dest="color",
            action="store_false",
            help="Disable colored output.",
        )
        # append
        parser.add_argument("--tag", action="append", help="Add one or more tags.")
        # subparsers
        sub1 = subparsers.add_parser("build", help="Build something.")
        sub1.add_argument(
            "--optimize", action="store_true", help="Enable optimizations."
        )
        sub1.add_argument("--target", type=str, help="Build target platform.")
        sub2 = subparsers.add_parser("deploy", help="Deploy something.")
        # NOTE handling missing values in subparsers is not implemented (we defer to tyro exception)
        # sub2.add_argument("host", type=str, help="Remote host.")
        sub2.add_argument("--port", type=int, default=22, help="SSH port.")
        sub2.add_argument("--user", type=str, default="root", help="SSH user.")

        with self.assertRaises(SystemExit) as cm:
            run(parser, interface=Mininterface)
        self.assertEqual(
            """input_file: Type must be str!
output_dir: Type must be str!
the following arguments are required: STR, STR""",
            cm.exception.code,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # zachytí všechna varování
            env = run(
                parser, args=["build", "/tmp/file", "/tmp"], interface=Mininterface
            ).form()
            self.assertEqual(
                len(w),
                0,
                f"Unexpected warning(s): {[str(warning.message) for warning in w]}",
            )

        PathType = type(Path(""))  # PosixPath on Linux
        self.assertEqual(
            f"""build(input_file='/tmp/file', output_dir='/tmp', verbosity=1, config={PathType.__name__}('.'), debug=False, no_color=False, tag=[], optimize=False, target='')""",
            repr(env),
        )
        self.assertTrue(env.color)
        self.assertFalse(env.no_color)

        env = run(
            parser,
            args=["build", "/tmp/file", "/tmp", "--no-color"],
            interface=Mininterface,
        ).env

        self.assertFalse(env.color)
        self.assertTrue(env.no_color)

    def test_unimplemented_positionals(self):
        """The original parser:

        usage: program.py [-h] [--verbosity VERBOSITY] input_file {deploy,build} ...

        Mininterface changes the order:

        usage: program.py [-h] [-v] {deploy,build}
        usage: program.py deploy [-h] [DEPLOY OPTIONS] STR
        """
        parser = ArgumentParser(description="Test parser for dataclass generation.")

        parser.add_argument("input_file", type=str, help="Path to the input file.")
        subs = parser.add_subparsers(dest="command", required=True)
        subs.add_parser("build", help="Build something")
        sub2 = subs.add_parser(
            "deploy", help="Deploy something", description="My thorough description."
        )
        sub2.add_argument("--port", type=int, default=22, help="SSH port.")
        parser.add_argument("--verbosity", type=int, default=1, help="Verbosity level.")

        # warning for the positional arguments change
        with self.assertWarnsRegex(UserWarning, r"This CLI parser"):
            run(
                parser,
                args=["deploy", "/tmp/file", "--port", "23"],
                interface=Mininterface,
            )

        # Nice help text
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            with (
                self.assertOutputs(
                    contains="Deploy something: My thorough description."
                ),
                self.assertRaises(SystemExit),
            ):
                run(parser, args=["--help"], interface=Mininterface)

            with (
                self.assertOutputs(
                    contains="Deploy something: My thorough description."
                ),
                self.assertRaises(SystemExit),
            ):
                run(parser, args=["deploy", "--help"], interface=Mininterface)

    def test_failed_constant(self):
        parser = ArgumentParser()
        parser.add_argument("--one", action="store_const", const="A")
        with self.assertRaises(NotImplementedError):
            runm(parser, args=[])

    def test_constant(self):
        parser = ArgumentParser()
        parser.add_argument("--one", action="store_const", const="A", dest="field")

        env = runm(parser, args=[]).env
        self.assertEqual(None, env.field)

        env = runm(parser, args=["--one"]).env
        self.assertEqual("A", env.field)

    def test_constants_order(self):
        parser = ArgumentParser()
        parser.add_argument(
            "--one",
            action="store_const",
            dest="section",
            const="A",
        )
        parser.add_argument(
            "--two",
            action="store_const",
            dest="section",
            const="B",
        )
        env = runm(parser, args=[]).env
        self.assertEqual(None, env.section)

        env = runm(parser, args=["--one"]).env
        self.assertEqual("A", env.section)

        env = runm(parser, args=["--two"]).env
        self.assertEqual("B", env.section)

        env = runm(parser, args=["--two", "--one"]).env
        self.assertEqual("A", env.section)

        # This behaviour differs from argparse:
        env = runm(parser, args=["--one", "--two"]).env
        self.assertEqual("A", env.section)

    def test_same_dest(self):
        parser = ArgumentParser()
        parser.add_argument(
            "--one",
            action="append_const",
            dest="sections",
            const="one",
        )
        parser.add_argument(
            "--two",
            action="append_const",
            dest="sections",
            const="two",
        )

        env = run(parser, args=["--two"]).env
        self.assertListEqual(["two"], env.sections)

        env = run(parser, args=["--one", "--two"]).env
        self.assertListEqual(["one", "two"], env.sections)
        # repeat the line, reading the property must not influence the result
        self.assertListEqual(["one", "two"], env.sections)
