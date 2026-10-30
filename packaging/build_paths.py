"""Builds and checks the Study Paths (📜) for the phone and the computer.

Each path is written by hand in packaging/paths/<id>.json. This script checks it against the Bible files and
writes web/paths/<id>.json plus web/paths/index.json, which both versions of BibleChat load.

The rules it enforces (the build stops on the first broken rule):
  * Scripture comes only from the Bible files: a path holds references, never verse text. The only words of
    Scripture in a path are a word to fill in, a phrase for "which translation says this" and the word that
    proves a multiple-choice answer, and each of them is checked against the Bible it names.
  * Every step, question, fact and answer points to a reference, and every reference exists in its Bible
    (KJV for the 66 books and the Apocrypha, the Ethiopian Canon for 1 Enoch, Jubilees and the rest).
  * Every quiz answer is a verse of that path; every verse Hans listed for the path is shown in a step.
  * Commentary is only Scofield or Matthew Henry, and the app shows it under its label (tests check that).
  * Every path has a category (the filter chips above the cards) and its own picture, web/paths/img/<id>.jpg.
  * Balance: when a broad topic of the search guide (web/guide.json) points to a path, the path has a step that reads
    each theme of that topic, so a path on a topic shows every side the Bible shows (bibleask/guide.py).
  * Words of another faith (the Quran in "What does the Quran say about the Bible?") come only from the checked files
    in packaging/outside/ (packaging/build_outside.py); a step names them ("outside": ["Quran 5:47"]) next to its Bible
    verses, the app shows them in their own box labelled "not Scripture", and no quiz answer is ever one of them.

It also works out, for every question, why it is worth asking: how many cross-references point to its verse
(OpenBible.info votes), how often the path's Hebrew/Greek words occur in its verses, and how much KJV, the
Ethiopian Canon and the Berean Standard Bible differ there. The app shows the strongest questions first and says
why under each one ("12 cross-references point here").

Usage:  python packaging/build_paths.py            (check and write web/paths/)
        python packaging/build_paths.py --check    (check only; fails if web/paths/ is out of date)
        --src FOLDER   a folder that already holds eng-kjv.osis.xml and eng-bsb.usfx.xml (skips downloading)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_outside import OutsideError, load_library, split_ref  # noqa: E402

SRC_DIR = os.path.join(ROOT, "packaging", "paths")
OUT_DIR = os.path.join(ROOT, "web", "paths")
IMG_DIR = os.path.join(OUT_DIR, "img")              # one picture per path, shown on its card: img/<id>.jpg
QUOTED = os.path.join(ROOT, "web", "quoted.json")   # "Quoted or named in Scripture", hand-checked
STATUS = ("text", "disputed", "lost", "not-in-biblechat")
TYPES = ("find_the_verse", "multiple_choice", "fill_word", "which_translation")
COMPARE = ("KJV", "ETH", "BSB")
ANIMS = ("fire", "light", "mist", "rainbow", "stars", "storm")   # the moving pictures (web/paths.js draws them; still for "reduce motion")
GROUPS = "Bible Study Groups"   # the category for studies made for a Bible study group; "group" names the group's folder
NOTES = {"scofield": "Commentary (Scofield, 1917)", "henry": "Commentary (Matthew Henry, Concise)"}
FILES = {"KJV": "eng-kjv.osis.xml", "BSB": "eng-bsb.usfx.xml"}
# 🌍 a path in another app language (packaging/paths/i18n/<lang>/<id>.json) quotes the Bible of that language
LANG_BIBLES = {"es": ("RV1909", "spa-rv1909.usfx.xml"), "de": ("LUT", "deu-luther1912.osis.xml")}
I18N_DIR = os.path.join(SRC_DIR, "i18n")
REF_RE = re.compile(r"^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$")


class PathError(Exception):
    pass


# ---------------------------------------------------------------- Bibles
def parse_ref(ref: str):
    """'John 17:11-12' -> ('John', (17, 11), (17, 12)); 'Jubilees 4-5' -> whole chapters (verse None)."""
    m = REF_RE.match(ref.strip())
    if not m:
        raise PathError(f"Not a reference: {ref!r}")
    book, c1, v1, x, y = m.groups()
    c1 = int(c1)
    if v1 is None:
        return book, (c1, None), (int(x) if x else c1, None)
    v1 = int(v1)
    if x is None:
        return book, (c1, v1), (c1, v1)
    if y is None:
        return book, (c1, v1), (c1, int(x))
    return book, (c1, v1), (int(x), int(y))


class Bibles:
    """The texts a path is checked against: {"KJV": {(book, ch, v): text}, "ETH": ..., "BSB": ...}."""

    def __init__(self, src: str | None = None, download: bool = True) -> None:
        self.text: dict[str, dict] = {}
        self.order: dict[str, list] = {}
        self.missing: list[str] = []
        from bibleask.loaders import load_bible
        self._add("ETH", load_bible(os.path.join(ROOT, "bibles", "eng-ethiopian-canon.zefania.xml")).verses)
        self._add("JASHER", load_bible(os.path.join(ROOT, "bibles", "eng-jasher-1840.zefania.xml")).verses)
        for key, file in list(FILES.items()) + list(LANG_BIBLES.values()):
            path = self._find(file, src, download)
            if path:
                self._add(key, load_bible(path).verses)
            elif key == "KJV":
                self._add_builtin_kjv()   # offline: the King James text that carries the Strong's numbers
            else:
                self.missing.append(key)

    def _find(self, file: str, src: str | None, download: bool) -> str | None:
        for folder in [src, tempfile.gettempdir()]:
            if folder and os.path.exists(os.path.join(folder, file)):
                return os.path.join(folder, file)
        if not download:
            return None
        from bibleask import catalog
        path = os.path.join(tempfile.gettempdir(), file)
        try:
            from bibleask.llm import _open
            with _open(catalog.url(file)) as r, open(path + ".part", "wb") as f:
                f.write(r.read())
            os.replace(path + ".part", path)
            return path
        except Exception as e:
            print(f"Couldn't download {file}: {e}", file=sys.stderr)
            return None

    def _add(self, key: str, verses) -> None:
        d: dict = {}
        for v in verses:
            k = (v.book, v.chapter, v.verse)
            d[k] = d[k] + " " + v.text if k in d else v.text
        self.text[key] = d

    def _add_builtin_kjv(self) -> None:
        from bibleask.strongs import STRONGS
        STRONGS._load()
        d = {}
        for (b, c, v), seg in STRONGS._verses.items():
            d[(b, c, v)] = "".join(s if isinstance(s, str) else s[0] for s in seg).strip()
        self.text["KJV"] = d

    def home(self, book: str) -> str:
        """The Bible a reference is checked in: KJV when it has the book, else the Ethiopian Canon."""
        if any(k[0] == book for k in self._books("KJV")):
            return "KJV"
        return "ETH"

    def _books(self, key: str):
        if key not in self.order:
            seen = {}
            for k in self.text.get(key, {}):
                seen.setdefault((k[0], 0, 0), None)
            self.order[key] = list(seen)
        return self.order[key]

    def verses(self, ref: str, key: str | None = None) -> list[tuple]:
        book, (c1, v1), (c2, v2) = parse_ref(ref)
        key = key or self.home(book)
        d = self.text.get(key, {})
        out = []
        for k in d:
            if k[0] != book:
                continue
            if v1 is None:
                if c1 <= k[1] <= c2:
                    out.append(k)
            elif (c1, v1) <= (k[1], k[2]) <= (c2, v2):
                out.append(k)
        return out


# ---------------------------------------------------------------- checking
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')).strip().lower()


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", norm(s))


def has_word(text: str, word: str) -> bool:
    return re.search(r"(?<![A-Za-z])" + re.escape(norm(word)) + r"(?![A-Za-z])", norm(text)) is not None


def quotes_ok(text: str, keys: list, B: Bibles, strongs: list | None = None, outside: list | None = None) -> str | None:
    """Words in quotation marks inside a question or fact must stand in one of its verses (in the KJV, the Ethiopian
    Canon or the BSB), in the Strong's entry it names or in the checked words of another faith that its step shows
    (outside); "___" stands for the word to fill in. Returns the first quote that doesn't, or None."""
    from bibleask.strongs import STRONGS
    pool = [norm(B.text[k].get(v, "")) for v in keys for k in COMPARE if k not in B.missing] + [norm(t) for t in outside or []]
    for n in strongs or []:
        e = STRONGS.entry(n) or {}
        pool.append(norm(" ".join(str(e.get(f, "")) for f in ("meaning", "kjv", "translit"))))
    whole = " ".join(pool)
    for q in re.findall(r'"([^"]+)"', text):
        parts = [re.escape(norm(x).strip(" .,;:!?")) for x in q.split("___")]
        pat = r"\W*\w+\W*".join(parts) if len(parts) > 1 else parts[0]
        if not re.search(pat, whole):
            return q
    return None


def outside_texts(refs: list, lib: dict, where: str) -> list[str]:
    """The checked words of another faith that a step names ("Quran 5:47"), in every translation; PathError if one
    isn't in packaging/outside/."""
    out = []
    for r in refs:
        name, ref = split_ref(r)
        w = lib.get(name)
        if not w or ref not in w["passages"]:
            raise PathError(f"{where}: {r} is not in the checked words of packaging/outside/ (packaging/build_outside.py)")
        out += [w["passages"][ref][t["key"]] for t in w["translations"]]
    return out


def check_path(p: dict, B: Bibles, file_id: str | None = None, lib: dict | None = None) -> dict:
    """Raise PathError for the first broken rule; return facts the build needs (verses of the path, checks done)."""
    from bibleask.strongs import STRONGS
    where = f"path {p.get('id')!r}"
    if lib is None:
        try:
            lib = load_library()
        except OutsideError as e:
            raise PathError(str(e))
    path_outside: list = []
    for k in ("id", "title", "category", "opening_question", "steps", "quiz", "sources", "required_refs"):
        if not p.get(k):
            raise PathError(f"{where}: missing {k!r}")
    an = p.get("anim")
    if an is not None and an.get("kind") not in ANIMS:
        raise PathError(f"{where}: anim kind must be one of {', '.join(ANIMS)}")
    se = p.get("series")
    if se is not None and not (re.fullmatch(r"[a-z0-9-]+", str(se.get("id", ""))) and se.get("title") and isinstance(se.get("session"), int)):
        raise PathError(f"{where}: series needs an id (a-z, 0-9, -), a title and the session number")
    sd = p.get("study_date")
    if sd is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(sd)):
        raise PathError(f"{where}: study_date is the day the group studies it, written 2026-10-30")
    ra = p.get("read_along")
    if ra is not None and (not ra.get("label") or not str(ra.get("url", "")).startswith("https://")):
        raise PathError(f"{where}: read_along needs a label and an https:// link (a link only, never copied text)")
    if p["category"] == GROUPS and not (p.get("group") or "").strip():
        raise PathError(f"{where}: a path in {GROUPS!r} needs the name of its group")
    if file_id and p["id"] != file_id:
        raise PathError(f"{where}: id must match the file name {file_id!r}")
    if not re.fullmatch(r"[a-z0-9-]+", p["id"]):
        raise PathError(f"{where}: id may only use a-z, 0-9 and -")
    show = p.get("show", 8)
    if not 5 <= show <= 10:
        raise PathError(f"{where}: show 5 to 10 questions, not {show}")
    if len(p["quiz"]) <= show:
        raise PathError(f"{where}: the question bank needs more questions ({len(p['quiz'])}) than it shows ({show})")

    def refs_ok(refs, ctx):
        if not refs:
            raise PathError(f"{where}: {ctx} points to no verse")
        out = []
        for r in refs:
            vs = B.verses(r)
            if not vs:
                raise PathError(f"{where}: {ctx}: {r} is not in the {B.home(parse_ref(r)[0])}")
            book, (c1, v1), (c2, v2) = parse_ref(r)
            if v1 is not None and v2 is not None and (c2, v2) > (c1, v1):
                last = (book, c2, v2)
                if last not in B.text[B.home(book)]:
                    raise PathError(f"{where}: {ctx}: {r} goes past the end of the chapter")
            out += vs
        return out

    def strongs_ok(nums, ctx):
        for n in nums:
            if not STRONGS.entry(n):
                raise PathError(f"{where}: {ctx}: no Strong's entry {n}")

    path_verses: list = []
    strongs_ok(p.get("words", []), "words")
    for i, s in enumerate(p["steps"], 1):
        ctx = f"step {i}"
        if not (s.get("question") or "").strip():
            raise PathError(f"{where}: {ctx} has no question")
        skeys = refs_ok(s.get("refs"), ctx)
        path_verses += skeys
        sout = outside_texts(s.get("outside", []), lib, f"{where}: {ctx}")
        path_outside += sout
        bad = quotes_ok(s["question"], skeys, B, outside=sout)
        if bad:
            raise PathError(f"{where}: {ctx}: \"{bad}\" is not in the step's verses")
        bad = set(s.get("compare", [])) - set(COMPARE)
        if bad:
            raise PathError(f"{where}: {ctx}: compare only {', '.join(COMPARE)}, not {', '.join(sorted(bad))}")
        bad = set(s.get("notes", [])) - set(NOTES)
        if bad:
            raise PathError(f"{where}: {ctx}: commentary may only be {', '.join(NOTES)}, not {', '.join(sorted(bad))}")
        lc = s.get("look_closer", {})
        strongs_ok(lc.get("strongs", []), ctx)
        if lc.get("letters"):
            strongs_ok([lc["letters"]], ctx)
        for j, f in enumerate(s.get("facts", []), 1):
            if not (f.get("text") or "").strip() or not (f.get("refs") or f.get("strongs")):
                raise PathError(f"{where}: {ctx} fact {j} must say something and point to a verse or a Strong's entry")
            fkeys = refs_ok(f["refs"], f"{ctx} fact {j}") if f.get("refs") else []
            bad = quotes_ok(f["text"], fkeys, B, f.get("strongs"), sout)
            if bad:
                raise PathError(f"{where}: {ctx} fact {j}: \"{bad}\" is not in its verses or Strong's entries")
            strongs_ok(f.get("strongs", []), f"{ctx} fact {j}")
            for c in f.get("check", []):
                if c["bible"] in B.missing:
                    continue
                t = " ".join(B.text[c["bible"]].get(k, "") for k in B.verses(c["ref"], c["bible"]))
                if not has_word(t, c["word"]):
                    raise PathError(f"{where}: {ctx} fact {j}: the {c['bible']} doesn't say {c['word']!r} in {c['ref']}")
    seen = set(path_verses)
    for r in p["required_refs"]:
        missing = [k for k in refs_ok([r], "required verses") if k not in seen]
        if missing:
            raise PathError(f"{where}: {r} is on the list but no step shows {missing[0][0]} {missing[0][1]}:{missing[0][2]}")
    # 🕊 Reflect: a few things to remember, each in the text's own words, each pointing to verses of this path
    rem = p.get("remember") or []
    if not 2 <= len(rem) <= 8:
        raise PathError(f"{where}: remember needs 2 to 8 points (the Reflect page at the end), not {len(rem)}")
    for j, pt in enumerate(rem, 1):
        ctx = f"remember {j}"
        if not (pt.get("text") or "").strip():
            raise PathError(f"{where}: {ctx} says nothing")
        rkeys = refs_ok(pt.get("refs"), ctx)
        outside = [k for k in rkeys if k not in seen]
        if outside:
            raise PathError(f"{where}: {ctx}: {outside[0][0]} {outside[0][1]}:{outside[0][2]} is not a verse of this path")
        bad = quotes_ok(pt["text"], rkeys, B)
        if bad:
            raise PathError(f"{where}: {ctx}: \"{bad}\" is not in its verses")
    for i, q in enumerate(p["quiz"], 1):
        ctx = f"question {i}"
        if not (q.get("q") or "").strip():
            raise PathError(f"{where}: {ctx} has no question text")
        t = q.get("type")
        if t not in TYPES:
            raise PathError(f"{where}: {ctx}: type must be one of {', '.join(TYPES)}")
        if t in ("fill_word", "which_translation"):
            q.setdefault("answer_refs", [q.get("ref")] if q.get("ref") else [])
        ans = refs_ok(q.get("answer_refs"), ctx)
        bad = quotes_ok(q["q"], sorted(seen), B, outside=path_outside)
        if bad:
            raise PathError(f"{where}: {ctx}: \"{bad}\" is not in the verses of this path")
        outside = [k for k in ans if k not in seen]
        if outside:
            raise PathError(f"{where}: {ctx}: the answer {outside[0][0]} {outside[0][1]}:{outside[0][2]} is not a verse of this path")
        if t == "multiple_choice":
            opts, a = q.get("options") or [], q.get("answer")
            if len(opts) < 2 or not isinstance(a, int) or not 0 <= a < len(opts):
                raise PathError(f"{where}: {ctx}: needs options and the number of the right one")
            c = q.get("check") or {}
            if not c.get("word"):
                raise PathError(f"{where}: {ctx}: say which word of the verse proves the answer (check)")
            bible = c.get("bible", "KJV")
            if bible not in B.missing:
                text = " ".join(B.text[bible].get(k, "") for k in B.verses(q["answer_refs"][0], bible))
                if not has_word(text, c["word"]):
                    raise PathError(f"{where}: {ctx}: {q['answer_refs'][0]} in the {bible} doesn't say {c['word']!r}")
        if t == "fill_word":
            if len(q["answer_refs"]) != 1 or len(ans) != 1:
                raise PathError(f"{where}: {ctx}: fill in the word needs exactly one verse")
            text = B.text[q.get("bible", "KJV")].get(ans[0], "")
            if not q.get("word") or not has_word(text, q["word"]):
                raise PathError(f"{where}: {ctx}: {q['ref']} in the {q.get('bible', 'KJV')} has no word {q.get('word')!r}")
        if t == "which_translation":
            if len(ans) != 1 or q.get("bible") not in COMPARE or not q.get("phrase"):
                raise PathError(f"{where}: {ctx}: which translation needs one verse, a phrase and the Bible that says it")
            for key in COMPARE:
                if key in B.missing:
                    continue
                said = has_word(B.text[key].get(ans[0], ""), q["phrase"])
                if key == q["bible"] and not said:
                    raise PathError(f"{where}: {ctx}: the {key} doesn't say {q['phrase']!r} in {q['ref']}")
                if key != q["bible"] and said:
                    raise PathError(f"{where}: {ctx}: the {key} also says {q['phrase']!r} in {q['ref']}, so the answer isn't one translation")
    return {"verses": path_verses}


def check_quoted(B: Bibles) -> list[dict]:
    """The hand-checked list "Quoted or named in Scripture": every verse exists, every entry says its source and
    whether the writing survives; a "text" entry points to the verse in the Bible that has it."""
    with open(QUOTED, encoding="utf-8") as f:
        items = json.load(f)["items"]
    for it in items:
        ctx = f"quoted.json {it.get('ref')!r}"
        for k in ("ref", "writing", "kind", "status", "note", "source"):
            if not it.get(k):
                raise PathError(f"{ctx}: missing {k!r}")
        if it["status"] not in STATUS or it["kind"] not in ("quoted", "named"):
            raise PathError(f"{ctx}: status must be one of {', '.join(STATUS)}; kind quoted or named")
        if not B.verses(it["ref"]):
            raise PathError(f"{ctx}: no such verse")
        t = it.get("target")
        if it["status"] == "text" and not t:
            raise PathError(f"{ctx}: a writing BibleChat has needs a target verse")
        if t and t["bible"] not in B.missing and not B.verses(t["ref"], t["bible"]):
            raise PathError(f"{ctx}: {t['ref']} is not in the {t['bible']}")
    return items


# ---------------------------------------------------------------- why this question
class Signals:
    def __init__(self) -> None:
        from bibleask.xref import XREFS
        from bibleask.strongs import STRONGS
        d = XREFS._load()
        self.books = d["books"]
        self.into: dict = defaultdict(lambda: [0, 0])     # (book, ch, v) -> [links pointing here, their votes]
        self.out: dict = {}
        for key, links in d["refs"].items():
            b, c, v = (int(x) for x in key.split("."))
            self.out[(self.books[b], c, v)] = links
            for tb, tc, tv, tc2, tv2, votes in links:
                if votes <= 0:
                    continue
                if tc2 == tc:
                    for n in range(tv, tv2 + 1):
                        e = self.into[(self.books[tb], tc, n)]; e[0] += 1; e[1] += votes
                else:
                    e = self.into[(self.books[tb], tc, tv)]; e[0] += 1; e[1] += votes
        STRONGS._load()
        self.strongs = STRONGS
        self.quoted: dict = {}     # (book, ch, v) -> "Quoted in Jude 1:14-15" / "Named in Scripture"
        self.B = None

    def add_quoted(self, items: list, B: "Bibles") -> None:
        for it in items:
            for k in B.verses(it["ref"]):
                self.quoted.setdefault(k, f"{it['writing']}: {'quoted' if it['kind'] == 'quoted' else 'named'} here")
            t = it.get("target")
            if t and it["status"] == "text":
                for k in B.verses(t["ref"], t["bible"]):
                    self.quoted[k] = f"Quoted in {it['ref']}"

    def numbers(self, k) -> list[str]:
        seg = self.strongs._verses.get(k) or []
        out = []
        for s in seg:
            if not isinstance(s, str):
                out += [n for n in s[1].split() if re.fullmatch(r"[HG]\d+", n)]
        return out

    def for_question(self, q: dict, p: dict, B: Bibles, path_verses: list) -> dict:
        ans = []
        for r in q["answer_refs"]:
            ans += B.verses(r)
        links = max((self.into[k][0] for k in ans), default=0)
        votes = max((self.into[k][1] for k in ans), default=0)
        words = set(p.get("words", []))
        for s in p["steps"]:
            words |= set(s.get("look_closer", {}).get("strongs", []))
        count: dict = defaultdict(int)
        for k in set(path_verses):
            for n in self.numbers(k):
                if n in words:
                    count[n] += 1
        best, best_n = None, 0
        for k in ans:
            for n in self.numbers(k):
                if n in words and count[n] > best_n:
                    best, best_n = n, count[n]
        differ = 0.0
        for k in ans:
            texts = [set(words_of(B.text[key].get(k, ""))) for key in COMPARE if key not in B.missing and B.text[key].get(k)]
            if len(texts) >= 2:
                pairs = [(a, b) for i, a in enumerate(texts) for b in texts[i + 1:]]
                differ = max(differ, 1 - sum(len(a & b) / max(1, len(a | b)) for a, b in pairs) / len(pairs))
        quoted = next((self.quoted[k] for k in ans if k in self.quoted), None)
        return {"xref": links, "votes": votes, "word": best, "word_count": best_n, "differ": round(differ, 3), "quoted": quoted}


def words_of(s: str) -> list[str]:
    return words(s)


def why(sig: dict, strongs) -> list[str]:
    out = []
    if sig["xref"]:
        out.append(f"{sig['xref']} cross-reference{'s' if sig['xref'] != 1 else ''} point here")
    if sig["word"] and sig["word_count"] >= 2:
        e = strongs.entry(sig["word"])
        out.append(f"The {e['language']} word {e['translit'].split()[0]} ({sig['word']}) is in {sig['word_count']} verses of this path")
    if sig["differ"] >= 0.5:
        out.append("Translations differ here")
    if sig.get("quoted"):
        out.append(sig["quoted"])
    return out


def score(sig: dict) -> float:
    return round(0.45 * min(1, math.log1p(sig["votes"]) / math.log1p(400)) + 0.35 * min(1, sig["word_count"] / 12)
                 + 0.20 * min(1, sig["differ"] / 0.8) + (0.4 if sig.get("quoted") else 0), 4)


# ---------------------------------------------------------------- build
def sha(path: str) -> str:
    """Fingerprint of a source file. Line endings don't count: Windows checks text files out with \r\n."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()[:16]


def embed_outside(p: dict, lib: dict) -> None:
    """Put the checked words into the built path: each step gets its boxes (the label, then every translation with its
    name and year) and the path lists the translations it used, with their sources."""
    used = {}
    for s in p["steps"]:
        if not s.get("outside"):
            continue
        boxes = []
        for r in s["outside"]:
            name, ref = split_ref(r)
            w = lib[name]
            used[name] = w
            boxes.append({"ref": r, "label": w["label"], "why": w["why"],
                          "texts": [{"name": t["name"], "text": w["passages"][ref][t["key"]]} for t in w["translations"]]})
        s["outside"] = boxes
    if used:
        p["outside_sources"] = [{"name": t["name"], "about": t["about"], "source": t["source"], "url": t["url"]}
                                for w in used.values() for t in w["translations"]]


def build(B: Bibles) -> dict[str, dict]:
    from bibleask.strongs import STRONGS
    try:
        lib = load_library()
    except OutsideError as e:
        raise PathError(str(e))
    sig = Signals()
    sig.add_quoted(check_quoted(B), B)
    out: dict[str, dict] = {}
    for f in sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            p = json.load(fh)
        info = check_path(p, B, os.path.basename(f)[:-5], lib)
        for q in p["quiz"]:
            s = sig.for_question(q, p, B, info["verses"])
            q["signals"], q["why"], q["score"] = s, why(s, STRONGS), score(s)
        p["verse_count"] = len(set(info["verses"]))
        embed_outside(p, lib)
        if not os.path.exists(os.path.join(IMG_DIR, p["id"] + ".jpg")):
            raise PathError(f"path {p['id']!r}: no picture web/paths/img/{p['id']}.jpg for its card")
        p["image"] = "img/" + p["id"] + ".jpg"
        p["labels"] = NOTES
        p["built_from"] = {"file": "packaging/paths/" + os.path.basename(f), "sha": sha(f),
                           "checked_in": [k for k in ("KJV", "ETH", "BSB") if k not in B.missing]}
        tr = translations(p, B)
        if tr:
            p["i18n"] = tr
        out[p["id"]] = p
    balance(out)
    return out


def translations(p: dict, B: Bibles) -> dict:
    """🌍 The path in Spanish and German, from packaging/paths/i18n/<lang>/<id>.json:
    {"title", "opening_question", "steps": [{"question", "facts": [text, ...]}, ...], "remember": [text, ...]}.
    It must have every step, fact and point of the English path, in the same order. Words in "straight quotes"
    are Scripture and must stand in that language's Bible (Reina-Valera 1909, Luther 1912) in the chapters the
    verses are in or next to them (Luther, for one, numbers Daniel 4:1-3 as 3:31-33). Word meanings from Strong's
    (an English dictionary) go in «guillemets» (Spanish) or »guillemets« (German), which are not checked.
    The quiz stays in English: its questions test English wording."""
    out = {}
    for lang, (key, _) in LANG_BIBLES.items():
        f = os.path.join(I18N_DIR, lang, p["id"] + ".json")
        if not os.path.exists(f):
            continue
        where = f"path {p['id']!r} ({lang})"
        with open(f, encoding="utf-8") as fh:
            t = json.load(fh)
        for k in ("title", "opening_question"):
            if not str(t.get(k) or "").strip():
                raise PathError(f"{where}: missing {k!r}")
        if len(t.get("steps", [])) != len(p["steps"]):
            raise PathError(f"{where}: {len(t.get('steps', []))} steps, the English has {len(p['steps'])}")
        if len(t.get("remember", [])) != len(p.get("remember", [])):
            raise PathError(f"{where}: {len(t.get('remember', []))} things to remember, the English has {len(p.get('remember', []))}")

        def pool(refs):
            keys = set()
            for r in refs:
                book, (c1, _), (c2, _) = parse_ref(r)
                keys |= {k for k in B.text[key] if k[0] == book and c1 - 1 <= k[1] <= c2 + 1}
            return " ".join(norm(B.text[key][k]) for k in keys)

        def quotes(text, refs, ctx):
            if not str(text).strip():
                raise PathError(f"{where}: {ctx} is empty")
            whole = None
            for q in re.findall(r'"([^"]+)"', text):
                whole = whole if whole is not None else pool(refs)
                if norm(q).strip(" .,;:!?¿¡") not in whole:
                    raise PathError(f"{where}: {ctx}: \"{q}\" is not in the {key} near {', '.join(refs)}")

        every = [r for s in p["steps"] for r in s["refs"]]
        quotes(t["title"], every, "title")
        quotes(t["opening_question"], every, "opening question")
        for i, (s, ts) in enumerate(zip(p["steps"], t["steps"]), 1):
            facts = s.get("facts", [])
            if len(ts.get("facts", [])) != len(facts):
                raise PathError(f"{where}: step {i} has {len(ts.get('facts', []))} facts, the English has {len(facts)}")
            quotes(ts.get("question"), s["refs"], f"step {i}")
            for j, (fe, ft) in enumerate(zip(facts, ts["facts"]), 1):
                quotes(ft, (fe.get("refs") or []) + s["refs"], f"step {i} fact {j}")
        for j, (re_, rt) in enumerate(zip(p.get("remember", []), t.get("remember", [])), 1):
            quotes(rt, re_["refs"], f"remember {j}")
        out[lang] = t
    return out


def balance(paths: dict[str, dict]) -> None:
    """The balance rule: a topic of the search guide (web/guide.json) that points to a Study Path lists every side the
    Bible shows as a theme, and the path must have a step that reads each of them (bibleask/guide.py)."""
    from bibleask import guide
    for t in guide.load().get("topics", []):
        pid = t.get("path")
        if not pid:
            continue
        if pid not in paths:
            raise PathError(f"web/guide.json: topic {t['id']!r} points to a Study Path that doesn't exist: {pid!r}")
        miss = guide.missing_themes(t, paths[pid])
        if miss:
            raise PathError(f"path {pid!r}: no step reads the theme(s) of the search topic {t['id']!r}: " + "; ".join(miss))


def minutes(p: dict) -> int:
    """About how long a path takes: reading its verses, thinking about each step, answering the questions."""
    m = 0.25 * p["verse_count"] + 3 * len(p["steps"]) + p.get("show", 8) + sum(len(s.get("outside", [])) for s in p["steps"])   # + a minute per box of another faith's words
    return max(10, int(5 * round(m / 5)))


def index(paths: dict[str, dict]) -> list[dict]:
    """What the cards need without loading every path: picture, category, size, time and the step questions."""
    return [{"id": p["id"], "title": p["title"], "category": p["category"], "image": p["image"],
             "opening_question": p["opening_question"], "steps": len(p["steps"]),
             "step_questions": [s["question"] for s in p["steps"]],
             "books": sorted({parse_ref(r)[0] for s in p["steps"] for r in s["refs"]}   # a search for "Genesis" or "Daniel" finds the path
                            | {b["ref"].rpartition(" ")[0] for s in p["steps"] for b in s.get("outside", [])}),   # ...and "Quran"
             "show": p.get("show", 8), "verses": p["verse_count"], "minutes": minutes(p),
             **{k: p[k] for k in ("group", "study_date", "read_along", "anim", "series") if p.get(k)},
             **({"i18n": {l: {"title": t["title"], "opening_question": t["opening_question"],
                              "step_questions": [s["question"] for s in t["steps"]]} for l, t in p["i18n"].items()}}
                if p.get("i18n") else {})}
            for p in paths.values()]


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--src")
    a = ap.parse_args()
    B = Bibles(a.src)
    if B.missing:
        print(f"Can't check against {', '.join(B.missing)} (download failed).", file=sys.stderr)
        return 1
    try:
        paths = build(B)
    except PathError as e:
        print(f"Study path check failed: {e}", file=sys.stderr)
        return 1
    files = {f"{pid}.json": dumps(p) for pid, p in paths.items()}
    files["index.json"] = dumps(index(paths))
    if a.check:
        stale = [n for n, s in files.items() if not os.path.exists(os.path.join(OUT_DIR, n))
                 or open(os.path.join(OUT_DIR, n), encoding="utf-8").read() != s]
        if stale:
            print("web/paths is out of date; run python packaging/build_paths.py: " + ", ".join(stale), file=sys.stderr)
            return 1
        print(f"{len(paths)} study paths OK")
        return 0
    os.makedirs(OUT_DIR, exist_ok=True)
    for n in os.listdir(OUT_DIR):
        if n.endswith(".json") and n not in files:
            os.remove(os.path.join(OUT_DIR, n))
    for n, s in files.items():
        with open(os.path.join(OUT_DIR, n), "w", encoding="utf-8") as f:
            f.write(s)
    for p in paths.values():
        shown = sorted(p["quiz"], key=lambda q: -q["score"])[:p.get("show", 8)]
        print(f"{p['id']:26} {len(p['steps'])} steps {p['verse_count']:4} verses {len(p['quiz']):2} questions, top: "
              + "; ".join(f"{q['score']:.2f} {q['why'][:1]}" for q in shown[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
