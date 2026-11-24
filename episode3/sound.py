"""Sound design + voice processing + final mix for episode 2 (all procedural, 48 kHz stereo).

python3 sound.py  ->  build/mix.wav
"""
import math, os, subprocess
import numpy as np
from scipy import signal

import timeline as TL
from render import wt, knock_times, L

SR = 48000
ROOT = TL.ROOT
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ DSP helpers
def sec(t):
    return int(round(t * SR))


def filt(x, kind, f, order=4):
    if kind == "bp":
        sos = signal.butter(order, [f[0] / (SR / 2), f[1] / (SR / 2)], "bandpass", output="sos")
    else:
        sos = signal.butter(order, f / (SR / 2), kind, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def noise(n):
    return rng.standard_normal(n).astype(np.float32)


def env_adsr(n, a, d, s_lvl, r):
    e = np.ones(n, np.float32) * s_lvl
    na, nd, nr = sec(a), sec(d), sec(r)
    na = min(na, n); e[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na); e[na:na + nd] = np.linspace(1, s_lvl, nd)
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def expdecay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def ir(length=1.6, tau=0.45, bright=4000, seed=1, pre=0.0):
    r = np.random.default_rng(seed)
    n = sec(length)
    out = np.zeros((n, 2), np.float32)
    for ch in range(2):
        x = r.standard_normal(n).astype(np.float32) * expdecay(n, tau)
        x = filt(x, "low", bright, 2)
        out[:, ch] = x
    if pre:
        out = np.vstack([np.zeros((sec(pre), 2), np.float32), out])
    out[0] += 0.0
    return out / np.sqrt((out ** 2).sum(axis=0, keepdims=True) + 1e-9) * 0.9


def reverb(x, wet=0.2, **kw):
    """x stereo"""
    h = ir(**kw)
    y = np.stack([signal.fftconvolve(x[:, ch], h[:, ch])[:len(x)] for ch in range(2)], 1)
    return x * (1 - wet * 0.5) + y * wet


def stereo(m, pan=0.0):
    l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
    return np.stack([m * l * 1.41, m * r * 1.41], 1).astype(np.float32)


def sine(f, n, phase=0.0):
    if np.isscalar(f):
        return np.sin(2 * np.pi * f * np.arange(n) / SR + phase).astype(np.float32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph + phase).astype(np.float32)


class Track:
    def __init__(self, total):
        self.buf = np.zeros((sec(total) + SR * 4, 2), np.float32)

    def add(self, t, x, gain=1.0):
        i = sec(t)
        if i < 0:
            x = x[-i:]; i = 0
        n = min(len(x), len(self.buf) - i)
        if n > 0:
            self.buf[i:i + n] += x[:n] * gain


# ------------------------------------------------------------------ sound objects
def sub_hit(dur=2.5, f0=70, f1=28, gain=1.0):
    n = sec(dur)
    f = np.geomspace(f0, f1, n)
    x = sine(f, n) * expdecay(n, dur / 4)
    click = filt(noise(n), "low", 1800) * expdecay(n, 0.03) * 0.5
    body = filt(noise(n), "bp", (60, 400)) * expdecay(n, 0.35) * 0.5
    return stereo((x + click + body) * gain)


def metal_knock(gain=1.0, seed=0):
    """fist on a heavy steel door: thud + inharmonic ring + room"""
    n = sec(3.0)
    r = np.random.default_rng(seed)
    thud = sine(np.geomspace(95, 40, n), n) * expdecay(n, 0.12) * 1.2
    nz = filt(noise(n), "low", 900) * expdecay(n, 0.04) * 1.0
    ring = np.zeros(n, np.float32)
    for k, (fr, a, tau) in enumerate([(173, 0.25, 0.9), (291, 0.18, 0.7), (447, 0.12, 0.5), (689, 0.07, 0.35), (1033, 0.04, 0.25)]):
        ring += sine(fr * (1 + r.uniform(-0.01, 0.01)), n) * a * expdecay(n, tau)
    x = stereo(thud + nz + ring * 0.6)
    return reverb(x, 0.45, length=2.5, tau=0.7, bright=2500, seed=seed + 3) * gain


def click(gain=1.0, bright=6000):
    n = sec(0.08)
    x = filt(noise(n), "high", 800) * expdecay(n, 0.006)
    x = filt(x, "low", bright)
    return stereo(x * gain)


def buzz(dur, gain=0.3):
    n = sec(dur)
    saw = signal.sawtooth(2 * np.pi * 100 * np.arange(n) / SR).astype(np.float32)
    x = filt(saw, "bp", (200, 3000)) * (0.6 + 0.4 * (noise(n) > 1.2))
    return stereo(x * env_adsr(n, 0.005, 0.01, 1, 0.02) * gain)


def whoosh(dur=0.6, up=True, gain=0.6):
    n = sec(dur)
    x = noise(n)
    f = np.geomspace(300, 6000, n) if up else np.geomspace(6000, 300, n)
    y = np.zeros(n, np.float32)
    blk = 1024
    for i in range(0, n, blk):  # moving bandpass
        fc = f[min(n - 1, i)]
        y[i:i + blk] = filt(x[i:i + blk], "bp", (fc * 0.6, min(SR / 2 - 100, fc * 1.6)), 2)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return stereo(y * e * gain)


def riser(dur, gain=0.5, f0=200, f1=1800):
    n = sec(dur)
    nz = filt(noise(n), "high", 1500) * np.linspace(0, 1, n) ** 2 * 0.5
    tone = sine(np.geomspace(f0, f1, n), n) * np.linspace(0, 1, n) ** 3 * 0.25
    tone2 = sine(np.geomspace(f0 * 1.5, f1 * 1.5, n), n) * np.linspace(0, 1, n) ** 3 * 0.12
    return stereo((nz + tone + tone2) * gain)


def reverse_swell(dur=1.2, gain=0.5):
    n = sec(dur)
    x = filt(noise(n), "bp", (500, 7000)) * expdecay(n, dur / 3)
    x = x[::-1].copy()
    return reverb(stereo(x * gain), 0.3, length=1.0, tau=0.3)


def heartbeat(gain=1.0):
    n = sec(0.5)
    def thump(f, tau):
        return sine(np.geomspace(f, f * 0.6, n), n) * expdecay(n, tau)
    lub = thump(58, 0.07); dub = thump(70, 0.05) * 0.7
    x = lub.copy(); off = sec(0.22)
    x[off:] += dub[:n - off]
    x = filt(x, "low", 160)
    return stereo(x * gain)


def tick(gain=0.4, f=2400):
    n = sec(0.06)
    x = sine(f, n) * expdecay(n, 0.008) + filt(noise(n), "high", 3000) * expdecay(n, 0.004) * 0.6
    return stereo(x * gain)


def glitch_burst(dur=0.25, gain=0.35, seed=0):
    r = np.random.default_rng(seed)
    n = sec(dur)
    x = np.zeros(n, np.float32)
    i = 0
    while i < n:
        L_ = int(r.uniform(0.008, 0.04) * SR)
        kind = r.integers(3)
        seg = noise(L_) if kind == 0 else sine(r.uniform(200, 4000), L_) if kind == 1 else np.sign(sine(r.uniform(50, 400), L_))
        x[i:i + L_] = seg[:max(0, min(L_, n - i))] * r.uniform(0.2, 1)
        i += L_ + int(r.uniform(0, 0.02) * SR)
    return stereo(filt(x, "low", 9000) * gain)


def breath(dur, inhale=True, gain=0.3):
    n = sec(dur)
    x = filt(noise(n), "bp", (300, 2600) if inhale else (200, 1800))
    x += filt(noise(n), "bp", (2500, 6000)) * 0.25
    e = np.sin(np.linspace(0, np.pi, n)) ** (1.5 if inhale else 0.8)
    if not inhale:
        e *= np.linspace(1, 0.4, n)
    return x * e * gain


def frost_crackle(dur, gain=0.25, seed=3):
    r = np.random.default_rng(seed)
    n = sec(dur)
    x = np.zeros(n, np.float32)
    for _ in range(int(dur * 45)):
        i = r.integers(0, n - 2000)
        L_ = r.integers(100, 1600)
        x[i:i + L_] += filt(noise(L_), "high", 3500, 2) * expdecay(L_, 0.002) * r.uniform(0.2, 1)
    return stereo(x * gain)


def creak(dur=1.6, gain=0.35):
    """metal wheel turning: stick-slip friction squeal"""
    n = sec(dur)
    f = 180 + 60 * np.sin(np.linspace(0, 3, n)) + 30 * filt(noise(n), "low", 6)
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    am = 0.5 + 0.5 * np.sign(sine(np.linspace(9, 22, n), n))
    x = filt(saw * am, "bp", (300, 2500)) * env_adsr(n, 0.2, 0.1, 0.9, 0.3)
    return reverb(stereo(x * gain), 0.4, length=2.0, tau=0.6, bright=3000)


# ------------------------------------------------------------------ voice processing
def load(path, sr=SR):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def ff(path, af):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def norm_peak(x, p=0.9):
    m = np.abs(x).max() + 1e-9
    return x / m * p


def comp(x, thr=0.25, ratio=3.0):
    lvl = np.abs(x).max(axis=1)
    e = signal.lfilter([0.002], [1, -0.998], lvl)
    g = np.where(e > thr, (thr + (e - thr) / ratio) / (e + 1e-9), 1.0)
    return x * g[:, None]


def voice(lid):
    ln = TL.line(lid)
    path = os.path.join(TL.VOICE, lid + ".mp3")
    spk = ln["spk"]
    if ln["placeholder"]:
        return np.zeros((sec(ln["dur"]), 2), np.float32)
    x = load(path)
    x = filt(x, "high", 70, 2)
    if spk == "narrator":
        x = comp(norm_peak(x), 0.3, 3)
        x = reverb(x, 0.14, length=1.2, tau=0.30, bright=5000, seed=11)
        g = 0.95
    elif spk == "oldman":
        x = comp(norm_peak(x), 0.3, 3)
        x = reverb(x, 0.24, length=1.6, tau=0.45, bright=4000, seed=12)
        g = 0.85
    elif spk == "victor":
        if lid == "l15":  # behind a steel door
            x = filt(norm_peak(x), "low", 650, 4)
            x = x + filt(x, "bp", (300, 380), 2) * 1.5
            x = reverb(x, 0.45, length=2.2, tau=0.6, bright=1200, seed=13)
            g = 0.75
        else:
            x = comp(norm_peak(x), 0.25, 4)
            x = reverb(x, 0.12, length=1.0, tau=0.3, seed=14)
            g = 1.0
    elif spk == "mom":
        if lid == "l18":  # memory, distant, echoing
            x = filt(norm_peak(x), "low", 3200, 2)
            x = reverb(x, 0.65, length=3.5, tau=1.1, bright=3000, seed=15, pre=0.05)
            d = np.zeros_like(x); k = sec(0.32)
            d[k:] += x[:-k] * 0.35; d[2 * k:] += x[:-2 * k] * 0.15
            x = x + d
            g = 0.75
        else:  # behind the door; the last word sinks into something that is not her
            clean = filt(norm_peak(x), "low", 800, 4)
            low = ff(path, "rubberband=pitch=0.62:formant=shifted")
            low = filt(norm_peak(low)[:len(clean)], "low", 600, 4)
            if len(low) < len(clean):
                low = np.vstack([low, np.zeros((len(clean) - len(low), 2), np.float32)])
            t_m = TL.word_time("l21", 3) - ln["start"]
            ramp_ = np.clip((np.arange(len(clean)) / SR - t_m + 0.1) / 0.5, 0, 1)[:, None]
            x = clean * (1 - 0.4 * ramp_) + low * ramp_ * 0.9
            x = reverb(x, 0.4, length=2.2, tau=0.6, bright=1200, seed=16)
            g = 0.8
    else:  # thing: the narrator's voice, pitched down, doubled, whispering
        a = ff(path, "rubberband=pitch=0.74:formant=shifted")
        b = ff(path, "rubberband=pitch=0.5:formant=shifted")
        n = len(x)
        a = np.resize(a, (n, 2)); b = np.resize(b, (n, 2))
        wh = filt(x, "high", 2200, 2) * 1.6
        x = norm_peak(a) * 0.9 + norm_peak(b) * 0.35 + norm_peak(wh) * 0.35
        x = comp(x, 0.3, 4)
        x = reverb(x, 0.3, length=2.5, tau=0.8, bright=2500, seed=17)
        if lid == "l20":  # right at your left ear
            x = x * np.array([1.0, 0.35], np.float32)
        g = 0.95
    return norm_peak(x, 0.95) * g


# ------------------------------------------------------------------ score
def build():
    tl = TL.build()
    total = tl["total"]
    T = Track(total)
    n_all = len(T.buf)
    tt = np.arange(n_all) / SR

    def at_scene(name, k=0):
        return [s for s in tl["scenes"] if s["name"] == name][k]

    # ---------- intensity curve for the drone (per scene) ----------
    level = {"cold": 0.45, "back": 0.5, "wall_line": 0.55, "count": 0.62, "oldman": 0.55, "hands": 0.68, "hands_late": 0.5,
             "victor_reveal": 0.72, "eyes": 0.8, "victor_face": 0.9, "step": 0.15, "flicker": 0.0, "five": 0.65,
             "knock": 0.7, "door_voice": 0.62, "oldman_door": 0.7, "flashback": 0.35, "flashback_mom": 0.25,
             "turn": 0.9, "ear": 0.55, "door_mom": 0.35, "endcard": 0.45}
    lv = np.zeros(n_all, np.float32)
    for s in tl["scenes"]:
        lv[sec(s["t0"]):sec(s["t1"])] = level[s["name"]]
    lv[sec(total):] = 0
    title_end = L("l01")["start"] - 0.25
    lv[sec(L("l00")["end"] + 0.5):sec(title_end)] *= 0.4
    lv = filt(lv, "low", 1.2, 2).astype(np.float32)
    # overall slow rise of tension
    lv *= (0.8 + 0.4 * np.clip(tt / total, 0, 1)).astype(np.float32)
    # turn: silence after the smash cut
    cut = L("l19")["end"] - 0.02
    lv[sec(cut):sec(cut + 1.4)] = 0

    # drone: detuned low partials + slowly sweeping filtered air
    d = (sine(41.2, n_all) * 0.5 + sine(41.6, n_all) * 0.5 + sine(61.8, n_all) * 0.28 + sine(82.0, n_all) * 0.18
         + sine(123.6 + 0.8 * np.sin(tt * 0.2), n_all) * 0.08)
    air = filt(noise(n_all), "bp", (90, 900), 2) * 0.35
    air_hi = filt(noise(n_all), "bp", (1800, 4000), 2) * 0.05 * (0.5 + 0.5 * np.sin(tt * 0.37))
    drone = (d * 0.55 + air + air_hi) * lv
    T.buf[:, 0] += drone * 0.32
    T.buf[:, 1] += np.roll(drone, 300) * 0.32
    # dissonant high string-like cluster that grows in the second half
    cl = (sine(587.3, n_all) + sine(622.3, n_all) * 0.8 + sine(659.3 + 2 * np.sin(tt * 0.3), n_all) * 0.6)
    cl = filt(cl * (0.6 + 0.4 * np.sin(tt * 3.1)), "low", 1500, 2) * np.clip((tt - 40) / 60, 0, 1) * lv * 0.035
    T.buf[:, 0] += cl; T.buf[:, 1] += np.roll(cl, 900)

    # ---------- heartbeat: tempo rises 62 -> 118 bpm ----------
    hb_on = {"back", "count", "oldman", "hands", "victor_reveal", "eyes", "victor_face", "five", "oldman_door", "ear", "door_voice"}
    t = 2.0
    hb = heartbeat()
    while t < total - 4:
        s = TL.scene_at(t)
        bpm = 62 + 56 * (t / total) + (18 if s["name"] in ("victor_face", "eyes") else 0)
        if s["name"] in hb_on:
            g = 0.55 if s["name"] not in ("victor_face", "ear") else 0.8
            T.add(t, hb, g)
        t += 60.0 / bpm

    # ---------- cold open ----------
    T.add(0.15, sub_hit(3.0, 55, 25, 0.7))
    T.add(L("l00")["start"] - 0.6, reverse_swell(0.7, 0.35))
    # ---------- title ----------
    tst = L("l00")["end"] + 0.5
    T.add(tst + 0.25, glitch_burst(0.35, 0.4, 1))
    T.add(tst + 0.3, sub_hit(2.5, 80, 30, 0.9))
    T.add(tst + 1.2, glitch_burst(0.08, 0.25, 2))
    T.add(title_end - 0.35, glitch_burst(0.3, 0.35, 3))

    # ---------- back: breathing behind him (syncs on "будто учился") ----------
    l1, l2 = L("l01"), L("l02")
    t = l1["end"] - 0.2
    while t < l2["end"] + 0.8:
        cyc = 2.6 if t < l2["start"] else 2.6 + 1.0 * min(1, (t - l2["start"]) / (l2["end"] - l2["start"]))
        inh = breath(cyc * 0.45, True, 0.22); exh = breath(cyc * 0.5, False, 0.2)
        T.add(t, stereo(inh, -0.6)); T.add(t + cyc * 0.47, stereo(exh, -0.5))
        t += cyc
    T.add(wt("l01", 2) - 0.2, whoosh(0.5, True, 0.15))  # the head almost turns

    # ---------- wall line: shuffling steps ----------
    k_start = wt("l03", 2)
    for i in range(6):
        for j in range(2):
            n = sec(0.12)
            st = filt(noise(n), "bp", (150, 1200)) * expdecay(n, 0.03) * 0.25
            T.add(k_start + i * 0.22 - 0.3 + j * 0.28, reverb(stereo(st, (i - 2.5) / 3), 0.3, length=1.0, tau=0.3))

    # ---------- count ----------
    t_people = wt("l04", 0); t_sh = wt("l04", 2)
    for i in range(6):
        T.add(t_people - 0.25 + i * 0.11, tick(0.25, 1800))
    for n_ in range(7):
        T.add(t_sh - 0.2 + n_ * 0.1, tick(0.3 if n_ < 6 else 0.5, 1400 if n_ < 6 else 900))
    T.add(t_sh + 0.5, sub_hit(2.5, 70, 28, 0.9))
    T.add(t_sh + 0.5, glitch_burst(0.1, 0.2, 4))

    # ---------- hands ----------
    t_up = wt("l06", 2) - 0.1
    for i in range(6):
        n = sec(0.25)
        T.add(t_up + i * 0.015, stereo(filt(noise(n), "bp", (400, 3000)) * expdecay(n, 0.06) * 0.08, (i - 2.5) / 3))
    t_pochti = wt("l06", 4)
    T.add(t_pochti - 1.3, riser(1.25, 0.35))
    T.add(t_pochti - 0.05, sub_hit(3.0, 60, 25, 1.0))
    T.add(t_pochti - 0.05, glitch_burst(0.12, 0.3, 5))
    # hands_late: slow clock ticks, underwater
    hl = at_scene("hands_late")
    t = hl["t0"] + 0.2
    while t < hl["t1"] - 0.3:
        T.add(t, tick(0.18, 700)); t += 0.6
    T.add(hl["t0"] + 0.2 + (hl["t1"] - hl["t0"] - 0.8) * 0.6 / 1.4 * 1.0, sub_hit(2.0, 90, 40, 0.5))

    # ---------- victor reveal / eyes ----------
    T.add(wt("l08", 3) - 0.05, sub_hit(2.0, 80, 35, 0.6))
    words = L("l09")["words"]
    for k in range(5):
        T.add(words[min(len(words) - 1, k % len(words))]["t0"] + 0.12 * k, click(0.35, 4000))
    T.add(words[-1]["t0"] + 0.2, reverse_swell(0.7, 0.3))

    # ---------- victor shouts ----------
    T.add(wt("l10", 2), sub_hit(1.5, 90, 40, 0.6))
    T.add(wt("l10", 2), glitch_burst(0.1, 0.25, 6))

    # ---------- step: sound gets sucked out, tinnitus ----------
    t_step = wt("l11", 2) - 0.1
    n = sec(0.3)
    T.add(t_step + 0.6, reverb(stereo(filt(noise(n), "bp", (100, 900)) * expdecay(n, 0.05) * 0.4, 0.4), 0.3))
    t_ost = wt("l11", 9)
    T.add(t_ost - 1.2, reverse_swell(1.25, 0.45))
    T.add(t_ost, sub_hit(3.0, 55, 22, 0.9))
    n = sec(5.0)
    tin = sine(5600, n) * env_adsr(n, 1.0, 0.1, 1.0, 1.5) * 0.035
    T.add(t_ost, stereo(tin))

    # ---------- flicker ----------
    t_m = wt("l12", 1)
    pattern = [(0.00, 0), (0.10, 1), (0.16, 0), (0.42, 1), (0.50, 0), (0.95, 1), (1.02, 0), (1.55, 1)]
    for t0, s in pattern:
        T.add(t_m + t0, click(0.6 if s == 0 else 0.45))
        if s == 1:
            T.add(t_m + t0, buzz(0.06, 0.12))
    for k, (t0, s) in enumerate(pattern):
        if s == 0:
            n = sec(0.3)
            wh = filt(noise(n), "bp", (300, 3000)) * np.sin(np.linspace(0, np.pi, n)) * 0.12 * (1 + k * 0.3)
            T.add(t_m + t0 + 0.02, stereo(wh, 0.4))
    T.add(t_m + 1.55, sub_hit(3.0, 50, 20, 1.0))
    T.add(t_m + 1.55, glitch_burst(0.12, 0.3, 7))

    # ---------- five ----------
    t5 = wt("l13", 2); t7 = wt("l13", 7)
    T.add(t5, glitch_burst(0.15, 0.3, 8)); T.add(t5, tick(0.4, 1100))
    T.add(t7, sub_hit(2.0, 75, 30, 0.7))

    # ---------- knocks ----------
    for i, k in enumerate(knock_times()):
        T.add(k, metal_knock(1.0 - 0.05 * i, seed=20 + i))
        T.add(k, sub_hit(1.2, 60, 30, 0.45))

    # ---------- door voice: frost ----------
    dv = at_scene("door_voice")
    T.add(dv["t0"] + 0.2, frost_crackle(dv["t1"] - dv["t0"], 0.18))
    n = sec(dv["t1"] - dv["t0"])
    wind = filt(noise(n), "bp", (400, 1400), 2) * (0.4 + 0.6 * np.sin(np.linspace(0, 3, n)) ** 2) * 0.05
    T.add(dv["t0"], stereo(wind, 0.2))

    # ---------- flashback: muffled world, projector rattle ----------
    fb0 = at_scene("flashback")["t0"]; fb1 = at_scene("turn")["t0"]
    n = sec(fb1 - fb0)
    tt2 = np.arange(n) / SR
    rattle = filt(noise(n), "bp", (1500, 5000), 2) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 24 * tt2))) * 0.025
    pad = (sine(110, n) + sine(164.8, n) * 0.6 + sine(220.5, n) * 0.3) * 0.05 * env_adsr(n, 1.0, 0.1, 1, 0.5)
    wind = filt(noise(n), "low", 500) * 0.12
    T.add(fb0, stereo(rattle + filt(pad, "low", 600) + wind))
    T.add(fb0, sub_hit(2.0, 60, 30, 0.4))
    # running footsteps, muffled
    t = fb0 + 0.3
    while t < L("l18")["start"]:
        n = sec(0.1)
        T.add(t, stereo(filt(noise(n), "low", 400) * expdecay(n, 0.02) * 0.2, rng.uniform(-0.6, 0.6)))
        t += 0.17 + rng.uniform(0, 0.08)

    # ---------- turn ----------
    t_turn = wt("l19", 2)
    T.add(t_turn - 0.9, riser(1.0, 0.45, 150, 2500))
    T.add(t_turn - 0.25, whoosh(0.45, True, 0.6))
    T.add(t_turn + 0.12, sub_hit(1.0, 120, 50, 0.6))
    T.add(cut, sub_hit(4.0, 60, 20, 1.2))
    T.add(cut, glitch_burst(0.1, 0.35, 9))
    n = sec(2.0)
    T.add(cut + 0.05, stereo(sine(6200, n) * env_adsr(n, 0.05, 0.1, 1.0, 1.4) * 0.04))

    # ---------- ear: flashlight dying ----------
    l20 = L("l20")
    die_t = l20["end"] + 0.55
    for k in range(6):
        T.add(die_t + k * 0.1 * (1 + 0.3 * k), click(0.35 - 0.04 * k, 3000))
    T.add(l20["start"] - 0.7, reverse_swell(0.75, 0.35))
    # ---------- door_mom ----------
    l21 = L("l21")
    T.add(l21["start"] - 1.25, metal_knock(0.35, seed=31))
    T.add(l21["start"] - 0.85, metal_knock(0.3, seed=32))
    t_mama = wt("l21", 3)
    T.add(t_mama + 0.4, creak(1.4, 0.3))
    n = sec(4.0)
    T.add(t_mama - 0.3, stereo(sine(np.geomspace(55, 38, n), n) * env_adsr(n, 1.5, 0.1, 1, 1.5) * 0.25))
    # ---------- end card ----------
    ec = at_scene("endcard")
    T.add(ec["t0"] + 0.3, sub_hit(3.5, 70, 22, 1.0))
    T.add(ec["t0"] + 0.3, glitch_burst(0.3, 0.35, 10))
    T.add(ec["t1"] - 1.4, metal_knock(0.25, seed=40))

    # ---------- voices with ducking ----------
    vb = np.zeros_like(T.buf)
    for ln in tl["lines"]:
        v = voice(ln["id"])
        i = sec(ln["start"])
        vb[i:i + len(v)] += v[:len(vb) - i]
    vl = np.abs(vb).max(axis=1)
    duck_env = signal.lfilter([0.0015], [1, -0.9985], (vl > 0.02).astype(np.float32))
    duck = 1 - 0.45 * np.clip(duck_env * 1.3, 0, 1)
    mix = T.buf * duck[:, None] + vb
    mix = mix[:sec(total)]
    # gentle master: soft clip + normalise
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.97
    out = os.path.join(ROOT, "build", "mix.wav")
    raw = (mix * 32767).astype(np.int16).tobytes()
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-af", "loudnorm=I=-15:TP=-1.0:LRA=14", "-ar", str(SR), out], input=raw, check=True)
    print("mix ->", out, f"{total:.2f}s")


if __name__ == "__main__":
    build()
