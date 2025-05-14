from mininterface import Mininterface, run
from mininterface._lib.form_dict import TagDict, dataclass_to_tagdict
from mininterface.tag import PathTag
from configs import AnnotatedClass, AnnotatedClass3, ConstrainedEnv, InheritedAnnotatedClass, MissingPositional
from shared import TestAbstract, runm


from pathlib import Path, PosixPath


class TestAnnotated(TestAbstract):
    # NOTE some of the entries are not well supported
    # NOTE The same should be for pydantic and attrs.

    def test_annotated(self):
        m = run(ConstrainedEnv)
        d: TagDict = dataclass_to_tagdict(m.env)[""]
        self.assertFalse(d["test"].update(""))
        self.assertFalse(d["test2"].update(""))
        self.assertTrue(d["test"].update(" "))
        self.assertTrue(d["test2"].update(" "))

    def test_class(self):
        with self.assertRaises(SystemExit):
            m = run(AnnotatedClass, interface=Mininterface)

        m = run(AnnotatedClass, args=["[]", "--files2", "[]"], interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertEqual(list[Path], d["files1"].annotation)
        self.assertEqual(list[Path], d["files2"].annotation)
        self.assertEqual(list[Path], d["files3"].annotation)
        # self.assertEqual(list[Path], d["files4"].annotation)  # does not work
        self.assertEqual(list[Path], d["files5"].annotation)
        # This does not work, however I do not know what should be the result
        # self.assertEqual(list[Path], d["files6"].annotation)
        # self.assertEqual(list[Path], d["files7"].annotation)
        # self.assertEqual(list[Path], d["files8"].annotation)

    def test_positional(self):
        # all arguments passed well, positional, positional with default and required flag
        m = runm(AnnotatedClass3, args=["1", "True", "False", "--foo2", "--foo3", "/tmp"])
        self.assertEqual(AnnotatedClass3(foo1=1, foo2=[], foo3=[PosixPath('/tmp')], foo4=[True, False]),
                         m.env)

        # positional but defaulted argument not mentioned
        self.assertEqual(AnnotatedClass3(foo1=1, foo2=[], foo3=[PosixPath('/tmp')], foo4=[]),
                         runm(AnnotatedClass3, args=["1", "--foo2", "--foo3", "/tmp"]).env)

        # required positional missing
        with self.assertRaises(SystemExit):
            runm(AnnotatedClass3, args=["--foo2", "--foo3", "/tmp"])

        # missing required flag
        with self.assertRaises(SystemExit):
            runm(AnnotatedClass3, args=["1", "--foo2"])

        # In the current implementation,
        # the validation is done not at dataclass built, but on the form call.
        # Hence, missing --foo3 will not raise an issue on run,
        # but later on the form call.
        # I'm not sure that this is the best behaviour and thus might be changed.
        m.form()
        m2 = runm(AnnotatedClass3, args=["1", "--foo2", "--foo3"])
        with self.assertRaises(SystemExit):
            m2.form()

    def test_inherited_class(self):
        # Without _parse_cli / yield_annotations on inherited members, it produced
        # UserWarning: Could not find field files6 in default instance namespace()
        with self.assertStderr(not_contains="Could not find field"), self.assertRaises(SystemExit):
            m = run(InheritedAnnotatedClass, interface=Mininterface)
        m = run(InheritedAnnotatedClass, args=["--files1", "/tmp"], interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertEqual(list[Path], d["files1"].annotation)
        # self.assertEqual(list[Path], d["files2"].annotation) does not work
        self.assertEqual(list[Path], d["files3"].annotation)
        self.assertEqual(list[Path], d["files4"].annotation)
        self.assertEqual(list[Path], d["files5"].annotation)
        # This does not work, however I do not know what should be the result
        # self.assertEqual(list[Path], d["files6"].annotation)
        # self.assertEqual(list[Path], d["files7"].annotation)
        # self.assertEqual(list[Path], d["files8"].annotation)

    def test_missing_positional(self):
        m = run(MissingPositional, interface=Mininterface)
        d = dataclass_to_tagdict(m.env)[""]
        self.assertReprEqual(
            {'files': PathTag(val=[], description='files ', annotation=list[Path], label='files')}, d)
