"""Builds bibleask/data/meaning/ (search by meaning) from BGE-small-en v1.5 (BAAI, MIT license) and the
Berean Standard Bible (public domain).

    python packaging/build_meaning.py MODEL_DIR eng-bsb.usfx.xml [--vectors bsb_vectors.npy]

MODEL_DIR holds the model's model.safetensors and vocab.txt from huggingface.co/BAAI/bge-small-en-v1.5.
Weights are stored as signed bytes, one scale per row (about a quarter of the size; answers barely change).
Verse fingerprints are made with the full model through "transformers" when it is installed (much faster),
otherwise with BibleChat's own engine; --vectors reuses fingerprints saved earlier (float array, one row per
verse of the 66 books in Bible order).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bibleask.loaders import PROTESTANT_BOOKS, load_bible  # noqa: E402

OUT = os.path.join(ROOT, "bibleask", "data", "meaning")
PREFIX = "Represent this sentence for searching relevant passages: "   # the model's own wording for questions
PART = 8 << 20          # model file parts of at most 8 MB (the phone loads them one by one)
VERSES_PER_PART = 4000  # about 1.6 MB each


def quantize_model(model_dir: str) -> None:
    from safetensors.numpy import load_file
    t = load_file(os.path.join(model_dir, "model.safetensors"))
    with open(os.path.join(model_dir, "config.json")) as f:
        cfg = json.load(f)
    blob, tensors = bytearray(), {}

    def put(arr: np.ndarray) -> int:
        while len(blob) % 4:
            blob.append(0)
        off = len(blob)
        blob.extend(arr.tobytes())
        return off

    for name, w in t.items():
        if name.startswith("pooler.") or name.endswith("position_ids"):
            continue
        w = w.astype(np.float32)
        if w.ndim == 2:
            scale = np.maximum(np.abs(w).max(1), 1e-12) / 127.0
            q = np.clip(np.round(w / scale[:, None]), -127, 127).astype(np.int8)
            off = put(q)
            tensors[name] = ["i8", list(w.shape), off, put(scale.astype(np.float32))]
        else:
            tensors[name] = ["f32", list(w.shape), put(w), 0]
    parts = [bytes(blob[i:i + PART]) for i in range(0, len(blob), PART)]
    for i, p in enumerate(parts):
        with open(os.path.join(OUT, f"model.{i}.bin"), "wb") as f:
            f.write(p)
    keep = ("hidden_size", "num_attention_heads", "num_hidden_layers", "intermediate_size", "max_position_embeddings")
    with open(os.path.join(OUT, "model.json"), "w") as f:
        json.dump({"name": "BAAI/bge-small-en-v1.5", "license": "MIT", "config": {k: cfg[k] for k in keep},
                   "query_prefix": PREFIX, "pooling": "cls", "parts": [len(p) for p in parts], "tensors": tensors}, f)
    shutil.copy(os.path.join(model_dir, "vocab.txt"), os.path.join(OUT, "vocab.txt"))
    print(f"model: {len(blob) / 1e6:.1f} MB in {len(parts)} parts")


def verse_vectors(model_dir: str, texts: list[str]) -> np.ndarray:
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        from bibleask.meaning import Meaning
        m = Meaning(OUT)
        return np.stack([m.embed(t, query=False) for t in texts])
    tok, model = AutoTokenizer.from_pretrained(model_dir), AutoModel.from_pretrained(model_dir).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 64):
            b = tok(texts[i:i + 64], padding=True, truncation=True, max_length=512, return_tensors="pt")
            out.append(torch.nn.functional.normalize(model(**b).last_hidden_state[:, 0], dim=-1).numpy())
    return np.concatenate(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir")
    ap.add_argument("bsb")
    ap.add_argument("--vectors")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    quantize_model(a.model_dir)
    books = list(PROTESTANT_BOOKS)
    verses = [v for v in load_bible(a.bsb).verses if v.book in books]
    vec = np.load(a.vectors).astype(np.float32) if a.vectors else verse_vectors(a.model_dir, [v.text for v in verses])
    assert len(vec) == len(verses), (len(vec), len(verses))
    vec /= np.linalg.norm(vec, axis=1, keepdims=True)
    scale = np.abs(vec).max(1)
    q = np.clip(np.round(vec / scale[:, None] * 127), -127, 127).astype(np.int8)
    counts = []
    for i in range(0, len(verses), VERSES_PER_PART):
        with open(os.path.join(OUT, f"verses.{len(counts)}.bin"), "wb") as f:
            f.write(q[i:i + VERSES_PER_PART].tobytes() + scale[i:i + VERSES_PER_PART].astype(np.float32).tobytes())
        counts.append(len(q[i:i + VERSES_PER_PART]))
    with open(os.path.join(OUT, "verses.json"), "w") as f:
        json.dump({"bible": "Berean Standard Bible", "books": books, "dim": int(vec.shape[1]), "parts": counts,
                   "refs": [[books.index(v.book), v.chapter, v.verse] for v in verses]}, f, separators=(",", ":"))
    print(f"verses: {len(verses)} in {len(counts)} parts, {q.nbytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
