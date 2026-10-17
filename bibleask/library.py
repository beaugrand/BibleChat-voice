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


def _catalog_language(name: str) -> str:
    """The language of a Bible downloaded from the free catalog (empty for the person's own files)."""
    from . import catalog
    for e in catalog.entries():
        if e["name"] == name:
            return e["language"]
    return ""


_BOOKNAMES: Optional[dict] = None


def book_names(bible_id: str) -> dict:
    """Book names in the Bible's own language ("1. Mose" for Genesis), by English name; empty for English."""
    global _BOOKNAMES
    if _BOOKNAMES is None:
        import json
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "booknames.json"), encoding="utf-8") as f:
                _BOOKNAMES = json.load(f)
        except OSError:
            _BOOKNAMES = {}
    bid = bible_id.lower()
    key = "chi-simp" if bid.startswith("chi-") and "simp" in bid else bid.split("-")[0].split(".")[0]
    return _BOOKNAMES.get(key, {})


class Library:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[Bible, Index]] = {}
        self._lookup: dict[str, dict] = {}
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
                        "books": len({v.book for v in b.verses}),
                        "language": _catalog_language(b.name)})
        return out

    # ---- reading view -----------------------------------------------------------------
    def books(self, bible_id: str) -> list[dict]:
        """Books in file order, each with its chapter numbers."""
        b, _ = self.get(bible_id)
        order: dict[str, list[int]] = {}
        for v in b.verses:
            chs = order.setdefault(v.book, [])
            if not chs or chs[-1] != v.chapter:
                if v.chapter not in chs:
                    chs.append(v.chapter)
        local = book_names(bible_id)
        return [{"name": k, "chapters": sorted(c), **({"local": local[k]} if local.get(k) else {})} for k, c in order.items()]

    def chapter(self, bible_id: str, book: str, chapter: int) -> dict:
        """All verses of one chapter (long verses that were split for search are joined again),
        plus the chapters before and after it."""
        b, _ = self.get(bible_id)
        verses: list[dict] = []
        for v in b.verses:
            if v.book == book and v.chapter == chapter:
                if verses and verses[-1]["verse"] == v.verse:
                    verses[-1]["text"] += " " + v.text
                else:
                    verses.append({"verse": v.verse, "text": v.text})
        seq = [(bk["name"], c) for bk in self.books(bible_id) for c in bk["chapters"]]
        try:
            i = seq.index((book, chapter))
        except ValueError:
            raise ValueError(f"{book} {chapter} isn't in this Bible.")
        nav = lambda j: {"book": seq[j][0], "chapter": seq[j][1]} if 0 <= j < len(seq) else None
        return {"bible": b.name, "book": book, "chapter": chapter, "verses": verses,
                "prev": nav(i - 1), "next": nav(i + 1)}

    def verse_text(self, bible_id: str, book: str, chapter: int, verse: int) -> Optional[str]:
        """One verse of one Bible (None if that Bible doesn't have it)."""
        b, _ = self.get(bible_id)
        with self._lock:
            look = self._lookup.get(bible_id)
            if look is None:
                look = {}
                for v in b.verses:
                    k = (v.book, v.chapter, v.verse)
                    look[k] = look[k] + " " + v.text if k in look else v.text
                self._lookup[bible_id] = look
        return look.get((book, chapter, verse))

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
            self._lookup.pop(bible_id, None)
        storage.remove_bible(bible_id)
