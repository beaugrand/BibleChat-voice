"""Builds bibleask/data/booknames.json: Bible book names in many languages, so BibleChat can show
"1. Mose" or "创世记" instead of "Genesis" for a German or Chinese Bible.

Source: the locale files of The SWORD Project (CrossWire), Ubuntu package libsword-common,
folder usr/share/sword/locales.d. Book names are plain facts; the SWORD files are GPL-2.

Usage: python packaging/build_booknames.py PATH/TO/locales.d
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bibleask.loaders import _BOOK_CODES  # noqa: E402

# SWORD locale file -> our language key (the language part of a BibleChat Bible id)
LOCALES = {"bg": "bul", "zh_Hans": "chi-simp", "zh_Hant": "chi", "cs": "cze", "da": "dan", "de": "deu", "nl": "dut",
           "fi": "fin", "fr": "fra", "hr": "hrv", "hu": "hun", "it": "ita", "ja": "jpn", "ko": "kor", "la": "lat",
           "lv": "lav", "nb": "nor", "pl": "pol", "pt": "por", "ro": "ron", "ru": "rus", "es": "spa", "sv": "swe",
           "th": "tha", "tr": "tur", "vi": "vie", "uk": "ukr", "el": "gre", "he": "heb", "ar": "ara", "id": "ind"}
ENGLISH = {n for _, _, n in _BOOK_CODES}


def ours(sword_name: str) -> str:
    n = re.sub(r"^III ", "3 ", re.sub(r"^II ", "2 ", re.sub(r"^I ", "1 ", sword_name.strip())))
    return {"Revelation of John": "Revelation", "Song of Songs": "Song of Solomon", "Psalm": "Psalms"}.get(n, n)


def read(path: str) -> dict:
    out, section = {}, ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):
                section = line
                continue
            if section == "[Text]" and "=" in line:
                k, v = line.split("=", 1)
                k = ours(k)
                if k in ENGLISH and v.strip() and not k.isupper():
                    out[k] = v.strip()
    return out


def main() -> None:
    src = sys.argv[1]
    table = {}
    for loc, key in LOCALES.items():
        p = os.path.join(src, loc + "-utf8.conf")
        if os.path.exists(p):
            names = read(p)
            if len(names) >= 60:
                table[key] = names
    dest = os.path.join(ROOT, "bibleask", "data", "booknames.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"{len(table)} languages -> {dest}")


if __name__ == "__main__":
    main()
