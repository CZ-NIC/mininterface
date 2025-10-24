from contextlib import contextmanager
from dataclasses import MISSING, fields, make_dataclass
import sys
from unittest import skipIf

from heavy_nesting_configs import (Grade5A, Level1, Level2A, Level2B, Level3A,
                                   Level5A)
from heavy_passages import (ccomp7, ccomp8, comp9, comp10, cpassage1,
                            cpassage2, cpassage3, cpassage4, cpassage5,
                            cpassage6, cpassage7, cpassage8, cpassage9, help1,
                            help2, help3, help4, help5, help6, help7, help8,
                            help9, passage1, passage2, passage3, passage4,
                            passage5, passage6, passage7, passage8, uccomp4,
                            ucomp4, ucpassage1, ucpassage2, ucpassage3,
                            upassage1, upassage2, upassage3)
from heavy_nesting_missing_configs import Level1 as MLevel1
from heavy_missing_passages import mpassage1, mpassage2, mpassage3, mcomp4, mcpassage1, mcpassage2,mcpassage3,mccomp4
from shared import TestAbstract, runm

@contextmanager
def remove_dataclass_defaults(cls):
    """
    From this:

    ```
    @dataclass
    class Level5A:
        epsilonA: str = "level5A class"
    ```

    make this:
    ```
    @dataclass
    class Level5A:
        epsilonA: str
    ```
    """
    orig_init = cls.__init__
    old_defaults = {}
    try:
        for f in fields(cls):
            old_defaults[f.name] = getattr(f, 'default', MISSING)
            f.default = MISSING
        new_fields = [(f.name, f.type) for f in fields(cls)]
        TempCls = make_dataclass(cls.__name__, new_fields)
        cls.__init__ = TempCls.__init__
        yield
    finally:
        cls.__init__ = orig_init
        for f in fields(cls):
            f.default = old_defaults[f.name]

@skipIf(sys.version_info[:2] < (3, 11), "Ignored on Python 3.10 due to exc.add_note")
class TestHeavyNesting(TestAbstract):
    """ Here, we test a deep structure that combines subparsers (`attr: Class`) and subcommands (`attr: Class1 | Class2`).

    Some classes have multiple attributes with subcommands, some share the objects, some have missing values that are fully/partly fetched from the config file.
    We trigger this structure either with none, part or full subcommand path from the CLI.
    While passing through the structure (deciding which subcommand to take), we usually take the first option.

    """

    def run_cases(self, env_classes, cases, config_file=False,wizzard=False):
        for args, expected, repr_comp in cases:
            with self.subTest(args=args):
                with self.assertForms(*(expected or tuple()), wizzard="short" if expected is None else False):
                    m = runm(env_classes, args=args.split(" ") if args else None, config_file=config_file)
                    if repr_comp:
                        self.assertEqual(repr_comp, repr(m.env))
                    if wizzard:
                        raise ValueError(m.env)

    def test_heavy_nesting(self):

        cases = [
            ("", passage1, False),
            ("", passage2, False),
            ("", passage3, False),
            ("command1:level2-a", passage4, False),
            ("command1:level2-a command1.command2:level3-a", passage5, False),
            ("command1:level2-a command1.command2:level3-a", passage6, False),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a",
                passage7,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a",
                passage8,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                False,
                comp9,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                False,
                comp10,
            ),
        ]
        self.run_cases(Level1, cases)

    def test_config_file(self):
        cases = [
            ("", cpassage1, False),
            ("", cpassage2, False),
            ("", cpassage3, False),
            ("command1:level2-a", cpassage4, False),
            ("command1:level2-a command1.command2:level3-a", cpassage5, False),
            ("command1:level2-a command1.command2:level3-a", cpassage6, False),
            ("command1:level2-a command1.command2:level3-a", cpassage7, False),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a",
                cpassage8,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a",
                cpassage9,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                False,
                ccomp7,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                False,
                ccomp8,
            ),
        ]
        self.run_cases(Level1, cases, config_file="tests/heavy_config.yaml")

    def DISABLED_test_helps(self):
        # TODO when tyro 0.10 is ready
        # * get rid of patched__format_help
        # * patch _help_formatting.format_help instead of TyroArgumentParser, add there a new ParserSpec with cf fields -> that way, they'll in the options group, not in commands1 group
        cases = [
            ("--help", help1),
            ("command1:level2-a --help", help2),
            ("command1:level2-a command1.command2:level3-a --help", help3),
            ("command1:level2-a command1.command2:level3-a --help", help4),
            ("command1:level2-a command1.command2:level3-a --help", help5),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a --help",
                help6,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a --help",
                help7,
            ),
            (
                "command1:level2-a command1.command2:level3-a command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a --help",
                help8,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a --help",
                help9,
            ),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                with self.assertOutputs(expected or "", wizzard=expected is None, raises=SystemExit, strip_white=True):
                    runm(Level1, args=args.split(" ") if args else None, config_file="tests/heavy_config.yaml")

    def test_union(self):
        cases = [
            ("", upassage1, False),
            ("level2-a", upassage2, False),
            ("level2-a command2:level3-a", upassage3, False),
            (
                "level2-a command2:level3-a --command2.gammaA 10 command2.command3.command4:level5-a command2.command3grade.command4:grade5-a",
                False,
                ucomp4,
            ),
        ]
        self.run_cases([Level2A, Level2B], cases)

    def test_union_config(self):
        self.maxDiff = None
        cases = [
            ("", ucpassage1, False),
            ("level2-a", ucpassage2, False),
            ("level2-a command2:level3-a", ucpassage3, False),
            (
                "level2-a command2:level3-a --command2.gammaA 10 command2.command3.command4:level5-a command2.command3grade.command4:grade5-a",
                False,
                uccomp4,
            ),
        ]
        self.run_cases([Level2A, Level2B], cases, config_file="tests/heavy_config_union.yaml")

    def test_missing_in_the_depth(self):
        cases = [
            ("", mpassage1, False),
            ("command1:level2-a", mpassage2, False),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                mpassage3,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a --command1.command2.command3.command4.epsilonA level5Acli command1.command2.command3grade.command4:grade5-a --command1.command2.command3grade.command4.epsilonGradeA grade5Acli",
                False,
                mcomp4,
            ),
        ]
        self.run_cases(MLevel1, cases)


    def test_missing_in_the_depth_with_config(self):
        cases = [
            ("", mcpassage1, False),
            ("command1:level2-a", mcpassage2, False),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a command1.command2.command3grade.command4:grade5-a",
                mcpassage3,
                False,
            ),
            (
                "command1:level2-a command1.command2:level3-a --command1.command2.gammaA 10 command1.command2.command3.command4:level5-a --command1.command2.command3.command4.epsilonA level5Acli command1.command2.command3grade.command4:grade5-a --command1.command2.command3grade.command4.epsilonGradeA grade5Acli",
                False,
                mccomp4,
            ),
        ]
        self.run_cases(MLevel1, cases, config_file="tests/heavy_config.yaml")