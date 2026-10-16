"""Builds the Strong's data BibleChat ships in bibleask/data/:

  strongs_kjv.json.gz   the King James Version with Strong's numbers on its words
  strongs_dict.json.gz  Strong's Hebrew and Greek dictionaries

Sources (all public domain), the CrossWire SWORD modules packaged by Debian/Ubuntu:
  sword-text-kjv (module engKJV2006eb, KJV with Strong's numbers)
  sword-dict-strongs-hebrew, sword-dict-strongs-greek (James Strong, 1890)

    apt-get download sword-text-kjv sword-dict-strongs-hebrew sword-dict-strongs-greek
    for f in *.deb; do dpkg-deb -x $f x; done
    python packaging/build_strongs.py x/usr/share/sword/modules  eng-kjv.osis.xml

The second argument is any plain KJV file BibleChat can read (e.g. eng-kjv.osis.xml from open-bibles);
it only supplies how many verses each chapter has, which the SWORD index needs.
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import struct
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bibleask.loaders import PROTESTANT_BOOKS, load_bible  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_nave import read_zld  # noqa: E402


def read_ztext(base: str):
    """SWORD zText: .bzs blocks (offset, size, raw size), .bzv verses (block, offset, size), .bzz zlib data."""
    bzs, bzv, bzz = (open(base + e, "rb").read() for e in (".bzs", ".bzv", ".bzz"))
    cache: dict[int, bytes] = {}

    def entry(n: int) -> str:
        b, off, size = struct.unpack("<IIH", bzv[n * 10:n * 10 + 10])
        if not size:
            return ""
        if b not in cache:
            o, cs, _us = struct.unpack("<III", bzs[b * 12:b * 12 + 12])
            cache[b] = zlib.decompress(bzz[o:o + cs])
        return cache[b][off:off + size].decode("utf-8", "replace")
    return entry, len(bzv) // 10


def layout(books):
    """KJV order inside a testament file: 2 module/testament headings, then per book a heading, per chapter a heading."""
    idx, n = {}, 2
    for name, chs in books:
        n += 1
        for c, count in enumerate(chs, 1):
            n += 1
            for v in range(1, count + 1):
                idx[(name, c, v)] = n
                n += 1
    return idx, n


def num(tag: str) -> str:
    return tag[0] + str(int(tag[1:]))           # H0430 -> H430


_W = re.compile(r'<w\b([^>]*)>(.*?)</w>', re.S)
_NOTE = re.compile(r'<note\b.*?</note>', re.S)
_TAG = re.compile(r'<[^>]+>')


def segments(osis: str) -> list:
    """'In the <w lemma="strong:H7225">beginning</w> ...' -> ['In the ', ['beginning', 'H7225'], ...]"""
    osis = _NOTE.sub("", osis)
    out: list = []
    pos = 0

    def plain(s: str):
        s = re.sub(r"\s+", " ", html.unescape(_TAG.sub("", s)).replace("¶", ""))
        if s:
            if out and isinstance(out[-1], str):
                out[-1] += s
            else:
                out.append(s)
    for m in _W.finditer(osis):
        plain(osis[pos:m.start()])
        word = html.unescape(_TAG.sub("", m[2]))
        nums = [num(t) for t in re.findall(r'strong:([HG]\d+)', m[1])]
        if nums and word.strip():
            out.append([word, " ".join(nums)])
        else:
            plain(word)
        pos = m.end()
    plain(osis[pos:])
    if out and isinstance(out[-1], str):
        out[-1] = out[-1].rstrip()
        if not out[-1]:
            out.pop()
    if out and isinstance(out[0], str):
        out[0] = out[0].lstrip()
        if not out[0]:
            out.pop(0)
    return out


def _clean(s: str) -> str:
    s = re.sub(r'<ref[^>]*>([^<]*)</ref>', r'\1', s)
    s = html.unescape(_TAG.sub("", s)).replace("{", "").replace("}", "")
    return re.sub(r'\s+', ' ', s).strip()


def dict_entry(raw: str) -> dict:
    orig = re.search(r'<orth>([^<]*)</orth>', raw)
    tr = re.search(r'<orth[^>]*type="trans"[^>]*>(.*?)</orth>', raw, re.S)
    pron = re.search(r'<pron[^>]*>(.*?)</pron>', raw, re.S)
    body = raw[pron.end():] if pron else raw
    body = re.sub(r'<orth[^>]*type="writing"[^>]*>.*?</orth>', "", body, flags=re.S)   # Greek in beta code
    text = _clean(body)
    m = re.search(r'\s*(?::--|:\s+-\s+)\s*', text)   # Strong's marks the KJV renderings with ":--"
    meaning, kjv = (text[:m.start()], text[m.end():]) if m else (text, "")
    return {"w": orig[1].strip() if orig else "", "t": _clean(tr[1]) if tr else "",
            "p": _clean(pron[1]) if pron else "", "d": meaning.strip(" ;"), "k": kjv.strip(" .")}


def main(mods: str, kjv_file: str, out_dir: str) -> None:
    kjv = load_bible(kjv_file)
    mx: dict = defaultdict(lambda: defaultdict(int))
    for v in kjv.verses:
        if v.book in PROTESTANT_BOOKS:
            mx[v.book][v.chapter] = max(mx[v.book][v.chapter], v.verse)
    books = [(b, [mx[b][c] for c in range(1, max(mx[b]) + 1)]) for b in PROTESTANT_BOOKS]
    verses = []
    tdir = os.path.join(mods, "texts", "ztext", "engKJV2006eb")
    for t, bs in (("ot", books[:39]), ("nt", books[39:])):
        entry, total = read_ztext(os.path.join(tdir, t))
        idx, n = layout(bs)
        assert n == total, f"{t}: verse layout {n} != index {total}"
        for (b, c, v), i in idx.items():
            seg = segments(entry(i))
            if seg:
                verses.append([b, c, v, seg])
    with gzip.open(os.path.join(out_dir, "strongs_kjv.json.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(verses, f, ensure_ascii=False, separators=(",", ":"))
    d = {}
    for letter, name in (("H", "strongshebrew"), ("G", "strongsgreek")):
        for key, raw in read_zld(os.path.join(mods, "lexdict", "zld", name, "dict")).items():
            if key.isdigit():
                d[letter + str(int(key))] = dict_entry(raw)
    with gzip.open(os.path.join(out_dir, "strongs_dict.json.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print(len(verses), "verses,", len(d), "dictionary entries")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else
         os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bibleask", "data"))
