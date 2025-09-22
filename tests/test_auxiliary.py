from pathlib import Path
from typing import Optional, Union

from mininterface._lib.auxiliary import allows_none, matches_annotation, strip_none, subclass_matches_annotation
from mininterface.tag import Tag
from shared import TestAbstract


from types import NoneType


class TestAuxiliary(TestAbstract):
    def test_matches_annotation(self):
        annotation = Optional[list[int] | str | tuple[int, str]]
        self.assertTrue(matches_annotation(None, annotation))
        self.assertTrue(matches_annotation([1, 2], annotation))
        self.assertTrue(matches_annotation("hello", annotation))
        self.assertTrue(matches_annotation((42, "world"), annotation))
        self.assertFalse(matches_annotation(42, annotation))
        self.assertTrue(matches_annotation([(1, "a"), (2, "b")], list[tuple[int, str]]))
        self.assertFalse(matches_annotation([(1, "a", "c"), (2, "b")], list[tuple[int, str]]))
        self.assertFalse(matches_annotation([(1, 2)], list[tuple[int, str]]))

    def test_subclass_matches_annotation(self):
        annotation = Optional[list[int] | str | tuple[int, str]]
        self.assertTrue(subclass_matches_annotation(NoneType, annotation))
        self.assertTrue(subclass_matches_annotation(str, annotation))
        self.assertFalse(subclass_matches_annotation(int, annotation))

        # The subclass_matches_annotation is not almighty. Tag behaves better:
        self.assertTrue(Tag(annotation=annotation)._is_subclass(tuple[int, str]))
        # NOTE but this should work too
        # self.assertTrue(Tag(annotation=annotation)._is_subclass(list[int]))

    def test_allows_none(self):
        cases = [
            (int, False),
            (Optional[int], True),
            (int | None, True),
            (Union[int, None], True),
            (Union[int, str], False),
            (Path, False),
            (Optional[Path], True),
            (Path | None, True),
        ]

        for annotation, expected in cases:
            with self.subTest(annotation=annotation):
                self.assertEqual(allows_none(annotation), expected)

    def test_strip_none(self):
        cases = [
            ((str | None), str),
            ((str | bool | None), str | bool),
            (Optional[str | bool], str | bool),
            (Optional[tuple[int] | bool], tuple[int] | bool),
        ]
        for annotation, expected in cases:
            with self.subTest(annotation=annotation):
                self.assertEqual(strip_none(annotation), expected)
