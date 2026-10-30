"""One ranked list from three ways of finding verses:

  matched word        the word search (search.Index.search): the verse uses the question's words
  Hebrew/Greek word   the question's words are what a Hebrew or Greek word means ("sea monsters" -> tannin,
                      H8577), so every verse with that word counts, even where the KJV says "great whales"
  matched by meaning  the verse's meaning fingerprint is close to the question's (meaning.py)

Each list is ranked on its own; a verse scores 1/(2 + rank) in each list it is in, so a verse that two or three
methods agree on, or that one method is sure about, rises to the top. Hebrew/Greek words and meaning work for English Bibles only; when they
can't run (data or numpy missing) the word search is used alone, exactly as before.
The phone version (web/index.html) follows the same rules.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .search import Index, tokenize

K = 2                 # rank smoothing: the 1st verse of a list counts 1/3, the 2nd 1/4, the 10th 1/12
DEPTH = 60            # how far down each list counts
MEANING_FLOOR = 0.55  # below this similarity a verse is not really "about" the question
W_STRONGS = 1.0       # weight of a Hebrew/Greek word match ...
W_PHRASE = 2.0        # ... that is a clear two-word phrase ("sea monster" = tannin)
W_MEANING = 1.0
PHRASE = 0.9          # the quality a phrase match needs to count as clear
WHY_WORD, WHY_NEAR, WHY_MEANING = "matched word", "matched words in the verses around it", "matched by meaning"
# words of an everyday question that say nothing about the topic ("how to deal with grief", "what to do when I feel
# anxious"): left out of the word and Hebrew/Greek search, so "deal" doesn't bring Sirach 29 and "feel" Psalm 58:9.
# The meaning search still reads the whole question.
FILLER = {"feel", "feels", "feeling", "felt", "deal", "deals", "dealing", "handle", "handles", "handling",
          "cope", "copes", "coping"}


def plain(question: str) -> str:
    """The question without FILLER words; the question itself if nothing would be left. Same as plain() in web/smart.js."""
    import re
    kept = [w for w in question.split() if re.sub(r"[^a-z]", "", w.lower()) not in FILLER]
    q = " ".join(kept)
    return q if tokenize(q) else question


@dataclass
class Found:
    index: int
    score: float
    why: list[str] = field(default_factory=list)


def _index_of(ix: Index, book: str, ch: int, v: int) -> Optional[int]:
    """The verse in this Bible (book names may differ: "Psalms" vs "Psalm")."""
    found = ix.by_ref.get((book, ch, v))
    if not found:
        title = ix.books.resolve(book)
        found = ix.by_ref.get((title, ch, v)) if title else None
    return found[0] if found else None


def strongs_ranked(question: str, ix: Index, sims: Optional[dict] = None) -> list[tuple[int, float, str, bool]]:
    """Verses with the Hebrew/Greek words the question asks about: [(verse index, score, reason, phrase)], best
    first. Score 0: nothing to add (the Bible already uses the asked word there); phrase: a clear two-word match
    where the Bible uses other words.
    sims (meaning similarity per verse) puts the verses that are also about the question first: tannin is a
    sea monster in Genesis 1:21 but Aaron's serpent in Exodus 7:9."""
    from .strongs import STRONGS, COMMON, _content
    if not STRONGS.available():
        return []
    matches = STRONGS.meaning_matches(question)
    if not matches:
        return []
    words = [w for r in _content(question) for w in r if w not in COMMON]
    agree = {i for i, _s in meaning_ranked(sims, ix)}
    best: dict = defaultdict(dict)          # ref -> term -> (weight, reason, quality)
    for m in matches:
        weight = m["quality"] * m["idf"]
        for ref in m["verses"]:
            if weight > best[ref].get(m["term"], (0, "", 0))[0]:
                best[ref][m["term"]] = (weight, m["label"], m["quality"])
    near_terms: dict = defaultdict(set)      # a story spans several verses: credit what the verses around it have
    for (b, c, v), terms in best.items():
        for d in (-3, -2, -1, 1, 2, 3):
            near_terms[(b, c, v + d)] |= set(terms)
    out = []
    for ref, terms in best.items():
        covered = sum(len(t.split()) for t in terms) + 0.5 * sum(len(t.split()) for t in near_terms[ref] - set(terms))
        score = sum(w for w, _l, _q in terms.values()) * (0.4 + 0.6 * min(covered / max(len(words), 1), 1.0))
        i = _index_of(ix, *ref)
        if i is None:
            continue
        # new: the Bible says it in other words (KJV "great whales" for "sea monsters")
        own = set(ix.tokens[i])
        new = [t for t in terms if not set(t.split()) <= own]
        clear = [t for t in terms if " " in t and terms[t][2] >= PHRASE]   # "sea monster" = tannin
        phrase = any(t in new for t in clear)     # ... where the Bible says it in other words: counts double
        # one word alone is clear enough only if the verse has two of the asked words in Hebrew/Greek
        # ("love is patient": agape and makrothymeo in 1 Corinthians 13:4), or the question is one word
        if not clear and len(terms) < 2 and len(words) > 1:
            score = 0.0
        if sims:   # the meaning search must agree, even for a phrase (tannin is also the ASV's "jackals")
            score *= max(sims.get(ref, 0.0) - 0.4, 0.02)
            if i not in agree:
                score = 0.0
        # a word the Bible already uses there adds nothing to the word search; a clear phrase still does
        out.append((i, score if (new or clear) else 0.0, max(terms.values())[1], phrase))
    out.sort(key=lambda x: -x[1])
    return out


def meaning_ranked(sims: Optional[dict], ix: Index) -> list[tuple[int, float]]:
    out = []
    for (b, c, v), sim in sorted((sims or {}).items(), key=lambda kv: -kv[1]):
        if sim < MEANING_FLOOR or len(out) >= DEPTH:
            break
        i = _index_of(ix, b, c, v)
        if i is not None:
            out.append((i, sim))
    return out


def real_words(question: str, ix: Index, known) -> bool:
    """Does the question have a real content word (one the Bible or the meaning model knows)? Without one
    ("asdf", "and verse 3?") the meaning search would only guess, so it isn't asked."""
    from .search import _STOP
    import re
    for w in re.findall(r"[a-z]+", question.lower()):
        if len(w) >= 3 and w not in _STOP and (w in ix.vocab or known(w)):
            return True
    return False


def blended(question: str, ix: Index, k: int = 12) -> list[Found]:
    """The best verses by all three methods together, each with the reasons it was found."""
    full, question = question, plain(question)   # the meaning search reads the whole question (full)
    words = ix.search(question, k=DEPTH)
    found: dict[int, Found] = {}

    def add(i: int, rank: Optional[int], why: str, weight: float = 1.0) -> None:
        f = found.setdefault(i, Found(i, 0.0))
        if rank is not None:
            f.score += weight / (K + rank + 1)
        if why not in f.why:
            f.why.append(why)

    qwords = set(tokenize(question)) or set(tokenize(question, keep_stop=True))
    for r, h in enumerate(words):
        has_word = bool(qwords & set(ix.tokens[h.index]))
        add(h.index, r, WHY_WORD if has_word else WHY_NEAR)
    if ix.lang == "en":
        sims = None
        try:
            from .meaning import MEANING
            if MEANING.available() and real_words(full, ix, MEANING.knows):
                sims = MEANING.similarities(full)
            for r, (i, _sim) in enumerate(meaning_ranked(sims, ix)):
                add(i, r, WHY_MEANING, W_MEANING)
        except Exception:
            sims = None
        try:
            r = 0
            for i, sc, label, phrase in strongs_ranked(question, ix, sims):
                if sc > 0 and r < DEPTH:
                    add(i, r, label, W_PHRASE if phrase else W_STRONGS)
                    r += 1
                elif i in found:                 # already found another way: say which Hebrew/Greek word it is
                    add(i, None, label)
        except Exception:
            pass
    ranked = sorted(found.values(), key=lambda f: (-f.score, f.index))
    # the same text twice (some Bibles print a book twice): keep the first
    seen, out = set(), []
    for f in ranked:
        key = ix.verses[f.index].text.lower()[:160]
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
        if len(out) >= k:
            break
    return out
