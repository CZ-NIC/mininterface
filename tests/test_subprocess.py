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
        from mininterface._lib.tui_command import TuiCommand
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
        self.assertEqual(TuiCommand.VALIDATE_RESULT, cmd)
        self.assertIs(True, error_text)

    def test_invalid_value_sends_error_text(self):
        """When validation fails, parent sends VALIDATE_RESULT(error_string)."""
        from mininterface._lib.tui_command import TuiCommand
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
        self.assertEqual(TuiCommand.VALIDATE_RESULT, cmd)
        self.assertIsNotNone(error_text)


if __name__ == "__main__":
    unittest.main()
