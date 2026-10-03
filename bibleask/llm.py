"""The small free AI model: pick one from Hugging Face, download it once, run it on this computer.

We use GGUF files (compact, CPU-friendly copies of open models) through llama-cpp-python.
The model is only asked to explain the verses that search found - it never supplies verses itself.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from .storage import models_dir


@dataclass(frozen=True)
class ModelChoice:
    label: str
    repo: str  # Hugging Face "owner/name"
    note: str
    style: str = "general"  # "bible" = trained for Bible Q&A with verses supplied; "general" = ordinary chat model


# Small models that run on ordinary laptops. Sizes are for the 4-bit "Q4_K_M" file.
MODELS: list[ModelChoice] = [
    ModelChoice("Bible Assistant 4B  (made for Bible questions, about 2.7 GB, slower)",
                "mradermacher/Bible-Assistant-Qwen3.5-4B-v3.2-GGUF", "2.7 GB", style="bible"),
    ModelChoice("Qwen2.5 1.5B Instruct  (general, about 1.1 GB, fast)", "Qwen/Qwen2.5-1.5B-Instruct-GGUF", "1.1 GB"),
    ModelChoice("Llama 3.2 1B Instruct  (about 0.8 GB, smallest)", "bartowski/Llama-3.2-1B-Instruct-GGUF", "0.8 GB"),
    ModelChoice("Llama 3.2 3B Instruct  (about 2.0 GB, smarter)", "bartowski/Llama-3.2-3B-Instruct-GGUF", "2.0 GB"),
    ModelChoice("Qwen2.5 3B Instruct  (about 2.1 GB, smarter)", "Qwen/Qwen2.5-3B-Instruct-GGUF", "2.1 GB"),
]

ProgressCB = Callable[[str, float], None]  # message, 0..1


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _open(url: str, headers: Optional[dict] = None):
    req = urllib.request.Request(url, headers={"User-Agent": "BibleAsk/1.0", **(headers or {})})
    return urllib.request.urlopen(req, timeout=30, context=_ssl_context())


def style_for_repo(repo: str) -> str:
    for m in MODELS:
        if m.repo.lower() == repo.lower():
            return m.style
    return "bible" if "bible-assistant" in repo.lower() else "general"


def passages_wanted(style: str) -> int:
    """The Bible Assistant was trained with exactly 8 retrieved verses; other models cope with a few more."""
    return 8 if style == "bible" else 12


def repo_from_text(text: str) -> str:
    """Accepts 'owner/name' or a full huggingface.co link."""
    t = text.strip()
    t = re.sub(r"^https?://huggingface\.co/", "", t).strip("/")
    t = t.split("/tree/")[0].split("/blob/")[0].split("?")[0]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", t):
        raise ValueError("Please enter a Hugging Face model as owner/name, for example Qwen/Qwen2.5-1.5B-Instruct-GGUF")
    return t


def pick_gguf_file(repo: str) -> str:
    """Ask Hugging Face which .gguf files the repo has and pick the 4-bit medium one."""
    with _open(f"https://huggingface.co/api/models/{repo}") as r:
        info = json.load(r)
    files = [s["rfilename"] for s in info.get("siblings", []) if s["rfilename"].lower().endswith(".gguf")]
    files = [f for f in files if "-of-" not in f.lower()]  # skip multi-part giants
    if not files:
        raise RuntimeError(f"No single-file .gguf model found in {repo}. Pick a repo whose name ends in -GGUF.")
    for want in ("q4_k_m", "q4_k_s", "q4_0", "q5_k_m", "q3_k_m", "q8_0"):
        for f in files:
            if want in f.lower():
                return f
    return sorted(files, key=len)[0]


def _bundle_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# The model someone chose and downloaded themselves always wins; a copy baked into the app
# (see packaging/fetch_models.py) is only used as a ready-to-go fallback for a brand new install.
DEFAULT_BUNDLED_REPO = "bartowski/Llama-3.2-1B-Instruct-GGUF"


def local_path(repo: str) -> Optional[str]:
    for base in (models_dir(), os.path.join(_bundle_dir(), "bundled_models")):
        d = os.path.join(base, repo.replace("/", "__"))
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().endswith(".gguf"):
                    return os.path.join(d, f)
    return None


def download_model(repo: str, progress: ProgressCB, cancel: Optional[threading.Event] = None) -> str:
    existing = local_path(repo)
    if existing:
        return existing
    progress("Looking up the model on Hugging Face…", 0.0)
    filename = pick_gguf_file(repo)
    dest_dir = os.path.join(models_dir(), repo.replace("/", "__"))
    os.makedirs(dest_dir, exist_ok=True)
    final = os.path.join(dest_dir, os.path.basename(filename))
    part = final + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    headers = {"Range": f"bytes={have}-"} if have else {}
    try:
        resp = _open(url, headers)
    except urllib.error.HTTPError as e:
        if e.code == 416 and have:  # already complete
            os.replace(part, final)
            return final
        raise
    status = getattr(resp, "status", 200)
    if have and status != 206:
        have = 0  # server ignored the resume request; start over
    total = int(resp.headers.get("Content-Length") or 0) + have
    mode = "ab" if have else "wb"
    done = have
    with resp, open(part, mode) as out:
        while True:
            if cancel is not None and cancel.is_set():
                raise RuntimeError("Download cancelled (it will resume next time).")
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                progress(f"Downloading model… {done / 1e6:,.0f} of {total / 1e6:,.0f} MB", done / total)
    os.replace(part, final)
    progress("Download complete", 1.0)
    return final


# --------------------------------------------------------------------------- running the model
SYSTEM_PROMPT = (
    "You are a careful Bible study helper. Answer the question using ONLY the Bible passages provided. "
    "Cite the reference in parentheses after each point, for example (Daniel 7:25). "
    "If the passages do not answer the question, say so plainly. Never invent or guess a verse. "
    "Keep the answer short: at most about 120 words, plain language."
)


def build_messages(question: str, passages: list[tuple[str, str]]) -> list[dict]:
    body = "\n".join(f"[{ref}] {text}" for ref, text in passages)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"BIBLE PASSAGES:\n{body}\n\nQUESTION: {question}"},
    ]


def cpu_problem() -> Optional[str]:
    """The AI engine needs a CPU with AVX2 (any PC from about 2014 on). Return a friendly message if it lacks it."""
    if not sys.platform.startswith("linux"):
        return None
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "compat_build.flag")):
        return None  # this build of the AI engine was compiled for older processors
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
            info = f.read().lower()
    except OSError:
        return None
    if "flags" in info and "avx2" not in info:
        return ("This computer's processor is too old for the AI helper (it needs a feature called AVX2). "
                "Searching your Bible still works fine.")
    return None


BIBLE_SYSTEM = "You are a Bible AI assistant. Answer questions about Scripture accurately and conversationally."


def build_bible_prompt(question: str, passages: list[tuple[str, str]]) -> str:
    """Exact layout the Bible Assistant was trained on (ChatML, verses in a Context block, thinking switched off)."""
    ctx = "\n".join(f"- **{ref}**: {text}" for ref, text in passages)
    return (
        f"<|im_start|>system\n{BIBLE_SYSTEM}<|im_end|>\n"
        f"<|im_start|>user\nContext:\n{ctx}\n\nQ: {question}<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


def strip_think(chunks: Iterator[str]) -> Iterator[str]:
    """Hide any <think>…</think> reasoning a model prints, even when the tags are split across chunks."""
    open_tag, close_tag = "<think>", "</think>"
    buf, inside = "", False
    for piece in chunks:
        buf += piece
        while True:
            if inside:
                i = buf.find(close_tag)
                if i == -1:
                    buf = buf[-(len(close_tag) - 1):]
                    break
                buf, inside = buf[i + len(close_tag):].lstrip("\n"), False
            else:
                i = buf.find(open_tag)
                if i == -1:
                    keep = 0
                    for k in range(min(len(open_tag) - 1, len(buf)), 0, -1):
                        if buf.endswith(open_tag[:k]):
                            keep = k
                            break
                    if len(buf) > keep:
                        yield buf[:len(buf) - keep]
                        buf = buf[len(buf) - keep:]
                    break
                if i:
                    yield buf[:i]
                buf, inside = buf[i + len(open_tag):], True
    if not inside and buf:
        yield buf


def engine_available() -> bool:
    try:
        import llama_cpp  # noqa: F401

        return True
    except Exception:
        return False


class LocalLLM:
    def __init__(self) -> None:
        self._llm = None
        self.path: Optional[str] = None
        self.style = "general"
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._llm is not None

    def load(self, path: str, style: str = "general") -> None:
        from llama_cpp import Llama

        threads = max(2, (os.cpu_count() or 4) // 2)
        with self._lock:
            try:
                # On Apple Silicon the Metal build can use the graphics chip; elsewhere this setting is ignored.
                gpu = -1 if sys.platform == "darwin" else 0
                self._llm = Llama(model_path=path, n_ctx=4096, n_threads=threads, n_gpu_layers=gpu, verbose=False)
            except Exception:
                self._llm = Llama(model_path=path, n_ctx=4096, n_threads=threads, n_gpu_layers=0, verbose=False)
            self.path = path
            self.style = style

    def stream(self, question: str, passages: list[tuple[str, str]]) -> Iterator[str]:
        assert self._llm is not None, "model not loaded"
        with self._lock:
            if self.style == "bible":
                pieces = (
                    c["choices"][0]["text"]
                    for c in self._llm.create_completion(
                        prompt=build_bible_prompt(question, passages),
                        temperature=0.0,  # the model's author evaluates with greedy decoding
                        max_tokens=600,
                        stop=["<|im_end|>", "<|endoftext|>"],
                        stream=True,
                    )
                )
            else:
                pieces = (
                    c["choices"][0]["delta"].get("content") or ""
                    for c in self._llm.create_chat_completion(
                        messages=build_messages(question, passages),
                        temperature=0.2,
                        max_tokens=450,
                        stream=True,
                    )
                )
            yield from strip_think(pieces)
