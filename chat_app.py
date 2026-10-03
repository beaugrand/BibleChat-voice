"""Start BibleChat.  Double-click the built app, or run:  python chat_app.py"""
import os
import sys


def _bundle_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


if getattr(sys, "frozen", False):  # a packaged build: use the AI models baked into the app, offline
    os.environ.setdefault("HF_HOME", os.path.join(_bundle_dir(), "hf_cache"))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

from bibleask.server import main

if __name__ == "__main__":
    sys.exit(main())
