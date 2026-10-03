"""Optional speech-to-text: turns a short voice clip into text using a small local Whisper model.

Lazy and optional on purpose, like the chat AI helper in llm.py: BibleChat works fine without it,
and the model is only downloaded/loaded the first time someone actually uses the microphone button.
"""
from __future__ import annotations

import io
import wave
from typing import Optional

MODEL = "openai/whisper-tiny.en"
TARGET_RATE = 16000

_pipe = None
_load_error: Optional[str] = None


def available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except Exception:
        return False


def _get_pipe():
    global _pipe, _load_error
    if _pipe is not None or _load_error is not None:
        return _pipe
    try:
        from transformers import pipeline
        _pipe = pipeline("automatic-speech-recognition", model=MODEL)
    except Exception as e:
        _load_error = str(e) or e.__class__.__name__
    return _pipe


def _wav_to_samples(data: bytes):
    import numpy as np
    with wave.open(io.BytesIO(data)) as w:
        channels, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError("Expected 16-bit WAV audio.")
    samples = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if rate != TARGET_RATE:
        from scipy.signal import resample
        samples = resample(samples, int(round(len(samples) * TARGET_RATE / rate))).astype("float32")
    return samples


def transcribe(wav_bytes: bytes) -> str:
    """wav_bytes: a whole WAV file (any sample rate, mono or stereo, 16-bit PCM)."""
    pipe = _get_pipe()
    if pipe is None:
        raise RuntimeError(_load_error or
            "The listening helper isn't installed. Run: pip install --user --break-system-packages transformers")
    samples = _wav_to_samples(wav_bytes)
    if samples.size < TARGET_RATE // 10:  # under ~0.1s, probably nothing
        return ""
    out = pipe({"array": samples, "sampling_rate": TARGET_RATE})
    return (out.get("text") or "").strip()
