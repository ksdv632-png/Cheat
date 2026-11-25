"""Channel branding in the series style: avatar (1024x1024) and YouTube banner (2560x1440).

python3 channel/branding.py  ->  channel/avatar.png, channel/banner_youtube.png
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "episode3"))
import numpy as np
import skia
from gfx import (paint, radial, linear, concrete, person_path, glow_eyes, rings, wheel, font, col, SO,
                 RED, WHITE, BEAM)


def save(surface, path):
    arr = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    from PIL import Image
    Image.fromarray(arr[:, :, :3]).save(path)


def grain(surface, amount=7, seed=3):
    arr = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32)
    rng = np.random.default_rng(seed)
    arr[:, :, :3] += rng.standard_normal(arr.shape[:2])[:, :, None] * amount
    img = skia.Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType)
    surface.getCanvas().drawImage(img, 0, 0)


def text_center(c, txt, x, y, size, name, rgb, a=1.0, glow=0.0, spacing=0):
    f = font(size, name)
    w = sum(f.measureText(ch) + spacing for ch in txt) - spacing
    xx = x - w / 2
    for ch in txt:
        if glow:
            c.drawString(ch, xx, y, f, paint(rgb, glow * a, blur=size * 0.12))
        c.drawString(ch, xx, y, f, paint(rgb, a))
        xx += f.measureText(ch) + spacing


def avatar(path, S=1024):
    sf = skia.Surface(S, S); c = sf.getCanvas()
    c.clear(col((4, 4, 6)))
    c.drawImageRect(concrete(11, (50, 56, 64), 0.4, w=S, h=S, panels=False), skia.Rect(0, 0, S, S), SO, paint((255, 255, 255), 0.55))
    # bunker wheel behind, cold
    wheel(c, S / 2, S * 0.44, S * 0.36, 0.3, 0.22, (150, 160, 175))
    # red light from below
    c.drawRect(skia.Rect(0, 0, S, S), paint(shader=radial(S / 2, S * 1.05, S * 0.8, [(0, RED, 0.55), (1, RED, 0.0)]), blend="screen"))
    # the figure: head and shoulders, eyes open
    fig = person_path(S / 2, S * 1.25, S * 1.45, wide=0.95, head_stretch=1.1)
    c.drawPath(fig, paint(RED, 0.35, blur=24))
    c.drawPath(fig, paint((3, 3, 4), 1))
    glow_eyes(c, S / 2, S * 0.40, S * 0.032, 1.0, gap=1.25)
    # nick
    text_center(c, "SRV", S / 2, S * 0.86, S * 0.2, "InterDisplay-Black", WHITE, glow=0.35, spacing=S * 0.01)
    c.drawLine(S * 0.42, S * 0.9, S * 0.58, S * 0.9, paint(RED, 1, stroke=S * 0.008))
    # vignette, round-crop friendly
    c.drawRect(skia.Rect(0, 0, S, S), paint(shader=radial(S / 2, S / 2, S * 0.72, [(0, (0, 0, 0), 0), (0.75, (0, 0, 0), 0.25), (1, (0, 0, 0), 0.9)])))
    grain(sf, 6)
    save(sf, path)


def banner(path, Wb=2560, Hb=1440):
    sf = skia.Surface(Wb, Hb); c = sf.getCanvas()
    c.clear(col((4, 4, 6)))
    c.drawImageRect(concrete(3, (52, 56, 62), 0.5, w=Wb, h=Hb), skia.Rect(0, 0, Wb, Hb), SO, paint((255, 255, 255), 0.6))
    cy = Hb / 2
    # torch pool on the wall
    c.drawRect(skia.Rect(0, 0, Wb, Hb), paint(shader=radial(Wb / 2, cy - 40, 900, [(0, BEAM, 0.35), (0.5, BEAM, 0.12), (1, BEAM, 0.0)]), blend="screen"))
    # seven shadows on the wall, the seventh too tall, eyes red (safe area: 1546 x 423 centred)
    base = cy + 200
    xs = [440, 620, 800, 980, 1580, 1760, 1940, 2120]
    for i, x in enumerate(xs):
        odd = i == 6
        h = 430 * (1.12 if odd else 1.0)
        yb = base + (150 if odd else 40)
        c.drawPath(person_path(x, yb, h, head_stretch=1.12 if odd else 1.0), paint((8, 8, 10), 0.85, blur=6))
        if odd:
            glow_eyes(c, x, yb - h * 0.86, 12, 1.0)
    # title block
    text_center(c, "БУНКЕР", Wb / 2, cy + 40, 190, "InterDisplay-Black", WHITE, glow=0.3, spacing=6)
    c.drawLine(Wb / 2 - 90, cy + 80, Wb / 2 + 90, cy + 80, paint(RED, 1, stroke=6))
    text_center(c, "НОВАЯ СЕРИЯ КАЖДЫЙ ДЕНЬ В 10:00", Wb / 2, cy + 150, 46, "Inter-Bold", RED, spacing=8)
    text_center(c, "АНИМАЦИЯ · ВЫЖИВАНИЕ · УЖАСЫ", Wb / 2, cy - 140, 36, "Inter-SemiBold", (200, 200, 200), spacing=10)
    c.drawRect(skia.Rect(0, 0, Wb, Hb), paint(shader=radial(Wb / 2, cy, Wb * 0.62, [(0, (0, 0, 0), 0), (0.7, (0, 0, 0), 0.35), (1, (0, 0, 0), 0.9)])))
    grain(sf, 6)
    save(sf, path)


if __name__ == "__main__":
    avatar(os.path.join(HERE, "avatar.png"))
    banner(os.path.join(HERE, "banner_youtube.png"))
    print("ok")
