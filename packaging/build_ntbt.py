"""Builds bibles/spa-ntbt.usfx.xml: the Nueva Traducción BibliaTodo (NTBT), a Spanish Bible of 66 books.

The NTBT is published by BibliaTodo Bible Society (an imprint of BibliaTodo LLC). It is free to use and share,
including in apps, with no royalties, under BibliaTodo's free agreement (LICENCIA.txt in the download, version 1.4).
The agreement asks for three things, and this file and BibleChat keep all three:
  1. the wording is kept exactly, brackets included (this script only changes the file format, to USFX);
  2. the official credit, with a link to https://www.bibliatodo.org/es/ntbt/, is shown in the Bibles list;
  3. anything BibleChat adds (notes, answers) is kept apart from the NTBT text.
Hans W. Beaugrand registered BibleChat with BibliaTodo for this, as the agreement asks.

The download is pinned to one exact delivery (checked by its SHA-256), so the text can't change underneath us.
For a new delivery: change DELIVERY and SHA256, run this again, and check the verse count.

    python packaging/build_ntbt.py [NTBT-json.zip]   (downloads it if not given)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

URL = "https://downloads.bibliatodo.org/texto/NTBT-json.zip"   # the Bible text edition, without study notes
DELIVERY = "NTBT-2026-11-06"
SHA256 = "1f5f7be551e66915204186b2befb47e59f98c082972480a1a47f2c6383739942"
OUT = os.path.join(ROOT, "bibles", "spa-ntbt.usfx.xml")
CREDIT = ("Santa Biblia, Nueva Traducción BibliaTodo (NTBT). Publicada por BibliaTodo Bible Society, "
          "sello editorial de BibliaTodo LLC. https://www.bibliatodo.org/es/ntbt/")


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            data = f.read()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "BibleChat build_ntbt.py"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != SHA256:
        raise SystemExit(f"The NTBT download changed (SHA-256 {got}). Check the new delivery, then update DELIVERY and SHA256.")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        d = json.loads(z.read("NTBT.json").decode("utf-8"))
    if d.get("identificacion") != DELIVERY:
        raise SystemExit(f"Expected delivery {DELIVERY}, got {d.get('identificacion')}")
    # USFX, like the eBible.org files: book codes (GEN, MAT ...) give BibleChat the English book names it uses
    # everywhere, and <h> carries the Spanish name the Bible itself prints (shown in the reader).
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             f"<!-- Nueva Traducción BibliaTodo (NTBT). {escape(CREDIT)} Delivery {DELIVERY}, Bible text edition, "
             "converted to USFX by BibleChat's packaging/build_ntbt.py with the wording unchanged. -->",
             '<usfx xmlns:xsi="http://eBible.org/usfx.xsd" xsi:noNamespaceSchemaLocation="usfx.xsd">',
             '<languageCode>spa</languageCode>']
    books = verses = 0
    for b in d["libros"]:
        parts.append(f'<book id="{b["codigo"]}"><h>{escape(b["nombre"])}</h>')
        books += 1
        for ch in b["capitulos"]:
            parts.append(f'<c id="{ch["numero"]}" />')
            for v in ch["versiculos"]:
                t = re.sub(r"\s+", " ", v["texto"]).strip()
                if t:
                    parts.append(f'<v id="{v["numero"]}" />{escape(t)}<ve />')
                    verses += 1
        parts.append("</book>")
    parts.append("</usfx>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"{books} books, {verses} verses -> {OUT}")


if __name__ == "__main__":
    main()
