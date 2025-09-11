from mininterface import Mininterface
from mininterface._lib.form_dict import dataclass_to_tagdict
from mininterface._lib.run import run
from mininterface.tag import Tag
from attrs_configs import AttrsModel, AttrsNested, AttrsNestedRestraint
from shared import TestAbstract


class TestAttrsIntegration(TestAbstract):
    def test_basic(self):
        m = run(AttrsModel, interface=Mininterface)
        self.assertEqual("hello", m.env.name)

    def test_nested(self):
        m = run(AttrsNested, interface=Mininterface)
        self.assertEqual(-100, m.env.number)

        self.sys("--number", "-200")
        m = run(AttrsNested, interface=Mininterface)
        self.assertEqual(-200, m.env.number)
        self.assertEqual(4, m.env.inner.number)

    def test_config(self):
        m = run(AttrsNested, config_file="tests/pydantic.yaml", interface=Mininterface)
        self.assertEqual(100, m.env.number)
        self.assertEqual(0, m.env.inner.number)
        self.assertEqual("hello", m.env.inner.text)

    def test_nested_restraint(self):
        m = run(AttrsNestedRestraint, interface=Mininterface)
        self.assertEqual("hello", m.env.inner.name)

        f: Tag = dataclass_to_tagdict(m.env)["inner"]["name"]
        self.assertTrue(f.update("short"))
        self.assertEqual("Restrained name", f.description)
        self.assertFalse(f.update("long words"))
        self.assertEqual("Length of 'check' must be <= 5: 10 Restrained name", f.description)
        self.assertTrue(f.update(""))
        self.assertEqual("Restrained name", f.description)
