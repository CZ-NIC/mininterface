from dataclasses import dataclass
from typing import Annotated
from mininterface import Mininterface, Tag
from mininterface._lib.auxiliary import flatten
from mininterface._lib.form_dict import MissingTagValue
from mininterface._mininterface import BackendAdaptor, Facet, UiSettings, dataclass_to_tagdict
from mininterface.facet import TagDict
from shared import TestAbstract, runm

from pathlib import Path


class TestAdaptor(BackendAdaptor):
    facet: Facet
    settings: UiSettings

    def widgetize(self, tag: Tag):
        """Wrap Tag to a UI widget."""
        pass

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        return super().run_dialog(form, title, submit)


@dataclass
class NestedEnv:
    foo6: Annotated[bool, Tag(mnemonic=True)] = False
    foo7: bool = False


@dataclass
class Env:
    """Set of options."""

    nested: NestedEnv

    foo1: Annotated[bool, Tag(mnemonic="o")] = False
    """My testing flag"""

    important_number: int = 4
    """This number is very important"""

    foo2: Annotated[bool, Tag(mnemonic="3")] = False
    foo3: Annotated[bool, Tag(mnemonic="g")] = False
    foo4: Annotated[bool, Tag(mnemonic=False)] = False
    foo5: Annotated[bool, Tag(mnemonic=True)] = False


@dataclass
class EnvUnderscored:
    my_name1: str = "a"
    my_name2: Annotated[str, Tag(label="Rich label")] = "b"


class TestTag(TestAbstract):
    def test_get_ui_val(self):
        self.assertEqual([1, 2], Tag([1, 2])._get_ui_val())
        self.assertEqual(["/tmp"], Tag([Path("/tmp")])._get_ui_val())
        self.assertEqual([(1, "a")], Tag([(1, "a")])._get_ui_val())

    def test_mnemonic(self):
        def _(settings):
            d = dataclass_to_tagdict(runm(Env).env)
            TestAdaptor(Mininterface(), settings).run_dialog(d)
            return [(tag.label, tag._mnemonic) for tag in flatten(d)]

        self.assertListEqual(
            [
                ("foo1", "o"),
                ("important number", "i"),
                ("foo2", "3"),
                ("foo3", "g"),
                ("foo4", None),
                ("foo5", "f"),
                ("foo6", "a"),
                ("foo7", "b"),
            ],
            _(UiSettings()),
        )

        self.assertListEqual(
            [
                ("foo1", None),
                ("important number", None),
                ("foo2", None),
                ("foo3", None),
                ("foo4", None),
                ("foo5", None),
                ("foo6", None),
                ("foo7", None),
            ],
            _(UiSettings(mnemonic=False)),
        )

        self.assertListEqual(
            [
                ("foo1", "o"),
                ("important number", None),
                ("foo2", "3"),
                ("foo3", "g"),
                ("foo4", None),
                ("foo5", "f"),
                ("foo6", "a"),
                ("foo7", None),
            ],
            _(UiSettings(mnemonic=None)),
        )

    def test_underscored(self):
        with self.assertForms(
            (
                {
                    "": {
                        "my_name1": Tag(val="a", description="", annotation=str, label="my name1"),
                        "my_name2": Tag(val="b", description="", annotation=str, label="Rich label"),
                    }
                },
                {},
            )
        ):
            runm(EnvUnderscored).form()
