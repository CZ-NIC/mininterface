from mininterface._lib.form_dict import TagDict, dataclass_to_tagdict, dict_to_tagdict
from mininterface.tag import DatetimeTag
from configs import DatetimeTagClass
from shared import TestAbstract, runm


from datetime import date


class TestTypes(TestAbstract):
    def test_datetime_tag(self):
        m = runm(DatetimeTagClass)
        d: TagDict = dataclass_to_tagdict(m.env)[""]
        d["extern"] = dict_to_tagdict({"extern": date.fromisoformat("2024-09-10")})["extern"]

        for key, expected_date, expected_time in [("p1", True, True), ("p2", False, True), ("p3", True, False),
                                                  ("pAnnot", True, False),
                                                  ("extern", True, False)]:
            tag: DatetimeTag = d[key]
            self.assertIsInstance(tag, DatetimeTag)
            self.assertEqual(expected_date, tag.date)
            self.assertEqual(expected_time, tag.time)
