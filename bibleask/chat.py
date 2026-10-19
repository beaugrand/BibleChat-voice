"""The brain of the chat: find verses in the chosen Bibles, then (optionally) let the small model explain them.

The chat only ever talks about the loaded Bibles. If nothing in them matches, it says so instead of guessing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Optional

from . import llm
from .blend import blended
from .library import Library
from .search import _STOP, guess_language, short_ref, tokenize
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

    # 0) cross-references: "cross references for Daniel 7:13", "Daniel to Revelation cross references"
    xr = _xref_group(question, loaded, id_of)
    if xr:
        return xr

    # 0b) a Strong's number such as "G25" or "H430": the word's meaning and every verse that uses it
    st = _strongs_group(question, loaded, id_of)
    if st:
        return st

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

    # typing slips ("NAMEW" for "name"): a word no Bible here knows is replaced by the closest word they do know
    question, fixed = _fix_spelling(question, same)

    def run(query: str):
        # words, Hebrew/Greek words and meaning together, each verse with the reasons it was found (blend.py)
        return [(bible, ix, blended(query, ix, k=MAX_VERSES)) for bible, ix in same]

    per_bible = run(question)
    words = question.lower().replace("?", " ").replace(".", " ").split()
    follow_up = len(words) <= 4 and (any(w in FOLLOW_UP_CUES for w in words) or any(w.isdigit() for w in words))
    if previous_question and follow_up and not any(ix.search(question, k=1) for _, ix in same):
        per_bible = run(previous_question + " " + question)
    chosen: list[tuple[str, dict]] = []  # (bible name, verse)
    for rank in range(MAX_VERSES):  # interleave so every Bible gets a say
        for bible, ix, hits in per_bible:
            if rank < len(hits) and len(chosen) < MAX_VERSES:
                v = ix.verses[hits[rank].index]
                chosen.append((bible.name, dict(_vd(v), why=hits[rank].why)))
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
    if fixed:
        note = "Searched for " + ", ".join(f"“{b}” (you typed “{a}”)" for a, b in fixed) + ". "
    if skipped:
        one = len(skipped) == 1
        note += (", ".join(skipped) + (" is" if one else " are") + " in another language, so " +
                ("it wasn't" if one else "they weren't") + " searched with these words. Ask in " +
                ("that language" if one else "their language") + " to search " + ("it." if one else "them."))
    return Retrieval("search", groups, for_model[:MAX_VERSES + 6], note)


# everyday words a question uses that older Bible English doesn't (never "corrected" to a Bible word)
_MODERN = {"does", "bible", "bibles", "explain", "tell", "talk", "talks", "verse", "verses", "chapter", "about", "mean",
           "means", "meaning", "jesus", "god's", "gods", "okay", "please", "story", "stories", "today", "people", "says", "bibel"}


def _fix_spelling(question: str, bibles: list) -> tuple[str, list[tuple[str, str]]]:
    vocab: set = set()
    for _b, ix in bibles:
        vocab |= ix.vocab
    if not vocab:
        return question, []
    letters = "abcdefghijklmnopqrstuvwxyz"
    fixed = []

    def best(w: str):
        dels = [w[:i] + w[i + 1:] for i in range(len(w))]
        swaps = [w[:i] + w[i + 1] + w[i] + w[i + 2:] for i in range(len(w) - 1)]
        adds = [w[:i] + c + w[i:] for i in range(len(w) + 1) for c in letters]
        # an extra key pressed, or two keys swapped, are the safest slips to undo; a missed letter only in long words
        for group in (dels, swaps) + ((adds,) if len(w) >= 7 else ()):
            hits = sorted({x for x in group if x in vocab and len(x) > 2})
            if hits:
                return hits[0]
        return None

    def repl(m):
        w = m.group(0)
        lw = w.lower()
        if (len(lw) < 4 or not lw.isascii() or lw in vocab or lw.rstrip("s") in vocab or lw.endswith("'s")
                or lw in _STOP or lw in _MODERN):
            return w
        b = best(lw)
        if not b:
            return w
        fixed.append((w, b))
        return b
    return re.sub(r"[A-Za-z']+", repl, question), fixed


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


_XREF_CUE = re.compile(r"cross[\s-]*ref\w*|xrefs?|related verses|parallel passages", re.I)


def _xref_group(question: str, loaded: list, id_of: dict) -> Optional[Retrieval]:
    """Cross-references (OpenBible.info): from one verse, a chapter, or everything linking two books."""
    from .xref import XREFS
    if not _XREF_CUE.search(question) or not XREFS.available():
        return None
    bible, ix = next(((b, x) for b, x in loaded if x.lang == "en"), loaded[0])
    rest = _XREF_CUE.sub(" ", question)
    rest = re.sub(r"\b(show|me|all|the|any|of|for|in|from|between|with|list|find|what|are|is|there|please|s)\b", " ", rest, flags=re.I)

    def text(book, c, v, c2, v2):
        from .study import passage_text
        title = book if (book, c, v) in ix.by_ref else ix.books.resolve(book)
        if title:
            idx = ix.by_ref.get((title, c, v), [])
            if idx and (c2, v2) == (c, v):
                return ix.verses[idx[0]].text
        return passage_text(None, "", book, c, v, c2, v2)

    # two books: "Daniel to Revelation", "give me all crossreferences between daniel and revelation"
    if not re.search(r"\d+\s*[:.]\s*\d", rest):
        books = _books_named(rest, ix)
        if len(books) == 2:
            a, b = books
            links = XREFS.between(a, b)
            if links:
                shown = links[:MAX_PASSAGE]
                verses = [{"ref": f"{x['from']} → {x['to']}", "book": x["to_ref"][0], "chapter": x["to_ref"][1], "verse": x["to_ref"][2],
                           "text": text(*x["to_ref"])} for x in shown]
                note = (f"{len(links)} cross-references link {a} and {b} (OpenBible.info, 3+ reader votes), strongest first"
                        + (f"; the first {MAX_PASSAGE} are shown." if len(links) > MAX_PASSAGE else ".")
                        + " Click a verse in Read mode to see its cross-references.")
                group = {"bible": f"Cross-references: {a} ↔ {b} · {bible.name}", "id": id_of.get(bible.name),
                         "topic": True, "xref": True, "verses": verses}
                return Retrieval("xref", [group], [(v["ref"], v["text"][:400]) for v in verses[:MAX_VERSES]], note)
    # one verse or chapter: "cross references Daniel 7:13", "Daniel 7 cross references"
    idx = ix.lookup_reference(rest.strip()) if rest.strip() else None
    if not idx:
        return None
    vs = [ix.verses[i] for i in idx]
    book, ch = vs[0].book, vs[0].chapter
    seen, links = set(), []
    for v in vs:
        for x in XREFS.for_verse(book, ch, v.verse):
            k = (x["ref"])
            if k not in seen:
                seen.add(k)
                links.append((x["votes"], v.verse, x))
    if not links:
        return None
    links.sort(key=lambda t: -t[0])
    one = len({v.verse for v in vs}) == 1
    src = f"{book} {ch}:{vs[0].verse}" if one else f"{book} {ch}" + (f":{vs[0].verse}–{vs[-1].verse}" if len(vs) < 200 and idx != ix.lookup_reference(f"{book} {ch}") else "")
    verses = [{"ref": (x["ref"] if one else f"{book} {ch}:{fv} → {x['ref']}"), "book": x["book"], "chapter": x["chapter"], "verse": x["verse"],
               "text": text(x["book"], x["chapter"], x["verse"], x["end_chapter"], x["end_verse"])} for _vt, fv, x in links[:MAX_PASSAGE]]
    note = (f"{len(links)} cross-references from {src} (OpenBible.info, 3+ reader votes), strongest first"
            + (f"; the first {MAX_PASSAGE} are shown." if len(links) > MAX_PASSAGE else "."))
    group = {"bible": f"Cross-references for {src} · {bible.name}", "id": id_of.get(bible.name), "topic": True,
             "xref": True, "verses": verses}
    return Retrieval("xref", [group], [(v["ref"], v["text"][:400]) for v in verses[:MAX_VERSES]], note)


_NOT_BOOKS = {"give", "me", "all", "the", "book", "books", "of", "from", "to", "and", "between", "what", "are", "is",
              "show", "list", "find", "please", "any", "in", "with", "im", "talking", "about", "verses", "where",
              "does", "that", "there", "link", "links", "connect", "connections", "how", "can", "you", "can't",
              "i", "a", "an", "for", "on", "do", "want", "need", "see", "let", "us", "tell", "every"}


def _books_named(text: str, ix) -> list[str]:
    """Bible books named in free text, in order ("daniel and the book of revelation" -> Daniel, Revelation)."""
    found: list[str] = []
    for m in re.finditer(r"(?:\b([1-3])\s*)?\b([A-Za-z]{3,})\b", text):
        word = m[2].lower()
        if word in _NOT_BOOKS:
            continue
        cand = ix.books.resolve((m[1] + " " if m[1] else "") + word)
        if cand and (len(word) >= 4 or word == cand.lower()[-len(word):]) and cand not in found:
            found.append(cand)
    return found


def _strongs_group(question: str, loaded: list, id_of: dict) -> Optional[Retrieval]:
    import re
    from .strongs import STRONGS, normalize
    m = re.search(r"(?<![\w])([HhGg])0*(\d{1,4})(?![\w])", question)
    if not m or not STRONGS.available():
        return None
    n = normalize(m[0])
    if not n or len(tokenize(question.replace(m[0], " "))) > 3:   # "G25" yes; a long sentence that happens to contain "g7" no
        return None
    e = STRONGS.entry(n)
    if not e:
        return None
    uses = STRONGS.verses_with(n)
    bible, ix = next(((b, x) for b, x in loaded if x.lang == "en"), loaded[0])   # the numbers are on English words
    verses = []
    for (book, ch, vn), _w in uses[:MAX_PASSAGE]:
        title = book if (book, ch, vn) in ix.by_ref else ix.books.resolve(book)
        idx = ix.by_ref.get((title, ch, vn), []) if title else []
        if idx:
            verses.append(_vd(ix.verses[idx[0]]))
        else:
            verses.append({"ref": f"{book} {ch}:{vn}", "text": STRONGS.kjv_text(book, ch, vn), "book": book, "chapter": ch})
    head = f"Strong's {n} · {e['word']} ({e['translit']}, {e['pron']}) · {bible.name}"
    note = f"{e['language']} {e['word']}: {e['meaning']}" + (f". KJV: {e['kjv']}" if e["kjv"] else "") + \
        f". Used in {e['count']} verses" + (f"; the first {MAX_PASSAGE} are shown." if e["count"] > MAX_PASSAGE else ".")
    group = {"bible": head, "id": id_of.get(bible.name), "topic": True, "strongs": n, "verses": verses}
    for_model = [(f"Strong's {n}", f"{e['word']} ({e['translit']}): {e['meaning']}. KJV renders it: {e['kjv']}")] + \
        [(v["ref"], v["text"][:600]) for v in verses[:MAX_VERSES]]
    return Retrieval("strongs", [group], for_model, note)


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
