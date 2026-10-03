"""Several Bibles at once: keep each one parsed and indexed so a chat can search any combination."""
from __future__ import annotations

import os
import tempfile
import threading
from typing import Callable, Optional

from . import storage
from .loaders import Bible, load_bible
from .search import Index

Progress = Optional[Callable[[str, float], None]]


class Library:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[Bible, Index]] = {}
        self._lock = threading.Lock()

    def ids(self) -> list[str]:
        return storage.list_bibles()

    def get(self, bible_id: str) -> tuple[Bible, Index]:
        with self._lock:
            if bible_id not in self._cache:
                b = storage.open_bible(bible_id)
                self._cache[bible_id] = (b, Index(b))
            return self._cache[bible_id]

    def summary(self) -> list[dict]:
        out = []
        for bid in self.ids():
            try:
                b, _ = self.get(bid)
            except Exception:  # a damaged file should not break the whole list
                continue
            out.append({"id": bid, "name": b.name, "verses": len(b.verses),
                        "books": len({v.book for v in b.verses})})
        return out

    def add_file(self, filename: str, data: bytes, progress: Progress = None) -> str:
        ext = os.path.splitext(filename)[1].lower() or ".txt"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            bible = load_bible(tmp, progress=progress)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        bible.name = os.path.splitext(os.path.basename(filename))[0] or bible.name
        slug = storage.save_bible(bible)
        with self._lock:
            self._cache[slug] = (bible, Index(bible))
        return slug

    def remove(self, bible_id: str) -> None:
        with self._lock:
            self._cache.pop(bible_id, None)
        storage.remove_bible(bible_id)
