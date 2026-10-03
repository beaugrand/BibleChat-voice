"""Load a Bible from a PDF, XML (Zefania / OSIS), TXT or our own JSON cache.

Everything ends up as a flat list of Verse records (book, chapter, verse, text),
so the search and AI layers never care what the original file looked like.
"""
from __future__ import annotations

import json
import os
import re
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
    else:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}. Use PDF, XML or TXT.")
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


def _load_xml(path: str, progress: Progress) -> list[Verse]:
    """Zefania XML (BIBLEBOOK/CHAPTER/VERS) and OSIS (<verse osisID="Gen.1.1">)."""
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
