"""Where BibleAsk keeps its files (your Bibles, downloaded AI models, settings).

Windows: %APPDATA%/BibleAsk      Mac: ~/Library/Application Support/BibleAsk      Linux: ~/.local/share/BibleAsk
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Optional

from .loaders import Bible


def data_dir() -> str:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "BibleAsk")
    os.makedirs(path, exist_ok=True)
    return path


def models_dir() -> str:
    p = os.path.join(data_dir(), "models")
    os.makedirs(p, exist_ok=True)
    return p


def library_dir() -> str:
    p = os.path.join(data_dir(), "bibles")
    os.makedirs(p, exist_ok=True)
    return p


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "bible"


def list_bibles() -> list[str]:
    return sorted(f[:-5] for f in os.listdir(library_dir()) if f.endswith(".json"))


def save_bible(b: Bible) -> str:
    slug = _slug(b.name)
    with open(os.path.join(library_dir(), slug + ".json"), "w", encoding="utf-8") as f:
        f.write(b.to_json())
    return slug


def open_bible(slug: str) -> Bible:
    with open(os.path.join(library_dir(), slug + ".json"), encoding="utf-8") as f:
        return Bible.from_json(f.read())


def remove_bible(slug: str) -> None:
    try:
        os.remove(os.path.join(library_dir(), slug + ".json"))
    except FileNotFoundError:
        pass


def _settings_path() -> str:
    return os.path.join(data_dir(), "settings.json")


def load_settings() -> dict:
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d: dict) -> None:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except OSError:
        pass
