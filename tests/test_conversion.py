from mininterface import Mininterface, run
from mininterface._lib.auxiliary import flatten
from mininterface._lib.form_dict import TagDict, dataclass_to_tagdict, dict_to_tagdict, formdict_resolve
from mininterface.tag import Tag
from configs import ConstrainedEnv, OptionalFlagEnv
from shared import TestAbstract


from datetime import datetime
from pathlib import Path


class TestConversion(TestAbstract):

    def test_tagdict_resolve(self):
        self.assertEqual({"one": 1}, formdict_resolve({"one": 1}))
        self.assertEqual({"one": 1}, formdict_resolve({"one": Tag(1)}))
        self.assertEqual({"one": 1}, formdict_resolve({"one": Tag(Tag(1))}))
        self.assertEqual({"": {"one": 1}}, formdict_resolve({"": {"one": Tag(Tag(1))}}))
        self.assertEqual({"one": 1}, formdict_resolve({"": {"one": Tag(Tag(1))}}, extract_main=True))

    def test_normalize_types(self):
        """ Conversion str("") to None and back.
        When using GUI interface, we input an empty string and that should mean None
        for annotation `int | None`.
        """
        origin = {'': {'test': Tag(False, 'Testing flag ', annotation=None),
                       'numb': Tag(4, 'A number', annotation=None),
                       'severity': Tag('', 'integer or none ', annotation=int | None),
                       'msg': Tag('', 'string or none', annotation=str | None)}}
        data = {'': {'test': False, 'numb': 4, 'severity': 'fd', 'msg': ''}}

        self.assertFalse(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': ''}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '', 'msg': ''}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'': {'test': False, 'numb': 4, 'severity': '1', 'msg': 'Text'}}
        self.assertTrue(Tag._submit(origin, data))

        # check value is kept if revision needed
        self.assertEqual(False, origin[""]["test"].val)
        data = {'': {'test': True, 'numb': 100, 'severity': '1', 'msg': 1}}  # ui put a wrong 'msg' type
        self.assertFalse(Tag._submit(origin, data))
        self.assertEqual(True, origin[""]["test"].val)
        self.assertEqual(100, origin[""]["numb"].val)

        # Check nested TagDict
        origin = {'test': Tag(False, 'Testing flag ', annotation=None),
                  'severity': Tag('', 'integer or none ', annotation=int | None),
                  'nested': {'test2': Tag(4, '')}}
        data = {'test': True, 'severity': "", 'nested': {'test2': 8}}
        self.assertTrue(Tag._submit(origin, data))
        data = {'test': True, 'severity': "str", 'nested': {'test2': 8}}
        self.assertFalse(Tag._submit(origin, data))

    def test_non_scalar(self):
        tag = Tag(Path("/tmp"), '')
        origin = {'': {'path': tag}}
        data = {'': {'path': "/usr"}}  # the input '/usr' is a str
        self.assertTrue(Tag._submit(origin, data))
        self.assertEqual(Path("/usr"), tag.val)  # the output is still a Path

    def test_datetime(self):
        new_date = "2020-01-01 17:35"
        tag2 = Tag(datetime.fromisoformat("2024-09-10 17:35:39.922044"))
        # The user might put datetime into Tag but we need to use DatetimeTag.
        # Calling a form will convert it automatically,
        # while the original Tag is being updated.
        d = dict_to_tagdict({"test": tag2})
        tag = d["test"]
        self.assertFalse(tag.update("fail"))
        self.assertTrue(tag.update(new_date))
        self.assertEqual(datetime.fromisoformat(new_date), tag.val)
        self.assertEqual(datetime.fromisoformat(new_date), tag2.val)

    def test_validation(self):
        def validate(tag: Tag):
            val = tag.val
            if 10 < val < 20:
                return "Number must be between 0 ... 10 or 20 ... 100", 20
            if val < 0:
                return False, 30
            if val > 100:
                return "Too high"
            return True

        tag = Tag(100, 'Testing flag', validation=validate)
        origin = {'': {'number': tag}}
        # validation passes
        self.assertTrue(Tag._submit(origin, {'': {'number': 100}}))
        self.assertIsNone(tag._error_text)
        # validation fail, value set by validion
        self.assertFalse(Tag._submit(origin, {'': {'number': 15}}))
        self.assertEqual("Number must be between 0 ... 10 or 20 ... 100", tag._error_text)
        self.assertEqual(20, tag.val)  # value set by validation
        # validation passes again, error text restored
        self.assertTrue(Tag._submit(origin, {'': {'number': 5}}))
        self.assertIsNone(tag._error_text)
        # validation fails, default error text
        self.assertFalse(Tag._submit(origin, {'': {'number': -5}}))
        self.assertEqual("Validation fail", tag._error_text)  # default error text
        self.assertEqual(30, tag.val)
        # validation fails, value not set by validation
        self.assertFalse(Tag._submit(origin, {'': {'number': 101}}))
        self.assertEqual("Too high", tag._error_text)
        self.assertEqual(30, tag.val)

    def test_env_instance_dict_conversion(self):
        m = run(OptionalFlagEnv, interface=Mininterface, prog="My application")
        env1: OptionalFlagEnv = m.env

        self.assertIsNone(env1.severity)

        fd = dataclass_to_tagdict(env1)
        ui = formdict_resolve(fd)
        self.assertEqual({'': {'severity': None, 'msg': None, 'msg2': 'Default text'},
                          'further': {'deep': {'flag': False}, 'numb': 0}}, ui)
        self.assertIsNone(env1.severity)

        # do the same as if the tkinter_form was just submitted without any changes
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

        # changes in the UI should not directly affect the original
        ui[""]["msg2"] = "Another"
        ui[""]["severity"] = 5
        ui["further"]["deep"]["flag"] = True
        self.assertEqual("Default text", env1.msg2)

        # on UI submit, the original is affected
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertEqual("Another", env1.msg2)
        self.assertEqual(5, env1.severity)
        self.assertTrue(env1.further.deep.flag)

        # Another UI changes, makes None from an int
        ui[""]["severity"] = ""  # UI is not able to write None, it does an empty string instead
        Tag._submit_values(zip(flatten(fd), flatten(ui)))
        self.assertIsNone(env1.severity)

    def test_tag_src_update(self):
        m = run(ConstrainedEnv, interface=Mininterface)
        d: TagDict = dataclass_to_tagdict(m.env)[""]

        # tagdict uses the correct reference to the original object
        # sharing a static annotation Tag is not desired:
        # self.assertIs(ConstrainedEnv.__annotations__.get("test").__metadata__[0], d["test"])

        # name is correctly determined from the dataclass attribute name
        self.assertEqual("test2", d["test2"].label)
        # but the tag in the annotation stays intact
        self.assertIsNone(ConstrainedEnv.__annotations__.get("test2").__metadata__[0].label)
        # name is correctly fetched from the dataclass annotation
        self.assertEqual("Better name", d["test"].label)

        # a change via set_val propagates
        self.assertEqual("hello", d["test"].val)
        self.assertEqual("hello", m.env.test)
        d["test"]._set_val("foo")
        self.assertEqual("foo", d["test"].val)
        self.assertEqual("foo", m.env.test)

        # direct val change does not propagate
        d["test"].val = "bar"
        self.assertEqual("bar", d["test"].val)
        self.assertEqual("foo", m.env.test)

        # a change via update propagates
        d["test"].update("moo")
        self.assertEqual("moo", d["test"].val)
        self.assertEqual("moo", m.env.test)

    def test_nested_tag(self):
        t0 = Tag(5)
        t1 = Tag(t0, label="Used name")
        t2 = Tag(t1, label="Another name")
        t3 = Tag(t1, label="Unused name")
        t4 = Tag()._fetch_from(t2)
        t5 = Tag(label="My name")._fetch_from(t2)

        self.assertEqual("Used name", t1.label)
        self.assertEqual("Another name", t2.label)
        self.assertEqual("Another name", t4.label)
        self.assertEqual("My name", t5.label)

        self.assertEqual(5, t1.val)
        self.assertEqual(5, t2.val)
        self.assertEqual(5, t3.val)
        self.assertEqual(5, t4.val)
        self.assertEqual(5, t5.val)

        t5._set_val(8)
        self.assertEqual(8, t0.val)
        self.assertEqual(8, t1.val)
        self.assertEqual(8, t2.val)
        self.assertEqual(5, t3.val)
        self.assertEqual(5, t4.val)
        self.assertEqual(8, t5.val)  # from t2, we inherited the hook to t1

        # update triggers the value propagation
        inner = Tag(2)
        outer = Tag(Tag(Tag(inner)))
        outer.update(3)
        self.assertEqual(3, inner.val)

    def test_fetch_from(self):
        t0 = Tag(5)
        t1 = Tag(t0, label="Used name")
        t2 = Tag(t1, label="Another name")
        t5 = Tag(label="My name")._fetch_from(t2, include_ref=True)

        t5._set_val(8)

        self.assertEqual(8, t0.val)
        self.assertEqual(8, t1.val)
        self.assertEqual(5, t2.val)  # the ref was fetches instead of the t2 object, hence it is not updated
        self.assertEqual(8, t5.val)

    def test_label(self):
        """ Dict labels do not have to be str,
        but Tag.labels have to. (Ex. TuiInterface would fail.) """
        self.assertReprEqual({1: Tag("a", label='1'),
                              45: Tag("b", label='45')},
                             dict_to_tagdict({1: "a", 45: "b"}))
