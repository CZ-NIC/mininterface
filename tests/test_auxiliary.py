from typing import Optional
from mininterface._lib.auxiliary import matches_annotation, subclass_matches_annotation
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
