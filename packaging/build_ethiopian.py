"""Builds bibles/eng-ethiopian-canon.zefania.xml: the books of the Ethiopian Orthodox Tewahedo canon that
exist in a public-domain English translation, in the order of the Ethiopian Bible.

Sources (all public domain):
  World English Bible (eng-web.usfx.xml from open-bibles): the 66 books and the deuterocanon
  R. H. Charles: 1 Enoch (1917) and Jubilees (1917); W. R. Morfill / R. H. Charles: 2 Enoch (1896)
  Roberts & Donaldson, Ante-Nicene Fathers vol. 1 (1885): 1 Clement
The last four as transcribed by the Scrollmapper project
(https://github.com/scrollmapper/bible_databases_deuterocanonical).

Not included, because no public-domain English translation is available: Meqabyan I-III and
4 Baruch (Paralipomena of Jeremiah).

    python packaging/build_ethiopian.py eng-web.usfx.xml SCROLLMAPPER_CLONE
"""
from __future__ import annotations

import json
import os
import re
import sys
from xml.sax.saxutils import escape, quoteattr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bibleask.loaders import load_bible  # noqa: E402

EXTRA = {   # name in the Ethiopian Bible -> file in the Scrollmapper clone
    "Jubilees": "sources/en/book-of-jubilees/book-of-jubilees.json",
    "1 Enoch": "sources/en/1-enoch/1-enoch.json",
    "2 Enoch": "sources/en/2-enoch/2-enoch.json",
    "1 Clement": "etc/en/church_history/ante-nicene/1-clement/1-clement.json",
}

ORDER = [   # the order of "The Complete Ethiopian Bible"; WEB's names where the book comes from the WEB
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Prayer of Manasseh",
    "Jubilees", "1 Enoch", "2 Enoch", "Ezra", "Nehemiah", "1 Esdras", "2 Esdras", "Tobit", "Judith",
    "Esther", "Esther (Greek)", "Job", "Psalms", "Psalm 151", "Proverbs", "Wisdom", "Ecclesiastes",
    "Song of Solomon", "Sirach", "Isaiah", "Jeremiah", "Lamentations", "Baruch", "Letter of Jeremiah",
    "Ezekiel", "Daniel", "Prayer of Azariah", "Susanna", "Bel and the Dragon",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy",
    "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation", "1 Clement",
]


def clean(t: str) -> str:
    t = t.replace("\x91", "‘").replace("\x92", "’")
    t = re.sub(r"\*\*\[\d+:\d+\]\*\*", " ", t)          # a verse marker left inside another verse
    t = re.sub(r"[†⌈⌉⌊⌋*]", "", t)                       # editor's marks
    return re.sub(r"\s+", " ", t).strip()


def _heading(t: str) -> bool:
    """'Chapter IV.', '—The Salutation.', 'Praise of the Corinthians ...': section titles, not text."""
    if re.fullmatch(r"Chapter [IVXLC]+\.?", t) or t.startswith("—"):
        return True
    words = [w for w in re.findall(r"[A-Za-z]+", t) if len(w) > 3]
    return bool(words) and len(t) < 120 and sum(w[0].isupper() for w in words) / len(words) > 0.7


# 1 Enoch 44 (a single verse in Charles 1917) is missing from the Scrollmapper transcription
ADD = {"1 Enoch": [(44, 1, "Also another phenomenon I saw in regard to the lightnings: how some of the stars "
                           "arise and become lightnings and cannot part with their new form.")]}


def extra_book(path: str, title_lines: bool) -> list[tuple[int, int, str]]:
    d = json.load(open(path, encoding="utf-8"))
    out = list(ADD.get(d["books"][0]["name"].replace("I Enoch", "1 Enoch"), []))
    for ch in d["books"][0]["chapters"]:
        vs = [(v["verse"], clean(v["text"])) for v in ch["verses"]]
        if title_lines:   # 1 Clement: the translator's chapter titles were numbered as verses; drop and renumber
            while vs and _heading(vs[0][1]):
                vs.pop(0)
            vs = [(i, t) for i, (_n, t) in enumerate(vs, 1)]
        out += [(ch["chapter"], n, t) for n, t in vs if t]
    return sorted(out)   # Charles moves 1 Enoch 91:12-17 after 93; keep the usual numbered order


def main(web_file: str, sm: str, out: str) -> None:
    web = load_bible(web_file)
    books: dict[str, list] = {}
    for v in web.verses:
        books.setdefault(v.book, []).append((v.chapter, v.verse, v.text))
    books["Psalm 151"] = [(1, vn, t) for _c, vn, t in books["Psalm 151"]]   # WEB numbers it as chapter 151
    for name, rel in EXTRA.items():
        books[name] = extra_book(os.path.join(sm, rel), name == "1 Clement")
    missing = [b for b in ORDER if b not in books]
    assert not missing, missing
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             '<XMLBIBLE biblename="Ethiopian Canon (public-domain English)" type="x-bible">',
             "<INFORMATION><title>Ethiopian Canon (public-domain English)</title>"
             "<description>84 books of the Ethiopian Orthodox Tewahedo canon in public-domain English: "
             "World English Bible; R. H. Charles (1 Enoch, Jubilees); Morfill/Charles (2 Enoch); "
             "Ante-Nicene Fathers (1 Clement). Meqabyan I-III and 4 Baruch are not included.</description>"
             "<rights>Public Domain</rights></INFORMATION>"]
    total = 0
    for i, name in enumerate(ORDER, 1):
        parts.append(f"<BIBLEBOOK bnumber=\"{i}\" bname={quoteattr(name)}>")
        cur = None
        for ch, vn, text in books[name]:
            if ch != cur:
                if cur is not None:
                    parts.append("</CHAPTER>")
                parts.append(f'<CHAPTER cnumber="{ch}">')
                cur = ch
            parts.append(f'<VERS vnumber="{vn}">{escape(text)}</VERS>')
            total += 1
        parts.append("</CHAPTER></BIBLEBOOK>")
    parts.append("</XMLBIBLE>")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"{len(ORDER)} books, {total} verses -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else
         os.path.join(ROOT, "bibles", "eng-ethiopian-canon.zefania.xml"))
