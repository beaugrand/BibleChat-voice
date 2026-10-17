"""Study tools for one verse in Read mode: Strong's numbers (the Hebrew/Greek words) and Nave's topics.

Strong's numbers belong to the King James wording, so the word-by-word view always shows the KJV; verse
lists (every verse with a word, every verse of a topic) are shown in the Bible the person is reading,
with the KJV as fallback when that Bible lacks a verse.
"""
from __future__ import annotations

from typing import Optional

from .strongs import STRONGS, normalize
from .topics import TOPICS
from .xref import XREFS
from .scofield import SCOFIELD
from .henry_easton import HENRY, EASTON

MAX_VERSES = 400


def _text(lib, bible_id: str, book: str, ch: int, v: int) -> str:
    t = None
    if bible_id:
        try:
            t = lib.verse_text(bible_id, book, ch, v)
        except Exception:
            t = None
    return t if t is not None else STRONGS.kjv_text(book, ch, v)


def passage_text(lib, bible_id: str, book: str, ch: int, v: int, ch2: int, v2: int, most: int = 3) -> str:
    """A verse, or the first few verses of a passage, in the person's Bible (KJV as fallback)."""
    if ch2 != ch:
        v2 = v + most - 1
    parts = [_text(lib, bible_id, book, ch, n) for n in range(v, min(v2, v + most - 1) + 1)]
    t = " ".join(x for x in parts if x)
    return t + (" …" if v2 > v + most - 1 or ch2 != ch else "")


def xrefs(lib, bible_id: str, book: str, ch: int, v: int, to_book: Optional[str] = None, limit: int = 60) -> list[dict]:
    out = []
    for x in XREFS.for_verse(book, ch, v, to_book)[:limit]:
        x["text"] = passage_text(lib, bible_id, x["book"], x["chapter"], x["verse"], x["end_chapter"], x["end_verse"])
        out.append(x)
    return out


def verse(lib, bible_id: str, book: str, ch: int, v: int) -> dict:
    words = STRONGS.verse(book, ch, v) if STRONGS.available() else []
    return {"ref": f"{book} {ch}:{v}", "book": book, "chapter": ch, "verse": v,
            "words": words, "topics": TOPICS.for_verse(book, ch, v)[:40],
            "xrefs": xrefs(lib, bible_id, book, ch, v),
            "henry": HENRY.for_verse(book, ch, v)}


def chapter_notes(book: str, ch: int) -> dict:
    """Scofield notes of one chapter, by verse number, for marking the words they explain."""
    return {str(v): SCOFIELD.note(book, ch, v) for v in SCOFIELD.verses_with_notes(book, ch)}


def strongs(lib, bible_id: str, number: str) -> Optional[dict]:
    if not STRONGS.available():
        return None
    e = STRONGS.entry(number)
    if not e:
        return None
    uses = STRONGS.verses_with(number)
    e["verses"] = [{"ref": f"{b} {c}:{v}", "book": b, "chapter": c, "verse": v, "kjv_word": w,
                    "text": _text(lib, bible_id, b, c, v)} for (b, c, v), w in uses[:MAX_VERSES]]
    e["more"] = max(0, len(uses) - MAX_VERSES)
    return e


def topic(lib, bible_id: str, topic_id: int) -> Optional[dict]:
    t = TOPICS.get(topic_id)
    if not t:
        return None
    out = []
    for b, c, v1, v2 in t.refs:
        for v in range(v1, v2 + 1):
            out.append({"ref": f"{b} {c}:{v}", "book": b, "chapter": c, "verse": v,
                        "text": _text(lib, bible_id, b, c, v)})
    return {"id": topic_id, "title": t.title, "verses": out[:MAX_VERSES]}


def find_topics(words: str) -> list[dict]:
    return TOPICS.search_titles(words)


__all__ = ["chapter_notes", "EASTON", "verse", "strongs", "topic", "find_topics", "normalize", "xrefs", "passage_text"]
