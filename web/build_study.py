"""Builds the study data for the phone version: Strong's numbers (KJV word by word, Hebrew/Greek dictionary,
every verse with a word) and Nave's topics, split into small files the phone loads only when needed.

    data/study/books.json          ["Genesis", ..., "Revelation"]   (book numbers used below)
    data/study/kjv/<book#>.json    {"3:16": [text | [words, "G25"], ...], ...}
    data/study/dict/<H|G><n//500>.json   {"G25": {w, t, p, d, k}, ...}
    data/study/where/<H|G><n//100>.json  {"G25": [[book#, ch, v, "loved"], ...], ...}
    data/study/topics.json         [[title, [[book#, ch, v1, v2], ...]], ...]

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
    rows = TOPICS._load()
    from bibleask.topics import TopicHit
    dump(os.path.join(base, "topics.json"),
         [[TopicHit(t, h, refs, 0).title, [[num[b], c, v1, v2] for b, c, v1, v2 in refs if b in num]]
          for t, h, refs, _a, _b in rows])
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(base) for f in fs)
    nfiles = sum(len(fs) for _, _, fs in os.walk(base))
    print(f"study data: {nfiles} files, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
