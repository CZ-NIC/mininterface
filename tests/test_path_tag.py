from pathlib import Path
from typing import Optional
from mininterface.tag import PathTag
from shared import TestAbstract


class TestPathTag(TestAbstract):
    def test_init_dir(self):
        self.assertEqual(Path("/tmp"), PathTag("/tmp")._get_init_dir())
        self.assertEqual(Path("/tmp"), PathTag(["/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log/", "/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log", "/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log/syslog", "/tmp"])._get_init_dir())

    def test_types(self):
        p = PathTag()
        self.assertEqual(Path("/tmp"), p._validate(Path("/tmp")))
        self.assertTrue(p.update("/tmp"))
        with self.assertRaises(ValueError):
            p._validate("/tmp")
        with self.assertRaises(ValueError):
            p._validate(None)

        p = PathTag(is_file=True)
        self.assertFalse(p.update("/tmp"))
        with self.assertRaises(ValueError):
            p._validate(None)

        # Allows none
        p = PathTag(annotation=Optional[Path])
        self.assertTrue(p.update("/tmp"))
        self.assertIsNone(p._validate(None))

        # Still allows none (different syntax with pipe) but checks for file
        p = PathTag(annotation=Path | None, is_file=True)
        self.assertFalse(p.update("/tmp"))
        self.assertTrue(p.update("/var/log/syslog"))
        self.assertIsNone(p._validate(None))