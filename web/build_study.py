"""Builds the study data for the phone version: Strong's numbers (KJV word by word, Hebrew/Greek dictionary,
every verse with a word) and Nave's topics, split into small files the phone loads only when needed.

    data/study/books.json          ["Genesis", ..., "Revelation"]   (book numbers used below)
    data/study/kjv/<book#>.json    {"3:16": [text | [words, "G25"], ...], ...}
    data/study/dict/<H|G><n//500>.json   {"G25": {w, t, p, d, k}, ...}
    data/study/where/<H|G><n//100>.json  {"G25": [[book#, ch, v, "loved"], ...], ...}
    data/study/topics.json         [[title, [[book#, ch, v1, v2], ...]], ...]
    data/study/scofield/<book#>.json   {"1:20": "note text", ...}   (Scofield Reference Notes, 1917)
    data/study/henry/<book#>.json  {"7:9": "note on the passage from 7:9", ...}  (Matthew Henry, Concise)
    data/study/easton/names.json   names marked in the text; easton/<letter>.json {"babylon": ["Babylon", text]}
    data/study/xref/<book#>.json   {"7:13": [[book#, ch, v, ch2, v2, votes], ...], ...}   (OpenBible.info, CC-BY)
    data/study/orig/<book#>.json   {"1:1": "בְּרֵאשִׁית…", "4:1": ["…", "3:19"]}  (Hebrew WLC / Greek TR line; Hebrew number if different)
    data/study/versemap.json       Septuagint verse numbers in King James numbering (bibleask/versemap.py)
    data/study/gloss.json          English words -> the Hebrew/Greek words that mean them (bibleask/strongs.py)
    data/meaning/                  the meaning model and verse fingerprints (bibleask/data/meaning, copied as is)

Usage:  python web/build_study.py OUT_DIR
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bibleask.loaders import PROTESTANT_BOOKS  # noqa: E402
from bibleask.strongs import STRONGS  # noqa: E402
from bibleask.topics import TOPICS  # noqa: E402


def dump(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def main(out: str) -> None:
    base = os.path.join(out, "data", "study")
    books = list(PROTESTANT_BOOKS)
    num = {b: i for i, b in enumerate(books)}
    dump(os.path.join(base, "books.json"), books)
    STRONGS._load()
    per_book: dict = defaultdict(dict)
    for (b, c, v), seg in STRONGS._verses.items():
        if b in num:
            per_book[num[b]][f"{c}:{v}"] = seg
    for i, d in per_book.items():
        dump(os.path.join(base, "kjv", f"{i}.json"), d)
    dicts: dict = defaultdict(dict)
    for n, e in STRONGS._dict.items():
        dicts[n[0] + str(int(n[1:]) // 500)][n] = e
    for k, d in dicts.items():
        dump(os.path.join(base, "dict", k + ".json"), d)
    where: dict = defaultdict(dict)
    for n, uses in STRONGS._where.items():
        where[n[0] + str(int(n[1:]) // 100)][n] = [[num[b], c, v, w] for (b, c, v), w in uses if b in num]
    for k, d in where.items():
        dump(os.path.join(base, "where", k + ".json"), d)
    from bibleask.xref import XREFS
    xd = XREFS._load()
    assert xd["books"] == books
    per: dict = defaultdict(dict)
    for key, links in xd["refs"].items():
        b, c, v = key.split(".")
        per[int(b)][f"{c}:{v}"] = links
    for i, d in per.items():
        dump(os.path.join(base, "xref", f"{i}.json"), d)
    from bibleask.scofield import SCOFIELD
    sd = SCOFIELD._load()
    assert sd["books"] == books
    per_s: dict = defaultdict(dict)
    for key, text in sd["notes"].items():
        b, c, v = key.split(".")
        per_s[int(b)][f"{c}:{v}"] = text
    for i, d in per_s.items():
        dump(os.path.join(base, "scofield", f"{i}.json"), d)
    from bibleask.henry_easton import EASTON, HENRY
    hd = HENRY.data()
    assert hd["books"] == books
    per_h: dict = defaultdict(dict)
    for key, text in hd["notes"].items():
        b, c, v = key.split(".")
        per_h[int(b)][f"{c}:{v}"] = text
    for i, d in per_h.items():
        dump(os.path.join(base, "henry", f"{i}.json"), d)
    dump(os.path.join(base, "easton", "names.json"), EASTON.names())
    by_letter: dict = defaultdict(dict)
    for k, v in EASTON.data().items():
        by_letter[k[0] if k[0].isalpha() else "_"][k] = v
    for letter, d in by_letter.items():
        dump(os.path.join(base, "easton", f"{letter}.json"), d)
    rows = TOPICS._load()
    from bibleask.topics import TopicHit
    dump(os.path.join(base, "topics.json"),
         [[TopicHit(t, h, refs, 0).title, [[num[b], c, v1, v2] for b, c, v1, v2 in refs if b in num]]
          for t, h, refs, _a, _b in rows])
    from bibleask.original import book_file
    for i, b in enumerate(books):
        o = book_file(b)
        if o:
            dump(os.path.join(base, "orig", f"{i}.json"), o)
    shutil_copy = __import__("shutil").copyfile
    shutil_copy(os.path.join(ROOT, "bibleask", "data", "versemap.json"), os.path.join(base, "versemap.json"))   # Septuagint numbers
    from bibleask.strongs import COMMON, VERSES
    gi = STRONGS.gloss_index()
    dump(os.path.join(base, "gloss.json"), dict(gi, common=sorted(COMMON), verses=VERSES))
    import shutil
    src = os.path.join(ROOT, "bibleask", "data", "meaning")
    with open(os.path.join(src, "verses.json"), encoding="utf-8") as f:
        assert json.load(f)["books"] == books
    shutil.copytree(src, os.path.join(out, "data", "meaning"), dirs_exist_ok=True)
    # 📜 Study Paths: the paths built by packaging/build_paths.py, their page code and "Quoted or named in Scripture"
    web = os.path.join(ROOT, "web")
    for f in ("paths.js", "quoted.json", "prayers.js", "prayers.json"):   # 🙏 Prayers ride along with the Study Paths
        shutil.copy2(os.path.join(web, f), os.path.join(out, f))
    shutil.copytree(os.path.join(web, "paths"), os.path.join(out, "paths"), dirs_exist_ok=True)
    # ↗ short share pages with their own preview: p/<id>/, series/<id>/, pray/<id>/ (web/build_share.py)
    sys.path.insert(0, web)
    from build_share import write_share_pages
    print(f"share pages: {len(write_share_pages(out, web))}")
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(base) for f in fs)
    nfiles = sum(len(fs) for _, _, fs in os.walk(base))
    print(f"study data: {nfiles} files, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
