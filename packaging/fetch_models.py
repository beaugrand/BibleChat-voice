"""Run once, during the Windows build only: downloads every AI model BibleChat uses so the
finished app needs no internet connection, not even on its very first launch.

- Pocket TTS's voice model and the Whisper listening model go into a bundled Hugging Face
  cache (hf_cache/), which transformers/pocket_tts read from automatically via HF_HOME.
- The default chat model is BibleChat's own kind of download (a single .gguf file picked the
  same way the app itself would pick it - see bibleask/llm.py), so it goes into bundled_models/
  in the layout bibleask/llm.py already knows how to find.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["HF_HOME"] = str(ROOT / "hf_cache")

from huggingface_hub import snapshot_download  # noqa: E402  (needs HF_HOME set first)

sys.path.insert(0, str(ROOT))
from bibleask import llm  # noqa: E402

print("Fetching the Pocket TTS voice model...")
snapshot_download("kyutai/pocket-tts")
snapshot_download("kyutai/pocket-tts-without-voice-cloning")

print("Fetching the listening (speech-to-text) model...")
snapshot_download("openai/whisper-tiny.en")

print(f"Fetching the default chat model ({llm.DEFAULT_BUNDLED_REPO})...")
filename = llm.pick_gguf_file(llm.DEFAULT_BUNDLED_REPO)
dest_dir = ROOT / "bundled_models" / llm.DEFAULT_BUNDLED_REPO.replace("/", "__")
dest_dir.mkdir(parents=True, exist_ok=True)
url = f"https://huggingface.co/{llm.DEFAULT_BUNDLED_REPO}/resolve/main/{filename}"
dest = dest_dir / os.path.basename(filename)
print(f"  {url}")
urllib.request.urlretrieve(url, dest)
print(f"  saved to {dest} ({dest.stat().st_size / 1e6:,.0f} MB)")

print("All models fetched.")
