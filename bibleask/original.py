"""The original-language line of a verse: Hebrew (Westminster Leningrad Codex) for the Old Testament, Greek
(Textus Receptus) for the New, both public domain. Data: bibleask/data/original.json.gz, made by
packaging/build_original.py, keyed by the King James book, chapter and verse. Where the Hebrew numbers a verse
differently (Malachi 4:1 is Hebrew Malachi 3:19), the Hebrew number comes along; verses that couldn't be lined up
with confidence have no line at all, so a line is never shown under the wrong verse."""
from __future__ import annotations

import gzip
import json
import os
import threading
from typing import Optional

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "original.json.gz")
_lock = threading.Lock()
_d: Optional[dict] = None


def data() -> dict:
    global _d
    with _lock:
        if _d is None:
            if os.path.exists(_DATA):
                with gzip.open(_DATA, "rt", encoding="utf-8") as f:
                    _d = json.load(f)
            else:
                _d = {"wlc": {}, "tr": {}, "moved": {"wlc": {}, "tr": {}}, "sources": {}}
        return _d


def line(book: str, ch: int, v: int) -> Optional[dict]:
    """{"text", "language", "source", "number"} or None. "number" is the original's own verse number."""
    d = data()
    for kind, lang in (("wlc", "Hebrew"), ("tr", "Greek")):
        t = d[kind].get(book, {}).get(f"{ch}:{v}")
        if t:
            return {"text": t, "language": lang, "source": d["sources"].get(kind, {}).get("name", ""),
                    "number": d["moved"].get(kind, {}).get(f"{book} {ch}:{v}", f"{ch}:{v}")}
    return None


def book_file(book: str) -> dict:
    """{"c:v": text or [text, "Hebrew c:v"]} for one book, the shape the phone's data/study/orig/<book#>.json has."""
    d = data()
    out = {}
    for kind in ("wlc", "tr"):
        moved = d["moved"].get(kind, {})
        for cv, t in d[kind].get(book, {}).items():
            m = moved.get(f"{book} {cv}")
            out[cv] = [t, m] if m else t
    return out
