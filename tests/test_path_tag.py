from pathlib import Path
from mininterface.tag import PathTag
from shared import TestAbstract


class TestPathTag(TestAbstract):
    def test_init_dir(self):
        self.assertEqual(Path("/tmp"), PathTag("/tmp")._get_init_dir())
        self.assertEqual(Path("/tmp"), PathTag(["/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log/", "/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log", "/tmp"])._get_init_dir())
        self.assertEqual(Path("/var/log"), PathTag(["/var/log/syslog", "/tmp"])._get_init_dir())
