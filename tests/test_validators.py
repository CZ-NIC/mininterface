from mininterface._lib.form_dict import TagDict, dataclass_to_tagdict
from mininterface.tag import DatetimeTag, Tag
from mininterface.tag.tag_factory import assure_tag
from mininterface.validators import limit, not_empty
from configs import AnnotatedTypes, AnnotatedTypesCombined
from shared import TestAbstract


from annotated_types import Gt, Lt


from datetime import time
from pathlib import Path


class TestValidators(TestAbstract):
    def test_not_empty(self):
        t1 = Tag("", validation=not_empty)
        self.assertFalse(t1.update(""))
        self.assertTrue(t1.update("1"))

        t2 = Tag(validation=not_empty, annotation=Path)
        self.assertFalse(t2.update(b""))
        self.assertFalse(t2.update(b"wrong type"))
        self.assertFalse(t2.update(Path("")))
        self.assertFalse(t2.update(Path(".")))
        self.assertTrue(t2.update(Path("/tmp")))

        t3 = Tag(validation=not_empty, annotation=bytes)
        self.assertFalse(t3.update(b""))
        self.assertTrue(t3.update(b"true"))

        t4 = DatetimeTag(validation=not_empty, annotation=time)
        self.assertFalse(t4.update(""))
        self.assertTrue(t4.update("12:12"))
        self.assertTrue(t4.update(time(10, 10)))
        self.assertFalse(t4.update(""))
        # This would pass through (if it's not midnight), as the _make_default_value is currently the current time,
        # not `time()`. We might implement it other way.
        self.assertTrue(t4.update(time()))

    def test_bare_limit(self):
        def f(val):
            return Tag(val)
        self.assertTrue(all(limit(1, 10)(f(v)) is True for v in (1, 2, 9, 10)))
        self.assertTrue(any(limit(1, 10)(f(v)) is not True for v in (-1, 0, 11)))
        self.assertTrue(all(limit(5)(f(v)) is True for v in (0, 2, 5)))
        self.assertTrue(any(limit(5)(f(v)) is not True for v in (-1, 6)))
        self.assertTrue(all(limit(1, 10, gt=2)(f(v)) is True for v in (9, 10)))
        self.assertTrue(all(limit(1, 10, gt=2)(f(v)) is not True for v in (1, 2, 11)))
        self.assertTrue(all(limit(1, 10, lt=3)(f(v)) is True for v in (1, 2)))
        self.assertTrue(all(limit(1, 10, lt=2)(f(v)) is not True for v in (3, 11)))

        # valid for checking str length
        self.assertTrue(all(limit(1, 10)(f("a"*v)) is True for v in (1, 2, 9, 10)))
        self.assertTrue(any(limit(1, 10)(f(v)) is not True for v in (-1, 0, 11)))

    def test_limited_field(self):
        t1 = Tag(1, validation=limit(1, 10))
        self.assertTrue(t1.update(2))
        self.assertEqual(2, t1.val)
        self.assertFalse(t1.update(11))
        self.assertEqual(2, t1.val)
        t2 = Tag(1, validation=limit(1, 10, transform=True))
        self.assertTrue(t2.update(2))
        self.assertEqual(2, t2.val)
        self.assertFalse(t2.update(11))
        self.assertEqual(10, t2.val)

    def test_assure_tag(self):
        t = assure_tag(int, Gt(1))
        for x in ("0", 0, 1, 2.5):
            self.assertFalse(t.update(x))
        for x in ("5", 5):
            self.assertTrue(t.update(x))

        t2 = assure_tag(Tag(annotation=float, validation=Gt(3)), Lt(100))
        for x in ("0", 0, 1, 2.5, 100.0):
            self.assertFalse(t2.update(x))
        for x in ("5", 5.0, 99.9):
            self.assertTrue(t2.update(x))

    def test_annotated_types(self):
        d: TagDict = dataclass_to_tagdict(AnnotatedTypes())[""]

        for i in ("19", 1000):
            self.assertTrue(d["age"].update(i))

        for i in (18, 18.0, "18.1", 19.5, False, "str"):
            self.assertFalse(d["age"].update(i))

        for i in (1, 2, 100):
            self.assertTrue(d["percent"].update(i))
        for i in (-1, 0, 101, 99.9):
            self.assertFalse(d["percent"].update(i))

        for i in (0.1, 1.0, "1", "2", "100", 99.9):
            self.assertTrue(d["percent_fl"].update(i), i)
        for i in (0.0, 1, 2):
            self.assertFalse(d["percent_fl"].update(i), i)

        for i in (0, 9, 10):
            self.assertTrue(d["my_list"].update([0]*i), i)

        for i in (11, 100):
            self.assertFalse(d["my_list"].update([0]*i), i)

    def test_annotated_types_combined(self):
        d: TagDict = dataclass_to_tagdict(AnnotatedTypesCombined())[""]

        for i in (-99, 0, 2, 40):
            self.assertTrue(d["combined1"].update(i), i)
            self.assertTrue(d["combined2"].update(i), i)
            self.assertTrue(d["combined3"].update(i), i)

        for i in (-1000, -100, 60, 90, 100):
            self.assertFalse(d["combined1"].update(i), i)
            self.assertFalse(d["combined2"].update(i), i)
            self.assertFalse(d["combined3"].update(i), i)

        # transforming funcion is before the annotated-types
        i = 49
        self.assertTrue(d["combined1"].update(i), i)
        self.assertTrue(d["combined2"].update(i), i)
        self.assertTrue(d["combined3"].update(i), i)
        self.assertFalse(d["combined4"].update(i), i)
