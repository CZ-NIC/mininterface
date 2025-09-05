from mininterface import run
from mininterface._lib.form_dict import dataclass_to_tagdict
from mininterface.tag import SelectTag, Tag
from mininterface.tag.tag_factory import tag_assure_type
from configs import ColorEnum, ConstrainedEnv
from shared import TestAbstract


from contextlib import redirect_stderr
from io import StringIO


class TestSelectTag(TestAbstract):

    def test_options_param(self):
        t = SelectTag("one", options=["one", "two"])
        t.update("two")
        self.assertEqual(t.val, "two")
        t.update("three")
        self.assertEqual(t.val, "two")

        m = run(ConstrainedEnv)
        d = dataclass_to_tagdict(m.env)
        self.assertFalse(d[""]["options"].update(""))
        self.assertTrue(d[""]["options"].update("two"))

        # Literal annotations
        self.assertEqual(d[""]["liter1"].val, "one")
        self.assertFalse(d[""]["liter1"].update("two"))
        self.assertEqual(d[""]["liter2"].val, "two")
        self.assertTrue(d[""]["liter2"].update("one"))

        # dict is the input
        t = SelectTag(1, options={"one": 1, "two": 2})
        self.assertFalse(t.update("two"))
        self.assertEqual(1, t.val)
        self.assertTrue(t.update(2))
        self.assertEqual(2, t.val)
        self.assertFalse(t.update(3))
        self.assertEqual(2, t.val)
        self.assertTrue(t.update(1))
        self.assertEqual(1, t.val)
        self.assertFalse(t.multiple)

        # list of Tags are the input
        t1 = Tag(1, label="one")
        t2 = Tag(2, label="two")
        t = SelectTag(1, options=[t1, t2])
        self.assertTrue(t.update(2))
        self.assertEqual(t2.val, t.val)
        self.assertFalse(t.update(3))
        self.assertEqual(t2.val, t.val)
        self.assertTrue(t.update(1))
        self.assertEqual(t1.val, t.val)
        self.assertFalse(t.multiple)

    def test_select_enum(self):
        # Enum type supported
        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum)
        t1.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE, t1.val)

        # list of enums supported
        t2 = SelectTag(ColorEnum.GREEN, options=[ColorEnum.BLUE, ColorEnum.GREEN])
        self.assertEqual({str(v.value): v for v in [ColorEnum.BLUE, ColorEnum.GREEN]}, t2._build_options())
        t2.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE, t2.val)

        # Enum type supported even without explicit definition
        t3 = SelectTag(ColorEnum.GREEN)
        self.assertEqual(ColorEnum.GREEN.value, t3._get_ui_val())
        self.assertEqual({str(v.value): v for v in list(ColorEnum)}, t3._build_options())
        t3.update(ColorEnum.BLUE)
        self.assertEqual(ColorEnum.BLUE.value, t3._get_ui_val())
        self.assertEqual(ColorEnum.BLUE, t3.val)

        # We pass the EnumType which does not include the default options.
        t4 = Tag(ColorEnum)
        # But the Tag itself does not work with the Enum, so it does not reset the value.
        self.assertIsNotNone(t4.val)
        # Raising a form will automatically invoke the SelectTag instead of the Tag.
        t5 = tag_assure_type(t4)
        # The SelectTag resets the value.
        self.assertIsNone(t5.val)

        [self.assertFalse(t.multiple) for t in (t1, t2, t3, t5)]

    def test_tips(self):
        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum)
        self.assertListEqual([
            ('1', ColorEnum.RED, False, ('1', )),
            ('2', ColorEnum.GREEN, False, ('2', )),
            ('3', ColorEnum.BLUE, False, ('3', )),
        ], t1._get_options())

        t1 = SelectTag(ColorEnum.GREEN, options=ColorEnum, tips=[ColorEnum.BLUE])
        self.assertListEqual([
            ('3', ColorEnum.BLUE, True, ('3', )),
            ('1', ColorEnum.RED, False, ('1', )),
            ('2', ColorEnum.GREEN, False, ('2', )),
        ], t1._get_options())

    def test_tupled_label(self):
        t1 = SelectTag(options={("one", "half"): 11, ("second", "half"): 22, ("third", "half"): 33})
        self.assertListEqual([
            ('one    - half', 11, False, ('one', 'half')),
            ('second - half', 22, False, ('second', 'half')),
            ('third  - half', 33, False, ('third', 'half')),
        ], t1._get_options())

    def test_stripped_tupled_label(self):
        t1 = SelectTag(options={("one", "half "): 11, (" second ", "half"): 22, ("third ", "half "): 33})
        self.assertListEqual([
            ('one    - half', 11, False, ('one', 'half')),
            ('second - half', 22, False, ('second', 'half')),
            ('third  - half', 33, False, ('third', 'half')),
        ], t1._get_options())

    def test_stripped_out_tupled_label(self):
        t1 = SelectTag(options={("one", ""): 11, ("second", ""): 22})
        self.assertListEqual([
            ('one', 11, False, ('one', )),
            ('second', 22, False, ('second', )),
        ], t1._get_options())

    def test_label_resilience(self):
        """ Convert the labels to str. """
        # In this test, we are using a type as label.
        t1 = SelectTag(options={("one", ColorEnum): 11, ("second", "half"): 22, ("third", "half", "another"): 33})
        self.assertListEqual([("one - <enum 'ColorEnum'>", 11, False, ('one', "<enum 'ColorEnum'>")),
                              ('second - half', 22, False, ('second', 'half')),
                              ('third - half - another', 33, False, ('third', 'half', 'another'))],
                             t1._get_options())

    def test_multiple(self):
        options = {("one", "half"): 11, ("second", "half"): 22, ("third", "half"): 33}
        t1 = SelectTag(options=options)
        t2 = SelectTag(11, options=options)
        t3 = SelectTag([11], options=options)
        t4 = SelectTag([11, 33], options=options)
        t5 = SelectTag(options=options, multiple=True)

        [self.assertTrue(t.multiple) for t in (t3, t4, t5)]
        [self.assertFalse(t.multiple) for t in (t1, t2)]

        with self.assertRaises(TypeError), redirect_stderr(StringIO()):
            self.assertFalse(t3.update(22))

        self.assertListEqual([11], t3.val)
        self.assertTrue(t3.update([22]))
        self.assertListEqual([22], t3.val)

        self.assertListEqual([11, 33], t4.val)
        self.assertTrue(t4.update([22, 11]))
        self.assertListEqual([22, 11], t4.val)

    def test_build_options(self):
        t = SelectTag()
        self.assertDictEqual({}, t._build_options())

        t.options = {"one": 1}
        self.assertDictEqual({"one": 1}, t._build_options())

        t.options = {"one": Tag(1, label="one")}
        self.assertDictEqual({"one": 1}, t._build_options())

        t.options = [Tag(1, label="one"), Tag(2, label="two")]
        self.assertDictEqual({"one": 1, "two": 2}, t._build_options())

        t.options = {("one", "col2"): Tag(1, label="one"), ("three", "column3"): 3}
        self.assertDictEqual({("one", "col2"): 1, ("three", "column3"): 3}, t._build_options())

        t.options = [Tag(1, label='A')]
        self.assertDictEqual({"A": 1}, t._build_options())
