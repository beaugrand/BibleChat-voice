"""Builds two study aids BibleChat ships in bibleask/data/:

  mhcc.json.gz    Matthew Henry's Concise Commentary on the Whole Bible (public domain), from the CrossWire
                  SWORD module "MHCC" (Debian/Ubuntu package sword-comm-mhcc; text from CCEL)
                  {"books": [...], "notes": {"<book#>.<ch>.<v>": "text", ...}}  (a note starts at the
                  first verse of the passage it explains)
  easton.json.gz  Easton's Bible Dictionary (M. G. Easton, 1897; public domain), as parsed from CCEL by
                  the NEUU bible-dictionary-dataset (https://github.com/neuu-org/bible-dictionary-dataset,
                  CC BY 4.0): {"babylon": ["Babylon", "text"], ...}

    apt-get download sword-comm-mhcc && dpkg-deb -x sword-comm-mhcc_*.deb x
    git clone --depth 1 https://github.com/neuu-org/bible-dictionary-dataset ed
    python packaging/build_henry_easton.py x/usr/share/sword/modules/comments/zcom/mhcc eng-kjv.osis.xml ed
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import struct
import sys
import zlib
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bibleask.loaders import PROTESTANT_BOOKS, load_bible  # noqa: E402
from build_scofield import clean  # noqa: E402
from build_strongs import layout, read_ztext  # noqa: E402


def build_mhcc(mod: str, kjv_file: str, out: str) -> None:
    kjv = load_bible(kjv_file)
    mx: dict = defaultdict(lambda: defaultdict(int))
    for v in kjv.verses:
        if v.book in PROTESTANT_BOOKS:
            mx[v.book][v.chapter] = max(mx[v.book][v.chapter], v.verse)
    books = list(PROTESTANT_BOOKS)
    shape = [(b, [mx[b][c] for c in range(1, max(mx[b]) + 1)]) for b in books]
    notes = {}
    for t, part in (("ot", shape[:39]), ("nt", shape[39:])):
        # one note covers a whole passage: the module links every verse of it to the same text,
        # so keep it once, at the passage's first verse
        entry, total = read_ztext(os.path.join(mod, t))
        bzv = open(os.path.join(mod, t) + ".bzv", "rb").read()
        idx, n = layout(part)
        assert n == total, (t, n, total)
        seen = set()
        for (b, c, v), i in sorted(idx.items(), key=lambda kv: kv[1]):
            where = bzv[i * 10:i * 10 + 10]
            if where in seen:
                continue
            seen.add(where)
            text = clean(entry(i))
            if text:
                notes[f"{books.index(b)}.{c}.{v}"] = text
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump({"books": books, "notes": notes}, f, ensure_ascii=False, separators=(",", ":"))
    print(len(notes), "Matthew Henry notes ->", out)


def build_easton(dataset: str, out: str) -> None:
    d = {}
    for f in sorted(glob.glob(os.path.join(dataset, "data", "02_sources", "easton", "[a-z].json"))):
        for _key, e in json.load(open(f, encoding="utf-8")).items():
            texts = [x["text"] for x in e.get("definitions", []) if x.get("source") == "EAS" and x.get("text")]
            if texts:
                d[e["name"].lower()] = [e["name"], "\n\n".join(t.strip() for t in texts)]
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print(len(d), "Easton entries ->", out)


if __name__ == "__main__":
    data = os.path.join(ROOT, "bibleask", "data")
    build_mhcc(sys.argv[1], sys.argv[2], os.path.join(data, "mhcc.json.gz"))
    build_easton(sys.argv[3], os.path.join(data, "easton.json.gz"))
