"""The search guide (web/guide.json), shared by the phone and the computer.

For a broad topic ("women", "prayer", "money"), word and meaning search can lean one way: the eight verses that
match the words best are not the whole picture. The guide adds, for 15 broad topics, the key passages grouped by
theme, so every side the Bible shows is on screen (Deborah, Proverbs 31, Phoebe and Junia next to 1 Corinthians 14).
It also labels books that are not in every Bible ("In Catholic and Orthodox Bibles" for Sirach), adds short
"In the original" notes where the Hebrew or Greek says more than the translation (Psalm 68:11), and "In context"
notes for hard verses (who wrote it, to whom, the verses around it). Notes are BibleChat's, never Scripture.

web/guide.js does the same on the phone and in the computer page; tests/test_guide.py checks both agree.
"""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Callable, Iterable, Optional

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "guide.json")
_REF = re.compile(r"^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$")
_lock = threading.Lock()
_data: Optional[dict] = None


def load(path: str = _PATH) -> dict:
    """The guide, read once. Missing file (an odd build): an empty guide, so search still works."""
    global _data
    with _lock:
        if _data is None:
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                d = {"stop": [], "sections": [], "canon": {"groups": {}, "books": {}}, "topics": [], "notes": {}}
            d["_notes"] = _expand_notes(d.get("notes", {}))
            d["_section"] = {b: name for name, books in d.get("sections", []) for b in books}
            _data = d
        return _data


def parse_ref(ref: str) -> Optional[tuple[str, int, int, int]]:
    """'Romans 16:1-7' -> ('Romans', 16, 1, 7)."""
    m = _REF.match(ref.strip())
    if not m:
        return None
    v1 = int(m[3])
    return m[1], int(m[2]), v1, int(m[4]) if m[4] else v1


def _expand_notes(notes: dict) -> dict:
    out: dict = {}
    for key, n in notes.items():
        p = parse_ref(key)
        if not p:
            continue
        book, ch, v1, v2 = p
        for v in range(v1, v2 + 1):
            cur = out.setdefault((book, ch, v), {})
            for kind, val in n.items():
                cur.setdefault(kind, dict(val, key=key))
    return out


# ---- words: the same simple rule as web/guide.js (letters a-z only, lower case)
def words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower().replace("’", "'"))


def content_words(text: str) -> list[str]:
    stop = set(load().get("stop", []))
    return [w for w in words(text) if w not in stop]


def topic_for(question: str) -> Optional[dict]:
    """The broad topic a question is about, or None. A topic's word or phrase must stand in the question;
    the topic with the most of them wins, the first in the list on a tie."""
    ws = words(question)
    if not ws:
        return None
    hay = " " + " ".join(ws) + " "
    best, best_n = None, 0
    for t in load().get("topics", []):
        n = sum(1 for w in t.get("words", []) if " " + w + " " in hay)
        if n > best_n:
            best, best_n = t, n
    return best


def broad(question: str) -> bool:
    """A broad question: a topic of the guide, or one or two words ("women", "angels", "end times")."""
    return topic_for(question) is not None or 0 < len(content_words(question)) <= 2


# ---- which Bibles a book is in
def canon(book: str) -> Optional[dict]:
    d = load()["canon"]
    g = d["books"].get(book)
    return dict(d["groups"][g], group=g) if g else None


def canon_short(book: str) -> str:
    c = canon(book)
    return c["short"] if c else ""


# ---- notes
def notes_for(book: str, ch: int, v: int) -> dict:
    """{"original": {...}, "context": {...}} for a verse (King James book names and numbers), or {}."""
    return load()["_notes"].get((book, ch, v), {})


# ---- parts of the Bible, and spreading a long list over them
def section_of(book: str) -> str:
    d = load()
    return d["_section"].get(book, d.get("other_section", "Other books"))


def spread(items: list, book_of: Callable[[object], str], k: int = 8, cap: int = 3) -> list:
    """The first k items with at most `cap` from one part of the Bible (Law, History, Wisdom, Prophets, Gospels,
    Acts, Letters, Revelation, other books), best first; the rest after them in their old order. If too few
    parts are found, the skipped items fill the first k after all. Same as BCGuide.spread in web/guide.js."""
    picked, skipped, count = [], [], {}
    for i, it in enumerate(items):
        if len(picked) >= k:
            break
        s = section_of(book_of(it))
        if count.get(s, 0) < cap:
            picked.append(i)
            count[s] = count.get(s, 0) + 1
        else:
            skipped.append(i)
    for i in skipped:
        if len(picked) >= k:
            break
        picked.append(i)
    chosen = set(picked)
    return [items[i] for i in picked] + [it for i, it in enumerate(items) if i not in chosen]


# ---- books that aren't in every Bible rank lower; key passages join the first answers
def demote(items: list, book_of: Callable[[object], str], question: str, k: int = 8) -> list:
    """Verses from books that are not in every Bible (Sirach, Tobit, 2 Esdras, Jasher; the groups in canon.demote)
    move below the first k answers, unless the question names the book ("Sirach on friendship"). They stay in the
    list, with their label. The Ethiopian books (1 Enoch, Jubilees) stay where they are: only Bibles that have
    them are searched for them. Same as BCGuide.demote in web/guide.js."""
    d = load()["canon"]
    low_groups = set(d.get("demote", []))
    named = set(words(question))

    def low(it) -> bool:
        b = book_of(it)
        g = d["books"].get(b)
        return g in low_groups and not (set(words(b)) - {"of", "the"}) & named

    keep = [it for it in items if not low(it)]
    lows = [it for it in items if low(it)]
    return keep[:k] + lows + keep[k:]


def key_verses(topic: Optional[dict], score: Optional[Callable[[str, int, int], float]] = None,
               question: str = "") -> list[tuple[str, int, int]]:
    """One verse of each key passage of a topic, one theme after another (the first passage of every theme, then the
    second...), so the first few cover different themes. With score(book, ch, v) (how close a verse is to the
    question in meaning), each passage gives its closest verse and each theme its closest passage first. Themes whose
    own words stand in the question come first ("how to deal with grief": "Grieve, but not without hope"; "fallen
    angels": the angels that sinned), the most such words first, each with all its passages; then the other themes
    one passage at a time, in the guide's order (the foundational passages first).
    Same as BCGuide.keyVerses in web/guide.js."""
    if not topic:
        return []
    themes = []
    for th in topic.get("themes", []):
        cands = []
        for r in th["refs"]:
            p = parse_ref(r)
            if not p:
                continue
            book, ch, v1, v2 = p
            best = v1
            if score:
                for v in range(v1, v2 + 1):
                    if score(book, ch, v) > score(book, ch, best):
                        best = v
            cands.append((score(book, ch, best) if score else 0.0, (book, ch, best)))
        if score:
            cands.sort(key=lambda x: -x[0])
        themes.append(cands)
    hay = " " + " ".join(words(question)) + " "
    hits = [sum(1 for w in th.get("words", []) if " " + w + " " in hay) for th in topic.get("themes", [])]
    order = sorted(range(len(themes)), key=lambda i: (-hits[i], i))
    out, seen = [], set()
    for i in order:                              # a theme the question names gives all its passages first
        if hits[i]:
            for _s, ref in themes[i]:
                if ref not in seen:
                    seen.add(ref)
                    out.append(ref)
    for r in range(max((len(t) for t in themes), default=0)):
        for i in order:
            t = themes[i]
            if r < len(t) and t[r][1] not in seen:
                seen.add(t[r][1])
                out.append(t[r][1])
    return out


def mix(items: list, keys: list, id_of: Callable[[object], object], make_key: Callable[[object], object],
        k: int = 8, n: int = 4) -> list:
    """The first k answers alternate: a key passage, the best match, the next key passage, the next best match...,
    up to n key passages; then the other matches in their order. A key passage that is already among the first k
    matches keeps its place and takes no key slot; one found further down moves up with its own reasons. keys: verse ids (as id_of gives them), best first. Same as BCGuide.mix in web/guide.js."""
    by_id = {id_of(it): it for it in items}
    shown = {id_of(it) for it in items[:k]}   # a key passage already among the first k needs no slot of its own
    out, seen, ki, ii, nk = [], set(), 0, 0, 0
    while len(out) < k:
        want_key = len(out) % 2 == 0 and nk < n
        while ki < len(keys) and (keys[ki] in seen or keys[ki] in shown):
            ki += 1
        while ii < len(items) and id_of(items[ii]) in seen:
            ii += 1
        if (want_key or ii >= len(items)) and ki < len(keys) and nk < n:
            key = keys[ki]
            out.append(by_id.get(key) or make_key(key))
            seen.add(key)
            nk += 1
        elif ii < len(items):
            out.append(items[ii])
            seen.add(id_of(items[ii]))
        else:
            break
    return out + [it for it in items if id_of(it) not in seen]


# ---- Study Paths: every theme of a linked topic has a step in the path
def verses_of(refs: Iterable[str]) -> set:
    out = set()
    for r in refs:
        p = parse_ref(r)
        if p:
            book, ch, v1, v2 = p
            out.update((book, ch, v) for v in range(v1, v2 + 1))
    return out


def missing_themes(topic: dict, path: dict) -> list[str]:
    """The themes of a topic that no step of its Study Path reads (the balance rule; empty = balanced)."""
    have = verses_of(r for s in path.get("steps", []) for r in s.get("refs", []))
    return [th["point"] for th in topic.get("themes", []) if not (verses_of(th["refs"]) & have)]
