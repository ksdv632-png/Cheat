"""Drawing primitives (skia) + post-processing (numpy) shared by all scenes."""
import math, os
import numpy as np
import skia

W, H = 1080, 1920
SO = skia.SamplingOptions(skia.FilterMode.kLinear)
FONT_DIR = "/usr/share/fonts/opentype/inter/"
_tf = {}


def typeface(name):
    if name not in _tf:
        _tf[name] = skia.Typeface.MakeFromFile(FONT_DIR + name + ".otf")
    return _tf[name]


def font(size, name="InterDisplay-ExtraBold"):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    f.setSubpixel(True)
    return f


# ---------------------------------------------------------------- colours
RED = (255, 59, 47)
YEL = (255, 196, 46)
WHITE = (245, 242, 236)
BEAM = (243, 228, 196)
ORANGE = (255, 92, 26)


def col(rgb, a=1.0):
    return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(max(0, min(1, a)) * 255))


def paint(rgb=(0, 0, 0), a=1.0, blur=0.0, stroke=0.0, cap="round", shader=None, blend=None):
    p = skia.Paint(AntiAlias=True, Color=col(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    if blend == "add":
        p.setBlendMode(skia.BlendMode.kPlus)
    elif blend == "screen":
        p.setBlendMode(skia.BlendMode.kScreen)
    elif blend == "multiply":
        p.setBlendMode(skia.BlendMode.kMultiply)
    return p


def radial(cx, cy, r, stops):
    """stops: list of (pos, rgb, alpha)"""
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), max(1, r),
                                          [col(c, a) for _, c, a in stops], [p for p, _, _ in stops])


def linear(x0, y0, x1, y1, stops):
    return skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)],
                                          [col(c, a) for _, c, a in stops], [p for p, _, _ in stops])


# ---------------------------------------------------------------- easing / helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ramp(t, t0, t1):
    if t1 == t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def hash01(*a):
    x = math.sin(sum((i + 1) * 12.9898 * v for i, v in enumerate(a)) + 78.233) * 43758.5453
    return x - math.floor(x)


def vnoise(t, seed=0.0):
    """smooth 1D value noise in [-1,1]"""
    i = math.floor(t); f = t - i
    a = hash01(i, seed) * 2 - 1; b = hash01(i + 1, seed) * 2 - 1
    return lerp(a, b, f * f * (3 - 2 * f))


def fbm(t, seed=0.0):
    return 0.6 * vnoise(t, seed) + 0.3 * vnoise(t * 2.13, seed + 7) + 0.1 * vnoise(t * 4.7, seed + 13)


# ---------------------------------------------------------------- textures
_tex = {}


def _noise_field(h, w, seed, octaves=5, base=6):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    import cv2
    for o in range(octaves):
        gh, gw = base * 2 ** o, int(base * 2 ** o * w / h) + 1
        g = rng.random((gh, gw)).astype(np.float32)
        acc += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp; amp *= 0.55
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
    return acc


def image_from(arr):
    arr = np.ascontiguousarray(arr)
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


def concrete(seed=3, tint=(40, 44, 50), contrast=0.55, w=W, h=H, panels=True):
    key = ("concrete", seed, tint, contrast, w, h, panels)
    if key in _tex:
        return _tex[key]
    n = _noise_field(h, w, seed, 6, 5)
    fine = np.random.default_rng(seed + 1).random((h, w)).astype(np.float32)
    v = 0.75 + contrast * (n - 0.5) + 0.10 * (fine - 0.5)
    if panels:  # horizontal concrete pour seams + some stains
        for y in range(0, h, 360):
            v[max(0, y - 2):y + 2, :] *= 0.55
        for x in range(0, w, 540):
            v[:, max(0, x - 1):x + 2] *= 0.75
    stains = _noise_field(h, w, seed + 9, 3, 3)
    v *= 0.85 + 0.3 * stains
    rgb = np.stack([v * tint[0], v * tint[1], v * tint[2]], -1)
    out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.full((h, w), 255, np.uint8)])
    img = image_from(out)
    _tex[key] = img
    return img


def skin_texture(seed=5, base=(196, 146, 96), w=700, h=900):
    key = ("skin", seed, base, w, h)
    if key in _tex:
        return _tex[key]
    n = _noise_field(h, w, seed, 5, 8)
    fine = np.random.default_rng(seed).random((h, w)).astype(np.float32)
    v = 0.82 + 0.35 * (n - 0.5) + 0.22 * (fine - 0.5)
    rgb = np.stack([v * base[0], v * base[1], v * base[2]], -1)
    out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.full((h, w), 255, np.uint8)])
    _tex[key] = image_from(out)
    return _tex[key]


# ---------------------------------------------------------------- shapes
def person_path(x, yb, h, wide=1.0, head_scale=1.0, neck=1.0, head_dx=0.0, head_stretch=1.0):
    """Pawn-like silhouette from episode 1: arched body + neck + round head. yb = feet line."""
    p = skia.Path()
    bw = 0.20 * h * wide
    top = yb - 0.62 * h
    r = 0.17 * h * min(1.0, wide)
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect(x - bw, top, x + bw, yb + 4), r, r))
    nw = 0.028 * h * neck
    p.addRect(skia.Rect(x - nw + head_dx * 0.5, top - 0.08 * h, x + nw + head_dx * 0.5, top + 2))
    hr = 0.085 * h * head_scale
    cy = top - 0.115 * h - (head_stretch - 1) * hr
    p.addOval(skia.Rect(x + head_dx - hr, cy - hr * head_stretch, x + head_dx + hr, cy + hr * head_stretch))
    return p


def arm(c, x, yb, h, raise_t, side=-1, p=None, wide=1.0):
    """raise the (viewer-left = their right) arm. raise_t 0..1"""
    if raise_t <= 0.001:
        return
    sx = x + side * 0.15 * h * wide
    sy = yb - 0.53 * h
    ang = math.radians(lerp(178, 14, ease_io(raise_t)))
    L1 = 0.30 * h
    ex = sx + side * math.sin(ang) * L1
    ey = sy - math.cos(ang) * L1
    path = skia.Path(); path.moveTo(sx, sy); path.lineTo(ex, ey)
    pp = skia.Paint(p) if p is not None else paint((0, 0, 0))
    pp.setStyle(skia.Paint.kStroke_Style); pp.setStrokeWidth(0.075 * h); pp.setStrokeCap(skia.Paint.kRound_Cap)
    c.drawPath(path, pp)
    hp = skia.Paint(p) if p is not None else paint((0, 0, 0))
    c.drawCircle(ex, ey, 0.05 * h, hp)


def stickman(c, x, yb, h, phase, p, run=1.0, lean=0.18):
    """Running stick figure (flashback, like episode 1)."""
    sw = 0.085 * h
    pp = skia.Paint(p); pp.setStyle(skia.Paint.kStroke_Style); pp.setStrokeWidth(sw)
    pp.setStrokeCap(skia.Paint.kRound_Cap); pp.setStrokeJoin(skia.Paint.kRound_Join)
    hip = (x, yb - 0.48 * h + abs(math.sin(phase)) * 0.03 * h * run)
    neck_ = (hip[0] + lean * h * 0.5, hip[1] - 0.34 * h)
    head = (neck_[0] + lean * h * 0.12, neck_[1] - 0.12 * h)
    c.drawCircle(head[0], head[1], 0.085 * h, p)
    path = skia.Path(); path.moveTo(*hip); path.lineTo(*neck_)
    for s in (0, math.pi):  # legs
        a = math.sin(phase + s) * 0.9 * run
        knee = (hip[0] + math.sin(a) * 0.25 * h, hip[1] + math.cos(a) * 0.25 * h)
        b = a - (0.9 + 0.6 * math.sin(phase + s + 1.2)) * run
        foot = (knee[0] + math.sin(b) * 0.25 * h, knee[1] + math.cos(b) * 0.25 * h)
        path.moveTo(*hip); path.lineTo(*knee); path.lineTo(*foot)
    for s in (math.pi, 0):  # arms
        a = math.sin(phase + s) * 1.0 * run
        el = (neck_[0] + math.sin(a) * 0.18 * h, neck_[1] + 0.05 * h + math.cos(a) * 0.16 * h)
        hd = (el[0] + math.sin(a + 1.3) * 0.15 * h, el[1] - math.cos(a + 1.3) * 0.02 * h)
        path.moveTo(neck_[0], neck_[1] + 0.04 * h); path.lineTo(*el); path.lineTo(*hd)
    c.drawPath(path, pp)


def glow_eyes(c, x, y, s, a=1.0, open_=1.0, color=RED, gap=1.0):
    """pair of red slit eyes with glow"""
    if a <= 0.01 or open_ <= 0.01:
        return
    for dx in (-1, 1):
        ex = x + dx * s * 0.9 * gap
        c.drawOval(skia.Rect(ex - s * 1.6, y - s * 1.4, ex + s * 1.6, y + s * 1.4), paint(color, 0.35 * a, blur=s * 1.2))
        c.drawOval(skia.Rect(ex - s * 0.62, y - s * 0.26 * open_, ex + s * 0.62, y + s * 0.26 * open_), paint(color, a, blur=s * 0.08))
        c.drawOval(skia.Rect(ex - s * 0.38, y - s * 0.10 * open_, ex + s * 0.38, y + s * 0.10 * open_), paint((255, 190, 170), 0.8 * a))


def rings(c, cx, cy, rx, ry, n, t, a=0.5, rgb=(200, 205, 215), speed=0.25, width=3.0):
    """concentric ellipse sound-rings (episode-1 motif) expanding outward"""
    for i in range(n):
        f = ((i / n) + t * speed) % 1.0
        al = a * math.sin(math.pi * f) ** 1.2
        c.drawOval(skia.Rect(cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f), paint(rgb, al, stroke=width))


def beam(c, ox, oy, angle, length, spread, a=1.0, rgb=BEAM):
    """flashlight cone from origin, angle in degrees (0 = up)"""
    if a <= 0.005:
        return
    ang = math.radians(angle)
    dx, dy = math.sin(ang), -math.cos(ang)
    px, py = -dy, dx
    hw = math.tan(math.radians(spread)) * length
    path = skia.Path()
    path.moveTo(ox + px * 10, oy + py * 10)
    path.lineTo(ox + dx * length + px * hw, oy + dy * length + py * hw)
    path.lineTo(ox + dx * length - px * hw, oy + dy * length - py * hw)
    path.lineTo(ox - px * 10, oy - py * 10)
    path.close()
    sh = linear(ox, oy, ox + dx * length, oy + dy * length,
                [(0, rgb, 0.55 * a), (0.35, rgb, 0.28 * a), (1, rgb, 0.0)])
    c.drawPath(path, paint(rgb, 1, blur=28, shader=sh, blend="screen"))


def rivets(c, y, x0, x1, step, a=0.6):
    x = x0
    while x <= x1:
        c.drawCircle(x, y, 5, paint((120, 128, 138), a))
        c.drawCircle(x - 1.5, y - 1.5, 2, paint((190, 196, 205), a * 0.7))
        x += step


def wheel(c, cx, cy, r, rot, a=1.0, rgb=(150, 154, 160)):
    c.drawCircle(cx + 6, cy + 10, r + 8, paint((0, 0, 0), 0.6 * a, blur=16))
    c.drawCircle(cx, cy, r, paint(rgb, a, stroke=r * 0.13))
    for i in range(6):
        ang = rot + i * math.pi / 3
        path = skia.Path(); path.moveTo(cx, cy)
        path.lineTo(cx + math.cos(ang) * r, cy + math.sin(ang) * r)
        c.drawPath(path, paint(rgb, a, stroke=r * 0.085))
    c.drawCircle(cx, cy, r * 0.16, paint(rgb, a))
    c.drawCircle(cx - r * 0.05, cy - r * 0.05, r * 0.07, paint((215, 220, 226), 0.6 * a))
    # rim highlight
    c.drawArc(skia.Rect(cx - r, cy - r, cx + r, cy + r), 200, 80, False, paint((220, 225, 232), 0.35 * a, stroke=4))


def door(c, t, shake=0.0, light=1.0, wheel_rot=0.0, seam_glow=0.0, frost=0.0):
    """Heavy bunker door, full frame, episode-1 style."""
    c.save()
    c.translate(shake * vnoise(t * 40, 1) * 22, shake * vnoise(t * 40, 2) * 14)
    c.drawImageRect(concrete(11, (58, 66, 76), 0.35, panels=False), skia.Rect(-40, -40, W + 40, H + 40),
                     SO, paint((255, 255, 255), light))
    # door frame + panels
    c.drawRect(skia.Rect(-40, 380, W + 40, 400), paint((10, 12, 15), 0.85 * light))
    c.drawRect(skia.Rect(-40, 1530, W + 40, 1550), paint((10, 12, 15), 0.85 * light))
    c.drawRect(skia.Rect(W / 2 - 6, 400, W / 2 + 6, 1530), paint((10, 12, 15), 0.7 * light))
    rivets(c, 430, 40, W - 40, 62, 0.55 * light)
    rivets(c, 1500, 40, W - 40, 62, 0.55 * light)
    if seam_glow > 0:
        c.drawRect(skia.Rect(W / 2 - 3, 400, W / 2 + 3, 1530), paint((200, 225, 255), seam_glow, blur=6))
        c.drawRect(skia.Rect(W / 2 - 30, 400, W / 2 + 30, 1530), paint((150, 190, 255), seam_glow * 0.25, blur=30))
    wheel(c, W / 2, 900, 250, wheel_rot, light)
    if frost > 0:
        draw_frost(c, frost, t)
    c.restore()


_frost_cache = {}


def draw_frost(c, amount, t):
    """crystalline frost creeping in from the door seam and edges"""
    if "segs" not in _frost_cache:
        rng = np.random.default_rng(42)
        segs = []
        def grow(x, y, ang, length, depth, t0):
            if depth > 5 or length < 8:
                return
            x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
            segs.append((x, y, x2, y2, t0, depth))
            n = 2 if depth < 3 else 1
            for _ in range(n):
                grow(x2, y2, ang + rng.uniform(-0.9, 0.9), length * rng.uniform(0.55, 0.8), depth + 1, t0 + 0.08)
        for i in range(60):
            if i < 30:  # from the seam
                x, y = W / 2 + rng.choice([-4, 4]), rng.uniform(420, 1520)
                ang = (0 if x > W / 2 else math.pi) + rng.uniform(-0.7, 0.7)
            else:  # from frame edges
                side = rng.integers(4)
                if side == 0: x, y, ang = rng.uniform(0, W), 400, math.pi / 2
                elif side == 1: x, y, ang = rng.uniform(0, W), 1530, -math.pi / 2
                elif side == 2: x, y, ang = 0, rng.uniform(400, 1530), 0
                else: x, y, ang = W, rng.uniform(400, 1530), math.pi
                ang += rng.uniform(-0.6, 0.6)
            grow(x, y, ang, rng.uniform(40, 120), 0, rng.uniform(0, 0.6))
        _frost_cache["segs"] = segs
    for (x, y, x2, y2, t0, d) in _frost_cache["segs"]:
        k = clamp((amount - t0) / 0.25)
        if k <= 0:
            continue
        xe, ye = lerp(x, x2, k), lerp(y, y2, k)
        path = skia.Path(); path.moveTo(x, y); path.lineTo(xe, ye)
        c.drawPath(path, paint((215, 235, 255), 0.55 - d * 0.07, stroke=max(1.2, 4 - d * 0.6)))
    # haze
    c.drawRect(skia.Rect(W / 2 - 220, 400, W / 2 + 220, 1530),
               paint((200, 225, 255), 0.08 * amount, blur=80))


# ---------------------------------------------------------------- faces
def egg_face(c, t, cx, cy, s, mouth, look=(0.0, 0.0), blink=0.0, kind="old", fear=0.0, light=1.0, sweat=0.0):
    """Episode-1 style egg head. s = scale (1 => 300x400 radii). mouth 0..1 openness."""
    rx, ry = 300 * s, 400 * s
    rect = skia.Rect(cx - rx, cy - ry, cx + rx, cy + ry)
    # drop shadow / halo
    c.drawOval(rect.makeOutset(30 * s, 30 * s), paint((0, 0, 0), 0.8, blur=40 * s))
    c.save()
    clip = skia.Path(); clip.addOval(rect)
    c.clipPath(clip, doAntiAlias=True)
    base = (196, 146, 96) if kind == "old" else (170, 120, 84)
    c.drawImageRect(skin_texture(5 if kind == "old" else 8, base), rect, SO, paint((255, 255, 255), 1))
    # under-lighting (flashlight from below) and edge darkening
    c.drawRect(rect, paint(shader=radial(cx, cy + ry * 0.35, ry * 1.25,
                                         [(0, (0, 0, 0), 0.0), (0.55, (0, 0, 0), 0.15), (1, (0, 0, 0), 0.92)])))
    c.drawRect(rect, paint((0, 0, 0), 1 - light))
    if kind == "old":  # white hair cap
        c.drawRect(skia.Rect(cx - rx, cy - ry, cx + rx, cy - ry * 0.70),
                   paint(shader=linear(0, cy - ry, 0, cy - ry * 0.70, [(0, (230, 230, 228), light), (1, (205, 205, 200), light)])))
        c.drawOval(skia.Rect(cx - rx, cy - ry * 0.76, cx + rx, cy - ry * 0.64), paint((0, 0, 0), 0.25, blur=8))
    else:  # victor: dark messy hair + stubble
        hp = skia.Path()
        hp.moveTo(cx - rx, cy - ry * 0.55)
        for i in range(13):
            xx = cx - rx + (2 * rx) * i / 12
            yy = cy - ry * (0.62 + 0.08 * math.sin(i * 2.7) + 0.03 * vnoise(t * 3 + i))
            hp.lineTo(xx, yy)
        hp.lineTo(cx + rx, cy - ry); hp.lineTo(cx - rx, cy - ry); hp.close()
        c.drawPath(hp, paint((26, 20, 16), 0.97 * light))
        rng = np.random.default_rng(3)
        for _ in range(260):
            a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0.15, 1))
            sx, sy = cx + math.cos(a) * rx * 0.55 * r, cy + ry * 0.42 + math.sin(a) * ry * 0.28 * r
            if sy > cy + ry * 0.18:
                c.drawCircle(sx, sy, 2.2 * s, paint((40, 28, 20), 0.55 * light))
    ey = cy - ry * 0.12
    ex = rx * 0.37
    for side in (-1, 1):
        x = cx + side * ex
        # sockets
        c.drawOval(skia.Rect(x - 95 * s, ey - 55 * s, x + 95 * s, ey + 60 * s), paint((0, 0, 0), 0.85, blur=26 * s))
        # eyes
        eh = (24 + 14 * fear) * s * (1 - blink)
        if eh > 1:
            c.drawOval(skia.Rect(x - 42 * s, ey - eh, x + 42 * s, ey + eh), paint((236, 232, 222), light))
            pr = (15 - 6 * fear) * s
            px = x + look[0] * 22 * s; py = ey + look[1] * 8 * s
            c.save(); cl = skia.Path(); cl.addOval(skia.Rect(x - 42 * s, ey - eh, x + 42 * s, ey + eh)); c.clipPath(cl, doAntiAlias=True)
            c.drawCircle(px, py, pr, paint((14, 12, 10), 1))
            c.drawCircle(px - pr * 0.35, py - pr * 0.4, pr * 0.28, paint((255, 255, 255), 0.85 * light))
            c.restore()
        # brows
        bp = skia.Path()
        inner = 40 * s * (1 + fear * 0.8)
        bp.moveTo(x - side * 70 * s, ey - 70 * s - (10 * fear * s if True else 0))
        bp.lineTo(x + side * 55 * s, ey - 70 * s - inner * (0.25 if kind == "old" else 0.45) * (1 if side == 1 else 1))
        bp2 = skia.Path()
        x_in, x_out = x - side * 60 * s, x + side * 60 * s
        bp2.moveTo(x_out, ey - 62 * s - 6 * s)
        bp2.quadTo(x, ey - 80 * s - 10 * fear * s, x_in, ey - 70 * s - 18 * fear * s)
        c.drawPath(bp2, paint((40, 28, 20) if kind == "old" else (24, 16, 12), 0.9 * light, stroke=14 * s))
    # nose shadow
    c.drawOval(skia.Rect(cx - 40 * s, cy - 10 * s, cx + 40 * s, cy + 150 * s), paint((40, 25, 15), 0.55, blur=22 * s))
    c.drawOval(skia.Rect(cx - 55 * s, cy + 120 * s, cx + 55 * s, cy + 160 * s), paint((30, 18, 10), 0.45, blur=12 * s))
    # mouth
    my = cy + ry * 0.53
    mw = (70 + 15 * mouth) * s
    mh = (4 + 50 * mouth) * s
    c.drawOval(skia.Rect(cx - mw, my - mh * 0.45, cx + mw, my + mh * 0.55), paint((18, 8, 6), 0.95))
    if mouth > 0.25:
        c.drawRect(skia.Rect(cx - mw * 0.6, my - mh * 0.45, cx + mw * 0.6, my - mh * 0.45 + 8 * s), paint((200, 190, 170), 0.35 * light))
    if sweat > 0:
        for i, (sx, sy0) in enumerate([(-0.55, -0.45), (0.62, -0.3), (0.35, -0.55)]):
            ph = (t * 0.35 + i * 0.37) % 1.0
            px = cx + sx * rx; py = cy + sy0 * ry + ph * 160 * s
            c.drawOval(skia.Rect(px - 9 * s, py - 14 * s, px + 9 * s, py + 14 * s), paint((235, 240, 245), 0.55 * sweat * light * (1 - ph)))
    c.restore()
    # rim
    c.drawOval(rect, paint((0, 0, 0), 0.6, stroke=6, blur=4))


# ---------------------------------------------------------------- post FX
class Post:
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.grain = (rng.standard_normal((H + 256, W + 256)).astype(np.float32))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.60)) ** 2)
        self.vig = np.clip(1.0 - 0.75 * d ** 2.2, 0.0, 1.0).astype(np.float32)
        self.scan = (0.86 + 0.14 * (np.arange(H) % 4 < 2)).astype(np.float32)[:, None, None]

    def apply(self, img, t, fx):
        f = img[:, :, :3].astype(np.float32)
        # glitch: horizontal slice displacement
        g = fx.get("glitch", 0.0)
        if g > 0.01:
            rng = np.random.default_rng(int(t * 30 * 7919) % 2**31)
            for _ in range(int(3 + 10 * g)):
                y0 = rng.integers(0, H - 40); hh = rng.integers(6, int(20 + 140 * g))
                f[y0:y0 + hh] = np.roll(f[y0:y0 + hh], int(rng.integers(-1, 2) * rng.uniform(10, 120) * g), axis=1)
        ca = fx.get("ca", 0.0) + g * 10
        if ca >= 1:
            s = int(ca)
            f[:, :, 0] = np.roll(f[:, :, 0], s, axis=1)
            f[:, :, 2] = np.roll(f[:, :, 2], -s, axis=1)
        tint = fx.get("tint")
        if tint is not None:
            lum = f.mean(axis=2, keepdims=True)
            f = f * (1 - tint[3]) + lum * np.array(tint[:3], np.float32)[None, None] / 255.0 * tint[3]
        if fx.get("scan", 0) > 0:
            f *= (1 - fx["scan"]) + fx["scan"] * self.scan
        vig = fx.get("vig", 1.0)
        if vig > 0:
            f *= (1 - vig) + vig * self.vig[:, :, None]
        f *= fx.get("bright", 1.0)
        gs = fx.get("grain", 10.0)
        if gs > 0:
            rng = np.random.default_rng(int(t * 30) * 31 + 7)
            ox, oy = rng.integers(0, 256, 2)
            n = self.grain[oy:oy + H, ox:ox + W]
            lum = f.mean(axis=2) / 255.0
            amp = gs * (0.55 + 0.9 * np.sqrt(np.clip(lum, 0, 1)))  # more grain in mids/highs, like film
            f += (n * amp)[:, :, None]
        return np.clip(f, 0, 255).astype(np.uint8)


def masked(c, draw, mask_shader):
    """draw something, then keep only where mask_shader alpha is (soft light pools)."""
    c.saveLayer(None, None)
    draw()
    p = skia.Paint(AntiAlias=True); p.setShader(mask_shader); p.setBlendMode(skia.BlendMode.kDstIn)
    c.drawRect(skia.Rect(-2000, -2000, 4000, 4000), p)
    c.restore()


def mother(c, x, yb, h, p, beckon=0.0, t=0.0, tall=1.0):
    """silhouette of a woman: long hair, A-line dress. beckon 0..1 raises right arm and waves it."""
    hh = h * tall
    hr = 0.068 * h
    hy = yb - hh + hr
    # hair (long, falls behind shoulders)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x - hr * 1.25, hy - hr * 1.05, x + hr * 1.25, hy + hr * 2.9), hr * 1.2, hr * 1.2), p)
    c.drawCircle(x, hy, hr, p)
    sy = hy + hr * 1.6
    neck = skia.Rect(x - hr * 0.35, hy + hr * 0.6, x + hr * 0.35, sy + 4)
    c.drawRect(neck, p)
    d = skia.Path()
    d.moveTo(x - 0.085 * h, sy)
    d.quadTo(x - 0.065 * h, sy + 0.12 * h, x - 0.05 * h, sy + 0.2 * h)
    d.quadTo(x - 0.17 * h, yb - 0.25 * h, x - 0.2 * h, yb - 0.06 * h)
    d.quadTo(x, yb - 0.02 * h, x + 0.2 * h, yb - 0.06 * h)
    d.quadTo(x + 0.17 * h, yb - 0.25 * h, x + 0.05 * h, sy + 0.2 * h)
    d.quadTo(x + 0.065 * h, sy + 0.12 * h, x + 0.085 * h, sy)
    d.close()
    c.drawPath(d, p)
    for s in (-1, 1):  # legs
        c.drawRect(skia.Rect(x + s * 0.06 * h - 0.012 * h, yb - 0.08 * h, x + s * 0.06 * h + 0.012 * h, yb), p)
    ap = skia.Paint(p); ap.setStyle(skia.Paint.kStroke_Style); ap.setStrokeWidth(0.03 * h); ap.setStrokeCap(skia.Paint.kRound_Cap)
    # left arm hangs
    path = skia.Path(); path.moveTo(x - 0.075 * h, sy + 0.01 * h); path.lineTo(x - 0.1 * h, sy + 0.3 * h)
    c.drawPath(path, ap)
    # right arm beckons
    ang = math.radians(lerp(172, 35, ease_io(beckon)) + 10 * math.sin(t * 4.5) * beckon)
    L1 = 0.17 * h
    ex = x + 0.075 * h + math.sin(ang) * L1 * 0.6
    ey = sy + 0.01 * h - math.cos(ang) * L1
    path = skia.Path(); path.moveTo(x + 0.075 * h, sy + 0.01 * h); path.lineTo(ex, ey)
    fa = ang - math.radians(25 + 30 * (0.5 + 0.5 * math.sin(t * 4.5)) * beckon)
    path.lineTo(ex + math.sin(fa) * L1 * 0.8, ey - math.cos(fa) * L1 * 0.8)
    c.drawPath(path, ap)
