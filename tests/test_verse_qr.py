"""🖨 Printable QR pages for one verse (packaging/verse_qr.py): the typed reference becomes the same link the phone's
Share button makes, and the PDF is one US-letter page with a High error-correction QR code."""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packaging"))
import verse_qr  # noqa: E402


class VerseQR(unittest.TestCase):
    def test_parse(self):
        for text, want in [("John 3:16", ("John", 3, 16)), ("Psalm 23:1", ("Psalms", 23, 1)), ("ps 23.1", ("Psalms", 23, 1)),
                           ("1 Cor 13:4", ("1 Corinthians", 13, 4)), ("1Cor 13:4", ("1 Corinthians", 13, 4)),
                           ("I John 4:8", ("1 John", 4, 8)), ("First Peter 5:7", ("1 Peter", 5, 7)),
                           ("Song of Songs 2:4", ("Song of Solomon", 2, 4)), ("Phil 4:13", ("Philippians", 4, 13)),
                           ("Philem 1:6", ("Philemon", 1, 6)), ("Rev 22:20", ("Revelation", 22, 20)),
                           ("Genesis 1 1", ("Genesis", 1, 1))]:
            self.assertEqual(verse_qr.parse_ref(text), want, text)
        for bad in ["John", "John 3", "Phi 4:13", "Hezekiah 1:1", "John 0:1"]:
            with self.assertRaises(ValueError, msg=bad):
                verse_qr.parse_ref(bad)

    def test_link_matches_the_phone_share_link(self):
        self.assertEqual(verse_qr.verse_link("John", 3, 16), "https://beaugrand.github.io/BibleChat-voice/#/eng-kjv/John/3/16/s")
        self.assertEqual(verse_qr.verse_link("1 Corinthians", 13, 4),
                         "https://beaugrand.github.io/BibleChat-voice/#/eng-kjv/1%20Corinthians/13/4/s")
        # the phone reads #/<bible>/<book>/<chapter>/<verse>/s (web/index.html, parseHash) and makes it in verseLinkAt
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('shared: p[4] === "s"', page)
        self.assertIn('"/" + ch + "/" + v + "/s"', page)
        self.assertIn('PHONE_URL = "' + verse_qr.SITE + '"', page)

    def test_pdf_is_one_letter_page(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "qr.pdf")
            link = verse_qr.make_page("John", 3, 16, out)
            self.assertTrue(link.endswith("/John/3/16/s"))
            with open(out, "rb") as f:
                pdf = f.read()
            self.assertTrue(pdf.startswith(b"%PDF"))
            self.assertEqual(len(re.findall(rb"/Type /Page\b", pdf)), 1)
            self.assertIn(b"/MediaBox [ 0 0 612 792 ]", pdf)

    def test_error_correction_high(self):
        from reportlab.graphics.barcode.qr import QrCodeWidget
        src = open(os.path.join(ROOT, "packaging", "verse_qr.py"), encoding="utf-8").read()
        self.assertIn('barLevel="H"', src)
        self.assertEqual(QrCodeWidget("x", barLevel="H").barLevel, "H")


if __name__ == "__main__":
    unittest.main()
