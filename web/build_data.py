"""Builds the data for the phone/web version of BibleChat (the site in this folder).

For every Bible in bibleask/catalog.py it downloads the XML from the pinned open-bibles address,
reads it with BibleChat's own tested readers, and writes a compact JSON file the browser loads:

    {"id": "...", "name": "...", "books": [{"n": "Genesis", "c": [[1, [[1, "In the beginning..."], ...]], ...]}, ...]}

Usage:  python web/build_data.py OUT_DIR [--src FOLDER_WITH_XML_FILES]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bibleask import catalog  # noqa: E402
from bibleask.loaders import load_bible, _USFX_NAME, _BOOK_CODES  # noqa: E402

with open(os.path.join(ROOT, "bibleask", "data", "booknames.json"), encoding="utf-8") as _f:
    BOOKNAMES = json.load(_f)   # book names per language, from the SWORD locales (packaging/build_booknames.py)


def bible_id(file: str) -> str:
    return re.sub(r"(\.(osis|usfx|zefania)\.xml|_usfx\.zip)$", "", file)


def lang_key(bid: str) -> str:
    return "chi-simp" if bid.startswith("chi-") and "simp" in bid else bid.split("-")[0]


def source_names(path: str) -> dict:
    """Book names printed in the Bible file itself (USFX <h>/<toc>, Zefania bname), by English name."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            s = f.read()
    except OSError:
        return {}
    out = {}
    for code, body in re.findall(r'<book id="(\w+)">(.{0,600})', s, re.S):
        m = re.search(r"<h>\s*([^<]+?)\s*</h>", body) or re.search(r'<toc level="1">\s*([^<]+?)\s*</toc>', body)
        if m and code in _USFX_NAME:
            out[_USFX_NAME[code]] = m.group(1).strip()
    for num, name in re.findall(r'<BIBLEBOOK[^>]*bnumber="(\d+)"[^>]*bname="([^"]+)"', s):
        if 1 <= int(num) <= 66:
            out[_BOOK_CODES[int(num) - 1][2]] = name.strip()
    return out


def to_web(bible, bid: str, name: str, local: dict | None = None) -> dict:
    books: list[dict] = []
    index: dict[str, dict] = {}
    for v in bible.verses:
        b = index.get(v.book)
        if b is None:
            b = index[v.book] = {"n": v.book, "c": []}
            if local and local.get(v.book) and local[v.book] != v.book:
                b["l"] = local[v.book]   # the book's name in the Bible's own language
            books.append(b)
        if not b["c"] or b["c"][-1][0] != v.chapter:
            b["c"].append([v.chapter, []])
        vs = b["c"][-1][1]
        if vs and vs[-1][0] == v.verse:  # a long verse split for the desktop search: join it again
            vs[-1][1] += " " + v.text
        else:
            vs.append([v.verse, v.text])
    return {"id": bid, "name": name, "books": books}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--src", help="folder that already holds the XML files (skips downloading)")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "data"), exist_ok=True)
    listing, localized = [], []
    for e in catalog.entries():
        bid = bible_id(e["file"])
        if a.src:
            path = os.path.join(a.src, e["file"])
        else:
            path = os.path.join(tempfile.gettempdir(), e["file"])
            if not os.path.exists(path):
                print("downloading", e["file"], flush=True)
                from bibleask.llm import _open   # the same download the app does
                try:
                    with _open(catalog.url(e["file"])) as r, open(path, "wb") as f:
                        f.write(r.read())
                except Exception as err:
                    raise SystemExit(f"Download failed: {catalog.url(e['file'])}: {err}")
        if path.endswith(".zip"):   # eBible.org: the USFX XML is inside the zip
            with open(path, "rb") as f:
                inner, data = catalog.unpack(e["file"], f.read())
            path = path[:-4] + ".usfx.xml"
            with open(path, "wb") as f:
                f.write(data)
        b = load_bible(path)
        local = dict(BOOKNAMES.get(lang_key(bid), {}))
        if not bid.startswith("eng"):
            local.update(source_names(path))
        web = to_web(b, bid, e["name"], local)
        n = sum(len(vs) for bk in web["books"] for _, vs in bk["c"])
        out = os.path.join(a.out, "data", bid + ".json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(web, f, ensure_ascii=False, separators=(",", ":"))
        if any("l" in bk for bk in web["books"]):
            localized.append(bid)
        listing.append({"id": bid, "name": e["name"], "abbr": e["abbr"] or e["title"],
                        "language": e["language"], "license": e["license"], "note": e["note"],
                        "verses": n, "books": len(web["books"]), "bytes": os.path.getsize(out)})
        print(f"{bid:28} {len(web['books']):3} books {n:6} verses {os.path.getsize(out) / 1e6:5.1f} MB", flush=True)
    print(f"::notice::Book names in the Bible's own language for {len(localized)} Bibles: {', '.join(localized)}", flush=True)
    with open(os.path.join(a.out, "data", "catalog.json"), "w", encoding="utf-8") as f:
        json.dump({"source": catalog.SOURCE, "commit": catalog.COMMIT, "bibles": listing}, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
