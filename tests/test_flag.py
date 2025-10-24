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
    t5: Blank[int | Literal["foo"]] = None


class TestFlag(TestAbstract):
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
