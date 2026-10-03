#!/bin/bash
# For tinkering on Linux: runs BibleChat from this folder. Needs: sudo apt install python3-venv  (once)
# --system-site-packages lets this reuse torch/transformers/pocket_tts already installed for your
# user (e.g. by pocket-tts) instead of redownloading them, so the voice features (Listen / mic) work.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv --system-site-packages .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install pypdfium2 certifi
  .venv/bin/pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu || echo "(AI engine could not be installed; search still works)"
  .venv/bin/pip install transformers || echo "(listening helper could not be installed; typed chat still works)"
fi
exec .venv/bin/python chat_app.py
