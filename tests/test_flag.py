from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from mininterface.tag import Tag
from mininterface.tag.flag import Blank
from shared import MISSING, TestAbstract, runm


@dataclass
class Env:
    t1: Blank[int]
    t2: Blank[int] = None
    t3: Annotated[Blank[int], Literal[3]] = None
    t4: Annotated[Blank[int | bool], Literal[3]] = 2


class TestFlag(TestAbstract):
    def test_flag(self):
        with self.assertForms(
            (
                {
                    "": {
                        "t1": Tag(val=MISSING, description="", annotation=int | None, label="t1"),
                        "t2": Tag(val=None, description="", annotation=int | None, label="t2"),
                        "t3": Tag(val=None, description="", annotation=int | None, label="t3"),
                        "t4": Tag(val=2, description="", annotation=int | bool | None, label="t4"),
                    }
                },
                {"": {"t1": None}},
            )
        ):
            runm(Env)

        def r(*args):
            return asdict(runm(Env, args=args).env)

        self.assertDictEqual({"t1": 1, "t2": None, "t3": None, "t4": 2}, r("--t1", "1"))
        self.assertDictEqual({"t1": 1, "t2": 3, "t3": None, "t4": 2}, r("--t1", "1", "--t2", "3"))
        self.assertDictEqual({"t1": 1, "t2": True, "t3": 3, "t4": 3}, r("--t1", "1", "--t2", "--t3", "--t4"))
        self.assertDictEqual({"t1": 10, "t2": None, "t3": None, "t4": False}, r("--t1", "10", "--t4", "False"))
        self.assertDictEqual({"t1": 10, "t2": None, "t3": None, "t4": True}, r("--t1", "10", "--t4", "True"))
        self.assertDictEqual({"t1": 10, "t2": None, "t3": None, "t4": 44}, r("--t1", "10", "--t4", "44"))


        with (
                self.assertOutputs(contains=["--t1 [int]             (required)",
                "--t2 [int]             (default: 'None / or if left blank: True') ",
                "--t3 [int]             (default: 'None / or if left blank: 3')",
                "--t4 [int|bool]        (default: '2 / or if left blank: 3')"
                ]),
                self.assertRaises(SystemExit),
            ):
            runm(Env, args=["--help"])
