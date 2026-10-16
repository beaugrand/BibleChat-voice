"""Strong's numbers and Nave's topics for one verse (Read mode's study panel), and Strong's in chat."""
import unittest

from bibleask import study
from bibleask.strongs import STRONGS, normalize
from bibleask.topics import TOPICS


class StrongsData(unittest.TestCase):
    def test_numbers_are_normalized(self):
        self.assertEqual(normalize("g0025"), "G25")
        self.assertEqual(normalize("Strong's H430"), "H430")
        self.assertIsNone(normalize("love"))
        self.assertIsNone(normalize("G0"))

    def test_john_3_16_words(self):
        words = STRONGS.verse("John", 3, 16)
        self.assertIn(["loved", "G25"], words)
        self.assertTrue(STRONGS.kjv_text("John", 3, 16).startswith("For God so loved the world"))

    def test_genesis_1_1_hebrew(self):
        self.assertIn(["God", "H430"], STRONGS.verse("Genesis", 1, 1))

    def test_dictionary_entry_and_concordance(self):
        e = STRONGS.entry("G26")
        self.assertEqual(e["word"], "ἀγάπη")
        self.assertIn("love", e["meaning"])
        self.assertGreater(e["count"], 100)
        refs = [r for r, _w in STRONGS.verses_with("G26")]
        self.assertIn(("1 Corinthians", 13, 4), refs)

    def test_unknown_number(self):
        self.assertIsNone(STRONGS.entry("G9999"))


class StudyPanel(unittest.TestCase):
    def test_verse_has_words_and_topics(self):
        v = study.verse(None, "", "Jude", 1, 6)
        self.assertTrue(v["words"])
        self.assertTrue(any("Demons" in t["title"] for t in v["topics"]))

    def test_topic_lists_its_verses(self):
        tid = next(t["id"] for t in TOPICS.for_verse("Jude", 1, 6) if t["title"] == "Demons — Punishment of")
        refs = [x["ref"] for x in study.topic(None, "", tid)["verses"]]
        self.assertIn("2 Peter 2:4", refs)

    def test_strongs_falls_back_to_kjv_text(self):
        s = study.strongs(None, "", "G25")
        self.assertEqual(s["number"], "G25")
        self.assertTrue(all(v["text"] for v in s["verses"]))

    def test_find_topics_by_name(self):
        self.assertTrue(any(t["title"].startswith("Prayer") for t in study.find_topics("prayer")))


if __name__ == "__main__":
    unittest.main()
