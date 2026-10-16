"""Study tools for one verse in Read mode: Strong's numbers (the Hebrew/Greek words) and Nave's topics.

Strong's numbers belong to the King James wording, so the word-by-word view always shows the KJV; verse
lists (every verse with a word, every verse of a topic) are shown in the Bible the person is reading,
with the KJV as fallback when that Bible lacks a verse.
"""
from __future__ import annotations

from typing import Optional

from .strongs import STRONGS, normalize
from .topics import TOPICS

MAX_VERSES = 400


def _text(lib, bible_id: str, book: str, ch: int, v: int) -> str:
    t = None
    if bible_id:
        try:
            t = lib.verse_text(bible_id, book, ch, v)
        except Exception:
            t = None
    return t if t is not None else STRONGS.kjv_text(book, ch, v)


def verse(lib, bible_id: str, book: str, ch: int, v: int) -> dict:
    words = STRONGS.verse(book, ch, v) if STRONGS.available() else []
    return {"ref": f"{book} {ch}:{v}", "book": book, "chapter": ch, "verse": v,
            "words": words, "topics": TOPICS.for_verse(book, ch, v)[:40]}


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


__all__ = ["verse", "strongs", "topic", "find_topics", "normalize"]
