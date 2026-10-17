"""Cross-references: other verses that speak to the same thing.

Data: OpenBible.info cross-references (CC-BY), built into bibleask/data/xref.json.gz by
packaging/build_xref.py. Each link carries readers' votes; the strongest come first.
"""
from __future__ import annotations

import gzip
import json
import os
import threading
from typing import Optional

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "xref.json.gz")


class CrossRefs:
    def __init__(self, path: str = _DATA) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._d: Optional[dict] = None

    def available(self) -> bool:
        return os.path.exists(self.path)

    def _load(self) -> dict:
        with self._lock:
            if self._d is None:
                with gzip.open(self.path, "rt", encoding="utf-8") as f:
                    self._d = json.load(f)
                self._num = {b: i for i, b in enumerate(self._d["books"])}
            return self._d

    @staticmethod
    def _label(book: str, c: int, v: int, c2: int, v2: int) -> str:
        if (c2, v2) == (c, v):
            return f"{book} {c}:{v}"
        return f"{book} {c}:{v}–{v2}" if c2 == c else f"{book} {c}:{v}–{c2}:{v2}"

    def for_verse(self, book: str, chapter: int, verse: int, to_book: Optional[str] = None) -> list[dict]:
        """Links from one verse, strongest first (optionally only those into one book)."""
        if not self.available():
            return []
        d = self._load()
        i = self._num.get(book)
        if i is None:
            return []
        out = []
        for b, c, v, c2, v2, votes in d["refs"].get(f"{i}.{chapter}.{verse}", []):
            name = d["books"][b]
            if to_book and name != to_book:
                continue
            out.append({"ref": self._label(name, c, v, c2, v2), "book": name, "chapter": c, "verse": v,
                        "end_chapter": c2, "end_verse": v2, "votes": votes})
        return out

    def between(self, book_a: str, book_b: str, min_votes: int = 3) -> list[dict]:
        """Every link from book A to book B and from B to A, strongest first, each pair once."""
        if not self.available():
            return []
        d = self._load()
        a, b = self._num.get(book_a), self._num.get(book_b)
        if a is None or b is None:
            return []
        pairs: dict = {}
        for key, links in d["refs"].items():
            fb, fc, fv = (int(x) for x in key.split("."))
            if fb not in (a, b):
                continue
            for tb, c, v, c2, v2, votes in links:
                if votes < min_votes or tb != (b if fb == a else a) or tb == fb:
                    continue
                src = (fb, fc, fv, fc, fv)
                dst = (tb, c, v, c2, v2)
                k = (src, dst) if fb == a else (dst, src)   # always book A first
                pairs[k] = max(votes, pairs.get(k, 0))
        out = []
        for (x, y), votes in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
            out.append({"from": self._label(d["books"][x[0]], *x[1:]), "to": self._label(d["books"][y[0]], *y[1:]),
                        "from_ref": [d["books"][x[0]], x[1], x[2]], "to_ref": [d["books"][y[0]], y[1], y[2], y[3], y[4]],
                        "votes": votes})
        return out


XREFS = CrossRefs()
