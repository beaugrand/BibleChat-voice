"""Builds bibles/eng-jasher-1840.zefania.xml: the Book of Jasher in its 1840 English translation (public domain),
as transcribed by the Scrollmapper project (pinned to one exact version, so the text can't change underneath us).

The 1840 book (published in New York by M. M. Noah and A. S. Gould) calls itself the Book of Jasher named in
Joshua 10:13 and 2 Samuel 1:18. Scholars dispute whether it is that book; BibleChat says so wherever it shows it.

    python packaging/build_jasher.py [book-of-jasher.json]   (downloads it if not given)
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT = "271173ef8be658239edcb4fc753cd39d2b2731d3"
URL = (f"https://raw.githubusercontent.com/scrollmapper/bible_databases_deuterocanonical/{COMMIT}"
       "/sources/en/book-of-jasher/book-of-jasher.json")
OUT = os.path.join(ROOT, "bibles", "eng-jasher-1840.zefania.xml")
LABEL = "The 1840 English Jasher; scholars dispute whether it is the book named in Joshua 10:13."


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            d = json.load(f)
    else:
        with urllib.request.urlopen(URL, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
    book = d["books"][0]
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             '<XMLBIBLE biblename="Book of Jasher (1840)" type="x-bible">',
             f"<INFORMATION><title>Book of Jasher (1840)</title><description>{escape(LABEL)} Public-domain English "
             f"translation of 1840, transcribed by the Scrollmapper project (commit {COMMIT[:12]}).</description>"
             "<rights>Public Domain</rights></INFORMATION>",
             '<BIBLEBOOK bnumber="1" bname="Jasher">']
    n = 0
    for ch in book["chapters"]:
        parts.append(f'<CHAPTER cnumber="{ch["chapter"]}">')
        for v in ch["verses"]:
            t = re.sub(r"\s+", " ", v["text"]).strip()
            if t:
                parts.append(f'<VERS vnumber="{v["verse"]}">{escape(t)}</VERS>')
                n += 1
        parts.append("</CHAPTER>")
    parts += ["</BIBLEBOOK>", "</XMLBIBLE>"]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"{len(book['chapters'])} chapters, {n} verses -> {OUT}")


if __name__ == "__main__":
    main()
