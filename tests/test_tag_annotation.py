from mininterface import Mininterface
from mininterface._lib.form_dict import dataclass_to_tagdict
from mininterface._lib.run import run
from mininterface.tag import Tag
from configs import ColorEnum, DynamicDescription, ParametrizedGeneric
from shared import TestAbstract


from pathlib import Path, PosixPath
from typing import Callable


class TestTagAnnotation(TestAbstract):
    """ Tests tag annotation. """
    # The class name could not be 'TestAnnotation', nor 'TestAnnotation2'. If so, another test on github failed with
    # StopIteration / During handling of the above exception, another exception occurred:
    # File "/opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/unittest/result.py", line 226, in _clean_tracebacks
    #     value.__traceback__ = tb
    # /opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/unittest/result.py", line 226
    #   File "<string>", line 4, in __setattr__
    # dataclasses.FrozenInstanceError: cannot assign to field '__traceback__'
    # On local machine, all the tests went fine.

    def test_type_guess(self):
        def _(type_, val):
            self.assertEqual(type_, Tag(val).annotation)

        _(int, 1)
        _(str, "1")
        _(list, [])
        _(list[PosixPath], [PosixPath("/tmp")])
        _(list, [PosixPath("/tmp"), 2])
        _(set[PosixPath], set((PosixPath("/tmp"),)))

    def test_type_discovery(self):
        def _(compared, annotation):
            self.assertListEqual(compared, Tag(annotation=annotation)._get_possible_types())

        _([], None)
        _([(None, str)], str)
        _([(None, str)], None | str)
        _([(None, str)], str | None)
        _([(list, str)], list[str])
        _([(list, str)], list[str] | None)
        _([(list, str)], None | list[str])
        _([(list, str), (tuple, [int])], None | list[str] | tuple[int])
        _([(list, int), (tuple, [str]), (None, str)], list[int] | tuple[str] | str | None)

        # I found no usecase for Callable, so currently, it returns None.
        _([(None, None)], Callable)
        _([(None, None)], Callable[[int], int])

    def test_subclass_check(self):
        def _(compared, annotation, true=True):
            getattr(self, "assertTrue" if true else "assertFalse")(Tag(annotation=annotation)._is_subclass(compared))

        _(int, int)
        _(list, list)
        _(Path, Path)
        _(Path, list[Path])
        _(PosixPath, list[Path])
        _(Path, list[PosixPath], False)
        _(PosixPath, list[PosixPath])
        _((Path, PosixPath), list[Path])
        _(tuple[int, int], tuple[int, int])
        _(Path, tuple[int, int], true=False)

    def test_generic(self):
        t = Tag("", annotation=list)
        t.update("")
        self.assertEqual("", t.val)
        t.update("[1,2,3]")
        self.assertEqual([1, 2, 3], t.val)
        t.update("['1',2,3]")
        self.assertEqual(["1", 2, 3], t.val)

    def test_parametrized_generic(self):
        t = Tag("", annotation=list[str])
        self.assertTrue(t.update(""))  # an empty input gets converted to an empty list
        t.update("[1,2,3]")
        self.assertEqual(["1", "2", "3"], t.val)
        t.update("[1,'2',3]")
        self.assertEqual(["1", "2", "3"], t.val)

    def test_parametrized_generic_nested(self):
        # ellipsis support
        t = Tag("", annotation=list[tuple[str, ...]])
        self.assertFalse(t.update("[1,2,3]"))
        self.assertTrue(t.update("[(1,),(2,),(3,)]"))
        self.assertEqual([("1",), ("2",), ("3",)], t.val)
        self.assertTrue(t.update("[(1,),(2,'b')]"))
        self.assertEqual([("1",), ("2","b")], t.val)

        t = Tag("", annotation=list[tuple[str]])
        self.assertFalse(t.update("[1,2]"))
        self.assertTrue(t.update("[(1,),(2,)]"))
        self.assertEqual([("1",), ("2",)], t.val)
        # NOTE this passes now, too tolerant
        # self.assertFalse(t.update("[(1,),(2,'b')]"))

        t = Tag("", annotation=list[tuple[str, int]])
        self.assertFalse(t.update("[1,2]"))
        self.assertFalse(t.update("[(1,),(2,)]"))
        self.assertTrue(t.update("[(1,5),(2,5)]"))
        self.assertEqual([("1",5), ("2",5)], t.val)

        t = Tag("", annotation=list[tuple])
        self.assertFalse(t.update("[1,3]"))
        self.assertTrue(t.update("[(1,'a'),(3,'b')]"))
        # NOTE not sure whether default literal_ast conversion to int(1), int(3) is required
        self.assertEqual([(1,"a"), (3,"b")], t.val)

    def test_single_path_union(self):
        t = Tag("", annotation=Path | None)
        t.update("/tmp/")
        self.assertEqual(Path("/tmp"), t.val)
        t.update("")
        self.assertIsNone(t.val)

    def test_path(self):
        t = Tag("", annotation=list[Path])
        t.update("['/tmp/','/usr']")
        self.assertEqual([Path("/tmp"), Path("/usr")], t.val)
        self.assertFalse(t.update("[1,2,3]"))
        self.assertFalse(t.update("[/home, /usr]"))  # missing parenthesis

    def test_path_union(self):
        t = Tag("", annotation=list[Path] | None)
        t.update("['/tmp/','/usr']")
        self.assertEqual([Path("/tmp"), Path("/usr")], t.val)
        self.assertFalse(t.update("[1,2,3]"))
        self.assertFalse(t.update("[/home, /usr]"))  # missing parenthesis
        self.assertTrue(t.update("[]"))
        self.assertEqual([], t.val)
        self.assertTrue(t.update(""))
        self.assertIsNone(t.val)

    def test_path_cli(self):
        with self.assertRaises(SystemExit):
            m = run(ParametrizedGeneric, interface=Mininterface, ask_for_missing=False)

        with self.assertRaises(SystemExit):
            m = run(ParametrizedGeneric, interface=Mininterface)
        env = ParametrizedGeneric([])
        f = dataclass_to_tagdict(env)[""]["paths"]
        self.assertEqual([], f.val)
        self.assertTrue(f.update("[]"))

        self.sys("--paths", "/usr", "/tmp")
        m = run(ParametrizedGeneric, interface=Mininterface)
        f = dataclass_to_tagdict(m.env)[""]["paths"]
        self.assertEqual([Path("/usr"), Path("/tmp")], f.val)
        self.assertEqual(['/usr', '/tmp'], f._get_ui_val())
        self.assertTrue(f.update("['/var']"))
        self.assertEqual([Path("/var")], f.val)
        self.assertEqual(['/var'], f._get_ui_val())

    def test_select_method(self):
        m = run(interface=Mininterface)
        with self.assertRaises(SystemExit):
            m.select((1, 2, 3))
        self.assertEqual(2, m.select((1, 2, 3), default=2))
        self.assertEqual(2, m.select((1, 2, 3), default=2))
        self.assertEqual(2, m.select({"one": 1, "two": 2}, default=2))
        self.assertEqual(2, m.select([Tag(1, label="one"), Tag(2, label="two")], default=2))

        # Enum type
        self.assertEqual(ColorEnum.GREEN, m.select(ColorEnum, default=ColorEnum.GREEN))

        # list of enums
        self.assertEqual(ColorEnum.GREEN, m.select([ColorEnum.BLUE, ColorEnum.GREEN], default=ColorEnum.GREEN))
        self.assertEqual(ColorEnum.BLUE, m.select([ColorEnum.BLUE]))
        with self.assertRaises(SystemExit):
            self.assertEqual(m.select([ColorEnum.RED, ColorEnum.GREEN]))

        # Enum instance signify the default
        self.assertEqual(ColorEnum.RED, m.select(ColorEnum.RED))

    def test_dynamic_description(self):
        """ This is an undocumented feature.
        When you need a dynamic text, you may use tyro's arg to set it.
        """
        m = run(DynamicDescription, interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        # tyro seems to add a space after the description in such case, I don't know why
        self.assertEqual("My dynamic str", d["foo"].description)
