"""The brain of the chat: find verses in the chosen Bibles, then (optionally) let the small model explain them.

The chat only ever talks about the loaded Bibles. If nothing in them matches, it says so instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from . import llm
from .library import Library
from .search import short_ref, tokenize

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
    def run(query: str):
        return [(bible, ix, ix.search(query, k=MAX_VERSES)) for bible, ix in loaded]

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
    if not chosen:
        return None
    by_bible: dict[str, list[dict]] = {}
    for name, vd in chosen:
        by_bible.setdefault(name, []).append(vd)
    groups = [{"bible": n, "id": id_of.get(n), "verses": vs} for n, vs in by_bible.items()]
    return Retrieval("search", groups, [(vd["ref"], vd["text"][:600]) for _, vd in chosen])


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
    yield ("sources", {"kind": r.kind, "groups": r.groups})
    if use_ai:
        if model.loaded:
            for piece in model.stream(question, r.for_model[:llm.passages_wanted(model.style)]):
                yield ("token", piece)
        else:
            yield ("notice", "The AI helper isn't loaded yet, so these are the matching verses only. "
                             "Load it from the sidebar to get an explanation.")
    yield ("done", None)
