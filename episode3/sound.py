"""Sound design + voice processing + final mix for episode 3 (all procedural, 48 kHz stereo).

python3 sound.py  ->  build/mix.wav
"""
import math, os, subprocess
import numpy as np
from scipy import signal

import timeline as TL
from render import wt, L

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
    elif spk == "mom":
        if lid == "l07":  # the lullaby, warm, distant, through the steel
            x = filt(norm_peak(x), "low", 2600, 2)
            x = reverb(x, 0.5, length=3.0, tau=0.9, bright=2800, seed=15, pre=0.04)
            g = 0.85
        else:  # behind the door; the last word sinks into something that is not her
            clean = filt(norm_peak(x), "low", 800, 4)
            x = reverb(clean, 0.4, length=2.2, tau=0.6, bright=1200, seed=16)
            if lid == "l21":
                low = ff(path, "rubberband=pitch=0.7:formant=shifted")
                low = filt(norm_peak(low)[:len(clean)], "low", 700, 4)
                if len(low) < len(clean):
                    low = np.vstack([low, np.zeros((len(clean) - len(low), 2), np.float32)])
                ramp_ = np.clip((np.arange(len(clean)) / SR - 1.0) / 0.6, 0, 1)[:, None]
                x = reverb(clean * (1 - 0.45 * ramp_) + low * ramp_ * 0.9, 0.4, length=2.2, tau=0.6, bright=1200, seed=16)
            g = 0.8
    else:  # thing
        if lid == "l14":  # Dima's own voice, a whisper right at the shoulder
            x = filt(norm_peak(x), "high", 300, 2) * 1.2
            x = reverb(x, 0.35, length=1.8, tau=0.5, bright=3500, seed=18)
            x = x * np.array([0.35, 1.0], np.float32)
            g = 0.95
        else:  # the narrator's voice pitched down, doubled, whispering
            a = ff(path, "rubberband=pitch=0.74:formant=shifted")
            b = ff(path, "rubberband=pitch=0.5:formant=shifted")
            n = len(x)
            a = np.resize(a, (n, 2)); b = np.resize(b, (n, 2))
            wh = filt(x, "high", 2200, 2) * 1.6
            x = norm_peak(a) * 0.9 + norm_peak(b) * 0.35 + norm_peak(wh) * 0.35
            x = comp(x, 0.3, 4)
            x = reverb(x, 0.3, length=2.5, tau=0.8, bright=2500, seed=17)
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

    level = {"door_cold": 0.35, "door_walk": 0.5, "oldman": 0.55, "door_hand": 0.6, "lullaby": 0.3, "dima_face": 0.7,
             "door_reach": 0.8, "silence": 0.05, "behind": 0.75, "wheel": 0.85, "open": 0.7, "endcard": 0.45}
    lv = np.zeros(n_all, np.float32)
    for s in tl["scenes"]:
        lv[sec(s["t0"]):sec(s["t1"])] = level[s["name"]]
    lv[sec(total):] = 0
    title_end = L("l01")["start"] - 0.25
    lv[sec(L("l00")["end"] + 0.5):sec(title_end)] *= 0.4
    lv = filt(lv, "low", 1.2, 2).astype(np.float32)
    lv *= (0.8 + 0.4 * np.clip(tt / total, 0, 1)).astype(np.float32)

    d = (sine(41.2, n_all) * 0.5 + sine(41.6, n_all) * 0.5 + sine(61.8, n_all) * 0.28 + sine(82.0, n_all) * 0.18
         + sine(123.6 + 0.8 * np.sin(tt * 0.2), n_all) * 0.08)
    air = filt(noise(n_all), "bp", (90, 900), 2) * 0.35
    air_hi = filt(noise(n_all), "bp", (1800, 4000), 2) * 0.05 * (0.5 + 0.5 * np.sin(tt * 0.37))
    drone = (d * 0.55 + air + air_hi) * lv
    T.buf[:, 0] += drone * 0.32
    T.buf[:, 1] += np.roll(drone, 300) * 0.32
    cl = (sine(587.3, n_all) + sine(622.3, n_all) * 0.8 + sine(659.3 + 2 * np.sin(tt * 0.3), n_all) * 0.6)
    cl = filt(cl * (0.6 + 0.4 * np.sin(tt * 3.1)), "low", 1500, 2) * np.clip((tt - 40) / 60, 0, 1) * lv * 0.035
    T.buf[:, 0] += cl; T.buf[:, 1] += np.roll(cl, 900)

    # heartbeat 62 -> 118 bpm
    hb_on = {"door_walk", "door_hand", "dima_face", "door_reach", "behind", "wheel", "oldman"}
    hb = heartbeat(); t = 2.0
    while t < total - 4:
        s = TL.scene_at(t)
        bpm = 62 + 56 * (t / total) + (14 if s["name"] in ("door_reach", "wheel") else 0)
        if s["name"] in hb_on:
            T.add(t, hb, 0.7 if s["name"] in ("door_reach", "behind") else 0.5)
        t += 60.0 / bpm

    # cold open + title
    T.add(0.15, sub_hit(3.0, 55, 25, 0.7))
    T.add(L("l00")["start"] - 0.6, reverse_swell(0.7, 0.35))
    dc = at_scene("door_cold")
    T.add(dc["t0"] + 0.2, frost_crackle(dc["t1"] - dc["t0"], 0.16))
    n = sec(dc["t1"] - dc["t0"])
    T.add(dc["t0"], stereo(filt(noise(n), "bp", (400, 1400), 2) * (0.4 + 0.6 * np.sin(np.linspace(0, 3, n)) ** 2) * 0.05, 0.2))
    tst = L("l00")["end"] + 0.5
    T.add(tst + 0.25, glitch_burst(0.35, 0.4, 1)); T.add(tst + 0.3, sub_hit(2.5, 80, 30, 0.9))
    T.add(tst + 1.2, glitch_burst(0.08, 0.25, 2)); T.add(title_end - 0.35, glitch_burst(0.3, 0.35, 3))

    # walking to the door: slow footsteps
    w0 = L("l02")["start"]
    for i in range(7):
        n = sec(0.13)
        T.add(w0 + i * 0.5, stereo(filt(noise(n), "low", 500) * expdecay(n, 0.03) * 0.3, (-1) ** i * 0.2))

    # old man cuts in
    T.add(L("l03")["start"] - 0.1, whoosh(0.3, True, 0.15))

    # hand on the metal
    t_h = L("l05")["start"] + 0.7
    T.add(t_h, metal_knock(0.25, seed=50)); T.add(t_h, frost_crackle(2.5, 0.2))
    T.add(t_h + 0.1, sub_hit(1.2, 70, 35, 0.4))

    # lullaby: warm pad that dies with the last note
    ll = at_scene("lullaby")
    n = sec(ll["t1"] - ll["t0"])
    pad = (sine(220.0, n) + sine(277.2, n) * 0.7 + sine(329.6, n) * 0.5) * 0.06 * env_adsr(n, 0.8, 0.1, 1, 1.0)
    T.add(ll["t0"], stereo(filt(pad, "low", 900)))

    # dima face: breath and his own heartbeat louder
    dm = at_scene("dima_face", 0)
    T.add(dm["t0"] + 0.2, stereo(breath(1.2, True, 0.2), 0.0)); T.add(dm["t0"] + 1.4, stereo(breath(1.4, False, 0.2), 0.0))
    # reach
    t_w = wt("l09", 5)
    T.add(t_w - 1.0, riser(1.0, 0.3)); T.add(L("l10")["start"] - 0.05, sub_hit(2.0, 60, 25, 0.6))

    # silence: cold hiss only, then the shoulder whisper
    sl = at_scene("silence")
    T.add(sl["t0"], frost_crackle(sl["t1"] - sl["t0"], 0.1))
    t_w1 = L("l14")["start"]
    T.add(t_w1 - 0.6, reverse_swell(0.6, 0.4)); T.add(t_w1 + 0.4, sub_hit(2.5, 70, 25, 0.8))
    T.add(t_w1 + 0.4, glitch_burst(0.12, 0.3, 4))
    # breath at the ear while he explains
    bh = at_scene("behind")
    t = L("l15")["start"]
    while t < L("l15")["end"]:
        T.add(t, stereo(breath(1.0, True, 0.14), 0.8)); T.add(t + 1.1, stereo(breath(1.1, False, 0.13), 0.8)); t += 2.4
    T.add(L("l16")["start"] - 0.4, reverse_swell(0.5, 0.3))

    # wheel moves by itself
    t_d = wt("l18", 8, True) - 0.35
    T.add(t_d, metal_knock(0.9, seed=60)); T.add(t_d, sub_hit(1.5, 60, 30, 0.6)); T.add(t_d, glitch_burst(0.1, 0.25, 5))
    t_s = L("l19")["start"]
    T.add(t_s + 0.1, creak(2.4, 0.4)); T.add(t_s + 0.9, metal_knock(0.5, seed=61)); T.add(t_s + 1.9, metal_knock(0.6, seed=62))
    T.add(t_s + 2.1, riser(1.3, 0.35, 120, 1800))

    # door opens
    t_o = L("l20")["start"]
    T.add(t_o - 0.2, sub_hit(4.0, 60, 20, 1.0)); T.add(t_o, creak(2.6, 0.5)); T.add(t_o, glitch_burst(0.1, 0.35, 6))
    n = sec(5.0)
    T.add(t_o + 0.3, stereo(filt(noise(n), "bp", (200, 1200), 2) * env_adsr(n, 1.5, 0.1, 1, 1.5) * 0.12))
    t_c = L("l22")["start"]
    T.add(t_c - 0.3, reverse_swell(0.6, 0.4))
    for k in range(11):
        T.add(t_c + 0.1 + k * 0.23, stereo(breath(0.7, k % 2 == 0, 0.1), (k - 5) / 6))
    ec = at_scene("endcard")
    T.add(ec["t0"] + 0.3, sub_hit(3.5, 70, 22, 1.0)); T.add(ec["t0"] + 0.3, glitch_burst(0.3, 0.35, 10))
    T.add(ec["t1"] - 1.4, metal_knock(0.25, seed=40))

    # voices with ducking
    vb = np.zeros_like(T.buf)
    for ln in tl["lines"]:
        v = voice(ln["id"]); i = sec(ln["start"])
        vb[i:i + len(v)] += v[:len(vb) - i]
    vl = np.abs(vb).max(axis=1)
    duck_env = signal.lfilter([0.0015], [1, -0.9985], (vl > 0.02).astype(np.float32))
    duck = 1 - 0.45 * np.clip(duck_env * 1.3, 0, 1)
    mix = (T.buf * duck[:, None] + vb)[:sec(total)]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.97
    out = os.path.join(ROOT, "build", "mix.wav")
    raw = (mix * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-af", "loudnorm=I=-15:TP=-1.0:LRA=14", "-ar", str(SR), out], input=raw, check=True)
    print("mix ->", out, f"{total:.2f}s")


if __name__ == "__main__":
    build()
