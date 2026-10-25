"""Checks the words of other faiths that a Study Path sets beside the Bible (packaging/outside/<work>.json).

Some Study Paths compare what another faith's book says with what the Bible says ("What does the Quran say about the
Bible?"). Those words are never Scripture: the app shows them in their own box, labelled "not Scripture", with the
translator's name and year, and no question is ever answered from them. This file makes sure every word is real:

  * The Quran in George Sale's translation (1734, the first English one made from the Arabic) must stand word for word
    in Project Gutenberg's text (eBook #7440). Sale didn't number the verses, so a passage is the run of his text that
    matches the standard verse numbers. Gutenberg prints footnote letters glued to words ("himp were"); they don't count.
    A typing slip of Gutenberg's is corrected only when the passage lists it under "sale_fixes".
  * The Quran in Marmaduke Pickthall's translation (1930) must equal the Tanzil.net text of it, verse by verse, except
    where the passage lists a difference under "pickthall_1930": places where the 1930 London printing reads otherwise
    (Tanzil writes "Allah" where Pickthall printed "God" in 4:171, 5:73 and 29:46, and drops "barter not" in 5:44).

Usage:  python packaging/build_outside.py            (download both texts, check every passage)
        --src FOLDER   a folder that already holds quran-sale-1734.txt and quran-pickthall.txt
The Study Paths build (packaging/build_paths.py) reads the same files with load_library() and puts the checked words
into each step that names them.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(ROOT, "packaging", "outside")
SALE_URL = "https://www.gutenberg.org/cache/epub/7440/pg7440.txt"
PICKTHALL_URL = "https://tanzil.net/trans/?transID=en.pickthall&type=txt-2"
FILES = {"quran-sale-1734.txt": SALE_URL, "quran-pickthall.txt": PICKTHALL_URL}
REF_RE = re.compile(r"^(\d+):(\d+)(?:-(\d+))?$")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


class OutsideError(Exception):
    pass


def load_library() -> dict[str, dict]:
    """{"Quran": {work info, "passages": {"5:47": {...}}}} from packaging/outside/*.json, with its own checks:
    a label that says "not Scripture", the translators named, every passage in every translation."""
    out = {}
    for f in sorted(glob.glob(os.path.join(LIB_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            w = json.load(fh)
        name = w.get("name") or ""
        if not name or "not Scripture" not in w.get("label", "") or not w.get("why") or not w.get("translations"):
            raise OutsideError(f"{os.path.basename(f)}: needs a name, a label that says \"not Scripture\", why it is shown and its translations")
        keys = [t["key"] for t in w["translations"]]
        for t in w["translations"]:
            if not (t.get("name") and t.get("source") and str(t.get("url", "")).startswith("https://")):
                raise OutsideError(f"{name}: translation {t.get('key')!r} needs its name and year, its source and a link")
        ps = {}
        for p in w["passages"]:
            if not REF_RE.match(p.get("ref", "")):
                raise OutsideError(f"{name}: not a chapter:verse reference: {p.get('ref')!r}")
            for k in keys:
                if not (p.get(k) or "").strip():
                    raise OutsideError(f"{name} {p['ref']}: no {k} text")
            ps[p["ref"]] = p
        out[name] = dict(w, passages=ps)
    return out


def split_ref(ref: str):
    """'Quran 4:157-158' -> ('Quran', '4:157-158')."""
    name, _, r = ref.strip().rpartition(" ")
    return name, r


# ---------------------------------------------------------------- the sources
def fetch(src: str | None) -> dict[str, str]:
    texts = {}
    for name, url in FILES.items():
        path = next((os.path.join(d, name) for d in (src, tempfile.gettempdir()) if d and os.path.exists(os.path.join(d, name))), None)
        if not path:
            path = os.path.join(tempfile.gettempdir(), name)
            req = urllib.request.Request(url, headers={"User-Agent": "BibleChat build (github.com/beaugrand/BibleChat-voice)"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path + ".part", "wb") as f:
                f.write(r.read())
            os.replace(path + ".part", path)
        with open(path, encoding="utf-8") as f:
            texts[name] = f.read()
    return texts


def roman(s: str) -> int:
    return sum(-ROMAN[c] if i + 1 < len(s) and ROMAN[s[i + 1]] > ROMAN[c] else ROMAN[c] for i, c in enumerate(s))


def sale_chapters(text: str) -> dict[int, str]:
    """Sale's text, chapter by chapter, without the footnotes (Gutenberg puts each footnote on a line starting with a tab)."""
    lines = text.replace("\r\n", "\n").split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip() == "CHAPTER I." and i > len(lines) // 6)
    ch: dict[int, list] = {}
    cur, kind = None, None
    for l in lines[start:]:
        if l.startswith("*** END"):
            break
        m = re.match(r"^\s*CHAPTER ([IVXLC]+)\.?\s*$", l)
        if m:
            cur, kind = roman(m.group(1)), None
            ch[cur] = []
            continue
        if cur is None:
            continue
        if re.match(r"^ {5}\S", l) or re.match(r"^\d+\t", l):
            kind = "v"; ch[cur].append(re.sub(r"^\d+\t", "", l).strip())
        elif l.startswith("\t"):
            kind = "f"
        elif l.strip() and kind == "v" and not l.isupper():
            ch[cur][-1] += " " + l.strip()
    # a footnote letter right after a stop or comma ("thereof.l Therefore") is not Sale's word
    return {c: re.sub(r"(?<=[.,;:!?])[a-z]{1,2}(?=\s|$)", "", " ".join(ps)) for c, ps in ch.items()}


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-zâêîôûà']+", s.lower().replace("’", "'"))


def sale_ok(passage: str, chapter: str) -> bool:
    """Every word of the passage, in order, in Sale's chapter; a footnote letter glued to a word is allowed."""
    words = tokens(passage.replace("…", " "))
    pat = r"[^a-zâêîôûà']+".join(re.escape(w) + r"[a-z]?" for w in words)
    return re.search(r"(?<![a-zâêîôûà'])" + pat, " ".join(tokens(chapter))) is not None


def pickthall_verses(text: str) -> dict[tuple, str]:
    out = {}
    for l in text.splitlines():
        p = l.split("|", 2)
        if len(p) == 3 and p[0].isdigit():
            out[(int(p[0]), int(p[1]))] = p[2]
    return out


def check(lib: dict, texts: dict) -> int:
    sale = sale_chapters(texts["quran-sale-1734.txt"])
    pick = pickthall_verses(texts["quran-pickthall.txt"])
    n = 0
    for p in lib["Quran"]["passages"].values():
        c, v1, v2 = (int(x) if x else None for x in REF_RE.match(p["ref"]).groups())
        s = p["sale"]
        for fx in p.get("sale_fixes", []):
            s = s.replace(fx["1734"], fx["gutenberg"])
        if not sale_ok(s, sale.get(c, "")):
            raise OutsideError(f"Quran {p['ref']}: Sale's words are not in his chapter {c} (Gutenberg #7440)")
        t = " ".join(pick[(c, v)] for v in range(v1, (v2 or v1) + 1))
        for d in p.get("pickthall_1930", []):
            if d["tanzil"] not in t:
                raise OutsideError(f"Quran {p['ref']}: Tanzil doesn't read {d['tanzil']!r}")
            t = t.replace(d["tanzil"], d["1930"], 1)
        if t != p["pickthall"]:
            raise OutsideError(f"Quran {p['ref']}: Pickthall's words differ from Tanzil (list a 1930 reading under pickthall_1930)")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    a = ap.parse_args()
    try:
        n = check(load_library(), fetch(a.src))
    except OutsideError as e:
        print(f"Check of the other faiths' words failed: {e}", file=sys.stderr)
        return 1
    print(f"{n} Quran passages OK in Sale (1734) and Pickthall (1930)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
