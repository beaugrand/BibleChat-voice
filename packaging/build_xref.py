"""Builds bibleask/data/xref.json.gz: cross-references between verses.

Source: OpenBible.info cross-references (https://www.openbible.info/labs/cross-references/), CC-BY,
as kept by the Scrollmapper project:
    https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/extras/cross_references.txt
Each line links a verse to a verse or passage and carries readers' votes (how helpful the link is).
Links with fewer than MIN_VOTES votes are left out.

Output: {"books": [names...], "refs": {"<book#>.<ch>.<v>": [[book#, ch, v, ch2, v2, votes], ...]}}
(strongest first; ch2/v2 = end of the passage, equal to ch/v for a single verse)

    python packaging/build_xref.py cross_references.txt
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bibleask.loaders import PROTESTANT_BOOKS, _OSIS_NAME  # noqa: E402

MIN_VOTES = 3
_REF = re.compile(r"(\w+)\.(\d+)\.(\d+)$")


def main(src: str, out: str) -> None:
    books = list(PROTESTANT_BOOKS)
    num = {b: i for i, b in enumerate(books)}
    refs: dict = defaultdict(dict)
    for line in open(src, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3 or not p[2].lstrip("-").isdigit():
            continue
        votes = int(p[2])
        if votes < MIN_VOTES:
            continue
        a = _REF.match(p[0])
        t1, _, t2 = p[1].partition("-")
        b, e = _REF.match(t1), _REF.match(t2) if t2 else None
        if not a or not b:
            continue
        fa, fb = _OSIS_NAME.get(a[1]), _OSIS_NAME.get(b[1])
        if fa not in num or fb not in num:
            continue
        ch2, v2 = (int(e[2]), int(e[3])) if e and e[1] == b[1] else (int(b[2]), int(b[3]))
        key = f"{num[fa]}.{a[2]}.{a[3]}"
        item = (num[fb], int(b[2]), int(b[3]), ch2, v2)
        refs[key][item] = max(votes, refs[key].get(item, 0))
    data = {"books": books,
            "refs": {k: [list(i) + [v] for i, v in sorted(d.items(), key=lambda x: -x[1])] for k, d in refs.items()}}
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(data, f, separators=(",", ":"))
    print(len(data["refs"]), "verses,", sum(len(v) for v in data["refs"].values()), "links ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "bibleask", "data", "xref.json.gz"))
