"""The Yahweh Edition: the public-domain World Messianic Bible with God's Name written "Yahweh". Its license lets
anyone change the text if the result is not called "World Messianic Bible". These tests keep that promise and check
that only God's Name changed."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web"))

from bibleask import catalog  # noqa: E402
from bibleask.loaders import load_bible  # noqa: E402

FILE = os.path.join(ROOT, "bibles", "eng-yahweh-edition.usfx.xml")


class YahwehEditionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bible = load_bible(FILE)
        cls.text = {(v.book, v.chapter, v.verse): v.text for v in cls.bible.verses}

    def test_listed_under_its_own_name(self):
        e = [x for x in catalog.entries() if x["abbr"] == "YAHWEH"]
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["language"], "English")
        self.assertEqual(e[0]["verses"], len(self.bible.verses))
        self.assertEqual(e[0]["bytes"], os.path.getsize(FILE))
        self.assertEqual(catalog.url(e[0]["file"]), catalog.OWN + "eng-yahweh-edition.usfx.xml")
        self.assertNotIn("WMB", e[0]["title"])
        self.assertIn("not called the World Messianic Bible", e[0]["license"])
        self.assertIn("https://ebible.org/engwmb/", e[0]["license"])

    def test_never_called_the_world_messianic_bible(self):
        raw = open(FILE, encoding="utf-8").read()
        self.assertNotIn("World Messianic Bible (WMB)", raw)
        ids = re.findall(r'<id id="[A-Z0-9]+">([^\n<]*)', raw)
        self.assertEqual(len(ids), 66)
        # (the source file has a stray "1" in front of the Deuteronomy header; it is kept as received)
        self.assertTrue(all("Yahweh Edition, based on the World Messianic Bible" in i for i in ids))

    def test_whole_bible(self):
        self.assertEqual(len({v.book for v in self.bible.verses}), 66)
        self.assertEqual(self.text[("Genesis", 1, 1)][:40], "In the beginning, God created the heaven")
        self.assertIn("Yeshua", self.text[("Matthew", 1, 1)])

    def test_gods_name_is_yahweh(self):
        self.assertEqual(self.text[("Psalms", 23, 1)], "Yahweh is my shepherd; I shall lack nothing.")
        self.assertIn("in the day that Yahweh God made the earth", self.text[("Genesis", 2, 4)])
        self.assertIn("Yahweh, the God of your fathers", self.text[("Exodus", 3, 15)])
        self.assertIn("Lord Yahweh", self.text[("Genesis", 15, 2)])

    def test_no_capital_letter_name_left_except_the_two_that_are_not_gods_name(self):
        left = [k for k, t in self.text.items() if re.search(r"\b(LORD|GOD)\b", t)]
        self.assertEqual(sorted(left), [("Acts", 17, 23), ("Revelation", 19, 16)])
        self.assertIn("TO AN UNKNOWN GOD", self.text[("Acts", 17, 23)])
        self.assertIn("KING OF KINGS AND LORD OF LORDS", self.text[("Revelation", 19, 16)])

    def test_the_word_the_is_dropped_before_the_name(self):
        self.assertFalse([k for k, t in self.text.items() if re.search(r"\b[Tt]he Yahweh\b", t)])

    def test_awkward_places_say_lord_with_a_note_giving_the_hebrew(self):
        self.assertIn("you Lord are among this people; for you Lord are seen face to face", self.text[("Numbers", 14, 14)])
        self.assertIn("May the good Lord pardon everyone", self.text[("2 Chronicles", 30, 18)])
        raw = open(FILE, encoding="utf-8").read()
        notes = re.findall(r'<f caller="\*"><fr>([^<]*)</fr><ft>([^<]*)</ft></f>', raw)
        self.assertEqual([n[0].strip() for n in notes], ["14:14", "14:14", "30:18"])
        for _ref, text in notes:
            self.assertIn("יהוה (YHWH)", text)
            self.assertIn("H3068", text)

    def test_nothing_else_changed(self):
        # John 3:16 has no divine name, so it must be exactly the World Messianic Bible's wording
        self.assertEqual(self.text[("John", 3, 16)],
                         "For God so loved the world, that he gave his only born Son, that whoever believes in him "
                         "should not perish, but have eternal life.")
        self.assertGreater(sum(t.count("Yahweh") for t in self.text.values()), 6800)


if __name__ == "__main__":
    unittest.main()
