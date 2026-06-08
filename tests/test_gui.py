"""Tests for the GUI (Tk subprocess) interface.

Requires a display. Run with:
    xvfb-run -a python -m unittest tests/test_gui.py

Tests use process.terminate() for cancel simulation since xvfb without a
window manager does not support reliable xdotool key injection.
"""
import os
import threading
import time
import unittest

from mininterface.exceptions import Cancelled


def _has_display():
    """True when a usable X display is available (real or Xvfb)."""
    if not os.environ.get("DISPLAY"):
        return False
    try:
        import tkinter
        r = tkinter.Tk()
        r.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_display(), "No display available (run under xvfb-run -a)")
class TestGUI(unittest.TestCase):
    """Tk subprocess GUI — tests that work without a window manager."""

    def _get_interface(self):
        from mininterface.interfaces import get_interface
        return get_interface("gui", title="TestApp")

    def test_cancel_on_process_terminate(self):
        """Killing the child process raises Cancelled in the parent."""
        m = self._get_interface()
        result = {}

        def killer():
            time.sleep(1.2)
            try:
                m._adaptor._process.terminate()
            except Exception as e:
                result["err"] = str(e)

        threading.Thread(target=killer, daemon=True).start()
        try:
            m.form({"x": 1}, "F")
            result["ok"] = False
        except Cancelled:
            result["ok"] = True
        finally:
            m._adaptor._destroy()

        self.assertTrue(result.get("ok"), result)

    def test_output_displayed(self):
        """Print output sent via the IPC pipe reaches the child (no crash)."""
        m = self._get_interface()
        result = {}

        def killer():
            time.sleep(1.2)
            m._adaptor._process.terminate()

        threading.Thread(target=killer, daemon=True).start()
        try:
            m._adaptor._send_output("hello from test\n")
            m.form({"x": 1}, "F")
        except Cancelled:
            result["ok"] = True
        finally:
            m._adaptor._destroy()

        self.assertTrue(result.get("ok"), result)

    def test_alert_cancel(self):
        """alert() blocks until the child is cancelled."""
        m = self._get_interface()
        result = {}

        def killer():
            time.sleep(1.2)
            m._adaptor._process.terminate()

        threading.Thread(target=killer, daemon=True).start()
        try:
            m.alert("Test alert")
            result["ok"] = False
        except (Cancelled, SystemExit):
            result["ok"] = True
        except Exception:
            result["ok"] = True
        finally:
            m._adaptor._destroy()

        self.assertTrue(result.get("ok"), result)

    def test_process_spawned_eagerly(self):
        """Child process is spawned at interface creation time, not at form()."""
        m = self._get_interface()
        try:
            self.assertIsNotNone(m._adaptor._process)
            self.assertIsNone(m._adaptor._process.poll(), "child should be running")
        finally:
            m._adaptor._destroy()

    def test_multiple_forms_same_child(self):
        """After cancel the adaptor can handle a second form (new child spawned)."""
        m = self._get_interface()
        result = {}

        def killer():
            time.sleep(0.8)
            m._adaptor._process.terminate()

        threading.Thread(target=killer, daemon=True).start()
        try:
            m.form({"x": 1}, "F1")
        except Cancelled:
            result["first_cancel"] = True

        def killer2():
            time.sleep(0.8)
            if m._adaptor._process:
                m._adaptor._process.terminate()

        threading.Thread(target=killer2, daemon=True).start()
        try:
            m.form({"x": 2}, "F2")
        except Cancelled:
            result["second_cancel"] = True
        finally:
            m._adaptor._destroy()

        self.assertTrue(result.get("first_cancel"))
        self.assertTrue(result.get("second_cancel"))


if __name__ == "__main__":
    unittest.main()
