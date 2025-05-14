from mininterface.tag import Tag
from shared import TestAbstract


from pathlib import Path


class TestTag(TestAbstract):
    def test_get_ui_val(self):
        self.assertEqual([1, 2], Tag([1, 2])._get_ui_val())
        self.assertEqual(["/tmp"], Tag([Path("/tmp")])._get_ui_val())
        self.assertEqual([(1, "a")], Tag([(1, 'a')])._get_ui_val())
