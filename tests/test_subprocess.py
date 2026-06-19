"""Tests for the subprocess IPC layer shared by the GUI (Tk) and TUI (Textual)
backends — the parent side, which is display-free and runs anywhere (incl. CI).

Covered:
* _safe_form never sends a __main__-defined function/class to the child
  (callbacks, validators and enum SelectTag values),
* a callback button is a submit: the whole form is validated before the
  callable runs, and the parent's real callable is never overwritten.

Run with:
    python -m unittest tests/test_subprocess.py
"""
import io
import pickle
import sys
import unittest
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from mininterface.tag import Tag, SelectTag
from mininterface.validators import not_empty
from mininterface._lib.auxiliary import flatten
from mininterface._lib.subprocess_base import SubprocessAdaptorBase, _stripped_callback


class Action(Enum):
    NOTIFY = "notify-send"
    SHUTDOWN = "shutdown"


class Point:
    """A user-defined class used as a field value (see docs/Supported-types.md)."""
    def __init__(self, i):
        self.i = int(i)

    def __str__(self):
        return str(self.i)


def a_callback():
    """Module-level so it is picklable by reference (like a user's function)."""
    a_callback.calls += 1
a_callback.calls = 0


def _import_or_skip(name):
    """Import a module or skip the test if it is not installed."""
    try:
        return __import__(name)
    except ImportError:
        raise unittest.SkipTest(f"{name} not installed")


def a_validator(tag):
    return True


@contextmanager
def _as_main(*objs):
    """Make objs look like they were defined in the user's __main__ script.

    pickle stores such functions/classes as `__main__.<name>` references, which
    the `python -c` child cannot resolve — exactly the situation we guard
    against.  The parent (here) can pickle them only while they live in
    __main__, so register them there for the duration of the test.
    """
    main = sys.modules["__main__"]
    saved_mod = {}
    added = []
    for obj in objs:
        saved_mod[obj] = obj.__module__
        obj.__module__ = "__main__"
        if not hasattr(main, obj.__name__):
            added.append(obj.__name__)
        setattr(main, obj.__name__, obj)
    try:
        yield
    finally:
        for obj, mod in saved_mod.items():
            obj.__module__ = mod
        for name in added:
            delattr(main, name)


class _ChildUnpickler(pickle.Unpickler):
    """Mimics the child: anything from the parent's __main__ is unreachable."""
    def find_class(self, module, name):
        if module == "__main__":
            raise AssertionError(f"leaked __main__ reference: {module}.{name}")
        return super().find_class(module, name)


def _child_safe(form):
    """Run _safe_form, then assert the result has no __main__ leaks by
    unpickling it the way the child would.  Returns the child-side copy."""
    safe = SubprocessAdaptorBase._safe_form(form)
    blob = pickle.dumps(safe)  # parent side — must not raise
    return _ChildUnpickler(io.BytesIO(blob)).load()  # child side — must not raise


class TestSafeForm(unittest.TestCase):
    """_safe_form keeps functions and user classes in the parent only."""

    def test_callback_becomes_button_placeholder(self):
        """A callable val is replaced by a real-function placeholder so the child
        still renders a button; the parent keeps the real callable."""
        with _as_main(a_callback):
            form = {"act": Tag(val=a_callback)}
            child = _child_safe(form)

        child_tag = list(flatten(child))[0]
        self.assertIs(child_tag.val, _stripped_callback)
        self.assertTrue(child_tag._is_a_callable(), "child must still see a button")
        # parent keeps the real callable
        self.assertIs(list(flatten(form))[0].val, a_callback)

    def test_validator_becomes_proxy(self):
        """Any validator (importable or __main__) is replaced by a _ValidationProxy.

        The proxy round-trips to the parent on FocusOut/Tab so live validation
        works even for __main__-defined functions, which the child can't unpickle."""
        from mininterface._lib.subprocess_child_base import _ValidationProxy
        for tag in (Tag(val="x", validation=a_validator),
                    Tag(val="", validation=not_empty)):
            child = _child_safe({"f": tag})
            child_validation = list(flatten(child))[0].validation
            self.assertIsInstance(child_validation, _ValidationProxy)

    def test_enum_select_is_labelized(self):
        """An enum SelectTag is sent as plain labels, not enum members."""
        with _as_main(Action):
            form = {"a": SelectTag(val=Action.NOTIFY, options=Action)}
            child = _child_safe(form)

        child_tag = list(flatten(child))[0]
        self.assertEqual({"notify-send": "notify-send", "shutdown": "shutdown"},
                         child_tag.options)
        self.assertEqual("notify-send", child_tag.val)
        # parent keeps the real enum
        self.assertIs(list(flatten(form))[0].val, Action.NOTIFY)

    def test_resolve_select_labels_maps_back(self):
        """The label the child returns is mapped back to the real enum member."""
        tags = [SelectTag(val=Action.NOTIFY, options=Action)]
        resolved = SubprocessAdaptorBase._resolve_select_labels(tags, ["shutdown"])
        self.assertEqual([Action.SHUTDOWN], resolved)

    def test_select_with_custom_option_values(self):
        """A SelectTag whose option *values* are custom objects still ships as
        labels, and the returned label resolves back to the real object."""
        with _as_main(Point):
            p1, p2 = Point(1), Point(2)
            form = {"a": SelectTag(val=p1, options={"one": p1, "two": p2})}
            child = _child_safe(form)
        self.assertEqual({"one": "one", "two": "two"}, list(flatten(child))[0].options)
        resolved = SubprocessAdaptorBase._resolve_select_labels(
            [form["a"]], ["two"])
        self.assertIs(p2, resolved[0])

    def test_custom_class_value_sent_as_string(self):
        """A custom-class value (defined in __main__) is sent to the child as a
        string; the parent's real tag rebuilds the object from it on submit."""
        with _as_main(Point):
            form = {"p": Tag(val=Point(10), annotation=Point)}
            child = _child_safe(form)

        child_tag = list(flatten(child))[0]
        self.assertEqual("10", child_tag.val)
        self.assertIsNone(child_tag.annotation)  # __main__ type dropped for the child

        # parent rebuilds the real object from the string the child returns
        real = list(flatten(form))[0]
        self.assertTrue(real.update("100"))
        self.assertIsInstance(real.val, Point)
        self.assertEqual(100, real.val.i)

    def test_layout_elements_are_child_safe(self):
        """facet._layout elements (str / Path / Image) cross the pipe intact."""
        from pathlib import Path
        from mininterface.facet import Image
        for el in ["text", Path("dog.jpg"), Image("dog.jpg")]:
            blob = pickle.dumps(el)
            _ChildUnpickler(io.BytesIO(blob)).load()  # raises on a __main__ leak

    def test_pydantic_form_is_child_safe(self):
        """A pydantic model's tag metadata does not leak __main__ to the child."""
        pydantic = _import_or_skip("pydantic")
        from mininterface._lib.form_dict import dataclass_to_tagdict
        from mininterface import run

        class PydEnv(pydantic.BaseModel):
            name: str = "x"
            age: int = 3

        m = run(PydEnv, interface="text", args=[])
        _child_safe(dataclass_to_tagdict(m.env, m))  # raises on a leak

    def test_attrs_form_is_child_safe(self):
        """An attrs class's tag metadata does not leak __main__ to the child."""
        attr = _import_or_skip("attr")
        from mininterface._lib.form_dict import dataclass_to_tagdict
        from mininterface import run

        @attr.s(auto_attribs=True)
        class AttrEnv:
            name: str = "x"
            age: int = 3

        m = run(AttrEnv, interface="text", args=[])
        _child_safe(dataclass_to_tagdict(m.env, m))  # raises on a leak


class TestButtonSubmitValidation(unittest.TestCase):
    """A callback button is a submit and must respect field validation."""

    def _adaptor(self):
        # Textual subprocess adaptor, constructed without spawning a child
        # (no display needed) — _handle_callback lives on the shared base.
        from mininterface._lib.redirectable import Redirectable
        from mininterface._mininterface import Mininterface
        from mininterface._textual_interface.subprocess_adaptor import TextualSubprocessAdaptor

        class _CI(Redirectable, Mininterface):
            _adaptor: TextualSubprocessAdaptor

        return TextualSubprocessAdaptor(_CI(), None)

    def setUp(self):
        a_callback.calls = 0

    def test_empty_validated_field_blocks_button(self):
        """Pressing the callback button with an invalid field must NOT submit
        and must NOT run the callable."""
        adaptor = self._adaptor()
        btn = Tag(val=a_callback)
        field = Tag(val="", validation=not_empty)
        adaptor.facet._form = {"btn": btn, "field": field}

        # child sends its button placeholder + the (empty) field value
        result = adaptor._handle_callback("button", 0, [_stripped_callback, ""])

        self.assertEqual("retry", result)
        self.assertEqual(0, a_callback.calls)
        self.assertIs(btn.val, a_callback, "real callable must be preserved")

    def test_valid_field_runs_callback(self):
        """With a valid field the button submits and runs the real callable."""
        adaptor = self._adaptor()
        btn = Tag(val=a_callback)
        field = Tag(val="", validation=not_empty)
        adaptor.facet._form = {"btn": btn, "field": field}

        result = adaptor._handle_callback("button", 0, [_stripped_callback, "hello"])

        self.assertEqual("done", result)
        self.assertEqual(1, a_callback.calls)
        self.assertEqual("hello", field.val)
        self.assertIs(btn.val, a_callback, "real callable must be preserved")


class TestValidationProxy(unittest.TestCase):
    """The validate round-trip: child fires proxy → parent runs real validator."""

    def _adaptor(self):
        from mininterface._lib.redirectable import Redirectable
        from mininterface._mininterface import Mininterface
        from mininterface._textual_interface.subprocess_adaptor import TextualSubprocessAdaptor

        class _CI(Redirectable, Mininterface):
            _adaptor: TextualSubprocessAdaptor

        return TextualSubprocessAdaptor(_CI(), None)

    def _sent(self, adaptor):
        """Drain what _handle_callback sent via _send (captured in write_fd)."""
        import os, pickle, struct
        r, w = os.pipe()
        adaptor._write_fd = w
        return r, w

    def test_valid_value_sends_true_result(self):
        """When validation passes, parent sends VALIDATE_RESULT(True)."""
        from mininterface._lib.ipc_command import IpcCommand
        import os, pickle, struct

        adaptor = self._adaptor()
        field = Tag(val="", validation=not_empty)
        adaptor.facet._form = {"f": field}

        r, w = os.pipe()
        adaptor._write_fd = w

        result = adaptor._handle_callback("validate", 0, "hello")
        os.close(w)

        raw = os.read(r, 4096)
        os.close(r)
        length = struct.unpack("!I", raw[:4])[0]
        cmd, error_text = pickle.loads(raw[4:4 + length])

        self.assertEqual("continue", result)
        self.assertEqual(IpcCommand.VALIDATE_RESULT, cmd)
        self.assertIs(True, error_text)

    def test_invalid_value_sends_error_text(self):
        """When validation fails, parent sends VALIDATE_RESULT(error_string)."""
        from mininterface._lib.ipc_command import IpcCommand
        import os, pickle, struct

        adaptor = self._adaptor()
        field = Tag(val="hello", validation=not_empty)
        adaptor.facet._form = {"f": field}

        r, w = os.pipe()
        adaptor._write_fd = w

        result = adaptor._handle_callback("validate", 0, "")
        os.close(w)

        raw = os.read(r, 4096)
        os.close(r)
        length = struct.unpack("!I", raw[:4])[0]
        cmd, error_text = pickle.loads(raw[4:4 + length])

        self.assertEqual("continue", result)
        self.assertEqual(IpcCommand.VALIDATE_RESULT, cmd)
        self.assertIsNotNone(error_text)


class TestRedirectTail(unittest.TestCase):
    """A print() streamed to a closing child (e.g. the last statement of a `with`
    block) is never re-rendered by another dialog. On __exit__ that swallowed tail
    must be replayed to the real stdout instead of being lost."""

    def _redirectable(self, captured):
        from mininterface._lib.redirectable import Redirectable

        class _R(Redirectable):
            pass

        r = _R()
        r._original_stdout = captured
        return r

    def test_tail_after_last_dialog_is_reprinted(self):
        captured = io.StringIO()
        sent = []
        r = self._redirectable(captured)

        with r:
            red = r._redirected
            red.output_callback = sent.append           # simulate IPC stream sink
            print("shown-in-dialog")                     # child renders this
            red.confirm_streamed()                       # next dialog confirms it
            print("tail-A")                              # never re-rendered
            print("tail-B", end="")                      # unterminated final line

        # Confirmed-shown line is NOT reprinted; the swallowed tail (incl. the
        # unterminated final line) IS reprinted to the real stdout.
        self.assertEqual("tail-A\ntail-B\n", captured.getvalue())
        self.assertEqual(["shown-in-dialog", "tail-A"], sent)

    def test_no_tail_when_everything_confirmed(self):
        captured = io.StringIO()
        sent = []
        r = self._redirectable(captured)

        with r:
            red = r._redirected
            red.output_callback = sent.append
            print("a")
            red.confirm_streamed()

        self.assertEqual("", captured.getvalue())

    def test_pending_buffer_still_flushed(self):
        """Text printed with no live child (output_callback unset) goes to
        pending_buffer and is flushed on exit, as before."""
        captured = io.StringIO()
        r = self._redirectable(captured)

        with r:
            print("no-child-here")

        self.assertEqual("no-child-here\n", captured.getvalue())


class TestProxySubmitSuppression(unittest.TestCase):
    """Pressing Enter to submit also fires on_blur → an on_change/validation proxy
    round-trip on the main thread, which races the RESULT the worker just sent and
    used to wedge a clean shutdown (leaving the terminal corrupted). Proxies are
    suppressed during submit/cancel; the parent re-validates the whole form anyway."""

    def setUp(self):
        import mininterface._lib.subprocess_child_base as scb
        self.scb = scb
        self.addCleanup(scb.set_proxies_active, True)  # restore module global

    def test_validation_proxy_noop_when_suppressed(self):
        from mininterface._lib.subprocess_child_base import _ValidationProxy
        self.scb.set_proxies_active(False)
        # No fds wired: if the proxy tried a round-trip it would assert/raise.
        # Suppressed, it must short-circuit to "valid" without touching the pipe.
        self.assertIs(True, _ValidationProxy(0)(Tag(val="x")))

    def test_on_change_proxy_noop_when_suppressed(self):
        from mininterface._lib.subprocess_child_base import _OnChangeProxy
        self.scb.set_proxies_active(False)
        self.assertIsNone(_OnChangeProxy(0)(Tag(val="x")))

    def test_proxies_reactivate(self):
        self.scb.set_proxies_active(False)
        self.assertFalse(self.scb._proxies_active)
        self.scb.set_proxies_active(True)
        self.assertTrue(self.scb._proxies_active)

    def test_shutdown_in_proxy_loop_triggers_hook_and_unblocks(self):
        """If a proxy round-trip is interrupted by SHUTDOWN (parent already moved on),
        the proxy must call the shutdown hook and return instead of parking forever."""
        from mininterface._lib.subprocess_child_base import _ValidationProxy, register_hooks, send_msg
        from mininterface._lib.ipc_command import IpcCommand
        import os

        called = []
        # Wire a real pipe the proxy reads from; parent end writes a SHUTDOWN frame.
        cmd_r, cmd_w = os.pipe()      # proxy reads responses from cmd_r
        res_r, res_w = os.pipe()      # proxy writes the CALLBACK to res_w (drained, ignored)
        self.addCleanup(lambda: [os.close(fd) for fd in (cmd_r, res_r) if _safe_open(fd)])

        register_hooks(cmd_r, res_w,
                       apply_form_update=lambda *a: None,
                       append_output=lambda *a: None,
                       shutdown=lambda: called.append("shutdown"))
        self.addCleanup(register_hooks, -1, -1, lambda *a: None, lambda *a: None)

        # Parent side: send a SHUTDOWN frame the proxy will read.
        send_msg(cmd_w, (IpcCommand.SHUTDOWN,))
        os.close(cmd_w)

        result = _ValidationProxy(0)(Tag(val="x"))
        os.close(res_w)
        os.close(res_r)

        self.assertIs(True, result)              # returns instead of blocking
        self.assertEqual(["shutdown"], called)   # shutdown hook fired


def _safe_open(fd):
    import os
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


class _AdaptorHarness(unittest.TestCase):
    """Parent-side adaptor wired to hand-made pipes instead of a spawned child."""

    def _adaptor(self):
        from mininterface._lib.redirectable import Redirectable
        from mininterface._mininterface import Mininterface
        from mininterface._textual_interface.subprocess_adaptor import TextualSubprocessAdaptor

        class _CI(Redirectable, Mininterface):
            _adaptor: TextualSubprocessAdaptor

        adaptor = TextualSubprocessAdaptor(_CI(), None)
        adaptor._ensure_process = lambda: None  # no child spawn; pipes are wired by hand
        return adaptor

    def _wire_child_reply(self, adaptor, *frames):
        """Hand the adaptor pipes where the 'child' already replied with frames.
        Returns the read end of the parent→child pipe (what the parent sent)."""
        from mininterface._lib.subprocess_child_base import send_msg
        import os
        cmd_r, cmd_w = os.pipe()   # parent _send sink (drained by the OS buffer)
        res_r, res_w = os.pipe()   # parent _receive source
        for frame in frames:
            send_msg(res_w, frame)
        os.close(res_w)
        adaptor._write_fd = cmd_w
        adaptor._read_fd = res_r
        self.addCleanup(lambda: [os.close(fd) for fd in (cmd_r, cmd_w, res_r) if _safe_open(fd)])
        return cmd_r

    def _parent_frames(self, adaptor, cmd_r):
        """Close the parent's write end and parse every frame it sent. A
        non-persistent dialog tears the child down on return (closing the write
        fd), so only close it here if it is still open — the frames it already
        sent stay buffered in cmd_r either way."""
        from mininterface._lib.subprocess_child_base import read_msg
        import os
        if adaptor._write_fd is not None:
            os.close(adaptor._write_fd)
            adaptor._write_fd = None
        frames = []
        while (msg := read_msg(cmd_r)) is not None:
            frames.append(msg)
        return frames


class TestChildErrorPropagation(_AdaptorHarness):
    """A dialog build that crashes in the child (e.g. facet._layout on a missing
    file) must surface in the parent as the ORIGINAL exception, not a misleading
    Cancelled the program would mistake for Esc."""

    @staticmethod
    def _a_child_error():
        """A real exception with a traceback, as the child would catch it."""
        try:
            Path("/nonexistent/dir/file").stat()
        except OSError as exc:
            return exc

    def test_error_payload_carries_exception_and_traceback(self):
        from mininterface._lib.subprocess_child_base import error_payload
        from mininterface._lib.ipc_command import IpcCommand

        cmd, exc, tb = error_payload(self._a_child_error())
        self.assertEqual(IpcCommand.ERROR, cmd)
        self.assertIsInstance(exc, FileNotFoundError)
        self.assertIn("FileNotFoundError", tb)
        pickle.dumps((cmd, exc, tb))  # the frame must survive the pipe

    def test_error_payload_unpicklable_exception_falls_back_to_text(self):
        from mininterface._lib.subprocess_child_base import error_payload
        try:
            raise ValueError(lambda: None)  # lambda arg → unpicklable exception
        except ValueError as exc:
            cmd, sent, tb = error_payload(exc)
        self.assertIsNone(sent)
        self.assertIn("ValueError", tb)

    def test_worker_loop_ships_error_instead_of_cancel(self):
        """An exception escaping a FORM handler reaches the parent as ERROR."""
        from mininterface._lib.subprocess_child_base import _ipc_worker_loop, send_msg, read_msg
        from mininterface._lib.ipc_command import IpcCommand
        import os

        cmd_r, cmd_w = os.pipe()
        res_r, res_w = os.pipe()
        self.addCleanup(lambda: [os.close(fd) for fd in (cmd_r, cmd_w, res_r, res_w) if _safe_open(fd)])

        def failing_form(write_fd, *args):
            Path("/nonexistent/dir/file").stat()

        send_msg(cmd_w, (IpcCommand.FORM,))
        os.close(cmd_w)  # EOF after the one command → loop exits via on_eof
        _ipc_worker_loop(cmd_r, res_w, {
            'FORM': failing_form, 'BUTTONS': None, 'OUTPUT': None, 'on_eof': lambda: None,
        })

        command, exc, tb = read_msg(res_r)
        self.assertEqual(IpcCommand.ERROR, command)
        self.assertIsInstance(exc, FileNotFoundError)
        self.assertIn("FileNotFoundError", tb)

    def test_run_dialog_reraises_original_exception(self):
        from mininterface._lib.subprocess_child_base import error_payload

        adaptor = self._adaptor()
        self._wire_child_reply(adaptor, error_payload(self._a_child_error()))

        with self.assertRaises(FileNotFoundError) as ctx:
            adaptor.run_dialog({"f": Tag(val="x")})
        # The child's traceback travels along as the cause.
        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)
        self.assertIn("FileNotFoundError", str(ctx.exception.__cause__))

    def test_buttons_reraises_original_exception(self):
        from mininterface._lib.subprocess_child_base import error_payload

        adaptor = self._adaptor()
        self._wire_child_reply(adaptor, error_payload(self._a_child_error()))

        with self.assertRaises(FileNotFoundError):
            adaptor.buttons("Continue?", [("Yes", True), ("No", False)])

    def test_unpicklable_error_raises_runtimeerror_with_traceback(self):
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        self._wire_child_reply(adaptor, (IpcCommand.ERROR, None, "Traceback ...\nValueError: boom"))

        with self.assertRaises(RuntimeError) as ctx:
            adaptor.run_dialog({"f": Tag(val="x")})
        self.assertIn("ValueError: boom", str(ctx.exception))


class TestQuitCommand(_AdaptorHarness):
    """Closing the window (X) quits the whole program — like the in-process GUI's
    WM_DELETE_WINDOW → sys.exit — instead of a recoverable Cancelled that a retry
    loop would answer with a freshly respawned window."""

    def test_run_dialog_quit_exits_program(self):
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        self._wire_child_reply(adaptor, (IpcCommand.QUIT,))

        with self.assertRaises(SystemExit) as ctx:
            adaptor.run_dialog({"f": Tag(val="x")})
        self.assertEqual(0, ctx.exception.code)

    def test_buttons_quit_exits_program(self):
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        self._wire_child_reply(adaptor, (IpcCommand.QUIT,))

        with self.assertRaises(SystemExit) as ctx:
            adaptor.buttons("Continue?", [("Yes", True)])
        self.assertEqual(0, ctx.exception.code)


class TestDialogReentrancy(_AdaptorHarness):
    """A dialog opened from a live on_change/validation callback would deadlock
    (the child UI thread is parked in the proxy round-trip) — refuse it fast."""

    def test_dialog_from_on_change_is_refused(self):
        from mininterface.exceptions import _DialogReentrancyError
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        cmd_r = self._wire_child_reply(adaptor)
        caught = []

        def opens_a_dialog(tag):
            try:
                adaptor.buttons("nested?", [("Ok", True)])
            except _DialogReentrancyError as e:
                caught.append(e)

        field = Tag(val="x", on_change=opens_a_dialog)
        adaptor.facet._form = {"f": field}
        result = adaptor._handle_callback("on_change", 0, "y")

        self.assertEqual("continue", result)
        self.assertEqual(1, len(caught))
        # The child's round-trip was still answered (else its proxy would hang).
        frames = self._parent_frames(adaptor, cmd_r)
        self.assertEqual(IpcCommand.FORM_UPDATE, frames[-1][0])

    def test_on_change_exception_still_answers_the_child(self):
        """Even a crashing on_change must not leave the child's proxy parked."""
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        cmd_r = self._wire_child_reply(adaptor)

        def boom(tag):
            raise ValueError("boom")

        adaptor.facet._form = {"f": Tag(val="x", on_change=boom)}
        with self.assertRaises(ValueError):
            adaptor._handle_callback("on_change", 0, "y")

        frames = self._parent_frames(adaptor, cmd_r)
        self.assertEqual(IpcCommand.FORM_UPDATE, frames[-1][0])

    def test_validator_exception_still_answers_the_child(self):
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        cmd_r = self._wire_child_reply(adaptor)

        def boom(tag):
            raise OSError("boom")

        adaptor.facet._form = {"f": Tag(val="x", validation=boom)}
        try:
            adaptor._handle_callback("validate", 0, "y")
        except OSError:
            pass  # may or may not propagate depending on Tag.update; both are fine

        frames = self._parent_frames(adaptor, cmd_r)
        self.assertEqual(IpcCommand.VALIDATE_RESULT, frames[-1][0])

    def test_guard_off_outside_callbacks(self):
        adaptor = self._adaptor()
        self.assertFalse(adaptor._in_live_callback)
        adaptor._guard_reentrancy()  # must not raise


class TestButtonsRawLayout(_AdaptorHarness):
    """facet._layout set before confirm()/alert() ships with the BUTTONS message
    instead of silently disappearing."""

    def test_buttons_message_carries_raw_layout(self):
        from mininterface._lib.ipc_command import IpcCommand

        adaptor = self._adaptor()
        cmd_r = self._wire_child_reply(adaptor, (IpcCommand.RESULT, True))

        adaptor.facet._layout(["AHoj", Path("/tmp")])
        result = adaptor.buttons("Continue?", [("Yes", True)], focused=1)

        self.assertIs(True, result)
        self.assertEqual([], adaptor.facet._raw_layout, "layout must be consumed")
        frames = self._parent_frames(adaptor, cmd_r)
        command, text, _buttons, _focused, _timeout, _redirected, raw_layout, *_ = frames[-1]
        self.assertEqual(IpcCommand.BUTTONS, command)
        self.assertEqual("Continue?", text)
        self.assertEqual(["AHoj", Path("/tmp")], raw_layout)


class TestTerminalReleaseAfterDialog(_AdaptorHarness):
    """Outside a `with` block the Textual child owns the tty (alternate screen +
    stdin), so it must be torn down after each dialog or a following input()/
    print() in the parent collides with it. Inside `with` (always_shown) it
    persists, and the web backend (TEXTUAL_DRIVER) holds no local tty."""

    def _spy_destroy(self, adaptor):
        calls = []
        adaptor._destroy = lambda: calls.append(1)
        return calls

    def _run_buttons(self, adaptor):
        from mininterface._lib.ipc_command import IpcCommand
        self._wire_child_reply(adaptor, (IpcCommand.RESULT, True))
        adaptor.buttons("Continue?", [("Yes", True)])

    def test_non_persistent_dialog_releases_terminal(self):
        adaptor = self._adaptor()
        calls = self._spy_destroy(adaptor)
        self._run_buttons(adaptor)
        self.assertEqual([1], calls, "a non-with Textual dialog must tear the child down")

    def test_with_block_keeps_child_alive(self):
        adaptor = self._adaptor()
        adaptor.interface._always_shown = True
        calls = self._spy_destroy(adaptor)
        self._run_buttons(adaptor)
        self.assertEqual([], calls, "inside `with` the child must persist")

    def test_web_mode_keeps_child_alive(self):
        import os
        adaptor = self._adaptor()
        calls = self._spy_destroy(adaptor)
        old = os.environ.get("TEXTUAL_DRIVER")
        os.environ["TEXTUAL_DRIVER"] = "textual.drivers.web_driver:WebDriver"
        try:
            self._run_buttons(adaptor)
        finally:
            os.environ.pop("TEXTUAL_DRIVER", None) if old is None else os.environ.__setitem__("TEXTUAL_DRIVER", old)
        self.assertEqual([], calls, "web backend holds no local tty; child persists")


class TestWorkerLoopDispatch(_AdaptorHarness):
    """The child worker loop routes the parent-only commands to their handlers."""

    def _run_loop(self, *frames, handlers=None):
        from mininterface._lib.subprocess_child_base import _ipc_worker_loop, send_msg
        import os
        cmd_r, cmd_w = os.pipe()
        res_r, res_w = os.pipe()
        self.addCleanup(lambda: [os.close(fd) for fd in (cmd_r, res_r, res_w) if _safe_open(fd)])
        for frame in frames:
            send_msg(cmd_w, frame)
        os.close(cmd_w)  # EOF ends the loop via on_eof
        _ipc_worker_loop(cmd_r, res_w, handlers)

    def test_settings_reach_the_handler(self):
        from mininterface._lib.ipc_command import IpcCommand
        got = []
        self._run_loop((IpcCommand.SETTINGS, {"combobox_since": 42}),
                       handlers={'SETTINGS': got.append, 'on_eof': lambda: None})
        self.assertEqual([{"combobox_since": 42}], got)

    def test_clear_output_reaches_the_handler(self):
        from mininterface._lib.ipc_command import IpcCommand
        cleared = []
        self._run_loop((IpcCommand.CLEAR_OUTPUT,),
                       handlers={'CLEAR_OUTPUT': lambda: cleared.append(True), 'on_eof': lambda: None})
        self.assertEqual([True], cleared)

    def test_parent_clear_output_resets_history_without_child(self):
        adaptor = self._adaptor()
        adaptor._record_output("old text\n")
        adaptor._clear_output()  # no child process — must not raise
        self.assertEqual("", adaptor._output_history)


if __name__ == "__main__":
    unittest.main()
