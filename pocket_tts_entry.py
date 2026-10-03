"""Launches Pocket TTS's own server. Bundled and auto-started alongside BibleChat so speaking
answers out loud needs no separate install step — see bibleask/server.py's _ensure_tts_helper().
"""
from __future__ import annotations

import os
import sys


def _bundle_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


os.environ.setdefault("HF_HOME", os.path.join(_bundle_dir(), "hf_cache"))
if getattr(sys, "frozen", False):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # the voice model is bundled; never phone home

from pocket_tts.main import serve

if __name__ == "__main__":
    serve(host="127.0.0.1", port=8000)
