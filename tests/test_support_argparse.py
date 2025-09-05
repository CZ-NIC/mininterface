import warnings

from mininterface.tag import Tag, SelectTag, PathTag
from shared import TestAbstract, runm, MISSING

from argparse import ArgumentParser
from pathlib import Path


class TestArgparse(TestAbstract):

    def test_argparse(self):
        self.maxDiff = None
        parser = ArgumentParser(description="Test parser for dataclass generation.")
        # positional
        subparsers = parser.add_subparsers(dest="command", required=True)
        parser.add_argument("input_file", type=str, help="Path to the input file.")
        parser.add_argument("output_dir", type=str, help="Directory where output will be saved.")
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
        sub1.add_argument("--optimize", action="store_true", help="Enable optimizations.")
        sub1.add_argument("--target", type=str, help="Build target platform.")
        sub2 = subparsers.add_parser("deploy", help="Deploy something.")
        # NOTE handling missing values in subparsers is not implemented (we defer to tyro exception)
        # sub2.add_argument("host", type=str, help="Remote host.")
        sub2.add_argument("--port", type=int, default=22, help="SSH port.")
        sub2.add_argument("--user", type=str, default="root", help="SSH user.")

        # Extremely peculiar situation. Do you know why the name of this file is not test_argparse.py?
        # These are ok: test_a.py test_am.py test_run.py test_whatever.py
        # These are not: test_ar.py test_arg.py test_arv.py test_argparse.py
        # If we use one of not-ok names AND IF THERE IS the following run statement, we get:
        #
        # FAILED tests/test_log.py::TestLog::test_custom_verbosity - StopIteration
        # self.sys("-v")
        # with (self.assertStderr(contains="running-tests: error: unrecognized arguments: -v"), self.assertRaises(SystemExit)):
        #     self.log(ConflictingEnv)
        #
        # Yes, the following run statement, the name of this file and the test_log file have NOTHING IN COMMON.
        #
        #         with self.assertRaises(SystemExit) as cm:
        #             runm(parser)
        #         self.assertEqual(
        #             """input_file: Type must be str!
        # output_dir: Type must be str!
        # the following arguments are required: STR, STR""",
        #             cm.exception.code,
        #         )
        # Now, we rather ask for subcommand (`Choose: Must be one of ['build', 'deploy']`) but I leave the comment intact.
        with self.assertForms(
            ({"": SelectTag(val=None, annotation=None, label=None, options=['Build  - Build something.', 'Deploy - Deploy something.'])}),
        ), self.assertRaises(SystemExit):
            runm(parser)

        with self.assertForms(
            (
                {
                    "": {
                        "input_file": Tag(
                            val=MISSING, description="Path to the input file.", annotation=str, label="input file"
                        ),
                        "output_dir": Tag(
                            val=MISSING,
                            description="Directory where output will be saved.",
                            annotation=str,
                            label="output dir",
                        ),
                        "verbosity": Tag(val=1, description="Verbosity level.", annotation=int, label="verbosity"),
                        "config": PathTag(
                            val=None,
                            description="Optional path to config file.",
                            annotation=Path | None,
                            label="config",
                        ),
                        "debug": Tag(val=False, description="Enable debug mode.", annotation=bool, label="debug"),
                        "no_color": Tag(
                            val=False, description="Disable colored output.", annotation=bool, label="no color"
                        ),
                        "tag": Tag(val=[], description="Add one or more tags.", annotation=list[str], label="tag"),
                        "optimize": Tag(
                            val=False, description="Enable optimizations.", annotation=bool, label="optimize"
                        ),
                        "target": Tag(
                            val=None, description="Build target platform.", annotation=str | None, label="target"
                        ),
                    }
                },
                {"": {"input_file": "", "output_dir": ""}},
            )
        ):
            runm(parser, args=["build"])
        return
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            env = runm(parser, args=["build", "/tmp/file", "/tmp"]).form()
            self.assertEqual(
                len(w),
                0,
                f"Unexpected warning(s): {[str(warning.message) for warning in w]}",
            )

        self.assertEqual(
            f"""build(input_file='/tmp/file', output_dir='/tmp', verbosity=1, config=None, debug=False, no_color=False, tag=[], optimize=False, target=None)""",
            repr(env),
        )
        self.assertTrue(env.color)
        self.assertFalse(env.no_color)

        env = runm(
            parser,
            args=["build", "/tmp/file", "/tmp", "--no-color"],
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
        sub2 = subs.add_parser("deploy", help="Deploy something", description="My thorough description.")
        sub2.add_argument("--port", type=int, default=22, help="SSH port.")
        parser.add_argument("--verbosity", type=int, default=1, help="Verbosity level.")

        # warning for the positional arguments change
        with self.assertWarnsRegex(UserWarning, r"This CLI parser"):
            runm(
                parser,
                args=["deploy", "/tmp/file", "--port", "23"],
            )

        # Nice help text
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            with (
                self.assertOutputs(contains="Deploy something: My thorough description."),
                self.assertRaises(SystemExit),
            ):
                runm(parser, args=["--help"])

            with (
                self.assertOutputs(contains="Deploy something: My thorough description."),
                self.assertRaises(SystemExit),
            ):
                runm(parser, args=["deploy", "--help"])

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

        env = runm(parser, args=["--two"]).env
        self.assertListEqual(["two"], env.sections)

        env = runm(parser, args=["--one", "--two"]).env
        self.assertListEqual(["one", "two"], env.sections)
        # repeat the line, reading the property must not influence the result
        self.assertListEqual(["one", "two"], env.sections)

    def test_default(self):
        parser = ArgumentParser()
        parser.add_argument("number", default=10, type=int, nargs="?")

        env = runm(parser, args=[]).env
        self.assertEqual(env.number, 10)

        env = runm(parser, args=["2"]).env
        self.assertEqual(env.number, 2)

        parser = ArgumentParser()
        parser.add_argument("--n", default=10, type=int, nargs="?")

        env = runm(parser, args=[]).env
        self.assertEqual(env.n, 10)
        env = runm(parser, args=["--n", "2"]).env
        self.assertEqual(env.n, 2)

    # NOTE this is not supported now
    # def test_official_example(self):
    #     parser = ArgumentParser()
    #     parser.add_argument( 'integers', metavar='int', type=int, choices=range(10), nargs='+', help='an integer in the range 0..9')
    #     parser.add_argument( '--sum', dest='accumulate', action='store_const', const=sum, default=max, help='sum the integers (default: find the max)')

    #     env = runm(parser, args=['1', '2', '3', '4']).env
    #     # parser.parse_args(['1', '2', '3', '4'])
    #     # Namespace(accumulate=<built-in function max>, integers=[1, 2, 3, 4])
    #     # parser.parse_args(['1', '2', '3', '4', '--sum'])
