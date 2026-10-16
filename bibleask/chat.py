"""The brain of the chat: find verses in the chosen Bibles, then (optionally) let the small model explain them.

The chat only ever talks about the loaded Bibles. If nothing in them matches, it says so instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from . import llm
from .library import Library
from .search import guess_language, short_ref, tokenize
from .topics import TOPICS

MAX_VERSES = 12
MAX_PASSAGE = 60
FOLLOW_UP_CUES = {"verse", "verses", "more", "that", "it", "this", "why", "how", "explain", "next", "previous",
                  "and", "also", "other", "else", "chapter", "them", "those", "what", "about", "again", "continue"}

NOTHING_FOUND = (
    "I couldn't find anything about that in your Bibles. I only answer from the Bibles you've added, "
    "so try different words from the verse, a reference like **John 3:16**, or add another Bible."
)


@dataclass
class Retrieval:
    kind: str  # "passage" (a typed reference) or "search"
    groups: list[dict]  # [{"bible": name, "verses": [{"ref":..., "text":...}]}]
    for_model: list[tuple[str, str]]  # (reference, text) pairs to hand to the AI
    note: str = ""  # shown under the verses, e.g. which Bibles weren't searched


def _vd(v) -> dict:
    return {"ref": short_ref(v), "text": v.text, "book": v.book, "chapter": v.chapter}


def retrieve(question: str, previous_question: Optional[str], lib: Library, bible_ids: list[str]) -> Optional[Retrieval]:
    loaded = []
    id_of: dict[str, str] = {}  # bible name -> id, so the page can open a verse in the reader
    for bid in bible_ids:
        try:
            loaded.append(lib.get(bid))
            id_of.setdefault(loaded[-1][0].name, bid)
        except Exception:
            continue
    if not loaded:
        return None

    # 1) a typed reference such as "Daniel 7:25" shows that passage in every selected Bible
    groups = []
    for bible, ix in loaded:
        idx = ix.lookup_reference(question)
        if idx:
            groups.append({"bible": bible.name, "id": id_of.get(bible.name),
                           "verses": [_vd(ix.verses[i]) for i in idx[:MAX_PASSAGE]]})
    if groups:
        first = groups[0]["verses"][:MAX_VERSES]
        return Retrieval("passage", groups, [(v["ref"], v["text"][:600]) for v in first])

    # 2) otherwise search by words; a very short follow-up ("and verse 4?") that finds nothing on its own
    #    borrows the earlier question
    # Words only mean something in their own language: an English question must not match the German
    # "Angel" (a fishing hook). Search only the Bibles in the question's language (if that's unclear,
    # the language most of the ticked Bibles are in).
    q_lang = _question_language(question, loaded)
    same = [(b, ix) for b, ix in loaded if not (q_lang and ix.lang and ix.lang != q_lang)] or loaded
    skipped = [b.name for b, ix in loaded if (b, ix) not in same]

    def run(query: str):
        return [(bible, ix, ix.search(query, k=MAX_VERSES)) for bible, ix in same]

    per_bible = run(question)
    words = question.lower().replace("?", " ").replace(".", " ").split()
    follow_up = len(words) <= 4 and (any(w in FOLLOW_UP_CUES for w in words) or any(w.isdigit() for w in words))
    if not any(h for _, _, h in per_bible) and previous_question and follow_up:
        per_bible = run(previous_question + " " + question)
    chosen: list[tuple[str, dict]] = []  # (bible name, verse)
    for rank in range(MAX_VERSES):  # interleave so every Bible gets a say
        for bible, ix, hits in per_bible:
            if rank < len(hits) and len(chosen) < MAX_VERSES:
                v = ix.verses[hits[rank].index]
                chosen.append((bible.name, _vd(v)))
    topic = _topic_group(question, same, id_of)
    if not chosen and not topic:
        return None
    by_bible: dict[str, list[dict]] = {}
    for name, vd in chosen:
        by_bible.setdefault(name, []).append(vd)
    groups = [{"bible": n, "id": id_of.get(n), "verses": vs} for n, vs in by_bible.items()]
    for_model = [(vd["ref"], vd["text"][:600]) for _, vd in chosen]
    if topic:
        groups.insert(0, topic)
        for_model = [(vd["ref"], vd["text"][:600]) for vd in topic["verses"]] + for_model
    note = ""
    if skipped:
        one = len(skipped) == 1
        note = (", ".join(skipped) + (" is" if one else " are") + " in another language, so " +
                ("it wasn't" if one else "they weren't") + " searched with these words. Ask in " +
                ("that language" if one else "their language") + " to search " + ("it." if one else "them."))
    return Retrieval("search", groups, for_model[:MAX_VERSES + 6], note)


def _question_language(question: str, loaded: list) -> Optional[str]:
    """Which language the question is in: the language of the ticked Bible that knows the most of its words
    (a German question's words are in the Luther Bible, not the KJV); else common little words; else the
    language most of the ticked Bibles are in."""
    import re
    words = [w for w in re.findall(r"[^\W\d_]+", question.lower()) if len(w) > 2]
    best: dict[str, float] = {}
    for _, ix in loaded:
        if ix.lang and words:
            cov = sum(w in ix.vocab for w in words) / len(words)
            best[ix.lang] = max(best.get(ix.lang, 0.0), cov)
    if best:
        ranked = sorted(best.items(), key=lambda kv: -kv[1])
        if ranked[0][1] > 0 and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
            return ranked[0][0]
    langs = [ix.lang for _, ix in loaded if ix.lang]
    return guess_language(question) or (max(set(langs), key=langs.count) if langs else None)


def _topic_group(question: str, bibles: list, id_of: dict) -> Optional[dict]:
    """Verses that Nave's Topical Bible lists for the question's topic, shown from the first Bible that has them."""
    try:
        hits = TOPICS.find(question, k=1)
    except Exception:
        return None
    if not hits:
        return None
    h = hits[0]
    for bible, ix in bibles:
        verses = []
        for book, ch, v1, v2 in h.refs:
            title = book if (book, ch, v1) in ix.by_ref else ix.books.resolve(book)
            if not title:
                continue
            for vn in range(v1, v2 + 1):
                for i in ix.by_ref.get((title, ch, vn), [])[:1]:
                    verses.append(_vd(ix.verses[i]))
            if len(verses) >= MAX_VERSES:
                break
        if verses:
            return {"bible": f"Topic: {h.title} · {bible.name}", "id": id_of.get(bible.name), "topic": True,
                    "verses": verses[:MAX_VERSES]}
    return None


def respond(question: str, previous_question: Optional[str], lib: Library, bible_ids: list[str],
            model: llm.LocalLLM, use_ai: bool = True) -> Iterator[tuple[str, object]]:
    """Yields ("sources", retrieval-dict), ("token", text), ("notice", text), ("done", None)."""
    if not bible_ids:
        yield ("token", "Add a Bible first (the **Add Bible** button on the left), then ask your question.")
        yield ("done", None)
        return
    r = retrieve(question, previous_question, lib, bible_ids)
    if r is None:
        yield ("token", NOTHING_FOUND)
        yield ("done", None)
        return
    yield ("sources", {"kind": r.kind, "groups": r.groups, "note": r.note})
    if use_ai:
        if model.loaded:
            for piece in model.stream(question, r.for_model[:llm.passages_wanted(model.style)]):
                yield ("token", piece)
        else:
            yield ("notice", "The AI helper isn't loaded yet, so these are the matching verses only. "
                             "Load it from the sidebar to get an explanation.")
    yield ("done", None)
