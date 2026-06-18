import subprocess
import sys
from unittest.mock import patch

from mininterface import Mininterface
import mininterface.dialogs as dialogs

from shared import TestAbstract


class TestDialogs(TestAbstract):
    """The static `mininterface.dialogs` shortcut."""

    def setUp(self):
        super().setUp()
        dialogs._m = None  # reset the cached singleton

    def tearDown(self):
        super().tearDown()
        dialogs._m = None

    @patch.dict("os.environ", {"MININTERFACE_INTERFACE": "min"})
    def test_singleton(self):
        m1 = dialogs._get_interface()
        m2 = dialogs._get_interface()
        self.assertIs(m1, m2)
        # dialog functions reuse that very interface, never spawn a new one
        with patch.object(m1, "confirm", return_value=False) as mock:
            self.assertFalse(dialogs.confirm("OK?"))
        mock.assert_called_once()

    @patch.dict("os.environ", {"MININTERFACE_INTERFACE": "min"})
    def test_env_override(self):
        self.assertIs(type(dialogs._get_interface()), Mininterface)

    @patch.dict("os.environ", {"MININTERFACE_INTERFACE": "min"})
    def test_delegates(self):
        self.assertEqual(0, dialogs.ask("Number", int))
        self.assertTrue(dialogs.confirm("OK?"))
        self.assertFalse(dialogs.confirm("OK?", False))
        self.assertEqual({"count": 3}, dialogs.form({"count": 3}))
        self.assertEqual("b", dialogs.select(["a", "b"], default="b"))

    @patch.dict("os.environ", {"MININTERFACE_INTERFACE": "min"})
    def test_alert_outputs(self):
        with self.assertOutputs("Alert text Hello"):
            dialogs.alert("Hello")

    def test_top_level_access(self):
        import mininterface
        self.assertIn("dialogs", mininterface.__all__)
        # the lazy __getattr__ must resolve the submodule without recursing (regression)
        self.assertIs(mininterface.__getattr__("dialogs"), dialogs)
        # and the real-world fresh-import path: `import mininterface; mininterface.dialogs`
        out = subprocess.run(
            [sys.executable, "-c", "import mininterface; print(mininterface.dialogs.__name__)"],
            capture_output=True, text=True,
        )
        self.assertEqual("mininterface.dialogs", out.stdout.strip(), out.stderr)
