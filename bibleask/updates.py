"""Tells people when a newer BibleChat is out.

An installed BibleChat never changes by itself. Once a day, at start-up, it asks GitHub which release is
the newest (nothing about the person is sent) and, if that is newer than this copy, the page shows an
"Update available" box with a download link. If GitHub can't be reached, nothing is shown.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from typing import Optional

from . import __version__, storage

REPO = "beaugrand/BibleChat-voice"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES = f"https://github.com/{REPO}/releases/latest"
DAY = 24 * 3600

_found: Optional[dict] = None


def _ver(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3]) or (0,)


def newer(latest: str, current: str = __version__) -> bool:
    return _ver(latest) > _ver(current)


def download_url() -> str:
    """The file for this computer, straight from the newest release."""
    if sys.platform.startswith("win"):
        return RELEASES + "/download/BibleChat-Windows.zip"
    if sys.platform == "darwin":
        return RELEASES + "/download/BibleChat-Mac.zip"
    return RELEASES


def _result(tag: str) -> Optional[dict]:
    if not tag or not newer(tag):
        return None
    return {"version": tag.lstrip("v"), "url": download_url(), "page": RELEASES}


def check(force: bool = False) -> Optional[dict]:
    """Ask GitHub for the newest release (at most once a day). Never raises."""
    global _found
    s = storage.load_settings()
    last = s.get("update_check") or {}
    if not force and time.time() - last.get("time", 0) < DAY:
        _found = _result(last.get("tag", ""))
        return _found
    try:
        from .llm import _open
        with _open(LATEST_API, {"Accept": "application/vnd.github+json"}) as r:
            tag = json.load(r).get("tag_name", "")
    except Exception:
        _found = _result(last.get("tag", ""))
        return _found
    s = storage.load_settings()
    s["update_check"] = {"time": time.time(), "tag": tag}
    storage.save_settings(s)
    _found = _result(tag)
    return _found


def check_in_background() -> None:
    threading.Thread(target=check, daemon=True).start()


def status() -> dict:
    return {"version": __version__, "update": _found}
