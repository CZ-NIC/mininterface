"""Tests for the GUI (Tk subprocess) interface.

Requires a display. Run with:
    xvfb-run -a python -m unittest tests/test_gui.py

Like test_textual drives the Textual child app in-process with a Pilot, these
drive the **Tk child adaptor in-process** (no subprocess spawn) and introspect
the real widget tree: send a form, assert the right widgets actually appear.

One persistent adaptor is shared across the class — mirroring the real child,
which reuses a single Tk app for every dialog — because a second tkinter.Tk()
in the same process clashes with the first.
"""
import os
import unittest

from mininterface.tag import Tag, SelectTag
from mininterface._lib.auxiliary import flatten
from mininterface._lib.subprocess_base import SubprocessAdaptorBase


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


def _make_child_adaptor():
    """Build the persistent Tk child adaptor in-process (no subprocess, no IPC
    worker, no mainloop) so we can build forms and inspect the widget tree."""
    from mininterface._lib.redirectable import Redirectable
    from mininterface._mininterface import Mininterface
    from mininterface._tk_interface.subprocess_child import _make_child_adaptor_class

    AdaptorCls = _make_child_adaptor_class()
    read_fd, write_fd = os.pipe()  # never read — the IPC worker is not started

    class _CI(Redirectable, Mininterface):
        _adaptor: AdaptorCls

        def __init__(self):
            self._child_fds = (read_fd, write_fd)
            super().__init__()

    return _CI()._adaptor


def _walk(widget, acc=None):
    """All descendant widgets of `widget`."""
    acc = [] if acc is None else acc
    for child in widget.winfo_children():
        acc.append(child)
        _walk(child, acc)
    return acc


@unittest.skipUnless(_has_display(), "No display available (run under xvfb-run -a)")
class TestGuiWidgets(unittest.TestCase):
    """A form sent to the child renders the expected Tk widgets."""

    @classmethod
    def setUpClass(cls):
        cls.adaptor = _make_child_adaptor()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.adaptor.destroy()
        except Exception:
            pass
        # Don't leave a destroyed Tk root as the process-wide default — a later
        # tkinter-using test could otherwise pick it up (flaky cross-test state).
        import tkinter
        tkinter._default_root = None

    def _render(self, raw_form, title="Form"):
        """Send a form through the same path the real child uses and realise the
        widgets. Returns the adaptor."""
        ad = self.adaptor
        ad._clear_dialog()
        form = SubprocessAdaptorBase._safe_form(raw_form)  # what the child receives
        for k, t in form.items():
            if not t.label:
                t.label = k
        for t in flatten(form):
            t._facet = ad.facet
        ad._setup_form_facet(form)
        ad._build_form(form, title, True)
        ad.update_idletasks()
        ad.update()
        return ad

    def _of_class(self, cls):
        return [w for w in _walk(self.adaptor) if w.winfo_class() == cls]

    def test_single_input_renders_one_entry(self):
        """A form with one str field shows exactly one input field with its value."""
        ad = self._render({"name": Tag("Alice")})
        self.assertEqual(1, len(self._of_class("TEntry")))
        self.assertEqual({"name": "Alice"}, ad.form.get())

    def test_multiple_fields_render(self):
        """Each field of a multi-field form is rendered and reports its value."""
        ad = self._render({"first": Tag("a"), "second": Tag("b"), "third": Tag("c")})
        self.assertEqual(3, len(self._of_class("TEntry")))
        self.assertEqual({"first": "a", "second": "b", "third": "c"}, ad.form.get())

    def test_bool_renders_checkbutton(self):
        """A bool field renders a checkbox, not a text entry."""
        ad = self._render({"agree": Tag(True)})
        self.assertEqual(1, len(self._of_class("TCheckbutton")))
        self.assertEqual({"agree": True}, ad.form.get())

    def test_select_renders_one_radiobutton_per_option(self):
        """A SelectTag with N options renders N radio buttons and keeps the value."""
        ad = self._render({"choice": SelectTag("b", options=["a", "b", "c"])})
        self.assertEqual(3, len(self._of_class("TRadiobutton")))
        self.assertEqual({"choice": "b"}, ad.form.get())

    def test_title_is_shown_in_header(self):
        """The form title appears in the in-window header label."""
        ad = self._render({"x": Tag(1)}, title="My Title")
        self.assertEqual("My Title", ad.label.cget("text"))

    def test_redirected_output_is_displayed(self):
        """Program output sent to the child shows up in the output text widget."""
        ad = self._render({"x": Tag(1)})
        ad._write_output("hello from program\n")
        ad.update_idletasks()
        self.assertIn("hello from program", ad.text_widget.get("1.0", "end"))


@unittest.skipUnless(_has_display(), "No display available (run under xvfb-run -a)")
class TestGuiSubprocess(unittest.TestCase):
    """Smoke test of the real subprocess wiring (the `python -c` child)."""

    def test_process_spawned_eagerly(self):
        """Creating the GUI interface spawns a live child process immediately."""
        from mininterface.interfaces import get_interface
        m = get_interface("gui", title="TestApp")
        try:
            self.assertIsNotNone(m._adaptor._process)
            self.assertIsNone(m._adaptor._process.poll(), "child should be running")
        finally:
            m._adaptor._destroy()


if __name__ == "__main__":
    unittest.main()
