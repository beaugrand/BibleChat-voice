"""Load a Bible from a PDF, XML (Zefania / OSIS), TXT or our own JSON cache.

Everything ends up as a flat list of Verse records (book, chapter, verse, text),
so the search and AI layers never care what the original file looked like.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Optional

Progress = Optional[Callable[[str, float], None]]  # (message, 0..1)


@dataclass
class Verse:
    book: str
    chapter: int
    verse: int
    text: str

    @property
    def ref(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"


@dataclass
class Bible:
    name: str
    verses: list[Verse]

    def to_json(self) -> str:
        return json.dumps(
            {"name": self.name, "verses": [[v.book, v.chapter, v.verse, v.text] for v in self.verses]},
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(s: str) -> "Bible":
        d = json.loads(s)
        return Bible(d["name"], [Verse(*row) for row in d["verses"]])


def _tick(progress: Progress, msg: str, frac: float) -> None:
    if progress:
        progress(msg, frac)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------- entry point
def load_bible(path: str, progress: Progress = None) -> Bible:
    ext = os.path.splitext(path)[1].lower()
    name = os.path.splitext(os.path.basename(path))[0]
    if ext == ".json":
        with open(path, encoding="utf-8") as f:
            return Bible.from_json(f.read())
    if ext in (".xml", ".osis", ".zef"):
        verses = _load_xml(path, progress)
    elif ext in (".txt", ".text"):
        verses = _load_txt(path, progress)
    elif ext == ".pdf":
        verses = _load_pdf(path, progress)
    elif ext == ".spb":
        verses = _load_spb(path, progress)
    elif ext == ".tsv":
        verses = _load_tsv(path, progress)
    elif ext in (".sqlite3", ".sqlite", ".mybible"):
        verses = _load_mybible(path, progress)
    else:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}. Use PDF, XML, TXT, SPB, TSV or MyBible SQLite3.")
    if not verses:
        raise ValueError("I could not find any Bible text in that file.")
    return Bible(name, _split_long(verses))


def _split_long(verses: list[Verse], limit: int = 1500, target: int = 700) -> list[Verse]:
    """A scan glitch can glue many verses together. Split very long entries so search stays precise."""
    out: list[Verse] = []
    for v in verses:
        if len(v.text) <= limit:
            out.append(v)
            continue
        sentences = re.split(r"(?<=[.!?”’\"])\s+", v.text)
        cur = ""
        for sent in sentences:
            if cur and len(cur) + len(sent) > target:
                out.append(Verse(v.book, v.chapter, v.verse, cur.strip()))
                cur = ""
            cur += sent + " "
        if cur.strip():
            out.append(Verse(v.book, v.chapter, v.verse, cur.strip()))
    return out


# --------------------------------------------------------------------------- XML
def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


# Book codes used by OSIS (osisID="Gen.1.1") and USFX/Paratext (<book id="GEN">), with English names.
_BOOK_CODES = [
    ("Gen", "GEN", "Genesis"), ("Exod", "EXO", "Exodus"), ("Lev", "LEV", "Leviticus"), ("Num", "NUM", "Numbers"),
    ("Deut", "DEU", "Deuteronomy"), ("Josh", "JOS", "Joshua"), ("Judg", "JDG", "Judges"), ("Ruth", "RUT", "Ruth"),
    ("1Sam", "1SA", "1 Samuel"), ("2Sam", "2SA", "2 Samuel"), ("1Kgs", "1KI", "1 Kings"), ("2Kgs", "2KI", "2 Kings"),
    ("1Chr", "1CH", "1 Chronicles"), ("2Chr", "2CH", "2 Chronicles"), ("Ezra", "EZR", "Ezra"), ("Neh", "NEH", "Nehemiah"),
    ("Esth", "EST", "Esther"), ("Job", "JOB", "Job"), ("Ps", "PSA", "Psalms"), ("Prov", "PRO", "Proverbs"),
    ("Eccl", "ECC", "Ecclesiastes"), ("Song", "SNG", "Song of Solomon"), ("Isa", "ISA", "Isaiah"), ("Jer", "JER", "Jeremiah"),
    ("Lam", "LAM", "Lamentations"), ("Ezek", "EZK", "Ezekiel"), ("Dan", "DAN", "Daniel"), ("Hos", "HOS", "Hosea"),
    ("Joel", "JOL", "Joel"), ("Amos", "AMO", "Amos"), ("Obad", "OBA", "Obadiah"), ("Jonah", "JON", "Jonah"),
    ("Mic", "MIC", "Micah"), ("Nah", "NAM", "Nahum"), ("Hab", "HAB", "Habakkuk"), ("Zeph", "ZEP", "Zephaniah"),
    ("Hag", "HAG", "Haggai"), ("Zech", "ZEC", "Zechariah"), ("Mal", "MAL", "Malachi"), ("Matt", "MAT", "Matthew"),
    ("Mark", "MRK", "Mark"), ("Luke", "LUK", "Luke"), ("John", "JHN", "John"), ("Acts", "ACT", "Acts"),
    ("Rom", "ROM", "Romans"), ("1Cor", "1CO", "1 Corinthians"), ("2Cor", "2CO", "2 Corinthians"), ("Gal", "GAL", "Galatians"),
    ("Eph", "EPH", "Ephesians"), ("Phil", "PHP", "Philippians"), ("Col", "COL", "Colossians"),
    ("1Thess", "1TH", "1 Thessalonians"), ("2Thess", "2TH", "2 Thessalonians"), ("1Tim", "1TI", "1 Timothy"),
    ("2Tim", "2TI", "2 Timothy"), ("Titus", "TIT", "Titus"), ("Phlm", "PHM", "Philemon"), ("Heb", "HEB", "Hebrews"),
    ("Jas", "JAS", "James"), ("1Pet", "1PE", "1 Peter"), ("2Pet", "2PE", "2 Peter"), ("1John", "1JN", "1 John"),
    ("2John", "2JN", "2 John"), ("3John", "3JN", "3 John"), ("Jude", "JUD", "Jude"), ("Rev", "REV", "Revelation"),
    ("Tob", "TOB", "Tobit"), ("Jdt", "JDT", "Judith"), ("EsthGr", "ESG", "Esther (Greek)"), ("AddEsth", "ADE", "Additions to Esther"),
    ("Wis", "WIS", "Wisdom"), ("Sir", "SIR", "Sirach"), ("Bar", "BAR", "Baruch"), ("EpJer", "LJE", "Letter of Jeremiah"),
    ("PrAzar", "S3Y", "Prayer of Azariah"), ("Sus", "SUS", "Susanna"), ("Bel", "BEL", "Bel and the Dragon"),
    ("1Macc", "1MA", "1 Maccabees"), ("2Macc", "2MA", "2 Maccabees"), ("3Macc", "3MA", "3 Maccabees"),
    ("4Macc", "4MA", "4 Maccabees"), ("1Esd", "1ES", "1 Esdras"), ("2Esd", "2ES", "2 Esdras"),
    ("PrMan", "MAN", "Prayer of Manasseh"), ("AddPs", "PS2", "Psalm 151"), ("DanGr", "DAG", "Daniel (Greek)"),
]
_OSIS_NAME = {o: n for o, _, n in _BOOK_CODES}
_USFX_NAME = {u: n for _, u, n in _BOOK_CODES}


def _root_tag(path: str) -> str:
    for _event, el in ET.iterparse(path, events=("start",)):
        return _strip_ns(el.tag)
    return ""


class _MilestoneReader:
    """Collects verse text for OSIS and USFX, where a verse may be an element or a pair of start/end markers.
    Footnotes, cross references and headings are left out."""
    SKIP = {"NOTE", "TITLE", "F", "X", "FE", "H", "TOC", "S", "S1", "S2", "IDE", "ID", "REFERENCE"}

    def __init__(self) -> None:
        self.verses: list[Verse] = []
        self.cur: Optional[tuple[str, int, int]] = None
        self.buf: list[str] = []
        self.skip = 0

    def open(self, ref: tuple[str, int, int]) -> None:
        self.close()
        self.cur, self.buf = ref, []

    def close(self) -> None:
        if self.cur:
            text = _clean("".join(self.buf))
            if text:
                self.verses.append(Verse(*self.cur, text))
        self.cur, self.buf = None, []

    def text(self, s: Optional[str]) -> None:
        if s and self.cur and not self.skip:
            self.buf.append(s)


def _walk(path: str, on_start, on_end, reader: "_MilestoneReader") -> None:
    """Depth-first walk that hands every element's text and tail to the reader in document order."""
    import xml.sax

    class H(xml.sax.ContentHandler):
        def startElement(self, name, attrs):
            on_start(name.rsplit(":", 1)[-1].upper(), attrs)

        def endElement(self, name):
            on_end(name.rsplit(":", 1)[-1].upper())

        def characters(self, content):
            reader.text(content)

    xml.sax.parse(path, H())
    reader.close()


def _load_osis(path: str, progress: Progress) -> list[Verse]:
    r = _MilestoneReader()
    container: list[bool] = []

    def start(tag, a):
        if tag in r.SKIP:
            r.skip += 1
        elif tag == "VERSE":
            if a.get("eID"):
                r.close()
                return
            oid = (a.get("osisID") or "").split()[0] if a.get("osisID") else ""
            parts = oid.split(".")
            if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                r.open((_OSIS_NAME.get(parts[0], parts[0]), int(parts[1]), int(parts[2])))
            container.append(not a.get("sID"))
        elif tag == "CHAPTER" and a.get("eID"):
            r.close()

    def end(tag):
        if tag in r.SKIP:
            r.skip -= 1
        elif tag == "VERSE" and container:
            if container.pop():
                r.close()
        elif tag in ("CHAPTER", "DIV", "BOOK"):
            pass

    _tick(progress, "Reading OSIS XML…", 0.1)
    _walk(path, start, end, r)
    return r.verses


def _load_usfx(path: str, progress: Progress) -> list[Verse]:
    r = _MilestoneReader()
    st = {"book": "", "chapter": 0}

    def start(tag, a):
        if tag in r.SKIP:
            r.skip += 1
        elif tag == "BOOK":
            r.close()
            code = (a.get("id") or "").upper()
            st["book"], st["chapter"] = _USFX_NAME.get(code, code), 0
        elif tag == "C":
            r.close()
            try:
                st["chapter"] = int((a.get("id") or "0").split("-")[0])
            except ValueError:
                st["chapter"] += 1
        elif tag == "V":
            vid = (a.get("id") or "").split("-")[0]
            if st["book"] and st["chapter"] and vid.isdigit():
                r.open((st["book"], st["chapter"], int(vid)))
        elif tag == "VE":
            r.close()

    def end(tag):
        if tag in r.SKIP:
            r.skip -= 1
        elif tag == "BOOK":
            r.close()

    _tick(progress, "Reading USFX XML…", 0.1)
    _walk(path, start, end, r)
    return r.verses


def _load_xml(path: str, progress: Progress) -> list[Verse]:
    """Zefania XML (BIBLEBOOK/CHAPTER/VERS), OSIS (<verse osisID="Gen.1.1">) and USFX (<book id="GEN"><c/><v/>)."""
    root = _root_tag(path)
    if root == "USFX":
        return _load_usfx(path, progress)
    if root == "OSIS":
        return _load_osis(path, progress)
    _tick(progress, "Reading XML…", 0.05)
    verses: list[Verse] = []
    book = ""
    chapter = 0
    book_no = 0
    # OSIS state
    osis_open: Optional[tuple[str, int, int]] = None
    osis_buf: list[str] = []
    for event, el in ET.iterparse(path, events=("start", "end")):
        tag = _strip_ns(el.tag)
        if event == "start":
            if tag == "BIBLEBOOK":
                book_no += 1
                book = (el.get("bname") or el.get("bsname") or "").strip() or f"Book {el.get('bnumber') or book_no}"
                chapter = 0
            elif tag == "CHAPTER":
                try:
                    chapter = int(el.get("cnumber") or chapter + 1)
                except ValueError:
                    chapter += 1
            continue
        # end events
        if tag == "VERS":
            text = _clean("".join(el.itertext()))
            try:
                vnum = int(el.get("vnumber") or 0)
            except ValueError:
                vnum = 0
            if text:
                verses.append(Verse(book or "Unknown", chapter or 1, vnum, text))
            el.clear()
        elif tag == "VERSE" and el.get("osisID"):
            parts = el.get("osisID", "").split(".")
            if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                text = _clean("".join(el.itertext()))
                if text:
                    verses.append(Verse(parts[0], int(parts[1]), int(parts[2]), text))
            el.clear()
        elif tag == "BIBLEBOOK":
            el.clear()
    _tick(progress, "Done reading XML", 1.0)
    return verses


# --------------------------------------------------------------------------- SPB / TSV / MyBible
# These three readers follow the file layouts handled by "Bible" (net.lugsole.bible_gui),
# Copyright (c) 2020 Lugsole, MIT License: https://github.com/Lugsole/net.lugsole.bible_gui
def _read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read().splitlines()


def _load_spb(path: str, progress: Progress) -> list[Verse]:
    """SoftProjector Bible: '##' header lines (the book list follows '##RightToLeft:'),
    a '-----' line, then one verse per line: id, book no., chapter, verse, text (tab separated)."""
    _tick(progress, "Reading SoftProjector file…", 0.05)
    lines = _read_lines(path)
    names: dict[int, str] = {}
    i, in_books = 0, False
    while i < len(lines) and not lines[i].startswith("--"):
        ln = lines[i]
        if ln.startswith("##"):
            in_books = ln.startswith("##RightToLeft:")
        elif in_books:
            parts = ln.split("\t")
            if len(parts) >= 2 and parts[0].strip().isdigit():
                names[int(parts[0])] = parts[1].strip()
        i += 1
    verses: list[Verse] = []
    for ln in lines[i + 1:]:
        parts = ln.split("\t")
        if len(parts) == 5 and parts[1].strip().isdigit() and parts[2].strip().isdigit() and parts[3].strip().isdigit():
            b = int(parts[1])
            text = _clean(parts[4])
            if text:
                verses.append(Verse(names.get(b, f"Book {b}"), int(parts[2]), int(parts[3]), text))
    _tick(progress, "Done", 1.0)
    return verses


def _load_tsv(path: str, progress: Progress) -> list[Verse]:
    """Six tab-separated columns: book name, abbreviation, book no., chapter, verse, text."""
    _tick(progress, "Reading TSV file…", 0.05)
    verses: list[Verse] = []
    for ln in _read_lines(path):
        parts = ln.split("\t")
        if len(parts) >= 6 and parts[3].strip().isdigit() and parts[4].strip().isdigit():
            text = _clean("\t".join(parts[5:]))
            if text:
                verses.append(Verse(parts[0].strip(), int(parts[3]), int(parts[4]), text))
    _tick(progress, "Done", 1.0)
    return verses


_MB_DROP = re.compile(r"<(S|f|n|m)>.*?</\1>", re.S)  # Strong's numbers, footnotes, notes, morphology
_MB_TAG = re.compile(r"<[^>]+>")


PROTESTANT_BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther",
    "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"]
# MySword markup: footnotes <RF>..<Rf>, headings <TS>..<Ts>, Strong's/morphology tags like <WH430>
_MS_DROP = re.compile(r"<RF[^>]*>.*?<Rf>|<TS[^>]*>.*?<Ts>|<RX[^>]*>.*?<Rx>", re.S)
_MS_TAG = re.compile(r"<[^>]*>")


def _load_mysword(conn, progress: Progress) -> list[Verse]:
    """MySword Bible (.bbl.mybible): table 'Bible' (Book 1-66, Chapter, Verse, Scripture) and 'Details'."""
    try:
        enc = conn.execute("SELECT * FROM Details").fetchone()
        cols = [d[0].lower() for d in conn.execute("SELECT * FROM Details").description]
        info = dict(zip(cols, enc or ()))
    except sqlite3.DatabaseError:
        info = {}
    if str(info.get("encryption") or "0").strip() not in ("", "0"):
        title = info.get("description") or info.get("title") or "This Bible"
        raise ValueError(f"{title} is locked (encrypted) by its publisher, so it only opens inside MySword. "
                         "BibleChat can read unlocked MySword Bibles, but not locked ones.")
    verses: list[Verse] = []
    for b, c, v, t in conn.execute("SELECT Book, Chapter, Verse, Scripture FROM Bible ORDER BY Book, Chapter, Verse"):
        if isinstance(t, bytes):
            try:
                import zlib
                t = zlib.decompress(t).decode("utf-8")
            except Exception:
                t = t.decode("utf-8", errors="replace")
        text = _clean(_MS_TAG.sub("", _MS_DROP.sub("", t or "")))
        b = int(b)
        if text:
            verses.append(Verse(PROTESTANT_BOOKS[b - 1] if 1 <= b <= 66 else f"Book {b}", int(c), int(v), text))
    return verses


def _load_mybible(path: str, progress: Progress) -> list[Verse]:
    """MyBible module (SQLite3): tables 'books' (book_number, long_name) and 'verses'.
    MySword Bibles (.bbl.mybible) use a different layout and are handled by _load_mysword."""
    _tick(progress, "Reading MyBible / MySword file…", 0.05)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        try:
            tables = {r[0].lower() for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError as e:
            raise ValueError("That file isn't a MyBible or MySword Bible.") from e
        if "bible" in tables:
            verses = _load_mysword(conn, progress)
            _tick(progress, "Done", 1.0)
            return verses
        names = {int(r[0]): (r[1] or "").strip() for r in conn.execute("SELECT book_number, long_name FROM books")}
        verses: list[Verse] = []
        for b, c, v, t in conn.execute("SELECT book_number, chapter, verse, text FROM verses ORDER BY book_number, chapter, verse"):
            t = re.sub(r"<(br|pb)\s*/?>", " ", _MB_DROP.sub("", t or ""), flags=re.I)
            text = _clean(_MB_TAG.sub("", t).replace("¶", ""))
            if text:
                verses.append(Verse(names.get(int(b)) or f"Book {b}", int(c), int(v), text))
    except sqlite3.DatabaseError as e:
        raise ValueError("That file isn't a MyBible or MySword Bible.") from e
    finally:
        conn.close()
    _tick(progress, "Done", 1.0)
    return verses


# --------------------------------------------------------------------------- TXT
_TXT_REF = re.compile(r"^\s*((?:[1-3]\s*)?[A-Za-z][A-Za-z .'’]*?)\s+(\d{1,3})[:.](\d{1,3})\s+(.*\S)\s*$")


def _load_txt(path: str, progress: Progress) -> list[Verse]:
    """Lines like 'Genesis 1:1 In the beginning...'. Otherwise plain paragraphs."""
    _tick(progress, "Reading text file…", 0.05)
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    verses: list[Verse] = []
    for ln in lines:
        m = _TXT_REF.match(ln)
        if m:
            verses.append(Verse(m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.group(4)))
    if len(verses) >= 20:
        return verses
    gut = _load_chapter_verse_text(lines)
    if len(gut) >= 100:
        return gut
    return _chunk_text("\n".join(lines), label="Text")


_CV_LINE = re.compile(r"^\s*(\d{1,3}):(\d{1,3})\s+(.*\S)\s*$")
_GUTENBERG_END = re.compile(r"\*\*\*\s*END OF|^\s*End of (the )?Project Gutenberg", re.I)


def _load_chapter_verse_text(lines: list[str]) -> list[Verse]:
    """Project Gutenberg style: a book title line, then verses such as '1:1 In the beginning…'."""
    verses: list[Verse] = []
    book = "Bible"
    cur: Optional[list] = None  # [chapter, verse, [text pieces]]

    def flush() -> None:
        nonlocal cur
        if cur:
            text = _clean(" ".join(cur[2]))
            if text:
                verses.append(Verse(book, cur[0], cur[1], text))
        cur = None

    def next_nonblank(i: int) -> str:
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        return lines[j] if j < len(lines) else ""

    for i, ln in enumerate(lines):
        if _GUTENBERG_END.search(ln):
            break
        m = _CV_LINE.match(ln)
        if m:
            flush()
            cur = [int(m.group(1)), int(m.group(2)), [m.group(3)]]
            continue
        s = ln.strip()
        if not s:
            continue
        after_blank = i == 0 or not lines[i - 1].strip()
        if after_blank:
            nxt = _CV_LINE.match(next_nonblank(i))
            flush()
            if nxt and len(s) <= 100:
                book = s.rstrip(":")
            # any other stand-alone paragraph (license text, part titles) is not scripture
        elif cur is not None:
            cur[2].append(s)  # a verse wrapped onto a second line
    flush()
    return verses


def _chunk_text(text: str, label: str, page_of: Optional[Callable[[int], int]] = None) -> list[Verse]:
    """Fallback: split into ~350-character passages so search still works."""
    out: list[Verse] = []
    words = text.split()
    buf: list[str] = []
    size = 0
    n = 0
    for w in words:
        buf.append(w)
        size += len(w) + 1
        if size >= 350:
            n += 1
            out.append(Verse(label, 1, n, " ".join(buf)))
            buf, size = [], 0
    if buf:
        n += 1
        out.append(Verse(label, 1, n, " ".join(buf)))
    return out


# --------------------------------------------------------------------------- PDF
_FILLER_STOP = re.compile(r"[.,;:!?]$")
_SMALL_WORDS = {"of", "the", "and", "to", "from", "with", "or", "in", "a", "an", "on", "for", "by", "at", "according"}
_ROMAN = re.compile(r"^[IVXLC]+([-–][IVXLC]+)?\.?$")


def _title_like(s: str) -> bool:
    """True for 'The Book of Daniel' style lines, false for a sentence fragment."""
    if _ROMAN.match(s) or "," in s and not s.split(",")[0].istitle():
        return False
    words = [w for w in re.split(r"\s+", s) if w and w.lower().strip("’'") not in _SMALL_WORDS]
    if not words or len(words) > 10:
        return False
    caps = sum(1 for w in words if w[0].isupper() or w[0].isdigit())
    return caps / len(words) >= 0.8


def _pdf_text(path: str, progress: Progress) -> str:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(path)
    n = len(pdf)
    pages: list[str] = []
    for i in range(n):
        page = pdf[i]
        tp = page.get_textpage()
        pages.append(tp.get_text_range())
        tp.close()
        page.close()
        if i % 25 == 0:
            _tick(progress, f"Reading PDF page {i + 1} of {n}…", 0.05 + 0.6 * i / max(n, 1))
    pdf.close()
    return "\n".join(pages).replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")


def _is_chapter_marker(lines: list[str], i: int, expected: Optional[int] = None) -> Optional[int]:
    """A line holding only a number, followed (after a few label lines) by a line that starts verse '1'."""
    s = lines[i].strip()
    if not s.isdigit() or len(s) > 3:
        return None
    n = int(s)
    if expected is not None and n != expected:
        return None
    j = i + 1
    skipped = 0
    while j < len(lines) and skipped < 8:
        t = lines[j].strip()
        if not t or re.match(r"^Book \d+$", t) or (len(t) <= 2 and not t.isdigit()):
            j += 1  # blank line, Psalms "Book 1" divider, or a one-letter margin label
            continue
        if re.match(r"^(1(?!\d)|[lI]\.\s)", t):  # "l." is how the scan sometimes reads "1."
            return n
        if re.search(r"[.:;!?”\"]\s1\s*[A-Z“‘]", t):  # "For the Chief Musician. By David. 1 In Yahweh…"
            return n
        if len(t) <= 140 and not t[0].isdigit():
            skipped += 1  # a superscription such as "A Psalm by David"
            j += 1
            continue
        return None
    return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _heading_matches(lines: list[str], k: int, title_norm: str) -> Optional[str]:
    """Does a heading for `title` start at line k? Handles titles wrapped over two lines."""
    a = lines[k].strip()
    if not a or len(a) > 100:
        return None
    n1 = _norm(a)
    if n1 == title_norm:
        return a
    if len(n1) >= 15 and k + 1 < len(lines):
        b = lines[k + 1].strip()
        if b and len(b) <= 100:
            joined = n1 + _norm(b)
            if title_norm.startswith(n1) and (joined.startswith(title_norm) or title_norm.startswith(joined)):
                return f"{a} {b}"
    return None


def _find_headings(lines: list[str]) -> list[tuple[int, str]]:
    """Return [(line_index, title)] for every book heading in the PDF text."""
    found: dict[int, str] = {}
    toc_hits: set[str] = set()

    # 1) Titles from a table of contents (needed for books whose first chapter is preceded by intro text)
    toc_titles: list[str] = []
    for i, ln in enumerate(lines[:6000]):
        if re.match(r"^\s*(table of )?contents\s*$", ln, re.I):
            j = i + 1
            while j < len(lines) and len(toc_titles) < 300:
                s = lines[j].strip()
                if not s and toc_titles:
                    break
                if s:
                    if len(s) > 100 or _FILLER_STOP.search(s):
                        break
                    toc_titles.append(s)
                j += 1
            toc_end = j
            break
    else:
        toc_end = 0
    if toc_titles:
        ptr = toc_end
        for title in toc_titles:
            tn = _norm(title)
            if len(tn) < 3:
                continue
            for k in range(ptr, len(lines)):
                hit = _heading_matches(lines, k, tn)
                if hit:
                    found[k] = hit
                    toc_hits.add(hit)
                    ptr = k + 1
                    break

    # 2) Auto-detect: a short title line, then (up to 3 lines later) a standalone "1" chapter marker
    start = toc_end if toc_titles else 0
    for i in range(start, len(lines) - 2):
        s = lines[i].strip()
        if not s or len(s) > 80 or s.isdigit() or _FILLER_STOP.search(s) or not s[0].isupper():
            continue
        if not _title_like(s):
            continue
        if i in found:
            continue
        seen = 0
        for j in range(i + 1, min(i + 5, len(lines))):
            if not lines[j].strip():
                continue
            seen += 1
            if seen > 3:
                break
            if _is_chapter_marker(lines, j, expected=1) is not None:
                # Only accept if the title is not the tail of a previous verse (avoid mid-paragraph lines)
                if i == 0 or not lines[i - 1].strip() or _looks_like_verse_end(lines[i - 1]):
                    found[i] = s
                break
    items = sorted(found.items())
    toc_set = toc_hits
    cleaned: list[tuple[int, str]] = []
    for idx, title in items:
        if cleaned and title not in toc_set and idx - cleaned[-1][0] <= 8:
            continue  # a subtitle under the previous heading, not a new book
        cleaned.append((idx, title))
    return cleaned


def _looks_like_verse_end(prev: str) -> bool:
    return bool(re.search(r"[.!?”’\"')\]]\s*$", prev.strip())) or prev.strip().isdigit()


_SKIP_BOOKS = re.compile(r"^(introduction|glossary|preface|contents|table of contents|index|foreword|appendix)$", re.I)
_MARKER = re.compile(r"(?<![\w.,:;/\-–—’'])(\d{1,4})(?=\s|$|[“\"‘'(\[⌈<A-Z])")
_MARKER_LINESTART = re.compile(r"^\s*(\d{1,4})(?!\d)")


def _parse_book(title: str, lines: list[str]) -> list[Verse]:
    out: list[Verse] = []
    chapter = 0
    verse = 0
    buf: list[str] = []
    # Short books (Susanna, Letter of Jeremiah…) often have no chapter numbers at all: treat as chapter 1.
    if not any(_is_chapter_marker(lines, i, expected=1) is not None for i in range(len(lines))):
        chapter = 1

    def flush() -> None:
        nonlocal buf
        if chapter and verse and buf:
            t = _clean(" ".join(buf))
            if t:
                out.append(Verse(title, chapter, verse, t))
        buf = []

    def find_marker(ln: str, pos: int):
        """Next verse number (or a chapter number glued to verse 1, e.g. '291 Now…') in this line."""
        cands = []
        if pos == 0:
            cand = _MARKER_LINESTART.match(ln)
            if cand:
                cands.append(cand)
            elif verse == 0:
                lm = re.match(r"^\s*[lI]\.(?=\s)", ln)
                if lm:
                    return "verse", lm
        cands.extend(_MARKER.finditer(ln, pos))
        for cand in cands:
            g = cand.group(1)
            if int(g) == verse + 1:
                return "verse", cand
            if verse >= 1 and chapter >= 1 and g == f"{chapter + 1}1":
                return "chapter", cand
        return None, None

    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue
        cm = _is_chapter_marker(lines, i, expected=chapter + 1)
        if cm is not None:
            flush()
            chapter, verse = cm, 0
            continue
        if re.match(r"^Book \d+$", stripped):  # Psalms "Book 1" dividers
            continue
        if chapter == 0:
            continue  # subtitle/intro text before chapter 1
        pos = 0
        while True:
            kind, m = find_marker(ln, pos)
            if not m:
                buf.append(ln[pos:])
                break
            buf.append(ln[pos:m.start()])
            flush()
            if kind == "chapter":
                chapter += 1
                verse = 1
            else:
                verse += 1
            pos = m.end()
    flush()
    return out


def _load_pdf(path: str, progress: Progress) -> list[Verse]:
    text = _pdf_text(path, progress)
    _tick(progress, "Finding books and verses…", 0.7)
    lines = text.split("\n")
    heads = _find_headings(lines)
    verses: list[Verse] = []
    for idx, (start, title) in enumerate(heads):
        if _SKIP_BOOKS.match(title):
            continue
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        verses.extend(_parse_book(title, lines[start + 1:end]))
        _tick(progress, f"Reading {title}…", 0.7 + 0.28 * (idx + 1) / max(len(heads), 1))
    # If the layout was not recognised, fall back to plain passages so search still works.
    parsed_chars = sum(len(v.text) for v in verses)
    if len(verses) < 5 or parsed_chars < 0.3 * len(text):
        _tick(progress, "Unfamiliar layout — indexing as plain text", 0.9)
        verses = _chunk_text(text, label="PDF")
    _tick(progress, "Done", 1.0)
    return verses
