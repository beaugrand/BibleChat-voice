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


class CrossReferences(unittest.TestCase):
    def test_daniel_7_13_links_to_revelation_1_7(self):
        from bibleask.xref import XREFS
        refs = [x["ref"] for x in XREFS.for_verse("Daniel", 7, 13, "Revelation")]
        self.assertEqual(refs[0], "Revelation 1:7")

    def test_between_two_books(self):
        from bibleask.xref import XREFS
        links = XREFS.between("Daniel", "Revelation")
        self.assertGreater(len(links), 200)
        self.assertTrue(all(x["from"].startswith("Daniel") and x["to"].startswith("Revelation") for x in links))
        self.assertIn(("Revelation 2:10–11"), {x["to"] for x in links if x["from"] == "Daniel 3:18"})

    def test_study_panel_has_cross_references(self):
        v = study.verse(None, "", "John", 3, 16)
        self.assertTrue(any(x["ref"] == "Romans 5:8" for x in v["xrefs"]))
        self.assertTrue(all(x["text"] for x in v["xrefs"]))


class BookNames(unittest.TestCase):
    def test_isaiah_is_not_first_saiah(self):
        from bibleask.search import BookIndex
        ix = BookIndex(["1 Samuel", "Isaiah", "2 Kings", "1 John"])
        self.assertEqual(ix.resolve("Isaiah"), "Isaiah")
        self.assertEqual(ix.resolve("Isa"), "Isaiah")
        self.assertEqual(ix.resolve("I Samuel"), "1 Samuel")
        self.assertEqual(ix.resolve("ii kings"), "2 Kings")
        self.assertEqual(ix.resolve("1john"), "1 John")


class CrossReferenceQuestions(unittest.TestCase):
    def test_natural_wording_finds_both_books(self):
        from bibleask.chat import _books_named
        from bibleask.search import BookIndex

        class Ix:
            books = BookIndex(["Genesis", "Isaiah", "Daniel", "Matthew", "John", "1 John", "Revelation"])
        for q, want in [("give me all crossreferences between daniel and revelation", ["Daniel", "Revelation"]),
                        ("what are the cross references from daniel to the book of revelation", ["Daniel", "Revelation"]),
                        ("show cross references from Isaiah to Matthew", ["Isaiah", "Matthew"]),
                        ("cross references 1 john and john", ["1 John", "John"])]:
            self.assertEqual(_books_named(q, Ix), want, q)


class NotesAndDictionary(unittest.TestCase):
    def test_scofield_on_revelation_1_20(self):
        notes = study.chapter_notes("Revelation", 1)
        self.assertIn("20", notes)
        self.assertTrue(notes["20"].startswith("**angels**"))

    def test_matthew_henry_covers_the_passage(self):
        h = study.verse(None, "", "Daniel", 7, 13)["henry"]
        self.assertEqual(h["from_verse"], 9)
        self.assertIn("Verses 9-14", h["text"])

    def test_easton_names_and_entries(self):
        names = set(study.EASTON.names())
        self.assertIn("babylon", names)
        self.assertIn("patmos", names)
        self.assertNotIn("god", names)          # too common to mark
        self.assertIn("Dan. 10:13", study.EASTON.entry("Michael")["text"])
        self.assertIsNone(study.EASTON.entry("nothing-like-this"))
