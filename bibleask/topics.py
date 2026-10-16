"""Topic search with Nave's Topical Bible (Orville J. Nave, 1896; public domain).

Word search only finds verses that use the words you typed. Many questions are about a topic whose key
verses use other words: "fallen angels" is about 2 Peter 2:4 ("the angels that sinned") and Jude 6 ("the
angels which kept not their first estate"). Nave's lists those verses under its topics, so BibleChat can
show them. The verse text itself always comes from your own Bibles.

Data: bibleask/data/nave.json.gz, built by packaging/build_nave.py.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .loaders import _OSIS_NAME
from .search import tokenize

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nave.json.gz")

# Modern ways of naming a topic that Nave files under another name. Each: words that must all be in the
# question -> (Nave topic, words its heading must contain).
ALIASES: list[tuple[set[str], str, str]] = [
    ({"fall", "angel"}, "DEMONS", "punishment"),
    ({"fall", "angel"}, "DEMONS", "judged"),
]


@dataclass
class TopicHit:
    topic: str
    heading: str
    refs: list[tuple[str, int, int, int]]  # (book, chapter, first verse, last verse)
    score: float

    @property
    def title(self) -> str:
        t = self.topic.title()
        return f"{t} — {self.heading}" if self.heading and self.heading.lower() != "see" else t


def _parse_ref(r: str) -> Optional[tuple[str, int, int, int]]:
    a, _, b = r.partition("-")
    m = re.match(r"(\w+)\.(\d+)\.(\d+)$", a)
    if not m:
        return None
    book, ch, v1 = _OSIS_NAME.get(m[1], m[1]), int(m[2]), int(m[3])
    v2 = v1
    m2 = re.match(r"(\w+)\.(\d+)\.(\d+)$", b) if b else None
    if m2 and int(m2[2]) == ch:
        v2 = max(v1, int(m2[3]))
    return book, ch, v1, v2


class Topics:
    def __init__(self, path: str = _DATA) -> None:
        self.path = path
        self._rows: Optional[list] = None
        self._lock = threading.Lock()

    def _load(self) -> list:
        with self._lock:
            if self._rows is None:
                rows = []
                if os.path.exists(self.path):
                    with gzip.open(self.path, "rt", encoding="utf-8") as f:
                        for topic, heading, refs in json.load(f):
                            if refs and refs[0].startswith("see:"):
                                continue
                            toks = set(tokenize(topic.split("(")[0] + " " + heading))
                            parsed = [p for p in (_parse_ref(r) for r in refs) if p]
                            if parsed:
                                rows.append((topic, heading, parsed, toks, set(tokenize(topic.split("(")[0]))))
                self._rows = rows
                by_verse: dict = defaultdict(list)
                for i, (_t, _h, refs, _toks, _tt) in enumerate(rows):
                    for book, ch, v1, v2 in refs:
                        for v in range(v1, v2 + 1):
                            lst = by_verse[(book, ch, v)]
                            if not lst or lst[-1] != i:
                                lst.append(i)
                self._by_verse = dict(by_verse)
                df: dict[str, int] = defaultdict(int)
                for *_, toks, _t in rows:
                    for w in toks:
                        df[w] += 1
                n = max(len(rows), 1)
                self._idf = {w: math.log(1 + n / c) for w, c in df.items()}
            return self._rows

    def find(self, question: str, k: int = 2) -> list[TopicHit]:
        """Best topic lines for a question; only lines that cover every word asked about (or a known alias)."""
        rows = self._load()
        q = set(tokenize(question))
        if not q or not rows:
            return []
        hits: list[TopicHit] = []
        for words, topic, need in ALIASES:
            if words <= q:
                for t, h, refs, _toks, _tt in rows:
                    if t == topic and need in h.lower():
                        hits.append(TopicHit(t, h, refs, 100.0))
                        break
        for t, h, refs, toks, ttoks in rows:
            if not q <= toks:
                continue
            score = sum(self._idf.get(w, 0) for w in q) + 2.0 * len(q & ttoks) + 0.25 * min(len(refs), 12)
            hits.append(TopicHit(t, h, refs, score))
        hits.sort(key=lambda h: -h.score)
        out, seen = [], set()
        for h in hits:
            key = (h.topic, h.heading)
            if key not in seen and len(h.refs) <= 40:   # very long lists ("the general judgment") are too broad
                seen.add(key)
                out.append(h)
            if len(out) >= k:
                break
        return out

    def for_verse(self, book: str, chapter: int, verse: int) -> list[dict]:
        """The Nave's topic lines that list this verse (shortest lists first: they are the most specific)."""
        rows = self._load()
        ids = self._by_verse.get((book, chapter, verse), [])
        out = [{"id": i, "title": TopicHit(rows[i][0], rows[i][1], rows[i][2], 0).title, "count": len(rows[i][2])}
               for i in ids]
        return sorted(out, key=lambda t: (t["count"], t["title"]))

    def get(self, topic_id: int) -> Optional[TopicHit]:
        rows = self._load()
        if 0 <= topic_id < len(rows):
            t, h, refs, _toks, _tt = rows[topic_id]
            return TopicHit(t, h, refs, 0)
        return None

    def search_titles(self, words: str, k: int = 30) -> list[dict]:
        """Topic lines whose name contains every word typed (for browsing Nave's by name)."""
        rows = self._load()
        q = set(tokenize(words))
        if not q:
            return []
        out = [{"id": i, "title": TopicHit(r[0], r[1], r[2], 0).title, "count": len(r[2])}
               for i, r in enumerate(rows) if q <= r[4] or q <= r[3]]
        out.sort(key=lambda t: (not (q <= set(tokenize(t["title"].split(" — ")[0]))), t["title"]))
        return out[:k]


TOPICS = Topics()
