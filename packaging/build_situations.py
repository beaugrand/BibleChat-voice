"""Builds and checks 🕊 "What would Jesus do?" (the box under the phone's search field).

The situations are written by hand in packaging/situations.json. This script checks them against the Bible files and
writes web/situations.json, which the phone loads (web/situations.js).

The rules it enforces (the build stops on the first broken rule):
  * Scripture comes only from the Bible files: a situation holds references, never verse text. The headings ("point")
    are BibleChat's words, and the app labels them so.
  * Every reference exists in the King James Bible, every verse of it.
  * "What Jesus said" ("jesus") is only His words: every verse of those references carries the words of Jesus in the
    King James file's own markup (<q who="Jesus">), with the corrections the Study Paths make ("red_fix"). His words are red wherever they stand in an answer ("What Jesus did"
    too). The built file keeps where the red starts and ends, with the length
    and a fingerprint of the verse text (packaging/build_paths.py, red_marks()), so the phone colours the words of Jesus
    only in a Bible that reads exactly so, never in the wrong place. A verse that is wholly His words is red in the
    Reina-Valera 1909 and the Luther 1912 too.
  * Every situation has a title, words to recognise it, at least two sayings of Jesus, something Jesus did, more
    verses, and a prayer of the Prayers page (web/prayers.json); a Study Path it names exists (web/paths/index.json).

Usage:  python packaging/build_situations.py            (check and write web/situations.json)
        python packaging/build_situations.py --check    (check only; fails if web/situations.json is out of date)
        --src FOLDER   a folder that already holds eng-kjv.osis.xml (skips downloading)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_paths as bp  # noqa: E402

SRC = os.path.join(ROOT, "packaging", "situations.json")
OUT = os.path.join(ROOT, "web", "situations.json")
PRAYERS = os.path.join(ROOT, "web", "prayers.json")
PATHS = os.path.join(ROOT, "web", "paths", "index.json")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SituationError(Exception):
    pass


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def all_refs(s: dict) -> list[str]:
    return list(s["jesus"]) + [r for g in s["did"] + s["verses"] for r in g["refs"]]


def check_ref(B, ref: str, where: str) -> list[tuple]:
    """Every verse of the reference stands in the King James Bible."""
    try:
        book, (c1, v1), (c2, v2) = bp.parse_ref(ref)
    except bp.PathError as e:
        raise SituationError(f"{where}: {e}")
    if v1 is None:
        raise SituationError(f"{where}: {ref} names whole chapters; name the verses")
    ks = sorted(B.verses(ref, "KJV"), key=lambda k: (k[1], k[2]))
    if not ks or ks[0] != (book, c1, v1) or ks[-1] != (book, c2, v2):
        raise SituationError(f"{where}: {ref} is not in the King James Bible")
    if c1 == c2 and len(ks) != v2 - v1 + 1:
        raise SituationError(f"{where}: {ref} has verses missing in the King James Bible")
    return ks


def red_fixes(B) -> dict:
    """The hand-checked corrections of the King James red-letter markup that the Study Paths use ("red_fix", e.g. the
    "Amen" of Matthew 28:20 is not His words): {(book, ch, v): [[start, end], ...]}, [] for no red at all."""
    out = {}
    for f in sorted(glob.glob(os.path.join(bp.SRC_DIR, "*.json"))):
        for ref, pieces in (_load(f).get("red_fix") or {}).items():
            ks = B.verses(ref, "KJV")
            if len(ks) != 1:
                raise SituationError(f"{os.path.basename(f)}: red_fix {ref} must be one verse")
            t, sp = B.text["KJV"][ks[0]], []
            for piece in pieces:
                if t.count(piece) != 1:
                    raise SituationError(f"{os.path.basename(f)}: red_fix {piece!r} does not stand (once) in {ref}")
                sp.append([t.index(piece), t.index(piece) + len(piece)])
            out[ks[0]] = sorted(sp)
    return out


def build(B) -> dict:
    src = _load(SRC)
    prayers = {p["id"] for p in _load(PRAYERS)["prayers"]}
    paths = {p["id"] for p in _load(PATHS)}
    if "KJV" not in B.files:
        raise SituationError("the words of Jesus need the King James file (eng-kjv.osis.xml), which carries them")
    jw = dict(bp.jesus_words(B.files["KJV"]))
    for k, sp in red_fixes(B).items():   # the same corrections as the Study Paths
        jw[k] = (B.text["KJV"][k], sp)
    seen, red, out = set(), {}, []
    for s in src["situations"]:
        sid = s.get("id", "")
        where = f"situation {sid!r}"
        if not ID_RE.match(sid) or sid in seen:
            raise SituationError(f"{where}: the id must be new, lower case, words joined by -")
        seen.add(sid)
        for key in ("title", "words", "jesus", "did", "verses", "prayer"):
            if not s.get(key):
                raise SituationError(f"{where}: {key} is missing")
        if len(s["jesus"]) < 2:
            raise SituationError(f"{where}: name at least two sayings of Jesus")
        words = s["words"]
        if any(w != w.lower().strip() or not w for w in words) or len(set(words)) != len(words):
            raise SituationError(f"{where}: words are lower case, each once")
        for g in s["did"] + s["verses"]:
            if not g.get("point") or not g.get("refs"):
                raise SituationError(f"{where}: every group has a point and references")
        if s["prayer"] not in prayers:
            raise SituationError(f"{where}: prayer {s['prayer']!r} is not on the Prayers page (web/prayers.json)")
        if s.get("path") and s["path"] not in paths:
            raise SituationError(f"{where}: Study Path {s['path']!r} does not exist")
        for ref in all_refs(s):
            check_ref(B, ref, where)
        for ref in s["jesus"]:   # 🔴 only His words
            for k in check_ref(B, ref, where):
                if k not in jw or not jw[k][1]:
                    raise SituationError(f"{where}: {k[0]} {k[1]}:{k[2]} has no words of Jesus in the King James (What Jesus said)")
        for ref in all_refs(s):   # 🔴 His words are red wherever they stand, in "What Jesus did" too
            for k in check_ref(B, ref, where):
                vref = f"{k[0]} {k[1]}:{k[2]}"
                if k not in jw or not jw[k][1]:
                    continue
                if jw[k][0] != B.text["KJV"].get(k):
                    raise SituationError(f"{where}: the King James text of {vref} reads differently with its red-letter markup")
                if vref in red:
                    continue
                kjv_text, sp = jw[k]
                marks = [bp.mark(kjv_text, sp)]
                if sp == [[0, len(kjv_text)]]:   # wholly His words: the whole verse in the Spanish and German Bible too
                    for key, _ in bp.LANG_BIBLES.values():
                        t = B.text.get(key, {}).get(k)
                        if t:
                            marks.append(bp.mark(t, [[0, len(t)]]))
                red[vref] = marks
        out.append(s)
    return {"about": src["about"], "situations": out, "red": dict(sorted(red.items()))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--src")
    a = ap.parse_args()
    B = bp.Bibles(a.src)
    if B.missing:
        print(f"Can't check against {', '.join(B.missing)} (download failed).", file=sys.stderr)
        return 1
    try:
        data = build(B)
    except SituationError as e:
        print(f"What would Jesus do? check failed: {e}", file=sys.stderr)
        return 1
    text = bp.dumps(data)
    n = len(data["situations"])
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
            print("web/situations.json is out of date; run python packaging/build_situations.py", file=sys.stderr)
            return 1
        print(f"{n} situations OK")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{n} situations, {sum(len(all_refs(s)) for s in data['situations'])} references, "
          f"{len(data['red'])} verses with words in red -> web/situations.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
