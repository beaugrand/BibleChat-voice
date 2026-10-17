"""Matthew Henry's Concise Commentary and Easton's Bible Dictionary (both public domain).

Data: bibleask/data/mhcc.json.gz and easton.json.gz, built by packaging/build_henry_easton.py.
"""
from __future__ import annotations

import gzip
import json
import os
import threading
from typing import Optional

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Capitalised words that are in Easton's but appear on nearly every page: not marked in the text.
NOT_MARKED = {"god", "lord", "jesus", "christ", "spirit", "holy", "ghost", "father", "son", "i", "o", "amen"}


class _Lazy:
    def __init__(self, name: str) -> None:
        self.path = os.path.join(_DIR, name)
        self._lock = threading.Lock()
        self._d = None

    def available(self) -> bool:
        return os.path.exists(self.path)

    def data(self):
        with self._lock:
            if self._d is None:
                with gzip.open(self.path, "rt", encoding="utf-8") as f:
                    self._d = json.load(f)
            return self._d


class Henry(_Lazy):
    def __init__(self) -> None:
        super().__init__("mhcc.json.gz")

    def for_verse(self, book: str, chapter: int, verse: int) -> Optional[dict]:
        """The note on the passage this verse belongs to (notes start at a passage's first verse)."""
        if not self.available():
            return None
        d = self.data()
        try:
            i = d["books"].index(book)
        except ValueError:
            return None
        for v in range(verse, 0, -1):
            t = d["notes"].get(f"{i}.{chapter}.{v}")
            if t:
                return {"from_verse": v, "text": t}
        return None


class Easton(_Lazy):
    def __init__(self) -> None:
        super().__init__("easton.json.gz")

    def names(self) -> list[str]:
        """Headwords worth marking in the text: one capitalised word each (names and places)."""
        if not self.available():
            return []
        return sorted(k for k, (name, _t) in self.data().items()
                      if k.isalpha() and len(k) > 2 and k not in NOT_MARKED and name[:1].isupper())

    def entry(self, term: str) -> Optional[dict]:
        if not self.available():
            return None
        e = self.data().get((term or "").strip().lower())
        return {"term": e[0], "text": e[1]} if e else None


HENRY = Henry()
EASTON = Easton()
