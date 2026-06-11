"""Tests for the Textual (TUI) subprocess interface.

Fully headless — uses Textual's built-in run_test() Pilot, no display needed.
Works in CI out of the box.

Run with:
    python -m unittest tests/test_textual.py
"""
import os
import unittest

from mininterface.tag import Tag, SelectTag


class TestTextual(unittest.IsolatedAsyncioTestCase):
    """Textual persistent child app — headless via run_test() Pilot."""

    async def _open(self, form=None):
        """Create app + open IPC pipe. Call inside run_test() context."""
        from mininterface._lib.redirectable import Redirectable
        from mininterface._lib.subprocess_base import SubprocessAdaptorBase
        from mininterface._mininterface import Mininterface
        from mininterface._textual_interface import subprocess_child as sc
        from mininterface._textual_interface.adaptor import TextualAdaptor

        class _CI(Redirectable, Mininterface):
            _adaptor: TextualAdaptor

        interface = _CI()
        adaptor = TextualAdaptor(interface, None)
        App = sc._make_persistent_child_app_class()
        cmd_r, self._cmd_w = os.pipe()
        _res_r, res_w = os.pipe()
        self.app = App(adaptor, cmd_r, res_w)
        if form is not None:
            safe = SubprocessAdaptorBase._safe_form(form)
            for k, t in safe.items():
                if not t.label:
                    t.label = k
            self._safe_form = safe
        return self.app

    async def asyncTearDown(self):
        try:
            os.close(self._cmd_w)
        except OSError:
            pass

    async def test_output_log_appends(self):
        """_append_output writes lines into the RichLog."""
        from textual.widgets import RichLog
        app = await self._open()
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._append_output("hello world")
            app._append_output("second line")
            await pilot.pause(0.1)
            log = app.query_one("#output-log", RichLog)
            texts = [str(line) for line in log.lines]
            self.assertTrue(any("hello world" in t for t in texts))
            self.assertTrue(any("second line" in t for t in texts))
            app.exit()

    async def test_output_autoscrolls_to_bottom(self):
        """After many appends the RichLog stays scrolled to the latest line."""
        from textual.widgets import RichLog
        app = await self._open()
        async with app.run_test(size=(60, 10)) as pilot:
            await pilot.pause(0.3)
            for i in range(30):
                app._append_output(f"line {i}")
            await pilot.pause(0.2)
            log = app.query_one("#output-log", RichLog)
            self.assertEqual(log.scroll_offset.y, log.max_scroll_y)
            app.exit()

    async def test_form_renders_inputs(self):
        """_setup_form + _async_refresh renders one Input per tag."""
        from textual.widgets import Input
        form = {"name": Tag("Alice", label="name"), "age": Tag(30, label="age")}
        app = await self._open(form)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "Test Form", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            inputs = list(app.query(Input))
            self.assertEqual(2, len(inputs))
            values = [i.value for i in inputs]
            self.assertIn("Alice", values)
            self.assertIn("30", values)
            app.exit()

    async def test_bool_renders_checkbox(self):
        """A bool field renders a Checkbox reflecting its value (not an Input)."""
        from textual.widgets import Checkbox, Input
        form = {"agree": Tag(True, label="agree")}
        app = await self._open(form)
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "T", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            boxes = list(app.query(Checkbox))
            self.assertEqual(1, len(boxes))
            self.assertTrue(boxes[0].value)
            self.assertEqual(0, len(list(app.query(Input))))
            app.exit()

    async def test_select_renders_one_radio_per_option(self):
        """A SelectTag with N options renders N radio buttons and keeps the value."""
        from textual.widgets import RadioButton
        form = {"choice": SelectTag("b", options=["a", "b", "c"], label="choice")}
        app = await self._open(form)
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "T", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            radios = list(app.query(RadioButton))
            self.assertEqual(3, len(radios))
            from mininterface._textual_interface.widgets import TagWidget
            widget = next(w for w in app.widgets if isinstance(w, TagWidget))
            self.assertEqual("b", widget.get_ui_value())
            app.exit()

    async def test_form_title_shown(self):
        """Form title is reflected in app.title after _async_refresh."""
        form = {"v": Tag(0, label="v")}
        app = await self._open(form)
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "My Title", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            self.assertEqual("My Title", app.title)
            app.exit()

    async def test_submit_sets_result(self):
        """Pressing Enter on a form sets _result to (RESULT, [ui_vals])."""
        from mininterface._lib.ipc_command import IpcCommand
        form = {"x": Tag(7, label="x")}
        app = await self._open(form)
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "T", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            app._submitted.clear()
            await pilot.press("enter")
            await pilot.pause(0.1)
            self.assertEqual(IpcCommand.RESULT, app._result[0])

    async def test_escape_sets_cancel(self):
        """Pressing Escape sets _result to (CANCEL,)."""
        from mininterface._lib.ipc_command import IpcCommand
        form = {"x": Tag(1, label="x")}
        app = await self._open(form)
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app._setup_form(self._safe_form, "T", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            app._submitted.clear()
            await pilot.press("escape")
            await pilot.pause(0.1)
            self.assertEqual(IpcCommand.CANCEL, app._result[0])

    async def test_escape_keeps_app_alive_for_next_dialog(self):
        """A plain Escape cancel must NOT tear the persistent app down: after the
        worker's CANCEL post-processing the app stays alive and a second form
        renders. Regression for the cancel-then-reuse hang/exit."""
        import threading
        from mininterface._lib.subprocess_base import SubprocessAdaptorBase
        from mininterface._lib.subprocess_child_base import read_msg
        from mininterface._lib.ipc_command import IpcCommand
        from mininterface._textual_interface.form_contents import FormContents

        form = {"x": Tag(1, label="x")}
        app = await self._open(form)
        safe = self._safe_form
        # A result pipe whose read end (res_r) we drain like the parent would.
        res_r, res_w = os.pipe()
        app.write_fd = res_w

        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)

            # Run the real worker handler in a thread (mirrors _ipc_worker).
            done = threading.Event()

            def worker():
                app._handle_form(res_w, safe, "T", True, "", [])
                done.set()

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            await pilot.pause(0.3)  # let the form render

            await pilot.press("escape")
            # Parent side drains the CANCEL the worker sends back.
            msg = read_msg(res_r)
            self.assertEqual(IpcCommand.CANCEL, msg[0])
            await pilot.pause(0.2)
            self.assertTrue(done.wait(2), "worker did not finish after cancel")

            # The app must still be running — not exited by the cancel.
            self.assertFalse(app._closing)
            self.assertTrue(app.is_running, "app was torn down by a plain cancel")

            # And a second form renders fine on the same live app.
            app._setup_form(safe, "T2", True, [])
            await app._async_refresh()
            await pilot.pause(0.2)
            self.assertTrue(list(app.query(FormContents)))

        os.close(res_r)

    async def test_buttons_render_and_submit(self):
        """Button dialog renders two buttons; Enter confirms the focused one."""
        from mininterface._lib.ipc_command import IpcCommand
        from textual.widgets import Button
        app = await self._open()
        async with app.run_test(size=(60, 16)) as pilot:
            await pilot.pause(0.3)
            app.adaptor._build_buttons("Sure?", [("Yes", True), ("No", False)], 1)
            app.submit = False
            await app._async_refresh()
            await pilot.pause(0.2)
            buttons = list(app.query(Button))
            self.assertEqual(2, len(buttons))
            app._submitted.clear()
            await pilot.press("enter")
            await pilot.pause(0.1)
            self.assertEqual(IpcCommand.RESULT, app._result[0])
            self.assertTrue(app._result[1])  # "Yes" = True was focused


if __name__ == "__main__":
    unittest.main()
