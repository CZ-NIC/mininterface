from mininterface._lib.form_dict import dataclass_to_tagdict, dict_to_tagdict
from mininterface.tag import PathTag, Tag
from configs import PathTagClass
from shared import TestAbstract, runm


from pathlib import Path


class TestInheritedTag(TestAbstract):
    def test_inherited_path(self):
        PathType = type(Path(""))  # PosixPath on Linux
        m = runm()
        d = dict_to_tagdict({
            "1": Path("/tmp"),
            "2": Tag("", annotation=Path),
            "3": PathTag([Path("/tmp")], multiple=True),
            "4": PathTag([Path("/tmp")]),
            "5": PathTag(Path("/tmp")),
            "6": PathTag(["/tmp"]),
            "7": PathTag([]),
            # NOTE these should work
            # "7": Tag(Path("/tmp")),
            # "8": Tag([Path("/tmp")]),
        }, m)

        # every item became PathTag
        [self.assertEqual(type(v), PathTag) for v in d.values()]
        # val stayed the same
        self.assertEqual(d["1"].val, Path('/tmp'))
        # correct annotation
        self.assertEqual(d["1"].annotation, PathType)
        self.assertEqual(d["2"].annotation, Path)
        self.assertEqual(d["3"].annotation, list[Path])
        self.assertEqual(d["4"].annotation, list[PathType])
        self.assertEqual(d["5"].annotation, PathType)
        self.assertEqual(d["6"].annotation, list[Path])
        self.assertEqual(d["7"].annotation, list[Path])
        # PathTag specific attribute
        [self.assertTrue(v.multiple) for k, v in d.items() if k in ("3", "4", "6", "7")]
        [self.assertFalse(v.multiple) for k, v in d.items() if k in ("1", "2", "5")]

    def test_path_class(self):
        m = runm(PathTagClass, ["/tmp"])  # , "--files2", "/usr"])
        d: dict[str, PathTag | Tag] = dataclass_to_tagdict(m.env)[""]

        [self.assertEqual(PathTag, type(v)) for v in d.values()]
        self.assertEqual(d["files"].label, "files")
        self.assertTrue(d["files"].multiple)

        self.assertEqual(d["files2"].label, "Custom name")
        self.assertTrue(d["files2"].multiple)

        # self.assertEqual(d["files3"].label, "Custom name")
        # self.assertTrue(d["files3"].multiple)
