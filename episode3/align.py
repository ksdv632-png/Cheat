"""Install downloaded ElevenLabs takes (build/voice_raw/*.mp3) into build/voice/ with character timings.

Timings are estimated from the audio itself: each character gets a phonetic weight (vowels heavy,
consonants light, spaces/punctuation zero) and the cumulative weight is spread over the *voiced*
frames only, so real pauses in the take land between words.
"""
import json, os, subprocess, sys
import numpy as np

from lines import LINES

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "build", "voice_raw")
OUT = os.path.join(ROOT, "build", "voice")
SR = 16000
HOP = 160  # 10 ms
VOWELS = set("аеёиоуыэюяaeiou")


def pcm(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def voiced_mask(x):
    n = len(x) // HOP
    rms = np.array([np.sqrt(np.mean(x[i * HOP:(i + 1) * HOP] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-9)
    thr = np.percentile(db, 95) - 28
    m = db > thr
    # close tiny gaps (<60 ms) and drop tiny blips (<40 ms)
    out = m.copy()
    i = 0
    while i < n:
        if not m[i]:
            j = i
            while j < n and not m[j]:
                j += 1
            if 0 < i and j < n and j - i < 6:
                out[i:j] = True
            i = j
        else:
            i += 1
    m = out.copy(); i = 0
    while i < n:
        if m[i]:
            j = i
            while j < n and m[j]:
                j += 1
            if j - i < 4:
                out[i:j] = False
            i = j
        else:
            i += 1
    return out


def segments(m):
    segs, i, n = [], 0, len(m)
    while i < n:
        if m[i]:
            j = i
            while j < n and m[j]:
                j += 1
            segs.append([i, j]); i = j
        else:
            i += 1
    return segs


def align(text, x):
    m = voiced_mask(x)
    segs = segments(m) or [[0, len(m)]]
    w = np.array([0.0 if not ch.isalnum() else (1.0 if ch.lower() in VOWELS else 0.4) for ch in text])
    # phrase boundaries: character index right after strong punctuation
    import re
    cuts = [mm.end() for mm in re.finditer(r"[.!?…,:—]+[»\"]?\s+", text)]
    phrases = list(zip([0] + cuts, cuts + [len(text)]))
    phrases = [p for p in phrases if w[p[0]:p[1]].sum() > 0]
    # gaps between voiced segments, choose the largest ones as phrase breaks
    gaps = sorted(range(len(segs) - 1), key=lambda k: segs[k + 1][0] - segs[k][1], reverse=True)
    nb = min(len(phrases) - 1, len(gaps))
    chosen = sorted(k for k in gaps[:nb] if segs[k + 1][0] - segs[k][1] >= 8)  # >= 80 ms
    groups, start = [], 0
    for k in chosen:
        groups.append(segs[start:k + 1]); start = k + 1
    groups.append(segs[start:])
    # if fewer pause groups than phrases, merge trailing phrases into the last group
    if len(groups) < len(phrases):
        merged = phrases[:len(groups) - 1] + [(phrases[len(groups) - 1][0], phrases[-1][1])]
        phrases = merged
    starts = [0.0] * len(text); ends = [0.0] * len(text)
    for (a, b), g in zip(phrases, groups):
        frames = np.concatenate([np.arange(s, e) for s, e in g])
        nv = len(frames)
        ww = w[a:b]
        cw = np.concatenate([[0], np.cumsum(ww)]) / max(ww.sum(), 1e-9)
        for i in range(b - a):
            k0 = min(nv - 1, int(cw[i] * nv)); k1 = min(nv - 1, int(max(cw[i], cw[i + 1] - 1e-6) * nv))
            starts[a + i] = round(float(frames[k0] * HOP / SR), 3)
            ends[a + i] = round(float(frames[k1] * HOP / SR + HOP / SR), 3)
    # punctuation inherits previous end so it never jumps forward
    for i in range(len(text)):
        if w[i] == 0:
            starts[i] = ends[i] = ends[i - 1] if i else starts[i]
    return {"characters": list(text), "character_start_times_seconds": starts, "character_end_times_seconds": ends,
            "source": "elevenlabs_v3+local_align"}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for L in LINES:
        src = os.path.join(RAW, L["id"] + ".mp3")
        x = pcm(src)
        js = align(L["text"], x)
        subprocess.run(["cp", src, os.path.join(OUT, L["id"] + ".mp3")], check=True)
        json.dump(js, open(os.path.join(OUT, L["id"] + ".json"), "w"), ensure_ascii=False)
        words = []
        import re
        for mm in re.finditer(r"\S+", L["text"]):
            idx = [i for i in range(mm.start(), mm.end()) if L["text"][i].isalnum()] or [mm.start()]
            words.append(f'{mm.group()}@{js["character_start_times_seconds"][idx[0]]:.2f}')
        print(L["id"], f"{len(x)/SR:.2f}s", " ".join(words))
