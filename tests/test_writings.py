"""More Bibles and writings: the original-language line, the Septuagint's own verse numbers, the Book of Jasher,
and the list "Quoted or named in Scripture". A line or a note must never stand under the wrong verse."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)

from bibleask import catalog, original, versemap, studyfiles  # noqa: E402


class OriginalLineTest(unittest.TestCase):
    # well-known places where the Hebrew Bible numbers verses differently from the King James
    MOVED = {"Malachi 4:1": "3:19", "Malachi 4:6": "3:24", "Joel 2:32": "3:5", "Joel 3:1": "4:1", "Genesis 32:1": "32:2",
             "Isaiah 9:2": "9:1", "Daniel 4:1": "3:31", "Jonah 2:1": "2:2", "Exodus 22:2": "22:1", "Deuteronomy 29:2": "29:1",
             "Job 41:1": "40:25", "Zechariah 1:18": "2:1", "Micah 5:2": "5:1", "1 Kings 4:21": "5:1", "Daniel 6:1": "6:2",
             "Nehemiah 4:1": "3:33", "Psalms 3:2": "3:3", "Psalms 18:50": "18:51", "Psalms 51:19": "51:21",
             "Numbers 16:37": "17:2", "Ezekiel 21:1": "21:6", "Numbers 17:1": "17:16", "1 Chronicles 6:1": "5:27"}

    def test_renumbered_verses_get_the_right_hebrew_line_or_none(self):
        for ref, heb in self.MOVED.items():
            book, cv = ref.rsplit(" ", 1); c, v = map(int, cv.split(":"))
            got = original.line(book, c, v)
            if got:   # left out is allowed (no line), a wrong line is not
                self.assertEqual(got["number"], heb, ref)
                self.assertEqual(got["language"], "Hebrew")

    def test_same_numbers_and_greek(self):
        for book, c, v in [("Genesis", 1, 1), ("Psalms", 23, 1), ("Isaiah", 40, 22), ("Exodus", 3, 14)]:
            got = original.line(book, c, v)
            self.assertTrue(got and got["number"] == f"{c}:{v}" and got["language"] == "Hebrew", (book, c, v))
        import re; self.assertIn("אור", re.sub(r"[\u0591-\u05C7]", "", original.line("Genesis", 1, 3)["text"]))
        g = original.line("John", 1, 1)
        self.assertEqual(g["language"], "Greek"); self.assertIn("λόγος", g["text"])
        self.assertEqual(original.data()["moved"]["tr"], {})          # the Greek NT numbers verses like the KJV
        self.assertEqual(studyfiles.get("orig/38.json")["4:1"][1], "3:19")


class SeptuagintNumbersTest(unittest.TestCase):
    def test_psalms_and_the_rest(self):
        L, B = "eng-lxx2012", "eng-Brenton"
        self.assertEqual(versemap.to_kjv(L, "Psalms", 22, 1), (23, 1))       # "The Lord tends me as a shepherd"
        self.assertEqual(versemap.to_kjv(L, "Psalms", 50, 1), (51, 1))
        self.assertEqual(versemap.from_kjv(L, "Psalms", 23, 1), (22, 1))
        self.assertEqual(versemap.to_kjv(B, "Jeremiah", 32, 15), (25, 15))  # Jeremiah's chapters in another order
        self.assertEqual(versemap.to_kjv(B, "Malachi", 3, 22), (4, 5))
        self.assertEqual(versemap.to_kjv(L, "Genesis", 1, 1), (1, 1))
        self.assertEqual(versemap.to_kjv(None, "Psalms", 22, 1), (22, 1))   # every other Bible keeps its numbers
        self.assertEqual(versemap.key_for("LXX2012 - Septuagint in modern English (LXX2012)"), L)
        self.assertIsNone(versemap.key_for("KJV - King James Version"))

    def test_study_uses_the_king_james_verse_in_its_place(self):
        from bibleask import study

        class Lib:
            class B:
                name = "LXX2012 - Septuagint in modern English (LXX2012)"
            def get(self, bid):
                return self.B(), None
            def verse_text(self, bid, book, c, v):
                return f"[{book} {c}:{v}]"
        r = study.verse(Lib(), "lxx", "Psalms", 22, 1)
        self.assertEqual(r["kjv_ref"], "Psalms 23:1")
        self.assertTrue(any(isinstance(w, list) and w[1].startswith("H7462") for w in r["words"]))   # "shepherd"
        x = r["xrefs"][0]
        back = versemap.from_kjv("eng-lxx2012", x["book"], x["chapter"], x["verse"])
        if back:
            self.assertTrue(x["text"].startswith(f"[{x['book']} {back[0]}:{back[1]}]"), x)


class WritingsCatalogTest(unittest.TestCase):
    def test_new_entries_with_license_and_honest_labels(self):
        e = {x["abbr"]: x for x in catalog.entries()}
        for abbr in ("JASHER", "WLC", "TR"):
            self.assertEqual(e[abbr]["license"], "Public Domain")
        self.assertIn("scholars dispute whether it is the book named in Joshua 10:13", e["JASHER"]["note"])
        self.assertIn("Scrivener 1881", e["TR"]["note"])
        self.assertTrue(os.path.exists(os.path.join(ROOT, "bibles", "eng-jasher-1840.zefania.xml")))
        self.assertNotIn("NIV", e)                                  # copyrighted: never bundled or offered
        from bibleask.loaders import load_bible
        j = load_bible(os.path.join(ROOT, "bibles", "eng-jasher-1840.zefania.xml"))
        self.assertEqual(len(j.verses), 3910)
        self.assertTrue(any(v.chapter == 88 and v.verse == 64 and "sun stood still" in v.text for v in j.verses))

    def test_quoted_list(self):
        with open(os.path.join(ROOT, "web", "quoted.json"), encoding="utf-8") as f:
            items = json.load(f)["items"]
        refs = {it["ref"]: it for it in items}
        self.assertEqual(refs["Jude 1:14-15"]["target"]["ref"], "1 Enoch 1:9")
        self.assertEqual(refs["Numbers 21:14"]["status"], "lost")
        self.assertEqual(refs["Joshua 10:13"]["status"], "disputed")
        self.assertIn("2 Timothy 3:8", refs); self.assertIn("2 Samuel 1:18", refs)
        self.assertTrue(all(it["source"] and it["note"] for it in items))

    def test_niv_is_only_a_link(self):
        for p in ("web/index.html", "bibleask/web/index.html", "web/paths.js"):
            with open(os.path.join(ROOT, p), encoding="utf-8") as f:
                s = f.read()
            self.assertIn("biblegateway.com/passage/?search=", s, p)
            self.assertIn("version=NIV", s)
            self.assertIn("Open in NIV ↗", s)


if __name__ == "__main__":
    unittest.main()
