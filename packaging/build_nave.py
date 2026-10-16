"""Builds bibleask/data/nave.json.gz, the topic index BibleChat searches alongside the verses.

Source: Nave's Topical Bible (Orville J. Nave, 1896; public domain), as the CrossWire SWORD module
"Nave" packaged by Debian/Ubuntu ("sword-dict-naves", from https://ccel.org/ccel/n/nave/bible.xml).

    apt-get download sword-dict-naves && dpkg-deb -x sword-dict-naves_*.deb x
    python packaging/build_nave.py x/usr/share/sword/modules/lexdict/zld/nave/nave

Output: [[topic, heading, [osisRef, ...]], ...]  one row per line of a topic that lists verses.
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


def read_zld(base: str) -> dict[str, str]:
    """Read a SWORD zLD dictionary (.idx/.dat keys, .zdx/.zdt zlib blocks)."""
    idx, dat = open(base + ".idx", "rb").read(), open(base + ".dat", "rb").read()
    zdx, zdt = open(base + ".zdx", "rb").read(), open(base + ".zdt", "rb").read()
    blocks: dict[int, tuple[bytes, list]] = {}

    def block(n: int):
        if n not in blocks:
            off, sz = struct.unpack("<II", zdx[n * 8:n * 8 + 8])
            raw = zlib.decompress(zdt[off:off + sz])
            cnt = struct.unpack("<I", raw[:4])[0]
            blocks[n] = (raw, [struct.unpack("<II", raw[4 + i * 8:12 + i * 8]) for i in range(cnt)])
        return blocks[n]

    out = {}
    for i in range(len(idx) // 8):
        off, sz = struct.unpack("<II", idx[i * 8:i * 8 + 8])
        key, rest = dat[off:off + sz].split(b"\r\n", 1)
        raw, ents = block(struct.unpack("<II", rest[:8])[0])
        o, s = ents[struct.unpack("<II", rest[:8])[1]]
        out[key.decode()] = raw[o:o + s].decode("utf-8", "replace").rstrip("\x00")
    return out


# one-chapter books were mis-tagged in the module: <ref osisRef="Jude.1.1">Jude 1</ref>:6  means Jude 1:6
_ONE_CH = re.compile(r'<ref osisRef="(Jude|Obad|Phlm|2John|3John)\.1\.1">[^<]*</ref>:(\d+)(?:-(\d+))?')


def _fix(t: str) -> str:
    return _ONE_CH.sub(lambda m: f'<ref osisRef="{m[1]}.1.{m[2]}' + (f'-{m[1]}.1.{m[3]}' if m[3] else "") + '">x</ref>', t)


def rows(entries: dict[str, str]) -> list:
    out = []
    for topic, body in entries.items():
        body = _fix(body)
        parent = ""
        # each <lb/> or <item> starts a line: "heading text  <refs>"
        for kind, piece in re.findall(r"(<lb/>|<item>)(.*?)(?=<lb/>|<item>|</def>|$)", body, re.S):
            refs = re.findall(r'osisRef="([^"]+)"', piece)
            see = re.findall(r'target="Nave:([^"]+)"', piece)
            text = re.sub(r"<ref[^>]*>.*?</ref>", " ", piece, flags=re.S)
            text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("→", " ").replace("&#", " ")
            text = re.sub(r"[\s;:,.]+", " ", re.sub(r"\b\d+[\d:,;\- ]*", " ", text)).strip()
            if kind == "<lb/>":
                parent = text
                heading = text
            else:
                heading = (parent + " — " + text).strip(" —") if parent else text
            if refs:
                out.append([topic, heading, refs])
            elif see:
                out.append([topic, heading, ["see:" + s for s in see]])
    return out


if __name__ == "__main__":
    data = rows(read_zld(sys.argv[1]))
    dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bibleask", "data", "nave.json.gz")
    with gzip.open(dest, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(len(data), "lines,", sum(len(r[2]) for r in data), "references ->", dest, os.path.getsize(dest), "bytes")
