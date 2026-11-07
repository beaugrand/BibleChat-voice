"""The Nueva Traducción BibliaTodo (NTBT, Spanish): BibliaTodo's free agreement (LICENCIA.txt 1.4) lets BibleChat
share it if the wording stays exactly as received, brackets included, and the official credit is shown with an
active link to its page. These tests keep both promises."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web"))

from bibleask import catalog  # noqa: E402
from bibleask.loaders import load_bible  # noqa: E402

FILE = os.path.join(ROOT, "bibles", "spa-ntbt.usfx.xml")
CREDIT = ("Santa Biblia, Nueva Traducción BibliaTodo (NTBT). Publicada por BibliaTodo Bible Society, sello editorial "
          "de BibliaTodo LLC. https://www.bibliatodo.org/es/ntbt/")


class NtbtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bible = load_bible(FILE)
        cls.text = {(v.book, v.chapter, v.verse): v.text for v in cls.bible.verses}

    def test_in_the_list_with_the_official_credit(self):
        e = [x for x in catalog.entries() if x["abbr"] == "NTBT"]
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["language"], "Spanish")
        self.assertEqual(e[0]["license"], CREDIT)
        self.assertEqual(e[0]["verses"], len(self.bible.verses))
        self.assertEqual(catalog.url(e[0]["file"]), catalog.OWN + "spa-ntbt.usfx.xml")

    def test_whole_bible_with_english_book_keys(self):
        self.assertEqual(len(self.bible.verses), 31104)
        self.assertEqual(len({v.book for v in self.bible.verses}), 66)
        self.assertEqual(self.text[("Genesis", 1, 1)], "En el principio creó Dios los cielos y la tierra.")
        self.assertEqual(self.text[("Revelation", 22, 21)], "La gracia del Señor Jesús sea con todos.")

    def test_wording_and_brackets_kept(self):
        self.assertTrue(self.text[("John", 3, 16)].startswith("Porque de tal manera amó Dios al mundo que dio a su Hijo unigénito"))
        for ref in [("Mark", 16, 9), ("Mark", 16, 20), ("Acts", 8, 37), ("Romans", 16, 25)]:
            t = self.text[ref]
            self.assertTrue(t.startswith("[") and t.endswith("]"), ref)
        self.assertEqual(sum(t.startswith("[") for t in self.text.values()), 31)

    def test_newest_delivery_el_senor(self):
        # Hans chose BibliaTodo's delivery NTBT-2026-11-06 (7 November 2026): God's name in the Old Testament is "el SEÑOR"
        with open(FILE, encoding="utf-8") as f:
            s = f.read()
        self.assertIn("Delivery NTBT-2026-11-06", s)
        self.assertNotIn("Jehová", s)
        self.assertEqual(self.text[("Psalms", 23, 1)], "El SEÑOR es mi pastor; nada me faltará.")

    def test_spanish_book_names_for_the_reader(self):
        import build_data
        names = build_data.source_names(FILE)
        self.assertEqual(names["Genesis"], "Génesis")
        self.assertEqual(names["Revelation"], "Apocalipsis")

    def test_the_credit_address_is_a_link_in_both_bible_lists(self):
        for page in ("web/index.html", "bibleask/web/index.html"):
            with open(os.path.join(ROOT, page), encoding="utf-8") as f:
                s = f.read()
            self.assertIn("const escLinks = s =>", s, page)
            self.assertIn("escLinks(", s.split("const escLinks", 1)[1], page)


if __name__ == "__main__":
    unittest.main()
