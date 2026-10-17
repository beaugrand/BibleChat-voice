"""Scofield Reference Notes (C. I. Scofield, 1917 edition; public domain): short study notes on many verses,
strong on prophecy (Daniel, Revelation). Data: bibleask/data/scofield.json.gz, built by
packaging/build_scofield.py from the CrossWire SWORD module "Scofield"."""
from __future__ import annotations

import gzip
import json
import os
import threading
from typing import Optional

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scofield.json.gz")


class Scofield:
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

    def note(self, book: str, chapter: int, verse: int) -> Optional[str]:
        if not self.available():
            return None
        d = self._load()
        i = self._num.get(book)
        return None if i is None else d["notes"].get(f"{i}.{chapter}.{verse}")

    def verses_with_notes(self, book: str, chapter: int) -> list[int]:
        """The verses of a chapter that carry a note (so the panel can point to them)."""
        if not self.available():
            return []
        d = self._load()
        i = self._num.get(book)
        if i is None:
            return []
        pre = f"{i}.{chapter}."
        return sorted(int(k[len(pre):]) for k in d["notes"] if k.startswith(pre))


SCOFIELD = Scofield()
