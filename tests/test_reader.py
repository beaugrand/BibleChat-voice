"""Reading view (books, whole chapters) and the SPB / TSV / MyBible readers.
Run with:  python -m unittest discover -s tests -v"""
import os
import sqlite3
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp()
os.environ["XDG_DATA_HOME"] = _TMP  # keep test Bibles out of the real data folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bibleask.library import Library  # noqa: E402
from bibleask.loaders import load_bible  # noqa: E402

ZEF = b"""<?xml version="1.0" encoding="utf-8"?>
<XMLBIBLE biblename="Tiny">
 <BIBLEBOOK bnumber="1" bname="Genesis">
  <CHAPTER cnumber="1"><VERS vnumber="1">In the beginning.</VERS><VERS vnumber="2">Formless and empty.</VERS></CHAPTER>
  <CHAPTER cnumber="2"><VERS vnumber="1">Thus the heavens were completed.</VERS></CHAPTER>
 </BIBLEBOOK>
 <BIBLEBOOK bnumber="2" bname="Exodus">
  <CHAPTER cnumber="1"><VERS vnumber="1">These are the names.</VERS></CHAPTER>
 </BIBLEBOOK>
</XMLBIBLE>"""


def _write(suffix: str, text: str) -> str:
    fd, p = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return p


class Reader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = Library()
        cls.bid = cls.lib.add_file("Tiny.xml", ZEF)

    def test_books_in_file_order_with_chapters(self):
        self.assertEqual(self.lib.books(self.bid), [{"name": "Genesis", "chapters": [1, 2]},
                                                   {"name": "Exodus", "chapters": [1]}])

    def test_chapter_and_neighbours(self):
        c = self.lib.chapter(self.bid, "Genesis", 2)
        self.assertEqual(c["verses"], [{"verse": 1, "text": "Thus the heavens were completed."}])
        self.assertEqual(c["prev"], {"book": "Genesis", "chapter": 1})
        self.assertEqual(c["next"], {"book": "Exodus", "chapter": 1})
        self.assertIsNone(self.lib.chapter(self.bid, "Genesis", 1)["prev"])
        self.assertIsNone(self.lib.chapter(self.bid, "Exodus", 1)["next"])

    def test_missing_chapter_is_a_plain_error(self):
        with self.assertRaises(ValueError):
            self.lib.chapter(self.bid, "Genesis", 9)

    def test_long_verse_is_joined_again(self):
        long = " ".join(["This is a fairly long sentence about the beginning."] * 60)
        xml = f'<XMLBIBLE><BIBLEBOOK bname="Job"><CHAPTER cnumber="1"><VERS vnumber="1">{long}</VERS></CHAPTER></BIBLEBOOK></XMLBIBLE>'
        bid = self.lib.add_file("Long.xml", xml.encode())
        v = self.lib.chapter(bid, "Job", 1)["verses"]
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0]["text"], long)


USFX = """<?xml version="1.0" encoding="utf-8"?>
<usfx><book id="GEN"><h>Genesis</h><c id="1"/><p><v id="1"/>In the beginning<f>note text</f> God created.<ve/>
<v id="2"/>The earth was empty.<ve/></p></book>
<book id="JHN"><c id="3"/><p><v id="16"/>For God so <wj>loved</wj> the world.<ve/></p></book></usfx>"""

OSIS_MILESTONE = """<?xml version="1.0"?><osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace"><osisText><div type="book" osisID="Gen">
<chapter osisID="Gen.1" sID="Gen.1.s"/><verse osisID="Gen.1.1" sID="a"/>In the beginning<note>a note</note> God created.<verse eID="a"/>
<verse osisID="Gen.1.2" sID="b"/>The earth was <transChange>empty</transChange>.<verse eID="b"/><chapter eID="Gen.1.s"/></div>
<div type="book" osisID="Matt"><chapter osisID="Matt.1"><verse osisID="Matt.1.1">The book of the genealogy.</verse></chapter></div></osisText></osis>"""


class Catalog(unittest.TestCase):
    def test_every_entry_is_well_formed(self):
        from bibleask import catalog
        items = catalog.entries()
        self.assertGreaterEqual(len(items), 40)
        self.assertEqual(len({i["name"] for i in items}), len(items))  # names are unique
        for i in items:
            self.assertTrue(catalog.url(i["file"]).startswith(catalog.BASE))
            self.assertNotIn("/", i["name"])
            self.assertGreater(i["verses"], 1000)

    def test_unknown_file_is_refused(self):
        from bibleask import catalog
        with self.assertRaises(KeyError):
            catalog.url("../../etc/passwd")


class OtherFormats(unittest.TestCase):
    def test_usfx(self):
        b = load_bible(_write(".xml", USFX))
        self.assertEqual([(v.book, v.chapter, v.verse, v.text) for v in b.verses],
                         [("Genesis", 1, 1, "In the beginning God created."), ("Genesis", 1, 2, "The earth was empty."),
                          ("John", 3, 16, "For God so loved the world.")])

    def test_osis_milestones_and_containers(self):
        b = load_bible(_write(".xml", OSIS_MILESTONE))
        self.assertEqual([(v.book, v.chapter, v.verse, v.text) for v in b.verses],
                         [("Genesis", 1, 1, "In the beginning God created."), ("Genesis", 1, 2, "The earth was empty."),
                          ("Matthew", 1, 1, "The book of the genealogy.")])

    def test_spb(self):
        p = _write(".spb", "##spDataVersion:\t1\n##Title:\tTest\n##RightToLeft:\t0\n1\tGenesis\t50\n43\tJohn\t21\n"
                           "-----\nB001C001V001\t1\t1\t1\tIn the beginning.\nB043C003V016\t43\t3\t16\tFor God so loved the world.\n")
        b = load_bible(p)
        self.assertEqual([(v.book, v.chapter, v.verse, v.text) for v in b.verses],
                         [("Genesis", 1, 1, "In the beginning."), ("John", 3, 16, "For God so loved the world.")])

    def test_tsv(self):
        p = _write(".tsv", "Genesis\tGen\t1\t1\t1\tIn the beginning.\nRuth\tRut\t8\t1\t16\tWhere you go I will go.\n")
        b = load_bible(p)
        self.assertEqual([(v.book, v.chapter, v.verse) for v in b.verses], [("Genesis", 1, 1), ("Ruth", 1, 16)])

    def test_mybible_strips_markup(self):
        fd, p = tempfile.mkstemp(suffix=".SQLite3"); os.close(fd)
        con = sqlite3.connect(p)
        con.executescript("CREATE TABLE books(book_number, short_name, long_name);"
                          "CREATE TABLE verses(book_number, chapter, verse, text);"
                          "INSERT INTO books VALUES(10,'Gen','Genesis');"
                          "INSERT INTO verses VALUES(10,1,1,'In the <S>7225</S>beginning<f>[1]</f> God <i>created</i>.<pb/>¶');")
        con.commit(); con.close()
        b = load_bible(p)
        self.assertEqual([(v.book, v.chapter, v.verse, v.text) for v in b.verses], [("Genesis", 1, 1, "In the beginning God created.")])

    def _mysword(self, encryption):
        fd, p = tempfile.mkstemp(suffix=".bbl.mybible"); os.close(fd)
        con = sqlite3.connect(p)
        con.executescript("CREATE TABLE Bible(Book, Chapter, Verse, Scripture);"
                          "CREATE TABLE Details(Title, Description, Encryption);"
                          f"INSERT INTO Details VALUES('T','Test Bible','{encryption}');"
                          "INSERT INTO Bible VALUES(43,3,16,'For Elohim so loved<RF>note<Rf> the <FI>world<Fi><WG2889>.');")
        con.commit(); con.close()
        return p

    def test_mysword_unlocked(self):
        b = load_bible(self._mysword("0"))
        self.assertEqual([(v.book, v.chapter, v.verse, v.text) for v in b.verses], [("John", 3, 16, "For Elohim so loved the world.")])

    def test_mysword_locked_says_so(self):
        with self.assertRaisesRegex(ValueError, "locked"):
            load_bible(self._mysword("2"))

    def test_not_a_mybible_file(self):
        p = _write(".sqlite3", "just text")
        with self.assertRaises(ValueError):
            load_bible(p)


if __name__ == "__main__":
    unittest.main()
