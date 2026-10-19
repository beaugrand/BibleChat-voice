"""Search by meaning: a small sentence model turns a question into a "meaning fingerprint" (384 numbers) and
compares it with a fingerprint made beforehand for every verse of the Berean Standard Bible.

The model is BGE-small-en v1.5 (BAAI, MIT license), stored with 8-bit weights. It runs here with numpy only
(no special processor instructions, so it also works on older processors without AVX2). The phone version runs
the very same files in plain JavaScript (web/index.html), so both give the same answers.

Data, built by packaging/build_meaning.py:
  bibleask/data/meaning/vocab.txt        the model's word pieces
  bibleask/data/meaning/model.json       where each weight sits in model.<i>.bin (8-bit rows with a scale each)
  bibleask/data/meaning/verses.json      {"bible", "books", "refs": [[book#, ch, v], ...], "parts": [count, ...]}
  bibleask/data/meaning/verses.<i>.bin   count x 384 signed bytes, then count float32 scales
If anything is missing (or numpy isn't there), meaning search is simply off and the word search still works.
"""
from __future__ import annotations

import json
import os
import threading
import unicodedata
from typing import Optional

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "meaning")


# --------------------------------------------------------------------------- word pieces (BERT, lower case)
def _is_punct(ch: str) -> bool:
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


def _is_cjk(cp: int) -> bool:
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF or 0x2A700 <= cp <= 0x2B81F
            or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)


def basic_words(text: str) -> list[str]:
    """Lower case, accents off, split at spaces and punctuation (each punctuation mark is its own word)."""
    out, cur = [], []
    text = unicodedata.normalize("NFD", text.lower())
    for ch in text:
        cp = ord(ch)
        if cp == 0 or cp == 0xFFFD or unicodedata.category(ch) == "Mn":
            continue
        if unicodedata.category(ch) in ("Cc", "Cf") and ch not in "\t\n\r":
            continue
        if ch.isspace():
            if cur:
                out.append("".join(cur)); cur = []
        elif _is_punct(ch) or _is_cjk(cp):
            if cur:
                out.append("".join(cur)); cur = []
            out.append(ch)
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


class WordPiece:
    def __init__(self, vocab: list[str]):
        self.ids = {w: i for i, w in enumerate(vocab)}
        self.unk, self.cls, self.sep = self.ids["[UNK]"], self.ids["[CLS]"], self.ids["[SEP]"]

    def encode(self, text: str, max_len: int = 512) -> list[int]:
        out = [self.cls]
        for w in basic_words(text):
            if len(w) > 100:
                out.append(self.unk)
                continue
            pieces, start = [], 0
            while start < len(w):
                end, hit = len(w), None
                while start < end:
                    sub = ("##" if start else "") + w[start:end]
                    if sub in self.ids:
                        hit = self.ids[sub]
                        break
                    end -= 1
                if hit is None:
                    pieces = [self.unk]
                    break
                pieces.append(hit)
                start = end
            out.extend(pieces)
        return out[:max_len - 1] + [self.sep]


# --------------------------------------------------------------------------- the model
def _erf(x, np):
    # Abramowitz & Stegun 7.1.26 (error below 1.5e-7); the phone uses the same formula
    s = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    return s * y


class Meaning:
    def __init__(self, data_dir: str = _DIR) -> None:
        self.data_dir = data_dir
        self._lock = threading.Lock()
        self._ready: Optional[bool] = None
        self._full: dict = {}
        self.error = ""

    def available(self) -> bool:
        return os.path.exists(os.path.join(self.data_dir, "model.json")) and \
            os.path.exists(os.path.join(self.data_dir, "verses.json"))

    def _load(self) -> bool:
        with self._lock:
            if self._ready is not None:
                return self._ready
            try:
                import numpy as np
                self.np = np
                with open(os.path.join(self.data_dir, "vocab.txt"), encoding="utf-8") as f:
                    self.tok = WordPiece(f.read().split("\n"))
                with open(os.path.join(self.data_dir, "model.json"), encoding="utf-8") as f:
                    head = json.load(f)
                blob = b"".join(open(os.path.join(self.data_dir, f"model.{i}.bin"), "rb").read()
                                for i in range(len(head["parts"])))
                self.cfg, self.prefix = head["config"], head["query_prefix"]
                self.w = {}
                for name, (kind, shape, off, soff) in head["tensors"].items():
                    n = 1
                    for s in shape:
                        n *= s
                    if kind == "i8":
                        q = np.frombuffer(blob, np.int8, n, off).reshape(shape)
                        sc = np.frombuffer(blob, np.float32, shape[0], soff)
                        self.w[name] = (q, sc)
                    else:
                        self.w[name] = np.frombuffer(blob, np.float32, n, off).reshape(shape)
                with open(os.path.join(self.data_dir, "verses.json"), encoding="utf-8") as f:
                    vj = json.load(f)
                self.books, self.refs, dim = vj["books"], [tuple(r) for r in vj["refs"]], vj["dim"]
                self.parts = []
                for i, cnt in enumerate(vj["parts"]):
                    with open(os.path.join(self.data_dir, f"verses.{i}.bin"), "rb") as f:
                        raw = f.read()
                    self.parts.append((np.frombuffer(raw, np.int8, cnt * dim).reshape(cnt, dim),
                                       np.frombuffer(raw, np.float32, cnt, cnt * dim)))
                self._ready = True
            except Exception as e:   # no numpy, missing or broken files: word search carries on alone
                self.error = f"{type(e).__name__}: {e}"
                self._ready = False
            return self._ready

    def _lin(self, x, name):
        w = self._full.get(name)
        if w is None:   # unpacked once from 8 bits (about 85 MB in memory for the whole model), then reused
            q, sc = self.w[name + ".weight"]
            w = self._full[name] = self.np.ascontiguousarray((q.astype(self.np.float32) * sc[:, None]).T)
        return x @ w + self.w[name + ".bias"]

    def _norm(self, x, name):
        np = self.np
        m = x.mean(-1, keepdims=True)
        v = ((x - m) ** 2).mean(-1, keepdims=True)
        return (x - m) / np.sqrt(v + 1e-12) * self.w[name + ".weight"] + self.w[name + ".bias"]

    def embed(self, text: str, query: bool = True):
        """The meaning fingerprint of a text: 384 numbers, length 1."""
        if not self._load():
            return None
        np = self.np
        ids = self.tok.encode((self.prefix if query else "") + text, 512)
        word_q, word_s = self.w["embeddings.word_embeddings.weight"]
        pos_q, pos_s = self.w["embeddings.position_embeddings.weight"]
        typ_q, typ_s = self.w["embeddings.token_type_embeddings.weight"]
        n = len(ids)
        x = word_q[ids].astype(np.float32) * word_s[ids, None] + pos_q[:n].astype(np.float32) * pos_s[:n, None] \
            + typ_q[0].astype(np.float32) * typ_s[0]
        x = self._norm(x, "embeddings.LayerNorm")
        heads = self.cfg["num_attention_heads"]
        hd = x.shape[1] // heads
        for i in range(self.cfg["num_hidden_layers"]):
            p = f"encoder.layer.{i}."
            q = self._lin(x, p + "attention.self.query").reshape(n, heads, hd).transpose(1, 0, 2)
            k = self._lin(x, p + "attention.self.key").reshape(n, heads, hd).transpose(1, 0, 2)
            v = self._lin(x, p + "attention.self.value").reshape(n, heads, hd).transpose(1, 0, 2)
            a = q @ k.transpose(0, 2, 1) / np.sqrt(hd)
            a = np.exp(a - a.max(-1, keepdims=True))
            a /= a.sum(-1, keepdims=True)
            ctx = (a @ v).transpose(1, 0, 2).reshape(n, heads * hd)
            x = self._norm(x + self._lin(ctx, p + "attention.output.dense"), p + "attention.output.LayerNorm")
            h = self._lin(x, p + "intermediate.dense")
            h = 0.5 * h * (1.0 + _erf(h / np.sqrt(2.0), np))
            x = self._norm(x + self._lin(h, p + "output.dense"), p + "output.LayerNorm")
        e = x[0]   # the [CLS] position carries the sentence's meaning in this model
        return e / max(float(np.linalg.norm(e)), 1e-9)

    def knows(self, word: str) -> bool:
        """Is this a whole word in the model's English vocabulary ("worry" yes, "asdf" no)?"""
        return self._load() and word.lower() in self.tok.ids

    def similarities(self, query: str) -> Optional[dict]:
        """How close every verse is to the question in meaning: {(book, chapter, verse): similarity}."""
        scores = self._scores(query)
        if scores is None:
            return None
        return {(self.books[b], c, v): float(x) for (b, c, v), x in zip(self.refs, scores)}

    def _scores(self, query: str):
        q = self.embed(query)
        if q is None:
            return None
        np = self.np
        return np.concatenate([(m @ q.astype(np.float32)) * s / 127.0 for m, s in self.parts])

    def search(self, query: str, k: int = 50) -> list[tuple[tuple[str, int, int], float]]:
        """The verses closest in meaning: [((book, chapter, verse), similarity 0..1), ...], best first."""
        scores = self._scores(query)
        if scores is None:
            return []
        np = self.np
        top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
        top = top[np.argsort(-scores[top])]
        return [((self.books[self.refs[i][0]], self.refs[i][1], self.refs[i][2]), float(scores[i])) for i in top]


MEANING = Meaning()
