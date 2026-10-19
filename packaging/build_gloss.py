"""Builds bibleask/data/strongs_gloss.json.gz: which Hebrew and Greek words mean each English word or phrase
("sea monster" -> H8577 tannin), made from the Strong's dictionary and the KJV with Strong's numbers.
Making it takes several seconds, so BibleChat ships it ready. Run this again after packaging/build_strongs.py.

    python packaging/build_gloss.py
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bibleask.strongs import STRONGS, build_gloss_index  # noqa: E402

if __name__ == "__main__":
    STRONGS._load()
    index = build_gloss_index(STRONGS._dict, STRONGS._where)
    path = os.path.join(ROOT, "bibleask", "data", "strongs_gloss.json.gz")
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(json.dumps(index, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    print(f"{len(index['terms'])} English words and phrases, {len(index['info'])} Hebrew/Greek words, "
          f"{os.path.getsize(path) / 1e3:.0f} KB")
