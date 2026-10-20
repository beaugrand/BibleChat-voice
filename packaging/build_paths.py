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

SRC_DIR = os.path.join(ROOT, "packaging", "paths")
OUT_DIR = os.path.join(ROOT, "web", "paths")
QUOTED = os.path.join(ROOT, "web", "quoted.json")   # "Quoted or named in Scripture", hand-checked
STATUS = ("text", "disputed", "lost", "not-in-biblechat")
TYPES = ("find_the_verse", "multiple_choice", "fill_word", "which_translation")
COMPARE = ("KJV", "ETH", "BSB")
NOTES = {"scofield": "Commentary (Scofield, 1917)", "henry": "Commentary (Matthew Henry, Concise)"}
FILES = {"KJV": "eng-kjv.osis.xml", "BSB": "eng-bsb.usfx.xml"}
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
        for key, file in FILES.items():
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


def quotes_ok(text: str, keys: list, B: Bibles, strongs: list | None = None) -> str | None:
    """Words in quotation marks inside a question or fact must stand in one of its verses (in the KJV, the Ethiopian
    Canon or the BSB) or in the Strong's entry it names; "___" stands for the word to fill in. Returns the first
    quote that doesn't, or None."""
    from bibleask.strongs import STRONGS
    pool = [norm(B.text[k].get(v, "")) for v in keys for k in COMPARE if k not in B.missing]
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


def check_path(p: dict, B: Bibles, file_id: str | None = None) -> dict:
    """Raise PathError for the first broken rule; return facts the build needs (verses of the path, checks done)."""
    from bibleask.strongs import STRONGS
    where = f"path {p.get('id')!r}"
    for k in ("id", "title", "opening_question", "steps", "quiz", "sources", "required_refs"):
        if not p.get(k):
            raise PathError(f"{where}: missing {k!r}")
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
        bad = quotes_ok(s["question"], skeys, B)
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
            bad = quotes_ok(f["text"], fkeys, B, f.get("strongs"))
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
        bad = quotes_ok(q["q"], sorted(seen), B)
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
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def build(B: Bibles) -> dict[str, dict]:
    from bibleask.strongs import STRONGS
    sig = Signals()
    sig.add_quoted(check_quoted(B), B)
    out: dict[str, dict] = {}
    for f in sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            p = json.load(fh)
        info = check_path(p, B, os.path.basename(f)[:-5])
        for q in p["quiz"]:
            s = sig.for_question(q, p, B, info["verses"])
            q["signals"], q["why"], q["score"] = s, why(s, STRONGS), score(s)
        p["verse_count"] = len(set(info["verses"]))
        p["labels"] = NOTES
        p["built_from"] = {"file": "packaging/paths/" + os.path.basename(f), "sha": sha(f),
                           "checked_in": [k for k in ("KJV", "ETH", "BSB") if k not in B.missing]}
        out[p["id"]] = p
    return out


def index(paths: dict[str, dict]) -> list[dict]:
    return [{"id": p["id"], "title": p["title"], "opening_question": p["opening_question"], "steps": len(p["steps"]),
             "show": p.get("show", 8), "verses": p["verse_count"]} for p in paths.values()]


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
