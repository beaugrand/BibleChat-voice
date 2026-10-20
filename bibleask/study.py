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
from .original import line as original_line
from . import versemap

MAX_VERSES = 400


def _key(lib, bible_id: str):
    """The verse-map key of a Septuagint Bible (its numbers differ from the King James), else None."""
    try:
        return versemap.key_for(lib.get(bible_id)[0].name) if bible_id else None
    except Exception:
        return None


def _text(lib, bible_id: str, book: str, ch: int, v: int) -> str:
    """A verse given in King James numbering, in the person's Bible (KJV as fallback)."""
    t = None
    if bible_id:
        at = versemap.from_kjv(_key(lib, bible_id), book, ch, v)
        try:
            t = lib.verse_text(bible_id, book, *at) if at else None
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
    """Study one verse, given in the numbering of the person's Bible. For the Septuagint the study data comes from
    the King James verse that stands in its place (Psalm 22 there is Psalm 23 here); with no clear match, none."""
    ref = f"{book} {ch}:{v}"
    at = versemap.to_kjv(_key(lib, bible_id), book, ch, v)
    if at is None:
        return {"ref": ref, "book": book, "chapter": ch, "verse": v, "words": [], "topics": [], "xrefs": [],
                "henry": None, "original": None, "nomatch": True}
    kjv_ref = f"{book} {at[0]}:{at[1]}" if at != (ch, v) else None
    ch, v = at
    words = STRONGS.verse(book, ch, v) if STRONGS.available() else []
    return {"ref": ref, "kjv_ref": kjv_ref, "book": book, "chapter": ch, "verse": v,
            "words": words, "topics": TOPICS.for_verse(book, ch, v)[:40],
            "xrefs": xrefs(lib, bible_id, book, ch, v),
            "henry": HENRY.for_verse(book, ch, v), "original": original_line(book, ch, v)}


def chapter_notes(book: str, ch: int, lib=None, bible_id: str = "", verses=None) -> dict:
    """Scofield notes of one chapter, by verse number, for marking the words they explain. For a Septuagint Bible
    each verse gets the note of the King James verse in its place."""
    key = _key(lib, bible_id) if lib is not None else None
    if not key:
        return {str(v): SCOFIELD.note(book, ch, v) for v in SCOFIELD.verses_with_notes(book, ch)}
    out = {}
    for v in verses or []:
        at = versemap.to_kjv(key, book, ch, v)
        n = SCOFIELD.note(book, *at) if at else None
        if n:
            out[str(v)] = n
    return out


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
