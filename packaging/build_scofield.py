"""Builds bibleask/data/scofield.json.gz: the Scofield Reference Notes (1917 edition, public domain).

Source: the CrossWire SWORD module "Scofield" (version 2.1, text from Wikisource), packaged by Debian/Ubuntu
as sword-comm-scofield. Its own licence line reads "DistributionLicense=Public Domain".

    apt-get download sword-comm-scofield && dpkg-deb -x sword-comm-scofield_*.deb x
    python packaging/build_scofield.py x/usr/share/sword/modules/comments/zcom/scofield eng-kjv.osis.xml

The second argument is any plain KJV file (for the number of verses per chapter, which the index needs).
Output: {"books": [...], "notes": {"<book#>.<ch>.<v>": "note text", ...}}
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bibleask.loaders import PROTESTANT_BOOKS, load_bible  # noqa: E402
from build_strongs import layout, read_ztext  # noqa: E402


def clean(osis: str) -> str:
    """OSIS -> plain text with paragraphs (blank lines), **keyword** for the verse words a note explains,
    and "• " for list items."""
    t = re.sub(r"<note\b.*?</note>", "", osis, flags=re.S)
    t = re.sub(r'<hi type="bold">(.*?)</hi>', lambda m: "\n\n**" + m[1].strip() + "**\n", t, flags=re.S)
    t = re.sub(r"<item\b[^>]*>", "\n• ", t)
    t = re.sub(r'<div [^>]*type="x-p"[^>]*/>', "\n", t)
    t = re.sub(r"<(lb|p|br)\b[^>]*/?>|</(p|div|list)>|<list\b[^>]*>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\*\*\n+", "** ", t)            # keyword runs into its explanation
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"(?<!\n)\n(?!\n|• )", " ", t)      # single breaks inside a paragraph
    return t.strip()


def main(mod: str, kjv_file: str, out: str) -> None:
    kjv = load_bible(kjv_file)
    mx: dict = defaultdict(lambda: defaultdict(int))
    for v in kjv.verses:
        if v.book in PROTESTANT_BOOKS:
            mx[v.book][v.chapter] = max(mx[v.book][v.chapter], v.verse)
    books = list(PROTESTANT_BOOKS)
    shape = [(b, [mx[b][c] for c in range(1, max(mx[b]) + 1)]) for b in books]
    notes = {}
    for t, part, offset in (("ot", shape[:39], 0), ("nt", shape[39:], 39)):
        entry, total = read_ztext(os.path.join(mod, t))
        idx, n = layout(part)
        assert n == total, (t, n, total)
        for (b, c, v), i in idx.items():
            text = clean(entry(i))
            if text:
                notes[f"{books.index(b)}.{c}.{v}"] = text
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump({"books": books, "notes": notes}, f, ensure_ascii=False, separators=(",", ":"))
    print(len(notes), "notes ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "bibleask", "data", "scofield.json.gz"))
