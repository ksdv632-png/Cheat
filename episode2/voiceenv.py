"""Per-frame loudness envelopes of the voice lines (for lip-sync and light reactions)."""
import os, subprocess
from functools import lru_cache
import numpy as np

import timeline as TL

SR = 16000


@lru_cache(maxsize=None)
def env(lid):
    ln = TL.line(lid)
    fps = TL.FPS
    if ln["placeholder"]:
        n = int(ln["dur"] * fps) + 2
        e = np.zeros(n, np.float32)
        for w in ln["words"]:
            a, b = int((w["t0"] - ln["start"]) * fps), int((w["t1"] - ln["start"]) * fps)
            for i in range(a, min(n, b + 1)):
                e[i] = 0.55 + 0.45 * abs(np.sin(i * 1.7))
        return e
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", os.path.join(TL.VOICE, lid + ".mp3"),
                                   "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    hop = SR // fps
    n = len(x) // hop + 1
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)], np.float32)
    e = e / (np.percentile(e, 95) + 1e-6)
    # smooth attack/release so the mouth does not jitter
    out = np.zeros_like(e); v = 0.0
    for i, s in enumerate(e):
        v = v + (s - v) * (0.65 if s > v else 0.35)
        out[i] = v
    return np.clip(out, 0, 1.2)


def at(lid, T):
    ln = TL.line(lid)
    e = env(lid)
    i = int((T - ln["start"]) * TL.FPS)
    if i < 0 or i >= len(e):
        return 0.0
    return float(e[i])


def active(T):
    """loudness of whichever line is speaking at T"""
    for ln in TL.build()["lines"]:
        if ln["start"] <= T <= ln["end"]:
            return at(ln["id"], T), ln
    return 0.0, None
