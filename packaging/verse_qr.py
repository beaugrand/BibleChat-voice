"""Make a printable US-letter page (8.5 x 11 in) with one large QR code for one Bible verse.

Scanning the code with a phone camera opens the phone version of BibleChat at that verse. BibleChat shows the
verse in a box titled "A friend shared a verse with you" and highlights it in the chapter.

The link is the one BibleChat's own Share button makes:
    https://beaugrand.github.io/BibleChat-voice/#/eng-kjv/John/3/16/s
    (site address / Bible / book / chapter / verse / "s" = shared, so the welcome box appears)

Usage:
    python packaging/verse_qr.py "John 3:16"
    python packaging/verse_qr.py "Ps 23:1" "1 Cor 13:4" --out qr-pages
    python packaging/verse_qr.py "John 3:16" --bible eng-web      (another Bible from the site's list)
    python packaging/verse_qr.py "John 3:16" --no-check           (skip the online check that the verse exists)

Each verse gives one PDF, for example QR-John-3-16.pdf. Needs only reportlab (already in requirements.txt).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bibleask.loaders import PROTESTANT_BOOKS, _BOOK_CODES  # noqa: E402

SITE = "https://beaugrand.github.io/BibleChat-voice/"
DEFAULT_BIBLE = "eng-kjv"


def _key(s: str) -> str:
    """'1 Cor.' -> '1cor', 'I John' -> '1john', 'First Peter' -> '1peter'."""
    s = s.lower().strip()
    s = re.sub(r"^(iii|3rd|third)\b\s*", "3", s)
    s = re.sub(r"^(ii|2nd|second)\b\s*", "2", s)
    s = re.sub(r"^(i|1st|first)\b\s*", "1", s)
    return re.sub(r"[^a-z0-9]", "", s)


_ALIASES: dict[str, str] = {}
for _osis, _usfx, _name in _BOOK_CODES:
    for _a in (_name, _osis, _usfx):
        _ALIASES.setdefault(_key(_a), _name)
for _a, _name in {"Psalm": "Psalms", "Ps": "Psalms", "Psa": "Psalms", "Song of Songs": "Song of Solomon",
                  "Canticles": "Song of Solomon", "Song": "Song of Solomon", "Jn": "John", "Mt": "Matthew",
                  "Mk": "Mark", "Lk": "Luke", "Rom": "Romans", "Revelations": "Revelation", "Rev": "Revelation",
                  "Phil": "Philippians", "Phm": "Philemon", "Jas": "James", "Heb": "Hebrews", "Prov": "Proverbs",
                  "Eccles": "Ecclesiastes", "Qoheleth": "Ecclesiastes", "Isa": "Isaiah", "Jer": "Jeremiah",
                  "Ezek": "Ezekiel", "Dan": "Daniel", "Gen": "Genesis", "Ex": "Exodus", "Deut": "Deuteronomy",
                  "Josh": "Joshua", "Judg": "Judges"}.items():
    _ALIASES[_key(_a)] = _name


def find_book(text: str) -> str:
    """The BibleChat book name for what was typed ('1 cor', 'Psalm', 'Jn'...). Raises ValueError if unknown."""
    k = _key(text)
    if not k:
        raise ValueError("No book name given.")
    if k in _ALIASES:
        return _ALIASES[k]
    hits = [b for b in PROTESTANT_BOOKS if _key(b).startswith(k)]
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise ValueError(f'"{text}" could be {", ".join(hits)}. Type a little more of the name.')
    raise ValueError(f'Unknown book "{text}". Try a full name such as "John" or "1 Corinthians".')


def parse_ref(text: str) -> tuple[str, int, int]:
    """'John 3:16' -> ('John', 3, 16). Also accepts 'John 3.16' and 'John 3 16'."""
    m = re.match(r"^\s*(.+?)\s*(\d+)\s*[:., ]\s*(\d+)\s*$", text)
    if not m:
        raise ValueError(f'Could not read "{text}". Write it like "John 3:16".')
    book, ch, v = find_book(m.group(1)), int(m.group(2)), int(m.group(3))
    if ch < 1 or v < 1:
        raise ValueError("Chapter and verse start at 1.")
    return book, ch, v


def verse_link(book: str, ch: int, v: int, bible: str = DEFAULT_BIBLE, site: str = SITE) -> str:
    """The same link BibleChat's Share button makes (web/index.html, verseLinkAt)."""
    q = urllib.parse.quote
    return f"{site}#/{q(bible, safe='')}/{q(book, safe='')}/{ch}/{v}/s"


def check_online(book: str, ch: int, v: int, bible: str = DEFAULT_BIBLE, site: str = SITE) -> str | None:
    """The verse text from the live site, or raise ValueError if the verse does not exist there.
    Returns None when the site cannot be reached (no internet): the page is still made."""
    try:
        with urllib.request.urlopen(f"{site}data/{urllib.parse.quote(bible)}.json", timeout=60) as r:
            data = json.load(r)
    except Exception as e:  # noqa: BLE001  (offline, proxy, unknown Bible id...)
        print(f"  Note: could not check the verse online ({e.__class__.__name__}). Making the page anyway.")
        return None
    for b in data["books"]:
        if b["n"] == book:
            for c, verses in b["c"]:
                if c == ch:
                    for n, text in verses:
                        if n == v:
                            return text
                    raise ValueError(f"{book} {ch} has no verse {v} in {bible}.")
            raise ValueError(f"{book} has no chapter {ch} in {bible}.")
    raise ValueError(f"{book} is not in {bible}.")


def make_page(book: str, ch: int, v: int, out_path: str, bible: str = DEFAULT_BIBLE, site: str = SITE) -> str:
    """Write the PDF. Returns the link inside the QR code."""
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    link = verse_link(book, ch, v, bible, site)
    ref = f"{book} {ch}:{v}"
    W, H = letter                                   # 612 x 792 points (8.5 x 11 in)
    margin = 0.5 * inch
    title_h, caption_h = 1.1 * inch, 0.95 * inch    # room for the reference above and the words below
    size = min(W - 2 * margin, H - 2 * margin - title_h - caption_h)   # as large as fits: 7.5 in

    qr = QrCodeWidget(link, barLevel="H", barBorder=4)   # error correction High; 4-module white quiet zone
    x0, y0, x1, y1 = qr.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(qr)

    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle(f"BibleChat QR · {ref}")
    c.setAuthor("BibleChat")
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    qr_y = margin + caption_h
    renderPDF.draw(d, c, (W - size) / 2, qr_y)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(W / 2, H - margin - 0.65 * inch, ref)
    c.setFont("Helvetica", 20)
    c.drawCentredString(W / 2, margin + 0.55 * inch, "Scan with your phone camera to read this verse")
    c.setFont("Helvetica", 11)
    c.drawCentredString(W / 2, margin + 0.2 * inch, "BibleChat · free, no sign-up · " + site.replace("https://", ""))
    c.showPage()
    c.save()
    return link


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Printable QR code page for one Bible verse in BibleChat.")
    ap.add_argument("refs", nargs="+", help='verse references, e.g. "John 3:16" "Psalm 23:1"')
    ap.add_argument("--out", default=".", help="folder for the PDF files (default: this folder)")
    ap.add_argument("--bible", default=DEFAULT_BIBLE, help=f"Bible id on the site (default {DEFAULT_BIBLE})")
    ap.add_argument("--no-check", action="store_true", help="do not check online that the verse exists")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    bad = 0
    for text in a.refs:
        try:
            book, ch, v = parse_ref(text)
            verse = None if a.no_check else check_online(book, ch, v, a.bible)
        except ValueError as e:
            print(f"✗ {text}: {e}")
            bad += 1
            continue
        path = os.path.join(a.out, f"QR-{book.replace(' ', '')}-{ch}-{v}.pdf")
        link = make_page(book, ch, v, path, a.bible)
        print(f"✓ {book} {ch}:{v}\n  Link: {link}\n  Page: {os.path.abspath(path)}")
        if verse:
            print(f"  Verse: {verse}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
