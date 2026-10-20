"""Builds bibleask/data/original.json.gz: the original-language line of every verse, for "Look closer".

Sources (both public domain, from eBible.org):
  Westminster Leningrad Codex, Hebrew Old Testament (hboWLC_usfx.zip). The WLC text is public domain.
  Greek Textus Receptus New Testament (grctr_usfx.zip): collated from Stephanus 1550, Elzevir 1624 and
  Scrivener 1881, with the manuscript notes Adam Boyd dedicated to the public domain.

The Hebrew Bible numbers some verses differently from the King James (Malachi 4 is Hebrew Malachi 3:19-24,
many Psalm titles are a verse of their own). A line must never be shown under the wrong verse, so this script
lines each King James verse up with the Hebrew/Greek verse that has its words: it takes the Strong's words of the
KJV verse (bibleask/data/strongs_kjv.json.gz), looks for their Hebrew/Greek dictionary forms in the verses around
the same number, and keeps the one that matches clearly best. Verses it can't place with confidence are left out
(the app then shows no original line for them) and counted in the summary.

    python packaging/build_original.py [FOLDER_WITH_THE_TWO_ZIPS]   (downloads them if not given)

Output: {"wlc": {"Genesis": {"1:1": "בְּרֵאשִׁית ...", ...}, ...}, "tr": {...}, "moved": {"wlc": {"Malachi 4:1": "3:19"}},
         "sources": {...}}   keyed by the King James book, chapter and verse.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import tempfile
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "bibleask", "data", "original.json.gz")
FILES = {"wlc": "hboWLC_usfx.zip", "tr": "grctr_usfx.zip"}
URL = "https://ebible.org/Scriptures/"
SOURCES = {
    "wlc": {"name": "Westminster Leningrad Codex (Hebrew Old Testament)", "license": "Public domain",
            "from": "https://ebible.org/hboWLC/copyright.htm"},
    "tr": {"name": "Greek Textus Receptus New Testament (Stephanus 1550, Elzevir 1624, Scrivener 1881 collated)",
           "license": "Public domain", "from": "https://ebible.org/grctr/copyright.htm"},
}
FINAL = str.maketrans("ךםןףץ", "כמנפצ")
SKIP = {"H853", "H5921", "H413", "H834", "H3588", "H3605", "H5973", "H4480", "H3808", "H1961", "H559", "H3651",
        "G3588", "G2532", "G1161", "G846", "G1722", "G1519", "G3754", "G1063", "G3756", "G1510", "G3739"}


def heb(s: str) -> str:
    """Hebrew consonants only: no vowel points or accents, final letters as normal letters."""
    s = re.sub(r"[֑-ׇ]", lambda m: " " if m.group() in "־׀׃" else "", s)
    return s.translate(FINAL)


def grk(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).replace("ς", "σ")


def load(path: str) -> dict:
    from bibleask import catalog
    from bibleask.loaders import load_bible
    with open(path, "rb") as f:
        _inner, data = catalog.unpack(os.path.basename(path), f.read())
    xml = path[:-4] + ".usfx.xml"
    with open(xml, "wb") as f:
        f.write(data)
    d: dict = {}
    for v in load_bible(xml).verses:
        k = (v.book, v.chapter, v.verse)
        d[k] = d[k] + " " + v.text if k in d else v.text
    return d


def lemmas(seg, kind: str, strongs) -> list[str]:
    out = []
    for s in seg:
        if isinstance(s, str):
            continue
        for n in s[1].split():
            if not re.fullmatch(r"[HG]\d+", n) or n in SKIP or n[0] != ("H" if kind == "wlc" else "G"):
                continue
            e = strongs._dict.get(n)
            if not e:
                continue
            forms = [heb(w).replace(" ", "") for w in e["w"].split()] if kind == "wlc" else [grk(e["w"])[:4]]
            forms = [f for f in forms if len(f) >= 2]
            if forms:
                out.append(forms)
    return out


def score(lem: list, text: str) -> float:
    if not lem:
        return 0.0
    return sum(1 for forms in lem if any(f in text for f in forms)) / len(lem)


def align(kind: str, orig: dict, strongs) -> tuple[dict, dict, int, int]:
    """Place each KJV verse. An offset (chapters, verses) is accepted only when it is clear: the verse's own best
    match, backed by a neighbour that moved the same way (renumbered verses come in blocks: Malachi 4 = Hebrew
    Malachi 3:19-24), or, for a verse that matches several places equally (a formula such as "And the LORD spake
    unto Moses, saying"), the offset both its neighbours agree on."""
    norm = heb if kind == "wlc" else grk
    by_book: dict = {}
    for (b, c, v), t in orig.items():
        by_book.setdefault(b, {})[(c, v)] = norm(t)
    chapters: dict = {}
    for (b, c, v) in orig:
        chapters.setdefault((b, c), []).append((c, v))
    info: dict = {}     # (book, c, v) -> {offset: score}, best offset, ambiguous?
    for (b, c, v), seg in strongs._verses.items():
        o = by_book.get(b)
        if not o:
            continue
        lem = lemmas(seg, kind, strongs)
        if not lem:
            continue
        cands = chapters.get((b, c - 1), []) + chapters.get((b, c), []) + chapters.get((b, c + 1), [])
        sc = {(k[0] - c, k[1] - v): score(lem, o[k]) for k in cands}
        if not sc:
            continue
        top = max(sc.values())
        best = min((off for off, x in sc.items() if x == top), key=lambda off: (off != (0, 0), abs(off[0]), abs(off[1])))
        info[(b, c, v)] = (sc, best, top, sum(1 for x in sc.values() if x >= top - 0.05) > 1)

    def own(key):   # the verse's own clear offset, or None
        x = info.get(key)
        if not x:
            return None
        sc, best, top, amb = x
        return best if top >= 0.5 and not amb else None

    def near(b, c, v, step):   # the nearest clear offset before (step -1) or after (+1) in the chapter
        for d in range(1, 6):
            k = (b, c, v + step * d)
            if k not in info:
                return None
            o = own(k)
            if o is not None:
                return o
        return None

    out: dict = {}
    moved: dict = {}
    placed = unsure = 0
    for (b, c, v), (sc, best, top, amb) in info.items():
        me, P, N = own((b, c, v)), near(b, c, v, -1), near(b, c, v, 1)
        place = None
        if kind == "tr":
            # the Greek New Testament numbers its verses like the King James: keep the number when the words agree
            place = (0, 0) if sc.get((0, 0), 0) >= 0.34 else None
        elif me == (0, 0):
            place = me
        elif me is not None:
            if me in (P, N):
                place = me           # part of a renumbered block
            elif sc.get((0, 0), 0) >= 0.5 and P in ((0, 0), None) and N in ((0, 0), None):
                place = (0, 0)       # a lone jump: more likely a chance match than a renumbering
        else:
            # several places match equally (a formula such as "And the LORD spake unto Moses, saying"):
            # follow the clear verses around it
            O = P if P == N else (P if N is None else N if P is None else None)
            if O is not None and sc.get(O, 0) >= max(0.34, top - 0.05):
                place = O
        if place is None:
            unsure += 1
            continue
        tc, tv = c + place[0], v + place[1]
        if (b, tc, tv) not in orig:
            unsure += 1
            continue
        placed += 1
        out.setdefault(b, {})[f"{c}:{v}"] = orig[(b, tc, tv)]
        if place != (0, 0):
            moved[f"{b} {c}:{v}"] = f"{tc}:{tv}"
    return out, moved, placed, unsure


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else tempfile.gettempdir()
    from bibleask.strongs import STRONGS
    STRONGS._load()
    result = {"sources": SOURCES, "moved": {}, "unsure": {}}
    for kind, file in FILES.items():
        path = os.path.join(folder, file)
        if not os.path.exists(path):
            from bibleask.llm import _open
            print("downloading", file, flush=True)
            with _open(URL + file) as r, open(path, "wb") as f:
                f.write(r.read())
        out, moved, placed, unsure = align(kind, load(path), STRONGS)
        result[kind], result["moved"][kind], result["unsure"][kind] = out, moved, unsure
        print(f"{kind}: {placed} verses placed, {len(moved)} under a different number, {unsure} left out", flush=True)
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(OUT, os.path.getsize(OUT) // 1000, "kB")


if __name__ == "__main__":
    main()
