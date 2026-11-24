"""Episode 3 renderer.  python3 render.py [--preview t1,t2,...] [--out file.mp4] [--from T --to T]"""
import math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
import skia

import timeline as TL
import voiceenv as VE
from gfx import *

FPS = TL.FPS
ROOT = TL.ROOT


# ============================================================== helpers bound to the timeline
def L(lid):
    return TL.line(lid)


def wt(lid, i, end=False):
    return TL.word_time(lid, i, end)



def cam(c, cx, cy, z):
    """zoom around point (cx,cy) which ends at frame centre"""
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-cx, -cy)


def label(c, text, x, y, a, rgb=WHITE, size=30, name="Inter-SemiBold", spacing=6):
    if a <= 0.01:
        return
    f = font(size, name)
    wtot = sum(f.measureText(ch) + spacing for ch in text) - spacing
    xx = x - wtot / 2
    for ch in text:
        c.drawString(ch, xx, y, f, paint(rgb, a))
        xx += f.measureText(ch) + spacing


def big_number(c, txt, x, y, size, rgb, a=1.0, glow=0.6):
    f = font(size, "InterDisplay-Black")
    w = f.measureText(txt)
    c.drawString(txt, x - w / 2, y, f, paint(rgb, a * glow, blur=size * 0.12))
    c.drawString(txt, x - w / 2, y, f, paint(rgb, a))



def face_common(c, T, lt, S, kind="old", fear=0.0, look=None, light_fn=None):
    c.clear(col((0, 0, 0)))
    ln = S["lines"][-1]
    m = 0.0
    for l in S["lines"]:
        m = max(m, VE.at(l["id"], T))
    z = 1.0 + 0.05 * lt
    blink = 0.0
    for bt in (0.7, 2.9, 4.6):
        if 0 <= lt - bt < 0.16:
            blink = math.sin((lt - bt) / 0.16 * math.pi)
    lk = look(T) if look else (0.3 * vnoise(T * 0.8, 3), 0.1 * vnoise(T, 4))
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1500, 1200, [(0, (40, 28, 18), 1), (1, (0, 0, 0), 1)])))
    c.save(); cam(c, 540, 860, z)
    egg_face(c, T, 540, 860, 1.0, min(1, m), look=lk, blink=blink, kind=kind, fear=fear,
             light=light_fn(T) if light_fn else 1.0, sweat=1.0 if kind == "victor" else 0.0)
    c.restore()



# ============================================================== episode 3 scenes
def hand(c, x, y, s, a=1.0, ang=0.0, rim=0.5):
    """silhouette of a right hand seen from the back, fingers pointing up. (x,y) = wrist centre."""
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    body = paint((3, 3, 4), a)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-62, -150, 62, 20), 38, 38), body)
    for i, (fx, fl) in enumerate([(-52, 120), (-26, 150), (0, 160), (26, 148), (50, 112)]):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(fx - 13, -150 - fl, fx + 13, -120), 13, 13), body)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-110, -110, -50, -20), 26, 26), body)  # thumb
    c.drawArc(skia.Rect(-62, -150, 62, 20), 200, 120, False, paint(BEAM, rim * a, stroke=4, blur=3))
    c.drawRect(skia.Rect(-50, 18, 50, 160), body)  # forearm
    c.restore()


def door_light(T, base=0.8, seed=3):
    return base + 0.04 * vnoise(T * 13, seed)


def sc_door_cold(c, T, lt, S):
    l = S["lines"][0]
    fr = smooth(ramp(lt, 0.0, S["t1"] - S["t0"]))
    e = VE.at("l00", T)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 900, 1.0 + 0.10 * ease_io(lt / (S["t1"] - S["t0"])))
    door(c, T, light=0.55 + 0.1 * e, wheel_rot=0.3, seam_glow=0.18 + 0.25 * e, frost=0.35 + 0.8 * fr)
    c.restore()
    rings(c, 540, 1500, 420, 120, 5, T, a=0.10 + 0.20 * e, rgb=(190, 215, 255), speed=0.3)
    return dict(grain=12, vig=1.0, tint=(170, 195, 230, 0.35))


def sc_door_walk(c, T, lt, S):
    l1 = S["lines"][0]
    title_dur = l1["start"] - S["t0"] - 0.25
    if lt < title_dur:
        c.clear(col((0, 0, 0)))
        a_in = smooth(ramp(lt, 0.25, 0.6)); a_out = 1 - smooth(ramp(lt, title_dur - 0.35, title_dur - 0.05))
        a = a_in * a_out
        label(c, "СЕРИЯ  3", 540, 800, a, RED, 34, "Inter-Bold", 14)
        f = font(104, "InterDisplay-Black")
        for i, txt in enumerate(["МАМА ЗА", "ДВЕРЬЮ"]):
            w = f.measureText(txt)
            c.drawString(txt, 540 - w / 2, 940 + i * 118, f, paint(WHITE, 0.25 * a, blur=18))
            c.drawString(txt, 540 - w / 2, 940 + i * 118, f, paint(WHITE, a))
        c.drawLine(540 - 60 * a, 1200, 540 + 60 * a, 1200, paint(RED, a, stroke=4))
        g = 0.9 * (1 - lt / 0.6) if lt < 0.6 else (0.8 * ramp(lt, title_dur - 0.35, title_dur) if lt > title_dur - 0.35 else 0)
        return dict(glitch=g, grain=9, vig=0.6)
    dur = S["t1"] - S["t0"]
    q = ease_io(ramp(T, S["t0"] + title_dur, S["t1"]))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, lerp(1000, 900, q), lerp(0.85, 1.55, q))
    door(c, T, light=0.7 + 0.1 * q, wheel_rot=0.3, seam_glow=0.35, frost=1.3)
    c.restore()
    # torch beam bobbing: steps toward the door
    bob = math.sin(T * 6.5) * 14 * (1 - q * 0.4)
    beam(c, 840, 1980, -12 + bob * 0.2, 1500, 20, 0.35)
    return dict(grain=12, vig=1.0, tint=(180, 200, 230, 0.25))


def sc_oldman(c, T, lt, S):
    nxt = S["lines"][0]["id"]
    scared = 0.35 + 0.25 * ramp(T, S["t0"], S["t1"])
    def look(T):
        a = smooth(ramp(T, S["t0"], S["t0"] + 0.5))
        return (lerp(0.0, -1.0, a), 0.1)
    face_common(c, T, lt, S, "old", fear=scared, look=look, light_fn=lambda T: 0.85 + 0.06 * vnoise(T * 14, 9))
    return dict(grain=13, vig=1.0)


def sc_door_hand(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    q = ease_io(ramp(lt, 0.0, dur))
    press = smooth(ramp(T, L("l05")["start"], L("l05")["start"] + 0.9))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, lerp(540, 600, q), lerp(1000, 900, q), lerp(1.8, 2.35, q))
    fr = 0.5 + 1.4 * press
    door(c, T, light=0.7, wheel_rot=0.3, seam_glow=0.3, frost=fr)
    hx, hy = lerp(900, 620, ease_out(press)), lerp(1500, 1180, ease_out(press))
    hand(c, hx, hy, 1.6, 1.0, ang=-0.08)
    c.restore()
    return dict(grain=13, vig=1.0, tint=(170, 195, 230, 0.35))


def sc_lullaby(c, T, lt, S):
    l = S["lines"][0]
    e = VE.at("l07", T)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 900, 1.15)
    door(c, T, light=0.55, wheel_rot=0.3, seam_glow=0.45 + 0.4 * e, frost=0.9)
    c.restore()
    # warm light bleeding through the seam, breathing with the song
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 900, 700, [(0, (255, 160, 70), 0.12 + 0.25 * e), (1, (255, 120, 40), 0)]), blend="screen"))
    rings(c, 540, 900, 520, 520, 6, T, a=0.10 + 0.25 * e, rgb=(255, 200, 150), speed=0.28)
    return dict(grain=12, vig=1.0, bright=0.95 + 0.1 * e)


def sc_dima_face(c, T, lt, S):
    def look(T):
        return (0.2 * vnoise(T * 0.9, 3), 0.15 * vnoise(T, 4))
    fear = 0.4 + 0.5 * smooth(ramp(T, S["t0"], S["t1"]))
    c.clear(col((0, 0, 0)))
    m = 0.0
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1500, 1200, [(0, (40, 28, 18), 1), (1, (0, 0, 0), 1)])))
    for l in S["lines"]:
        m = max(m, VE.at(l["id"], T))
    z = 1.0 + 0.06 * lt
    blink = 0.0
    for bt in (0.8, 3.1, 5.2):
        if 0 <= lt - bt < 0.16:
            blink = math.sin((lt - bt) / 0.16 * math.pi)
    c.save(); cam(c, 540, 860, z)
    egg_face(c, T, 540, 860, 1.0, min(1, m), look=look(T), blink=blink, kind="victor", fear=fear,
             light=0.9, sweat=1.0)
    c.restore()
    return dict(grain=12, vig=1.0, ca=1 + 3 * fear)


def sc_door_reach(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    t_w = wt("l09", 5)  # колесу
    reach = smooth(ramp(T, S["t0"] + 0.1, t_w + 0.2))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 900, lerp(1.7, 2.0, reach))
    door(c, T, light=0.75, wheel_rot=0.3, seam_glow=0.4, frost=1.3)
    hand(c, lerp(900, 640, reach), lerp(1650, 1010, reach), 1.3, 1.0, ang=lerp(-0.3, -0.05, reach))
    c.restore()
    return dict(grain=13, vig=1.0, tint=(180, 200, 230, 0.3))


def sc_silence(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    c.clear(col((0, 0, 0)))
    f = ramp(lt, 0, dur)
    c.save(); cam(c, 540, 900, 1.2)
    door(c, T, light=0.18, wheel_rot=0.3, seam_glow=0.12 * (1 - f), frost=1.4)
    c.restore()
    # the cold breath along the bottom
    y = 1500
    c.drawRect(skia.Rect(-20, y - 3, W + 20, y + 3), paint((200, 225, 255), 0.5 * (1 - 0.7 * f), blur=3))
    return dict(grain=11, vig=1.0, tint=(160, 190, 230, 0.4))


def sc_behind(c, T, lt, S):
    ln = S["lines"]
    t_whisper = L("l14")["start"]
    c.clear(col((4, 4, 6)))
    jitter = fbm(T * 1.3, 2) * 3.0
    px_, py_ = 470 + jitter * 9, 820
    ox, oy = 860, 1640
    masked(c, lambda: c.drawImageRect(concrete(21, (78, 78, 80), 0.7), skia.Rect(-100, -100, W + 100, H + 100), SO, paint((255, 255, 255), 1)),
           radial(px_, py_, 640, [(0, (0, 0, 0), 1.0), (0.5, (0, 0, 0), 0.45), (1, (0, 0, 0), 0.0)]))
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(px_, py_, 520, [(0, BEAM, 0.30), (1, BEAM, 0.0)]), blend="screen"))
    ang = math.degrees(math.atan2(px_ - ox, -(py_ - oy)))
    beam(c, ox, oy, ang, 1000, 17, 0.45)
    # back of his head: the head freezes, then turns a few degrees toward the voice at his shoulder
    tw = L("l15")["words"][8]["t0"]  # "плечом"
    turn = -10 * smooth(ramp(T, t_whisper - 0.1, t_whisper + 0.6)) + 4 * smooth(ramp(T, tw, tw + 0.6))
    nb = math.sin(T * 2.4)
    body = skia.Path()
    body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-160, 1560 + nb * 4, W + 160, H + 400), 380, 380))
    c.drawPath(body, paint((0, 0, 0), 1))
    c.drawPath(body, paint((120, 110, 96), 0.4, stroke=6, blur=6))
    c.save(); c.translate(540 + turn, 1400 + nb * 3); c.rotate(turn * 0.35)
    c.drawRect(skia.Rect(-70, 40, 70, 200), paint((0, 0, 0), 1))
    c.drawOval(skia.Rect(-175, -215, 175, 215), paint((0, 0, 0), 1))
    c.drawArc(skia.Rect(-175, -215, 175, 215), 190, 160, False, paint((150, 138, 118), 0.55, stroke=7, blur=5))
    c.drawOval(skia.Rect(160, -40, 195, 40), paint((0, 0, 0), 1))
    c.restore()
    # THE THING: at his right shoulder, enormous, soft, eyes only
    a = smooth(ramp(T, t_whisper - 0.4, t_whisper + 0.3)) * (1 - smooth(ramp(T, S["t1"] - 0.6, S["t1"] - 0.1)) * 0.0)
    if a > 0:
        e = VE.at("l14", T)
        hx, hy = 880, 1250
        c.drawOval(skia.Rect(hx - 330, hy - 450, hx + 330, hy + 700), paint((6, 7, 9), 0.95 * a, blur=36))
        rings(c, 760, 1350, 520, 320, 5, T, a=0.18 * a * (0.4 + e), speed=0.4)
        glow_eyes(c, hx - 90, hy - 40, 26, a * (0.75 + 0.25 * e), open_=0.85 - 0.4 * e, gap=1.2)
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1000, 1150, [(0, (0, 0, 0), 0), (0.6, (0, 0, 0), 0.1), (1, (0, 0, 0), 0.5)])))
    return dict(grain=12, vig=0.9, ca=2 + 4 * a)


def sc_wheel(c, T, lt, S):
    t_d = wt("l18", 8, True) - 0.35          # "дрогнуло"
    t_s = L("l19")["start"]
    r = smooth(ramp(T, t_d, t_d + 0.25)) * 0.12 + ease_io(ramp(T, t_s + 0.1, t_s + 2.4)) * 1.55
    shk = 0.5 * math.exp(-max(0.0, T - t_d) * 5) * (1 if T >= t_d else 0)
    c.clear(col((0, 0, 0)))
    z = 1.5 + 0.1 * lt / max(1e-6, S["t1"] - S["t0"])
    c.save(); cam(c, 540, 900, z)
    door(c, T, light=0.78, shake=shk, wheel_rot=0.3 + r, seam_glow=0.3 + 0.3 * ramp(T, t_s, t_s + 2.0), frost=1.4)
    c.restore()
    return dict(grain=13, vig=1.0, ca=3 * shk * 4, tint=(180, 200, 230, 0.25))


def person_row(c, cx, base_y, h, n, a, spread, seed):
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * spread
        hh = h * (0.85 + 0.25 * hash01(seed, i))
        c.drawPath(person_path(x, base_y, hh, wide=0.9 + 0.2 * hash01(seed, i + 9)), paint((3, 3, 4), a))
        glow_eyes(c, x, base_y - hh * 0.86, 5 + hh * 0.01, a * 0.9)


def sc_open(c, T, lt, S):
    t_o = L("l20")["start"]
    t_t = L("l21")["start"]
    t_c = L("l22")["start"]
    k = ease_io(ramp(T, t_o, t_o + 2.2))
    c.clear(col((0, 0, 0)))
    # what is outside: the burning orange sky of episode 1
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=linear(0, 0, 0, H, [(0, (120, 30, 8), 1), (0.55, (255, 92, 26), 1), (1, (160, 40, 10), 1)])))
    c.drawRect(skia.Rect(0, 1330, W, H), paint((18, 8, 4), 1))
    # mother, far away, far too tall, standing exactly in the doorway
    ma = smooth(ramp(T, t_o + 0.8, t_o + 2.0))
    grow = ease_out(ramp(T, t_t, t_t + 2.5))
    h = lerp(420, 640, grow)
    mother(c, 540, 1360, h, paint((10, 4, 2), ma), 0.0, T, tall=lerp(1.0, 1.14, grow))
    ea = smooth(ramp(T, t_t - 0.2, t_t + 0.4))
    glow_eyes(c, 540, 1360 - h * lerp(1.0, 1.14, grow) + 0.068 * h, 6 + 8 * grow, ea * ma, open_=ea)
    # the others: a crowd of silhouettes appears behind her on "Считай заново"
    n = int(ramp(T, t_c + 0.1, t_c + 2.6) * 11)
    if n > 0:
        person_row(c, 540, 1345, 300, n, 0.95 * smooth(ramp(T, t_c, t_c + 0.4)), 92, 7)
    # the two door halves slide apart
    for side in (-1, 1):
        c.save()
        c.clipRect(skia.Rect(0 if side < 0 else W / 2, 0, W / 2 if side < 0 else W, H))
        c.translate(side * k * W * 0.55, 0)
        door(c, T, light=0.7, wheel_rot=0.3 + 1.55, seam_glow=0.0, frost=1.4)
        c.restore()
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 900, 900, [(0, (255, 160, 70), 0.30 * k), (1, (255, 120, 40), 0)]), blend="screen"))
    g = 0.9 if 0 <= T - t_o < 0.1 else (0.9 if 0 <= T - t_c < 0.1 else 0.0)
    return dict(grain=13, vig=0.9, glitch=g, bright=1.0 + 0.1 * k, ca=2)


def sc_endcard(c, T, lt, S):
    c.clear(col((0, 0, 0)))
    a = smooth(ramp(lt, 0.3, 0.8))
    rings(c, 540, 1180, 520, 150, 6, T, a=0.18 * a)
    label(c, "СЕРИЯ  4", 540, 800, a, RED, 34, "Inter-Bold", 14)
    f = font(92, "InterDisplay-Black")
    for i, txt in enumerate(["СЧИТАЙ", "ЗАНОВО"]):
        w = f.measureText(txt)
        c.drawString(txt, 540 - w / 2, 950 + i * 110, f, paint(WHITE, a))
    label(c, "продолжение следует", 540, 1290, smooth(ramp(lt, 1.4, 2.0)) * 0.7, (190, 190, 190), 30, "Inter-Medium", 4)
    g = 0.8 * (1 - ramp(lt, 0.3, 0.7)) if lt < 0.7 else 0
    return dict(grain=9, vig=0.8, glitch=g)


SCENES = dict(door_cold=sc_door_cold, door_walk=sc_door_walk, oldman=sc_oldman, door_hand=sc_door_hand,
              lullaby=sc_lullaby, dima_face=sc_dima_face, door_reach=sc_door_reach, silence=sc_silence,
              behind=sc_behind, wheel=sc_wheel, open=sc_open, endcard=sc_endcard)

SUB_Y = dict(door_cold=1660, door_walk=1660, oldman=1520, door_hand=1660, lullaby=1660, dima_face=1520,
             door_reach=1660, silence=1560, behind=1060, wheel=1660, open=1620)
MUFFLED = {"l00", "l07", "l13", "l21"}



# ============================================================== subtitles + HUD
def wrap(words, f, maxw):
    lines, cur, cw = [], [], 0
    sp = f.measureText(" ")
    for w in words:
        ww = f.measureText(w["w"])
        if cur and cw + sp + ww > maxw:
            lines.append(cur); cur, cw = [], 0
        cw = cw + (sp if cur else 0) + ww
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def subtitles(c, T, scene):
    for ln in TL.build()["lines"]:
        for card in ln["cards"]:
            if card["t0"] <= T < card["t1"]:
                draw_card(c, T, card, ln, scene)


def draw_card(c, T, card, ln, scene):
    muff = ln["id"] in MUFFLED
    fname = "InterDisplay-ExtraBoldItalic" if muff else "InterDisplay-ExtraBold"
    f = font(68, fname)
    sp = f.measureText(" ")
    rows = wrap(card["words"], f, 900)
    y0 = SUB_Y.get(scene, 1300) - (len(rows) - 1) * 84 / 2
    out = smooth(ramp(T, card["t1"] - 0.10, card["t1"]))
    for r, row in enumerate(rows):
        tw = sum(f.measureText(w["w"]) for w in row) + sp * (len(row) - 1)
        x = 540 - tw / 2
        y = y0 + r * 84
        for w in row:
            p = ease_out(ramp(T, w["t0"] - 0.05, w["t0"] + 0.10))
            a = p * (1 - out)
            if a <= 0.01:
                x += f.measureText(w["w"]) + sp
                continue
            base = {"w": (255, 255, 255) if not muff else (214, 220, 232), "r": RED, "y": YEL}[w["c"]]
            ww = f.measureText(w["w"])
            dy = (1 - p) * 14
            sc = 1 + (0.18 if w["c"] != "w" else 0.06) * (1 - p)
            c.save()
            c.translate(x + ww / 2, y + dy - 22); c.scale(sc, sc); c.translate(-(x + ww / 2), -(y + dy - 22))
            c.drawString(w["w"], x + 2, y + dy + 5, f, paint((0, 0, 0), 0.85 * a, blur=9))
            st = paint((0, 0, 0), 0.7 * a, stroke=7); st.setStrokeJoin(skia.Paint.kRound_Join)
            c.drawString(w["w"], x, y + dy, f, st)
            if w["c"] != "w":
                c.drawString(w["w"], x, y + dy, f, paint(base, 0.45 * a, blur=14))
            c.drawString(w["w"], x, y + dy, f, paint(base, a))
            c.restore()
            x += ww + sp


def hud(c, T, total):
    f = font(26, "Inter-Bold")
    c.drawCircle(44, 62, 7, paint(RED, 0.95))
    c.drawString("СЕРИЯ 3 · БУНКЕР", 62, 71, f, paint((255, 255, 255), 0.85))
    c.drawRect(skia.Rect(0, H - 8, W, H), paint((40, 40, 40), 0.6))
    c.drawRect(skia.Rect(0, H - 8, W * T / total, H), paint(RED, 0.95))


# ============================================================== frame pipeline
_post = None
_surface = None


def frame(i):
    global _post, _surface
    if _post is None:
        _post = Post(1)
        _surface = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    T = i / FPS
    tl = TL.build()
    S = TL.scene_at(T)
    c = _surface.getCanvas()
    c.save()
    fx = SCENES[S["name"]](c, T, T - S["t0"], S) or {}
    c.restore()
    c.resetMatrix()
    arr = _surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    arr = _post.apply(arr, T, fx)
    # crisp overlays after grain
    img = skia.Image.fromarray(np.dstack([arr, np.full((H, W), 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    c.drawImage(img, 0, 0)
    subtitles(c, T, S["name"])
    if S["name"] != "endcard" or True:
        hud(c, T, tl["total"])
    out = _surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return out[:, :, :3].tobytes()


def main():
    args = sys.argv[1:]
    tl = TL.build()
    if "--preview" in args:
        times = [float(x) for x in args[args.index("--preview") + 1].split(",")]
        os.makedirs(os.path.join(ROOT, "build", "preview"), exist_ok=True)
        from PIL import Image
        for t in times:
            b = frame(int(round(t * FPS)))
            Image.frombytes("RGB", (W, H), b).save(os.path.join(ROOT, "build", "preview", f"p_{t:07.2f}.png"))
        return
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(ROOT, "build", "video.mp4")
    t_from = float(args[args.index("--from") + 1]) if "--from" in args else 0.0
    t_to = float(args[args.index("--to") + 1]) if "--to" in args else tl["total"]
    frames = range(int(t_from * FPS), int(t_to * FPS))
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-tune", "grain", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, b in enumerate(pool.imap(frame, frames, chunksize=6)):
            ff.stdin.write(b)
            if k % 150 == 0:
                print(f"frame {k}/{len(frames)}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done", out)


if __name__ == "__main__":
    main()
