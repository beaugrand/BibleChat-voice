"""Builds bibles/eng-yahweh-edition.usfx.xml: the World Messianic Bible with God's Name written "Yahweh".

The World Messianic Bible (eBible.org) is in the public domain. Its license asks only that a changed text is not
called "World Messianic Bible" any more, so this edition has its own name. What changes, and nothing else:
  1. God's Proper Name, written LORD or GOD in capital letters, becomes "Yahweh" (the word "the" before it is
     dropped: "the LORD" -> "Yahweh"; "Lord GOD" -> "Lord Yahweh"; all-capital "THE LORD" -> "YAHWEH");
  2. the two capital-letter words that are NOT God's Name (GOD in Acts 17:23, LORD in Revelation 19:16; the only
     ones with Greek Strong's tags) are left alone;
  3. the 41 notes that explain the capital letters say so; 4. the edition name in each book header.

Run it:
    python packaging/build_yahweh.py [engwmb_usfx.zip]   (downloads it from eBible.org if not given)
"""
import io
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://ebible.org/Scriptures/engwmb_usfx.zip"
OUT = os.path.join(ROOT, "bibles", "eng-yahweh-edition.usfx.xml")
EDITION = "Yahweh Edition, based on the World Messianic Bible, 2026-11-07"
NOTE_NEW = ("<ft>In this edition, God’s Proper Name, which the World Messianic Bible renders “LORD” or “GOD”, "
            "is written “Yahweh”.</ft>")
NOTE_RE = (r"<ft>When rendered in ALL CAPITAL LETTERS, “LORD” or “GOD” is the translation of God’s Proper "
           r"Name\.?\n?</ft>")
W = r'<w s="[^"]*">'


def convert(x: str) -> tuple[str, dict]:
    stats = {}

    def sub(pat, rep, label):
        nonlocal x
        x, stats[label] = re.subn(pat, rep, x)

    sub(r'(<w s="G\d+">)(LORD|GOD)(</w>)', r"\1@@KEEP_\2@@\3", "kept (Greek-tagged)")
    sub(NOTE_RE, "<ft>@@YNOTE@@</ft>", "notes replaced")
    sub(r"(?:" + W + r")(?:the|The)</w>\s+(" + W + r")LORD", r"\1Yahweh", "the-LORD, article tagged")
    sub(r"(?:" + W + r")THE</w>\s+(" + W + r")LORD", r"\1YAHWEH", "THE-LORD, article tagged")
    sub(r"(?<![\w’])(?:the|The)\s+(" + W + r")LORD", r"\1Yahweh", "the-LORD, article untagged")
    sub(r"(?<![\w’])THE\s+(" + W + r")LORD", r"\1YAHWEH", "THE-LORD, article untagged")
    sub(r"\b(?:the|The)\s+LORD\b", "Yahweh", "the-LORD, one text run")
    sub(r"\bTHE\s+LORD\b", "YAHWEH", "THE-LORD, one text run")
    x = re.sub(r">[^<]+<", lambda m: re.sub(r"\b(?:LORD|GOD)\b", "Yahweh", m.group(0)), x)
    x = x.replace("@@KEEP_LORD@@", "LORD").replace("@@KEEP_GOD@@", "GOD").replace("<ft>@@YNOTE@@</ft>", NOTE_NEW)
    sub(r'(<id id="[^"]*">[^<]*?)World Messianic Bible \(WMB\)(?: \d{4}-\d{2}-\d{2})?', r"\1" + EDITION,
        "book headers renamed")
    if stats["notes replaced"] != 41 or stats["kept (Greek-tagged)"] != 2 or "@@" in x:
        raise SystemExit(f"The World Messianic Bible file changed ({stats}). Check the new text, then update this script.")
    ET.fromstring(x.encode("utf-8"))   # must still be well-formed
    return x, stats


def main():
    if len(sys.argv) > 1:
        data = open(sys.argv[1], "rb").read()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "BibleChat build_yahweh.py"})
        data = urllib.request.urlopen(req, timeout=120).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        x = z.read("engwmb_usfx.xml").decode("utf-8").lstrip("﻿")
    out, stats = convert(x)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(stats)
    print("Wrote", OUT, len(out), "bytes")


if __name__ == "__main__":
    main()
