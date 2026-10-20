"""Builds bibleask/data/versemap.json: where each verse of the two Septuagint Bibles stands in the King James.

The Septuagint numbers many verses differently: its Psalm 22 is the King James Psalm 23 ("The Lord tends me as a
shepherd"), Jeremiah 25-51 come in another order, Brenton's Malachi has no chapter 4. Strong's numbers,
cross-references, Scofield and Matthew Henry all follow the King James numbering, so without this map a reader of
the Septuagint would see the study notes of a different verse.

How: each Septuagint verse is compared with the King James verses around the same place by their shared words
(both are English). A verse moves only together with a neighbour that moves the same way (renumbering comes in
blocks); a verse that matches nothing clearly gets no King James number, and the app then shows no study notes
for it rather than wrong ones.

    python packaging/build_versemap.py [FOLDER]   (FOLDER holds eng-kjv.osis.xml and the two eBible zips)

Output: {"eng-lxx2012": {"Psalms": {"22:1": "23:1", ...}, ...}, "eng-Brenton": {...},
         "none": {"eng-lxx2012": ["Esther 1:1", ...]}}   only verses whose number changes, or that have no match.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "bibleask", "data", "versemap.json")
BIBLES = {"eng-lxx2012": "eng-lxx2012_usfx.zip", "eng-Brenton": "eng-Brenton_usfx.zip"}
STOP = set("""a an and the of to in on unto upon for with by from at as is was be been are were shall will his her
their them they he she it its i me my mine thee thou thy thine you your ye we us our not no nor but or that this these
those which who whom what there then than so all also into out up down over him himself have has had do did done
said saith say says even when if o lord god""".split())


def words(t: str) -> set:
    out = set()
    for w in re.findall(r"[a-z]+", t.lower()):
        if w in STOP or len(w) < 3:
            continue
        for suf in ("eth", "est", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def load(path: str) -> dict:
    from bibleask import catalog
    from bibleask.loaders import load_bible
    if path.endswith(".zip"):
        with open(path, "rb") as f:
            _i, data = catalog.unpack(os.path.basename(path), f.read())
        path = path[:-4] + ".usfx.xml"
        with open(path, "wb") as f:
            f.write(data)
    d: dict = {}
    for v in load_bible(path).verses:
        k = (v.book, v.chapter, v.verse)
        d[k] = d[k] + " " + v.text if k in d else v.text
    return d


def align(src: dict, kjv: dict) -> tuple[dict, list]:
    kw: dict = {}
    chapters: dict = {}
    for (b, c, v), t in kjv.items():
        kw[(b, c, v)] = words(t)
        chapters.setdefault((b, c), []).append((c, v))
    whole: dict = {}
    for (b, c, v) in kjv:
        whole.setdefault(b, []).append((c, v))
    info: dict = {}
    for (b, c, v), t in src.items():
        if b not in whole:
            continue
        a = words(t)
        if len(a) < 2:
            continue
        cands = whole[b] if b == "Jeremiah" else [k for d in (-2, -1, 0, 1, 2) for k in chapters.get((b, c + d), [])]
        sc = {}
        for (kc, kv) in cands:
            bb = kw[(b, kc, kv)]
            if bb:
                sc[(kc - c, kv - v)] = len(a & bb) / min(len(a), len(bb))
        if not sc:
            continue
        top = max(sc.values())
        best = min((o for o, x in sc.items() if x == top), key=lambda o: (o != (0, 0), abs(o[0]), abs(o[1])))
        info[(b, c, v)] = (sc, best, top, sum(1 for x in sc.values() if x >= top - 0.05) > 1)

    def own(k):
        x = info.get(k)
        return x[1] if x and x[2] >= 0.45 and not x[3] else None

    def near(b, c, v, step):
        for d in range(1, 6):
            k = (b, c, v + step * d)
            if k not in info:
                return None
            o = own(k)
            if o is not None:
                return o
        return None

    moved: dict = {}
    none: list = []
    for (b, c, v) in src:
        if (b, c, v) not in info:
            if b in whole:
                none.append(f"{b} {c}:{v}")
            continue
        sc, best, top, amb = info[(b, c, v)]
        me, P, N = own((b, c, v)), near(b, c, v, -1), near(b, c, v, 1)
        place = None
        if me == (0, 0):
            place = me
        elif me is not None:
            if me in (P, N):
                place = me
            elif sc.get((0, 0), 0) >= 0.45 and P in ((0, 0), None) and N in ((0, 0), None):
                place = (0, 0)
        else:
            O = P if P == N else (P if N is None else N if P is None else None)
            if O is not None and sc.get(O, 0) >= max(0.3, top - 0.05):
                place = O
        if place is None:
            none.append(f"{b} {c}:{v}")
        elif place != (0, 0):
            moved.setdefault(b, {})[f"{c}:{v}"] = f"{c + place[0]}:{v + place[1]}"
    return moved, none


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else tempfile.gettempdir()
    kjv = load(os.path.join(folder, "eng-kjv.osis.xml"))
    out: dict = {"none": {}}
    for bid, file in BIBLES.items():
        moved, none = align(load(os.path.join(folder, file)), kjv)
        out[bid] = moved
        out["none"][bid] = none
        print(f"{bid}: {sum(len(x) for x in moved.values())} verses under another number, {len(none)} without a match")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(OUT, os.path.getsize(OUT) // 1000, "kB")


if __name__ == "__main__":
    main()
