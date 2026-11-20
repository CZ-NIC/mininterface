from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from shared import MISSING, TestAbstract, runm
from tyro.conf import Positional

from mininterface.tag import Tag
from mininterface.tag.flag import Blank, BlankTrue


@dataclass
class Env:
    t1: Blank[int]
    t2: Blank[int] = None
    t3: Annotated[Blank[int], Literal[3]] = None
    t4: Annotated[Blank[int | bool], Literal[3]] = 2
    t5: Blank[int | Literal["foo"]] = None


@dataclass
class PositionalEnv:
    pos: Positional[str | None] = None
    d: Blank[str] = None
    o: Blank[int] = None


@dataclass
class BooleanEnv:
    pos: Positional[str | None] = None
    enabled: BlankTrue = None


class TestFlag(TestAbstract):
    def test_blank_flag_rejects_excess_values(self):
        for args in (
            ["--d", "False", "x"],
            ["--d", "start", "x"],
            ["--o", "3", "x"],
            ["--d=start", "x"],
        ):
            with self.subTest(args=args):
                with (
                    self.assertStderr(
                        contains="positional arguments before", strip_white=True
                    ),
                    self.assertRaises(SystemExit) as caught,
                ):
                    runm(PositionalEnv, args=args)
                self.assertEqual(caught.exception.code, 2)

    def test_blank_flag_keeps_unambiguous_positionals(self):
        for args, expected_d, expected_o in (
            (["x", "--d", "False"], False, None),
            (["x", "--d", "start"], "start", None),
            (["x", "--d", "two words"], "two words", None),
            (["x", "--o", "3"], None, 3),
            (["x", "--o", "-3"], None, -3),
            (["--d", "start", "--", "x"], "start", None),
            (["--d", "", "--", "x"], "", None),
            (["--d", "--", "x"], True, None),
            (["x", "--d"], True, None),
        ):
            with self.subTest(args=args):
                env = runm(PositionalEnv, args=args).env
                self.assertEqual(env.pos, "x")
                self.assertEqual(env.d, expected_d)
                self.assertEqual(env.o, expected_o)

    def test_blank_true_still_rejects_excess_values(self):
        with (
            self.assertStderr(contains="Unrecognised value", strip_white=True),
            self.assertRaises(SystemExit),
        ):
            runm(BooleanEnv, args=["--enabled", "False", "x"])
        env = runm(BooleanEnv, args=["x", "--enabled", "False"]).env
        self.assertEqual(env.pos, "x")
        self.assertIs(env.enabled, False)

    def test_flag(self):
        with self.assertForms(
            (
                {
                    "": {
                        "t1": Tag(val=MISSING, description="", annotation=int | bool | None, label="t1"),
                        "t2": Tag(val=None, description="", annotation=int | bool | None, label="t2"),
                        "t3": Tag(val=None, description="", annotation=int | bool | None, label="t3"),
                        "t4": Tag(val=2, description="", annotation=int | bool | None, label="t4"),
                        "t5": Tag(val=None, description="", annotation=int | Literal["foo"] | bool | None, label="t5"),
                    }
                },
                {"": {"t1": None}},
            )
        ):
            runm(Env)

        def r(*args):
            return asdict(runm(Env, args=args).env)

        self.assertDictEqual({"t1": 1, "t2": None, "t3": None, "t4": 2, "t5": None}, r("--t1", "1"))
        self.assertDictEqual({"t1": 1, "t2": 3, "t3": None, "t4": 2, "t5": None}, r("--t1", "1", "--t2", "3"))
        self.assertDictEqual(
            {"t1": 1, "t2": True, "t3": 3, "t4": 3, "t5": True}, r("--t1", "1", "--t2", "--t3", "--t4", "--t5")
        )
        self.assertDictEqual(
            {"t1": 10, "t2": None, "t3": None, "t4": False, "t5": None}, r("--t1", "10", "--t4", "False")
        )
        self.assertDictEqual(
            {"t1": 10, "t2": None, "t3": None, "t4": True, "t5": 100}, r("--t1", "10", "--t5", "100", "--t4", "True")
        )
        self.assertDictEqual({"t1": 10, "t2": None, "t3": None, "t4": 44, "t5": None}, r("--t1", "10", "--t4", "44"))

        # NOTE this should work too, Literals now canot be constructed
        # self.assertDictEqual(
        #     {"t1": 10, "t2": None, "t3": None, "t4": False, "t5": "foo"}, r("--t1", "10", "--t4", "False", "--t5", "foo")
        # )

        with self.assertStderr(contains="Error parsing --t5", strip_white=True), self.assertRaises(SystemExit):
            # NOTE this might rather raise a wrong field dialog
            r("--t1", "10", "--t5", "invalid")

        with (
            self.assertOutputs(
                contains=[
                    "--t1 [int]              (required)",
                    "--t2 [int]              (default: 'None / or if left blank: True') ",
                    "--t3 [int]              (default: 'None / or if left blank: 3')",
                    "--t4 [int]              (default: '2 / or if left blank: 3')",
                    "--t5 [int|Literal]      (default: 'None / or if left blank: True')",
                ],
                strip_white=True,
            ),
            # NOTE t5 should display the mere Literal value
            self.assertRaises(SystemExit),
        ):
            runm(Env, args=["--help"])
