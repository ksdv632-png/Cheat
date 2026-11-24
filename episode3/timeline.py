"""Builds the absolute timeline (lines, words, subtitle cards, scenes) from voice alignment."""
import json, os, re, subprocess
from functools import lru_cache

from lines import LINES, END_CARD

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(ROOT, "build", "voice")
FPS = 30
W, H = 1080, 1920


def _dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def _words_from_alignment(text, al):
    chars = al["characters"]; st = al["character_start_times_seconds"]; en = al["character_end_times_seconds"]
    joined = "".join(chars)
    if joined != text:  # API may normalise; fall back to proportional mapping
        n = len(chars)
        def at(i):
            j = min(n - 1, int(i * n / max(1, len(text))))
            return st[j], en[j]
    else:
        def at(i):
            return st[i], en[i]
    words = []
    for m in re.finditer(r"\S+", text):
        s, e = m.start(), m.end()
        # skip leading/trailing punctuation for timing
        core = [i for i in range(s, e) if text[i].isalnum()]
        if not core:
            core = list(range(s, e))
        words.append(dict(w=m.group(), t0=at(core[0])[0], t1=at(core[-1])[1]))
    return words


@lru_cache(maxsize=1)
def build():
    t = 0.0
    lines = []
    for L in LINES:
        js = json.load(open(os.path.join(VOICE, L["id"] + ".json")))
        dur = _dur(os.path.join(VOICE, L["id"] + ".mp3"))
        start = t + L["pre"]
        words = _words_from_alignment(L["text"], js)
        for w in words:
            w["t0"] += start; w["t1"] += start
        # subtitle cards
        cards, wi = [], 0
        for ch in L["chunks"]:
            toks = ch.split()
            cw = []
            for tok in toks:
                color = "w"
                if tok.startswith("^"): color, tok = "r", tok[1:]
                elif tok.startswith("~"): color, tok = "y", tok[1:]
                ww = words[min(wi, len(words) - 1)]
                cw.append(dict(w=tok, c=color, t0=ww["t0"], t1=ww["t1"]))
                wi += 1
            cards.append(dict(words=cw, t0=cw[0]["t0"] - 0.06, t1=None))
        assert wi == len(words), (L["id"], wi, len(words))
        for i, c in enumerate(cards):
            c["t1"] = cards[i + 1]["t0"] if i + 1 < len(cards) else start + dur + min(L["gap"], 0.6)
        lines.append(dict(L, start=start, end=start + dur, dur=dur, scene_t0=t, words=words, cards=cards,
                          placeholder=bool(js.get("placeholder"))))
        t = start + dur + L["gap"]
    total = t + END_CARD
    # scenes: contiguous segments, a new segment whenever the scene name changes
    scenes = []
    for ln in lines:
        if scenes and scenes[-1]["name"] == ln["scene"]:
            scenes[-1]["lines"].append(ln)
        else:
            scenes.append(dict(name=ln["scene"], t0=ln["scene_t0"], lines=[ln]))
    scenes.append(dict(name="endcard", t0=t, lines=[]))
    for i, s in enumerate(scenes):
        s["t1"] = scenes[i + 1]["t0"] if i + 1 < len(scenes) else total
    return dict(lines=lines, scenes=scenes, total=total)


def scene_at(T):
    tl = build()
    for s in tl["scenes"]:
        if s["t0"] <= T < s["t1"]:
            return s
    return tl["scenes"][-1]


def line(lid):
    return next(l for l in build()["lines"] if l["id"] == lid)


def word_time(lid, idx, end=False):
    w = line(lid)["words"][idx]
    return w["t1"] if end else w["t0"]


if __name__ == "__main__":
    tl = build()
    for s in tl["scenes"]:
        print(f'{s["t0"]:6.2f}-{s["t1"]:6.2f}  {s["name"]:14s} ' + " | ".join(l["text"] for l in s["lines"]))
    print("total", round(tl["total"], 2))
