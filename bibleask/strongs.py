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
import math
import os
import re
import threading
import unicodedata
from collections import defaultdict
from typing import Optional

from .search import _STOP, _stem

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


    # -- the person's words -> the Hebrew and Greek words that mean them ("sea monsters" -> H8577 tannin)
    def gloss_index(self) -> dict:
        """{"terms": {"sea monster": [["H8577", 1.0], ...], "patient": [...]}, "info": {"H8577": [verses, "tannin",
        ["dragon", "sea monster", ...]]}}. Terms are stemmed like the word search ("sea monster", not "sea monsters")."""
        if getattr(self, "_gloss", None) is None:
            self._load()
            path = os.path.join(self.data_dir, "strongs_gloss.json.gz")   # made ahead by packaging/build_gloss.py
            if os.path.exists(path):
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    self._gloss = json.load(f)
            else:
                self._gloss = build_gloss_index(self._dict, self._where)
        return self._gloss

    def meaning_matches(self, query: str) -> list[dict]:
        """The Hebrew/Greek words a question clearly asks about, strongest first:
        [{"number", "term", "quality", "label", "verses": [(book, ch, v), ...]}]."""
        gi = self.gloss_index()
        out = []
        for term, q in gloss_terms(query, gi["terms"]):
            for n, quality in gi["terms"][term]:
                df, name, words = gi["info"][n]
                out.append({"number": n, "term": term, "quality": quality * q, "idf": math.log(1 + VERSES / df),
                            "label": gloss_label(n, name, words, term),
                            "verses": [ref for ref, _w in self._where.get(n, [])]})
        out.sort(key=lambda m: -m["quality"] * m["idf"])
        return out


# --------------------------------------------------------------------------- the word index
# The same index and rules serve the phone (web/build_study.py writes it to data/study/gloss.json).
VERSES = 31102                 # verses in the 66 books, for how rare a word is
TOO_COMMON = 1000              # a Hebrew/Greek word in more verses than this says little (God, LORD, day, man)
MAX_SENSES = 8                 # a word keeps only the 8 Hebrew/Greek words the KJV most often renders with it
# everyday words that would bring in thousands of verses without saying what the question is about
COMMON = set("""god lord day days man men say said make made come came go went thing one people time
word hand house son sons king give gave take took see saw know let put also call called good great many
upon unto shall will even every everything all like way before after first two three""".split())
COMMON = {_stem(w) for w in COMMON}
_DROP = re.compile(r"\([^)]*\)|\[[^\]]*\]|[+´`×]|\bX\b")
_ETYM = re.compile(r"\b[HG]\d+|\bfrom\b|\broot\b|\bprim|\bform\b|\bplural\b|\bfeminine\b|\bmasculine\b|"
                   r"\bparticiple\b|\bchaldee\b|\bcorresponding\b|\borigin\b|\bcompare\b|\bprolonged\b|\bderived\b|"
                   r"\bintensive\b|\bdenominative\b|\bordinal\b|\bcausative\b|\bapparently\b|\bprobably\b|\bperhaps\b", re.I)


def _content(text: str) -> list[list[str]]:
    """Runs of neighbouring content words (a little word such as "of" breaks a run)."""
    runs, cur = [], []
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in _STOP or len(w) < 3:
            if cur:
                runs.append(cur); cur = []
            continue
        cur.append(_stem(w))
    if cur:
        runs.append(cur)
    return runs


def build_gloss_index(dictionary: dict, where: dict) -> dict:
    """where: {"H8577": [((book, ch, v), "great whales"), ...]}, the KJV words used for each Hebrew/Greek word."""
    terms: dict = defaultdict(dict)
    info: dict = {}
    hits: dict = {}          # (word, number) -> verses where the KJV uses that word for it
    df = {n: len(u) for n, u in where.items()}
    kjv_words = {w for uses in where.values() for _r, eng in uses for w in re.findall(r"[a-z]+", eng.lower())}

    def share(n: str, term: str) -> float:
        """How often the KJV puts this word where the Hebrew/Greek word stands (tannin: "dragon" 21 of 28 times)."""
        uses = where.get(n, [])
        hit = sum(1 for _r, eng in uses if term in {w for r in _content(eng) for w in r})
        return hit / max(len(uses), 1)

    def add(term: str, n: str, quality: float) -> None:
        if all(w in COMMON for w in term.split()):
            return
        if quality > terms[term].get(n, 0):
            terms[term][n] = quality

    for n, e in dictionary.items():
        uses = df.get(n, 0)
        if not uses or uses > TOO_COMMON:
            continue
        k = _DROP.sub(" ", re.sub(r"\.?\s*(Compare|See)\b.*$", "", e.get("k", "")))   # "love(-ed). Compare G5368"
        if not k.strip() or k.strip()[0].isupper():          # a name (Crispus, Lasha): the word search finds those
            continue
        renderings = []
        phrases = k.split(",") if "," in k or n[0] == "G" else k.split()
        for ph in phrases:
            ph = ph.strip(" .;-")
            for compound in re.findall(r"[a-z]+(?:-[a-z]+)+", ph.lower()):      # "sea-monster"
                words = [w for r in _content(compound.replace("-", " ")) for w in r]
                if len(words) == 2:
                    add(" ".join(words), n, 1.0)
                    renderings.append(compound.replace("-", " "))
                ph = ph.replace(compound, " ")
            runs = _content(ph)
            words = [w for r in runs for w in r]
            raw = [w for w in re.findall(r"[a-z]+", ph.lower()) if w not in _STOP and len(w) > 2]
            if len(words) == 1 and raw and raw[0] in kjv_words:   # not a broken piece such as "fif" (from "fif[-teen]")
                # "beast", "be patient" -> patient; a main meaning when the KJV often uses it, or the definition says it
                sh = share(n, words[0])
                main = sh >= 0.2 or words[0] in {w for r in _content(e.get("d", "")) for w in r}
                add(words[0], n, 0.8 if main else 0.4)
                hits[(words[0], n)] = sh * uses
                renderings.append(ph.strip(" -").lower())
            elif n[0] == "G":
                for r in runs:                                # Greek renderings are whole phrases: "suffer long"
                    for a, b in zip(r, r[1:]):
                        add(a + " " + b, n, 0.9)
        meaning = [s for s in e.get("d", "").split(";") if s.strip() and not _ETYM.search(s)]
        for seg in meaning:
            for r in _content(re.sub(r"\bi\.\s*e\.?|\be\.\s*g\.?", " ", _DROP.sub(" ", seg))):
                for a, b in zip(r, r[1:]):                    # "a marine or land monster that is sea serpent"
                    add(a + " " + b, n, 0.7)
        if any(n in t for t in terms.values()):
            seen, words = set(), []
            for r in renderings:
                r = re.sub(r"\s+", " ", r).strip()
                if r and r not in seen:
                    seen.add(r); words.append(r)
            # the words the KJV uses most for it first (naphal: "fall", "cast", ... not "accepted")
            words.sort(key=lambda r: -share(n, _content(r)[0][0]) if " " not in r and _content(r) else 0)
            info[n] = [uses, simple_translit(e.get("t", "")), words[:6]]
    out = {}
    for term, ns in terms.items():
        if " " not in term:
            ns = {n: q for n, q in ns.items() if q >= 0.8}   # a single word only where it is a main meaning,
            best = sorted(ns, key=lambda n: -hits.get((term, n), 0))[:MAX_SENSES]   # the ones the KJV uses most
            ns = {n: ns[n] for n in best}
            if not ns:
                continue
        out[term] = sorted(([n, q] for n, q in ns.items()), key=lambda x: (-x[1], x[0]))
    return {"terms": out, "info": {n: v for n, v in info.items() if any(n == m for t in out.values() for m, _ in t)}}


def gloss_terms(query: str, terms: dict) -> list[tuple[str, float]]:
    """The question's words and two-word phrases found in the index; a phrase hides its own single words."""
    runs = _content(query)
    found, used = [], set()
    for r in runs:
        for i, (a, b) in enumerate(zip(r, r[1:])):
            if a + " " + b in terms:
                found.append((a + " " + b, 1.0)); used |= {(id(r), i), (id(r), i + 1)}
    for r in runs:
        for i, w in enumerate(r):
            if (id(r), i) not in used and w in terms and w not in COMMON:
                found.append((w, 1.0))
    return found


def simple_translit(t: str) -> str:
    """'tannîyn tannîym' -> 'tannin'; "'ĕlôhîym" -> 'elohim' (plain letters, easy to read)."""
    w = (t.split() or [""])[0]
    w = re.sub(r"îy", "i", w); w = re.sub(r"ûw", "u", w); w = re.sub(r"ôw", "o", w)
    w = unicodedata.normalize("NFD", w.replace("ώ", "s").replace("ω", "s"))   # the dictionary writes sin (ś) as ώ
    return "".join(c for c in w if unicodedata.category(c) != "Mn" and c not in "'‛’ʼ`").lower()


def gloss_label(n: str, name: str, words: list[str], term: str) -> str:
    """'Hebrew word tannin (H8577): sea monster, dragon, serpent, whale' (the matched meaning first)."""
    hit = [w for w in words if [x for r in _content(w) for x in r] == term.split()]
    shown = hit[:1] + [w for w in words if w not in hit[:1]]
    return f"{'Hebrew' if n[0] == 'H' else 'Greek'} word {name} ({n}): {', '.join(shown[:4])}"


STRONGS = Strongs()
