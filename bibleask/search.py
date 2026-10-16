"""Fast keyword search over verses (BM25) plus 'John 3:16'-style reference lookup.

No AI needed for this part, so results are always real verses from the loaded Bible.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

from .loaders import Bible, Verse

_STOP = set(
    """a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers herself him himself
his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours
ourselves out over own same she should so some such than that the their theirs them themselves then there these they this
those through to too under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves
say says said saying tell tells told mention mentions mentioned written write bible verse verses passage passages
scripture scriptures where whats what's find show give please want know person people someone anyone anything thing things
about regarding concerning""".split()
)


def _stem(w: str) -> str:
    if len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ing") and len(w) > 5:
        w = w[:-3]
    elif w.endswith("ed") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("es") and len(w) > 4:
        w = w[:-1]
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "lsz":
        w = w[:-1]
    return w


_WORD = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")


def tokenize(text: str, keep_stop: bool = False) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower().replace("’", "'")):
        w = w.split("'")[0] if w.endswith(("'s", "s'")) else w.replace("'", "")
        if not keep_stop and w in _STOP:
            continue
        out.append(_stem(w))
    return out


# --------------------------------------------------------------------------- book names
_NOISE = {
    "the", "book", "of", "first", "second", "third", "fourth", "fifth", "good", "news", "according", "to", "letter",
    "from", "epistle", "prophet", "and", "or", "with", "greek", "portions", "a", "in",
}
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "i": 1, "ii": 2, "iii": 3,
        "1": 1, "2": 2, "3": 3, "4": 4}


def _book_keys(title: str) -> tuple[Optional[int], list[str]]:
    t = title.lower().replace("’", "'").replace("'s ", " ")
    num = None
    m = re.match(r"^([1-4])\s", t)
    if m:
        num = int(m.group(1))
    else:
        for w in re.findall(r"[a-z0-9]+", t)[:4]:
            if w in ("first", "second", "third", "fourth"):
                num = _ORD[w]
                break
    toks = [w for w in re.findall(r"[a-z]+", t) if w not in _NOISE and len(w) > 1]
    if not toks:
        toks = [w for w in re.findall(r"[a-z]+", t) if len(w) > 1]
    if "moses" in t:
        num = None
    return num, toks


class BookIndex:
    def __init__(self, books: list[str]):
        self.books = books
        self.keys = {b: _book_keys(b) for b in books}

    def resolve_all(self, text: str) -> list[str]:
        """Books that could be meant by 'gen', '1 cor', 'psalm'… best guess first."""
        t = text.lower().strip(" .")
        t = t.replace("’", "'")
        num = None
        m = re.match(r"^(first|second|third|fourth|1st|2nd|3rd|iii|ii|i|[1-4])\s*\.?\s*(.+)$", t)
        if m:
            num, t = _ORD[m.group(1)], m.group(2).strip()
        t = re.sub(r"^(the book of|book of|the)\s+", "", t).strip()
        if len(t) < 2:
            return []
        scored: list[tuple[int, int, str]] = []
        for pos, b in enumerate(self.books):
            bnum, toks = self.keys[b]
            if num is not None and bnum != num:
                continue
            for tok in toks:
                if tok == t or tok.startswith(t) or (len(t) >= 4 and t.startswith(tok) and len(tok) >= 4):
                    score = 3 if tok == t else 2
                    if num is None and bnum is None:
                        score += 1
                    scored.append((-score, pos, b))
                    break
        scored.sort()
        return [b for _, _, b in scored]

    def resolve(self, text: str) -> Optional[str]:
        found = self.resolve_all(text)
        return found[0] if found else None


# --------------------------------------------------------------------------- the index
@dataclass
class Hit:
    index: int
    score: float


_REF_FULL = re.compile(
    r"^\s*((?:(?:[1-4]|i{1,3}|first|second|third|1st|2nd|3rd)\s*\.?\s*)?[a-z][a-z ]*?)\.?\s+(\d{1,3})"
    r"(?:\s*[:.]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?)?\s*$",
    re.I,
)
_REF_INLINE = re.compile(
    r"((?:(?:[1-4]|i{1,3}|first|second|third)\s*\.?\s*)?[A-Za-z]{2,}(?:\s+of\s+[A-Za-z]+)?)\.?\s+(\d{1,3})\s*[:.]\s*(\d{1,3})"
    r"(?:\s*[-–]\s*(\d{1,3}))?"
)


_REF_CHAPTER = re.compile(r"\b((?:(?:[1-4]|i{1,3}|first|second|third)\s*\.?\s*)?[A-Za-z]{3,})\s+(\d{1,3})\b")


class Index:
    def __init__(self, bible: Bible):
        self.bible = bible
        self.verses = bible.verses
        n = len(self.verses)
        self.post: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.dlen = [0] * n
        self.tokens: list[list[str]] = []
        for i, v in enumerate(self.verses):
            toks = tokenize(v.text)
            self.tokens.append(toks)
            self.dlen[i] = max(len(toks), 1)
            for term, tf in Counter(toks).items():
                self.post[term].append((i, tf))
        self.avg = sum(self.dlen) / max(n, 1)
        self.n = n
        names: list[str] = []
        for v in self.verses:
            if not names or names[-1] != v.book:
                if v.book not in names:
                    names.append(v.book)
        self.books = BookIndex(names)
        self.by_ref: dict[tuple[str, int, int], list[int]] = defaultdict(list)
        for i, v in enumerate(self.verses):
            self.by_ref[(v.book, v.chapter, v.verse)].append(i)

    # -- keyword search
    def _idf(self, term: str) -> float:
        df = len(self.post.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 10) -> list[Hit]:
        q = tokenize(query)
        if not q:
            q = tokenize(query, keep_stop=True)
        if not q:
            return []
        if "lord" in q and "yahweh" not in q:
            q = q + ["yahweh"]  # many modern translations print "Yahweh" where older ones print "the LORD"
        k1, b = 1.4, 0.75
        scores: dict[int, float] = defaultdict(float)
        for term in set(q):
            plist = self.post.get(term)
            if not plist:
                continue
            idf = self._idf(term)
            for i, tf in plist:
                denom = tf + k1 * (1 - b + b * self.dlen[i] / self.avg)
                scores[i] += idf * tf * (k1 + 1) / denom
        if not scores:
            return []
        # reward verses that contain the query words next to each other, and that match many distinct words
        top = sorted(scores.items(), key=lambda kv: -kv[1])[:400]
        bigrams = {(q[j], q[j + 1]) for j in range(len(q) - 1)}
        qset = set(q)
        rescored: list[Hit] = []
        for i, sc in top:
            toks = self.tokens[i]
            bonus = 0.0
            if bigrams:
                have = {(toks[j], toks[j + 1]) for j in range(len(toks) - 1)}
                bonus += 1.5 * len(bigrams & have)
            own = qset & set(toks)
            coverage = len(own) / len(qset)
            # a story spans several verses: credit the other asked-for words found in the verses
            # just around this one (same chapter), weighted by how rare each word is
            v = self.verses[i]
            near: set[str] = set()
            for j in range(max(0, i - 3), min(len(self.verses), i + 4)):
                if j != i and self.verses[j].book == v.book and self.verses[j].chapter == v.chapter:
                    near |= qset & set(self.tokens[j])
            bonus += 0.6 * sum(self._idf(t) for t in near - own)
            rescored.append(Hit(i, sc * (0.6 + 0.8 * coverage) + bonus))
        rescored.sort(key=lambda h: -h.score)
        # drop verses whose text is a duplicate of one already listed (some Bibles print a book twice)
        seen: set[str] = set()
        out: list[Hit] = []
        for h in rescored:
            key = re.sub(r"[^a-z0-9]", "", self.verses[h.index].text.lower())[:160]
            if key in seen:
                continue
            seen.add(key)
            out.append(h)
            if len(out) >= k:
                break
        return out

    # -- reference lookup
    def lookup_reference(self, query: str) -> Optional[list[int]]:
        """'Daniel 7:25', 'John 3', '1 Cor 13:4-7' -> list of verse indexes. None if not a reference."""
        m = _REF_FULL.match(query)
        if m:
            found = self._resolve(m.group(1), m.group(2), m.group(3), m.group(4))
            if found:
                return found
        for m in _REF_INLINE.finditer(query):
            found = self._resolve(m.group(1), m.group(2), m.group(3), m.group(4))
            if found:
                return found
        if len(query.split()) <= 8:  # "explain Psalm 23", "tell me about Ruth 2"
            for m in _REF_CHAPTER.finditer(query):
                found = self._resolve(m.group(1), m.group(2), None, None)
                if found:
                    return found
        return None

    def _resolve(self, book: str, ch: str, v1: Optional[str], v2: Optional[str]) -> Optional[list[int]]:
        chapter = int(ch)
        for title in self.books.resolve_all(book):
            if v1 is None:
                idxs = [i for i, v in enumerate(self.verses) if v.book == title and v.chapter == chapter]
            else:
                lo = int(v1)
                hi = int(v2) if v2 else lo
                idxs = [i for i, v in enumerate(self.verses)
                        if v.book == title and v.chapter == chapter and lo <= v.verse <= hi]
            if idxs:
                return idxs
        return None

    def context(self, i: int, before: int = 1, after: int = 1) -> list[int]:
        """Indexes of the verse and its neighbours inside the same chapter."""
        v = self.verses[i]
        out = []
        for j in range(max(0, i - before), min(self.n, i + after + 1)):
            w = self.verses[j]
            if w.book == v.book and w.chapter == v.chapter:
                out.append(j)
        return out


# --------------------------------------------------------------------------- friendly names
_ORDINAL_WORDS = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5"}


def short_title(title: str) -> str:
    """'The First Book of Moses, Genesis' -> 'Genesis'; 'Paul’s First Letter to the Corinthians' -> '1 Corinthians'."""
    t = title.replace("’", "'").strip()
    greek = " with Greek Portions" in t
    t = t.replace(" with Greek Portions", "")
    # King James / Project Gutenberg style titles
    km = re.search(r"Book of Moses:\s*Called\s+(\w+)", t)
    if km:
        return km.group(1)
    km = re.match(r"^The Gospel According to (?:Saint|St\.?) (\w+)$", t)
    if km:
        return km.group(1)
    km = re.match(r"^The (?:(First|Second|Third) )?(?:General )?Epistle(?: General)? of (?:Paul|Peter|John|James|Jude)(?: the \w+)?"
                  r"(?: to the (\w+)| to (\w+))?$", t)
    if km and (km.group(2) or km.group(3)):
        return ((_ORDINAL_WORDS[km.group(1).lower()] + " ") if km.group(1) else "") + (km.group(2) or km.group(3))
    km = re.match(r"^The (?:(First|Second|Third) )?(?:General )?Epistle (?:General )?of (Peter|John|James|Jude)$", t)
    if km:
        return ((_ORDINAL_WORDS[km.group(1).lower()] + " ") if km.group(1) else "") + km.group(2)
    if re.match(r"^The Revelation of (?:Saint|St\.?) John", t):
        return "Revelation"
    if re.search(r"Book of Moses,\s*(\w+)", t):
        return re.search(r"Book of Moses,\s*(\w+)", t).group(1)
    t = re.sub(r"^The (First|Second|Third) Epistle of (Clement)", r"The \1 Book of \2", t)
    m = re.match(r"^(?:The )?(First|Second|Third|Fourth) (?:Book|Epistle|Letter) (?:of|to) (?:the )?(.+)$", t)
    num = ""
    if m:
        num, t = _ORDINAL_WORDS[m.group(1).lower()] + " ", m.group(2)
    else:
        m = re.match(r"^(?:Paul|Peter|John)'s (First|Second|Third)? ?Letter(?: to (?:the )?(.+))?$", t)
        if m:
            who = title.replace("’", "'").split("'")[0]
            t = m.group(2) or who
            num = _ORDINAL_WORDS[m.group(1).lower()] + " " if m.group(1) else ""
    t = re.sub(r"^(The )?Good News According to ", "", t)
    t = re.sub(r"^(The )?Letter (from|to) (the )?", "", t)
    t = re.sub(r"^(The )?Book of (the )?(Prophet )?", "", t)
    t = re.sub(r"^The (Acts) of the Apostles$", r"\1", t)
    t = re.sub(r"^The ", "", t)
    t = re.split(r",| or ", t)[0].strip()
    t = re.sub(r"\s+or$", "", t)
    t = re.sub(r"^(Clement) to the Corinthians$", r"\1", t)
    t = re.sub(r"\s*\(.*$", "", t)
    out = (num + t).strip()
    return out + (" (Greek portions)" if greek else "")


def short_ref(v: Verse) -> str:
    return f"{short_title(v.book)} {v.chapter}:{v.verse}"
