"""The phone's study data files, made on request for the computer's 📜 Study Paths.

web/build_study.py writes these as small JSON files for the phone (data/study/...). The computer has the same data
in memory, so the local server answers /api/sdata/<file> with the same slice. Both versions then run the same
web/paths.js. Files: books.json, kjv/<book#>.json, dict/<H|G><n//500>.json, where/<H|G><n//100>.json,
xref/<book#>.json, scofield/<book#>.json, henry/<book#>.json, orig/<book#>.json.
"""
from __future__ import annotations

import re
import threading
from collections import defaultdict
from typing import Optional

from .loaders import PROTESTANT_BOOKS

_lock = threading.Lock()
_cache: dict = {}


def _per_book(kind: str) -> dict:
    """{book#: {"c:v": value}} for kjv, xref, scofield and henry, built once."""
    with _lock:
        if kind in _cache:
            return _cache[kind]
        books = list(PROTESTANT_BOOKS)
        num = {b: i for i, b in enumerate(books)}
        per: dict = defaultdict(dict)
        if kind == "kjv":
            from .strongs import STRONGS
            STRONGS._load()
            for (b, c, v), seg in STRONGS._verses.items():
                if b in num:
                    per[num[b]][f"{c}:{v}"] = seg
        else:
            if kind == "xref":
                from .xref import XREFS
                d = XREFS._load()
                items = d["refs"]
            elif kind == "scofield":
                from .scofield import SCOFIELD
                d = SCOFIELD._load()
                items = d["notes"]
            else:
                from .henry_easton import HENRY
                d = HENRY.data()
                items = d["notes"]
            assert d["books"] == books
            for key, val in items.items():
                b, c, v = key.split(".")
                per[int(b)][f"{c}:{v}"] = val
        _cache[kind] = per
        return per


def _strongs(kind: str, key: str) -> dict:
    from .strongs import STRONGS
    STRONGS._load()
    with _lock:
        if (kind, key) in _cache:
            return _cache[(kind, key)]
    letter, part = key[0], int(key[1:])
    if kind == "dict":
        out = {n: e for n, e in STRONGS._dict.items() if n[0] == letter and int(n[1:]) // 500 == part}
    else:
        num = {b: i for i, b in enumerate(PROTESTANT_BOOKS)}
        out = {n: [[num[b], c, v, w] for (b, c, v), w in uses if b in num]
               for n, uses in STRONGS._where.items() if n[0] == letter and int(n[1:]) // 100 == part}
    with _lock:
        _cache[(kind, key)] = out
    return out


def get(path: str) -> Optional[object]:
    """The content of one phone study file, or None if there is no such file."""
    if path == "books.json":
        return list(PROTESTANT_BOOKS)
    if path == "versemap.json":
        from .versemap import data
        return data()
    m = re.fullmatch(r"(kjv|xref|scofield|henry)/(\d{1,2})\.json", path)
    if m:
        i = int(m.group(2))
        return _per_book(m.group(1)).get(i, {}) if i < len(PROTESTANT_BOOKS) else None
    m = re.fullmatch(r"orig/(\d{1,2})\.json", path)
    if m:
        from .original import book_file
        i = int(m.group(1))
        return book_file(PROTESTANT_BOOKS[i]) if i < len(PROTESTANT_BOOKS) else None
    m = re.fullmatch(r"(dict|where)/([HG]\d{1,2})\.json", path)
    if m:
        return _strongs(m.group(1), m.group(2))
    return None
