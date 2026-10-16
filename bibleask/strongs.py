"""Strong's numbers: the Hebrew or Greek word behind each English word of the King James Version.

James Strong's Exhaustive Concordance (1890) gives every Hebrew and Greek word of the Bible a number,
H1-H8674 for Hebrew and G1-G5624 for Greek. The KJV text from CrossWire carries those numbers on its
words, so BibleChat can show the original word, its meaning, and every verse that uses it.

Data (public domain), built by packaging/build_strongs.py:
  bibleask/data/strongs_kjv.json.gz   [[book, chapter, verse, [text | [words, "G25 ..."], ...]], ...]
  bibleask/data/strongs_dict.json.gz  {"G25": {"w": original, "t": transliteration, "p": pronunciation,
                                               "d": meaning, "k": how the KJV translates it}, ...}
"""
from __future__ import annotations

import gzip
import json
import os
import re
import threading
from collections import defaultdict
from typing import Optional

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NUMBER = re.compile(r"^\s*(?:strong'?s\s*)?([HG])\s*0*(\d{1,4})\s*$", re.I)


def normalize(s: str) -> Optional[str]:
    """'g0025', 'G25', "Strong's H430" -> 'G25' / 'H430'; anything else -> None."""
    m = NUMBER.match(s or "")
    return f"{m[1].upper()}{int(m[2])}" if m and int(m[2]) > 0 else None


class Strongs:
    def __init__(self, data_dir: str = _DIR) -> None:
        self.data_dir = data_dir
        self._lock = threading.Lock()
        self._verses: Optional[dict] = None

    def available(self) -> bool:
        return os.path.exists(os.path.join(self.data_dir, "strongs_kjv.json.gz"))

    def _load(self) -> None:
        with self._lock:
            if self._verses is not None:
                return
            verses: dict = {}
            where: dict = defaultdict(list)
            with gzip.open(os.path.join(self.data_dir, "strongs_kjv.json.gz"), "rt", encoding="utf-8") as f:
                for book, ch, v, seg in json.load(f):
                    verses[(book, ch, v)] = seg
                    for s in seg:
                        if isinstance(s, list):
                            for n in s[1].split():
                                lst = where[n]
                                if not lst or lst[-1][0] != (book, ch, v):
                                    lst.append(((book, ch, v), s[0]))
            with gzip.open(os.path.join(self.data_dir, "strongs_dict.json.gz"), "rt", encoding="utf-8") as f:
                self._dict = json.load(f)
            self._where = dict(where)
            self._verses = verses

    def verse(self, book: str, chapter: int, verse: int) -> list:
        """The KJV verse as pieces: plain text, or [english words, 'G25'] for a word with a number."""
        self._load()
        return self._verses.get((book, chapter, verse), [])

    def kjv_text(self, book: str, chapter: int, verse: int) -> str:
        return "".join(s if isinstance(s, str) else s[0] for s in self.verse(book, chapter, verse))

    def entry(self, number: str) -> Optional[dict]:
        n = normalize(number)
        if not n:
            return None
        self._load()
        d = self._dict.get(n)
        if d is None:
            return None
        uses = self._where.get(n, [])
        words: dict[str, int] = defaultdict(int)
        for _ref, w in uses:
            words[w.lower()] += 1
        return {"number": n, "language": "Hebrew" if n[0] == "H" else "Greek",
                "word": d["w"], "translit": d["t"], "pron": d["p"], "meaning": d["d"], "kjv": d["k"],
                "count": len(uses),
                "kjv_words": sorted(words.items(), key=lambda x: -x[1])[:12]}

    def verses_with(self, number: str) -> list[tuple[tuple[str, int, int], str]]:
        """Every KJV verse that uses this Strong's number, in Bible order, with the English words used."""
        n = normalize(number)
        if not n:
            return []
        self._load()
        return list(self._where.get(n, []))


STRONGS = Strongs()
