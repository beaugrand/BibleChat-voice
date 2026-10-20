"""Verse numbers of the Septuagint Bibles in King James numbering (bibleask/data/versemap.json, made by
packaging/build_versemap.py). Strong's numbers, cross-references, Scofield and Matthew Henry follow the King James
numbering; the Septuagint's Psalm 22 is the King James Psalm 23. Without this map a Septuagint reader would see the
notes of another verse. A verse with no clear King James match gets None, and no study notes are shown for it."""
from __future__ import annotations

import json
import os
import threading
from typing import Optional

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "versemap.json")
_lock = threading.Lock()
_d: Optional[dict] = None
_rev: dict = {}
_none: dict = {}
PREFIX = {"LXX2012 - ": "eng-lxx2012", "BRENTON - ": "eng-Brenton"}   # library names of the two Septuagint Bibles


def data() -> dict:
    global _d
    with _lock:
        if _d is None:
            try:
                with open(_DATA, encoding="utf-8") as f:
                    _d = json.load(f)
            except OSError:
                _d = {"none": {}}
            for key in PREFIX.values():
                _none[key] = set(_d.get("none", {}).get(key, []))
                rev: dict = {}
                for book, m in _d.get(key, {}).items():
                    for src, kjv in m.items():
                        rev[(book, kjv)] = src
                _rev[key] = rev
        return _d


def key_for(bible_name: str) -> Optional[str]:
    """'LXX2012 - Septuagint in modern English (LXX2012)' -> 'eng-lxx2012'; other Bibles -> None (same numbers)."""
    for p, k in PREFIX.items():
        if (bible_name or "").startswith(p) or bible_name == k:
            return k
    return None


def to_kjv(key: Optional[str], book: str, ch: int, v: int) -> Optional[tuple[int, int]]:
    if not key:
        return ch, v
    d = data()
    if f"{book} {ch}:{v}" in _none.get(key, ()):
        return None
    m = d.get(key, {}).get(book, {}).get(f"{ch}:{v}")
    return tuple(int(x) for x in m.split(":")) if m else (ch, v)


def from_kjv(key: Optional[str], book: str, ch: int, v: int) -> Optional[tuple[int, int]]:
    """The Septuagint verse that stands where the King James has book ch:v (None if it has none)."""
    if not key:
        return ch, v
    data()
    src = _rev.get(key, {}).get((book, f"{ch}:{v}"))
    if src:
        return tuple(int(x) for x in src.split(":"))
    if to_kjv(key, book, ch, v) == (ch, v):
        return ch, v
    return None
