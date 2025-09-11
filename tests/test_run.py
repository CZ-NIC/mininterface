from unittest import skipUnless
from mininterface import Mininterface
from mininterface._lib.config_file import _merge_settings
from mininterface._lib.run import run
from mininterface.settings import UiSettings
from mininterface.tag import PathTag, Tag
from attrs_configs import AttrsNested
from importlib.metadata import version
from configs import (
    AnnotatedClass,
    ComplexEnv,
    FurtherEnv2,
    MissingCombined,
    MissingNonscalar,
    MissingPositional,
    MissingPositionalScalar,
    MissingUnderscore,
    SimpleEnv,
)
from dumb_settings import (
    GuiSettings,
    MininterfaceSettings,
    TextSettings,
    TextualSettings,
    TuiSettings,
    UiSettings as UiDumb,
    WebSettings,
)
from pydantic_configs import PydNested
from shared import MISSING, TestAbstract, runm


import os
import sys
import warnings
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tyro.conf import FlagConversionOff, OmitArgPrefixes


class TestRun(TestAbstract):
    def test_run_ask_empty(self):
        with self.assertOutputs("Asking the form SimpleEnv(test=False, important_number=4)"):
            run(SimpleEnv, True, interface=Mininterface)
        with self.assertOutputs(""):
            run(SimpleEnv, interface=Mininterface)

    def test_run_ask_for_missing(self):
        form = """Asking the form FurtherEnv2(token=MISSING, host='example.org')"""
        # Ask for missing, no interference with ask_on_empty_cli
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            run(FurtherEnv2, True, interface=Mininterface)
        with self.assertOutputs(form), self.assertRaises(SystemExit):
            run(FurtherEnv2, False, interface=Mininterface)
        # Ask for missing does not happen, CLI fails with tyro message before the Mininterface log 'Asking the form...' is displayed
        with self.assertOutputs(""), self.assertRaises(SystemExit):
            run(FurtherEnv2, True, ask_for_missing=False, interface=Mininterface)

        # No missing field
        self.sys("--token", "1")
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            run(FurtherEnv2, True, ask_for_missing=True, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())
            run(FurtherEnv2, True, ask_for_missing=False, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    @skipUnless(sys.version_info >= (3, 11), "requires Python 3.11+")
    def test_run_ask_for_missing_underscored(self):
        # Treating underscores
        form2 = """Asking the form MissingUnderscore(token_underscore=MISSING, host='example.org')"""
        with self.assertOutputs(form2), self.assertRaises(SystemExit):
            run(MissingUnderscore, True, interface=Mininterface)

        self.sys("--token-underscore", "1")  # dash used instead of an underscore

        with patch("sys.stdout", new_callable=StringIO) as stdout:
            run(MissingUnderscore, True, ask_for_missing=True, interface=Mininterface)
            self.assertEqual("", stdout.getvalue().strip())

    def test_wrong_fields(self):
        with self.assertForms(
            (
                {
                    "": {
                        "files1": PathTag(
                            val=[],
                            description="NOTE some of the entries are not well supported",
                            annotation=list[Path],
                            label="files1",
                        ),
                        "files2": PathTag(
                            val=MISSING,
                            description="NOTE some of the entries are not well supported",
                            annotation=list[Path],
                            label="files2",
                        ),
                        "files3": PathTag(
                            val=[],
                            description="files4: Positional[list[Path]] = field",
                            annotation=list[Path],
                            label="files3",
                        ),
                        "files5": PathTag(
                            val=[],
                            description="files4: Positional[list[Path]] = field",
                            annotation=list[Path],
                            label="files5",
                        ),
                    }
                },
                {"": {"files2": []}},
            )
        ):
            runm(AnnotatedClass)

        # NOTE yield_defaults instead of yield_annotations should be probably used in pydantic and attr
        # too to support default_factory,
        # ex: `my_complex: tuple[int, str] = field(default_factory=lambda: [(1, 'foo')])`

    def test_run_ask_for_missing_union(self):
        form = """Asking the form MissingNonscalar(path=MISSING, combined=MISSING, simple_tuple=MISSING)"""
        if sys.version_info[:2] <= (3, 12):  # NOTE remove with Python 3.12
            form = form.replace("pathlib._local.Path", "pathlib.Path")

        with self.assertOutputs(form), self.assertRaises(SystemExit):
            runm(MissingNonscalar)

        with self.assertForms(
            (
                {
                    "": {
                        "path": PathTag(val=MISSING, description="", annotation=str | Path, label="path"),
                        "combined": Tag(
                            val=MISSING, description="", annotation=int | tuple[int, int] | None, label="combined"
                        ),
                        "simple_tuple": Tag(
                            val=MISSING, description="", annotation=tuple[int, int], label="simple tuple"
                        ),
                    }
                },
                {"": {"path": "/tmp", "combined": None, "simple_tuple": (1, 1)}},
            )
        ):

            runm(MissingNonscalar)

    def test_missing_required_fail(self):
        with self.assertRaises(SystemExit):
            run(MissingPositionalScalar, interface=Mininterface)

        with self.assertForms(
            (
                {"": {"file": PathTag(val=MISSING, description="", annotation=Path, label="file")}},
                {"": {"file": Path("/tmp")}},
            )
        ):
            runm(MissingPositionalScalar)

        with self.assertForms(
            ({"": {"files": PathTag(val=[], description="", annotation=list[Path], label="files")}}, {})
        ):
            # Since the positional is list, we infer an empty list
            # This might be not the desired behaviouro.
            m2 = runm(MissingPositional)
            m2.form()
        self.assertListEqual([], m2.env.files)

    def test_missing_combined(self):
        with self.assertForms(
            (
                {
                    "": {
                        "file": PathTag(val=MISSING, description="", annotation=Path, label="file"),
                        "foo": Tag(val=MISSING, description="", annotation=str, label="foo"),
                        "bar": Tag(val="hello", description="", annotation=str, label="bar"),
                    }
                },
                {"": {"file": Path("."), "foo": ""}},
            )
        ):
            runm(MissingCombined)

    def test_run_config_file(self):
        os.chdir("tests")
        sys.argv = ["SimpleEnv.py"]
        self.assertEqual(
            10,
            run(SimpleEnv, config_file=True, interface=Mininterface).env.important_number,
        )
        self.assertEqual(
            4,
            run(SimpleEnv, config_file=False, interface=Mininterface).env.important_number,
        )
        self.assertEqual(
            20,
            run(SimpleEnv, config_file="SimpleEnv2.yaml", interface=Mininterface).env.important_number,
        )
        self.assertEqual(
            20,
            run(SimpleEnv, config_file=Path("SimpleEnv2.yaml"), interface=Mininterface).env.important_number,
        )
        self.assertEqual(
            4,
            run(SimpleEnv, config_file=Path("empty.yaml"), interface=Mininterface).env.important_number,
        )
        with self.assertRaises(FileNotFoundError):
            run(SimpleEnv, config_file=Path("not-exists.yaml"), interface=Mininterface)

    def test_complex_config(self):
        pattern = ComplexEnv(
            a1={1: "a"},
            a2={2: ("b", 22), 3: ("c", 33), 4: ("d", 44)},
            a3={5: ["e", "ee", "eee"]},
            a4=[6, 7],
            a5=("h", 8),
            a6=["i", 9],
            a7=[("j", 10.0), ("k", 11), ("l", 12)],
        )
        self.assertEqual(pattern, runm(ComplexEnv, config_file="tests/complex.yaml").env)

    def test_run_annotated(self):
        m = run(FlagConversionOff[OmitArgPrefixes[SimpleEnv]])
        self.assertEqual(4, m.env.important_number)

    def test_config_unknown(self):
        """An unknown field in the config file should emit a warning."""

        def r(model):
            run(model, config_file="tests/unknown.yaml", interface=Mininterface)

        for model in (PydNested, SimpleEnv, AttrsNested):
            with warnings.catch_warnings(record=True) as w:
                r(model)
                self.assertIn("Unknown fields in the configuration file", str(w[0].message))

    def test_settings(self):
        # NOTE
        # The settings had little params at the moment of the test writing.
        # when there is more settings, use the actual objects instead of the dumb ones here.
        # Then, you might get rid of the dumb_settings.py and _def_fact factory parameter in _merge_settings.

        opt1 = MininterfaceSettings(gui=GuiSettings(combobox_since=1))
        opt2 = MininterfaceSettings(gui=GuiSettings(combobox_since=10))
        self.assertEqual(
            opt1,
            _merge_settings(None, {"gui": {"combobox_since": 1}}, MininterfaceSettings),
        )

        # config file settings are superior to the program-given settings
        self.assertEqual(
            opt1,
            _merge_settings(opt2, {"gui": {"combobox_since": 1}}, MininterfaceSettings),
        )

        opt3 = MininterfaceSettings(
            ui=UiDumb(foo=3, p_config=0, p_dynamic=0),
            gui=GuiSettings(foo=3, p_config=0, p_dynamic=0, combobox_since=5, test=False),
            tui=TuiSettings(foo=3, p_config=2, p_dynamic=0),
            textual=TextualSettings(foo=3, p_config=1, p_dynamic=0, foobar=74),
            text=TextSettings(foo=3, p_config=2, p_dynamic=0),
            web=WebSettings(foo=3, p_config=1, p_dynamic=0, foobar=74),
            interface=None,
        )

        def conf():
            return {
                "textual": {"p_config": 1},
                "tui": {"p_config": 2},
                "ui": {"foo": 3},
            }

        self.assertEqual(opt3, _merge_settings(None, conf(), MininterfaceSettings))

        opt4 = MininterfaceSettings(
            text=TextSettings(p_dynamic=200),
            tui=TuiSettings(p_dynamic=100, p_config=100, foo=100),
        )

        res4 = MininterfaceSettings(
            ui=UiDumb(foo=3, p_config=0, p_dynamic=0),
            gui=GuiSettings(foo=3, p_config=0, p_dynamic=0, combobox_since=5, test=False),
            tui=TuiSettings(foo=100, p_config=2, p_dynamic=100),
            textual=TextualSettings(foo=100, p_config=1, p_dynamic=100, foobar=74),
            text=TextSettings(foo=100, p_config=2, p_dynamic=200),
            web=WebSettings(foo=100, p_config=1, p_dynamic=100, foobar=74),
            interface=None,
        )
        self.assertEqual(res4, _merge_settings(opt4, conf(), MininterfaceSettings))

    def test_settings_inheritance(self):
        """The interface gets the relevant settings section, not whole MininterfaceSettings"""
        opt1 = MininterfaceSettings(gui=GuiSettings(combobox_since=1))
        m = run(settings=opt1, interface=Mininterface)
        self.assertIsInstance(m, Mininterface)
        self.assertIsInstance(m._adaptor.settings, UiSettings)

    def test_add_version(self):
        with self.assertOutputs("v1.2.3"), self.assertRaises(SystemExit):
            runm(SimpleEnv, ["--version"], add_version="v1.2.3")

        # version flag does not appear in the program further
        with self.assertForms(
            (
                {
                    "": {
                        "test": Tag(val=False, description="My testing flag", annotation=bool, label="test"),
                        "important_number": Tag(
                            val=4,
                            description="This number is very important",
                            annotation=int,
                            label="important number",
                        ),
                    }
                },
                {"": {"important_number": 77}},
            )
        ):
            runm(SimpleEnv, add_version="v1.2.3").form()

    def test_add_version_package(self):
        version_ = version("mininterface")
        self.assertRegex(version_, r"^(\d+\.\d+\.\d+(?:-(?:rc|alpha|beta)\.?\d+)?)$")
        with self.assertOutputs(version_), self.assertRaises(SystemExit):
            runm(SimpleEnv, ["--version"], add_version_package="mininterface")

    def test_argparse_arguments(self):
        with self.assertRaises(SystemExit):
            run(SimpleEnv, args=["--im", "6"])

        # allow abbrev works
        self.assertEqual(6, run(SimpleEnv, args=["--im", "6"], allow_abbrev=True).env.important_number)