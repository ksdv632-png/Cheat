"""Episode 4 renderer.  python3 render.py [--preview t1,t2,...] [--out file.mp4] [--from T --to T]"""
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
    body = paint((4, 4, 5), a)
    rimp = paint(BEAM, rim * a, stroke=3, blur=2.5)
    # forearm + wrist, slightly tapered
    fa = skia.Path(); fa.moveTo(-44, 170); fa.lineTo(-40, 10); fa.quadTo(0, -6, 40, 10); fa.lineTo(48, 170); fa.close()
    c.drawPath(fa, body)
    # palm: wider at the knuckles
    pm = skia.Path(); pm.moveTo(-42, 12); pm.quadTo(-66, -60, -58, -128); pm.quadTo(0, -146, 58, -126)
    pm.quadTo(64, -60, 42, 12); pm.close()
    c.drawPath(pm, body)
    # fingers: tapered, slightly spread, three segments of rounding
    for (bx, ln, rot, w) in [(-44, 104, -9, 25), (-15, 132, -3, 27), (15, 140, 2, 27), (44, 118, 8, 25)]:
        c.save(); c.translate(bx, -120); c.rotate(rot)
        fp = skia.Path(); fp.moveTo(-w / 2, 10); fp.lineTo(-w * 0.42, -ln + w * 0.4)
        fp.quadTo(0, -ln - w * 0.25, w * 0.42, -ln + w * 0.4); fp.lineTo(w / 2, 10); fp.close()
        c.drawPath(fp, body)
        c.drawLine(-w * 0.45, -ln * 0.2, -w * 0.4, -ln * 0.85, rimp)
        c.restore()
    # thumb, angled out
    c.save(); c.translate(-50, -40); c.rotate(-48)
    tp = skia.Path(); tp.moveTo(-15, 20); tp.lineTo(-13, -70); tp.quadTo(0, -88, 13, -70); tp.lineTo(17, 20); tp.close()
    c.drawPath(tp, body); c.restore()
    c.drawPath(pm, rimp)
    c.restore()


def door_light(T, base=0.8, seed=3):
    return base + 0.04 * vnoise(T * 13, seed)


# ============================================================== episode 4 scenes («Считай заново»)
FLOOR = 1300
REAL_X = [190, 365, 540, 715, 890]          # the five people, lit, in front
THEM_X = [95 + i * 89 for i in range(11)]    # eleven of «them», against the wall


def shadow_x(x):
    return 540 + (x - 540) * 1.25


def wall_bg(c, T, light=1.0, beam_x=540):
    c.drawImageRect(concrete(3, (52, 56, 62), 0.5), skia.Rect(-200, -200, W + 200, FLOOR + 60), SO, paint((255, 255, 255), 1))
    flick = 1.0 + 0.03 * vnoise(T * 9, 5)
    c.drawRect(skia.Rect(-200, -200, W + 200, FLOOR + 60),
               paint(shader=radial(beam_x, 820, 900, [(0, BEAM, 0.5 * light * flick), (0.45, BEAM, 0.2 * light * flick), (1, BEAM, 0)]), blend="screen"))
    c.drawRect(skia.Rect(-200, -200, W + 200, FLOOR + 60),
               paint(shader=radial(beam_x, 820, 1100, [(0, (0, 0, 0), 0), (0.7, (0, 0, 0), 0.55), (1, (0, 0, 0), 0.9)])))
    c.drawRect(skia.Rect(-200, 0, W + 200, H + 200), paint((0, 0, 0), 1 - light))
    c.drawRect(skia.Rect(-200, FLOOR, W + 200, H + 200),
               paint(shader=linear(0, FLOOR, 0, H, [(0, (22, 22, 24), light), (0.4, (10, 10, 11), light), (1, (4, 4, 5), 1)])))


def crowd(c, T, n_them=11, light=1.0, beam_x=540, real_shadows=True, them_eyes=0.6, turn=0.0, shadow_eyes=0.0,
          labels=0, them_a=1.0):
    """five lit people in front (with shadows on the wall) and up to eleven of «them» against the wall (no shadows)."""
    wall_bg(c, T, light, beam_x)
    # shadows of the real ones on the wall; on `turn` their heads twist toward the camera and the eyes light up
    if real_shadows:
        for i, x in enumerate(REAL_X):
            sx = shadow_x(x)
            p = person_path(sx, FLOOR - 20, 800, head_dx=-26 * turn * (1 if x > 540 else -1))
            c.drawPath(p, paint((8, 8, 10), 0.8 * light, blur=7))
            if shadow_eyes > 0:
                glow_eyes(c, sx - 26 * turn * (1 if x > 540 else -1), FLOOR - 20 - 800 * 0.86, 11, shadow_eyes)
            if labels:
                k = min(5, labels)
                a = smooth(clamp(labels - i))
                if a > 0:
                    label(c, str(i + 1), sx, FLOOR - 20 - 800 * 1.03, a, YEL, 60, "InterDisplay-Black", 0)
    # them: against the wall, tall, no shadow, red eyes
    for j in range(n_them):
        x = THEM_X[j]
        h = 400 + 50 * hash01(j, 7)
        sway = 3 * vnoise(T * 0.6, j)
        c.drawPath(person_path(x + sway, FLOOR - 10, h, wide=0.8), paint((2, 2, 3), them_a))
        blink = 1.0 if (T * 0.7 + hash01(j, 3) * 7) % 5 > 0.15 else 0.1
        glow_eyes(c, x + sway, FLOOR - 10 - h * 0.86, 6, them_eyes * them_a * (0.7 + 0.3 * vnoise(T * 2, j)), open_=blink)
    # the five, lit from the torch (in front, lower, bigger)
    for i, x in enumerate(REAL_X):
        p = person_path(x, FLOOR + 230, 380)
        c.drawPath(p, paint(BEAM, 0.2 * light, blur=10))
        c.drawPath(p, paint((5, 5, 6), 1))
    for x in REAL_X:
        c.drawOval(skia.Rect(x - 80, FLOOR + 222, x + 80, FLOOR + 244), paint((0, 0, 0), 0.8, blur=8))


def sc_hook(c, T, lt, S):
    l = S["lines"][0]
    t16 = wt("l00", 5)  # «шестнадцать»
    n = int(round(11 * ease_out(ramp(T, wt("l00", 3), t16 + 0.3))))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 1050, 1.12 - 0.06 * ease_io(lt / (S["t1"] - S["t0"])))
    crowd(c, T, n_them=n, light=0.85, beam_x=540 + 200 * math.sin(lt * 1.3))
    c.restore()
    cnt = 5 + n
    label(c, "НАС", 540, 300, 0.9, WHITE, 34, "Inter-Bold", 12)
    pop = 1 + 0.12 * (1 - smooth(ramp(T, t16, t16 + 0.25))) * (1 if T > t16 else 0)
    big_number(c, str(cnt), 540, 520, 240 * pop, RED if cnt > 5 else YEL, 1.0, glow=0.9)
    a = (1 - smooth(ramp(lt, 3.2, 3.8)))
    label(c, "СЕРИЯ 4 · СЧИТАЙ ЗАНОВО", 540, 180, 0.85 * a, (220, 220, 220), 28, "Inter-Bold", 6)
    g = 0.8 if lt < 0.12 else (0.6 if 0 <= T - t16 < 0.1 else 0)
    return dict(grain=12, vig=0.95, glitch=g)


def sc_wall(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    q = ease_io(lt / dur)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, lerp(300, 780, q), 1000, 1.45)
    crowd(c, T, light=0.8, beam_x=lerp(250, 830, q), them_eyes=0.8)
    c.restore()
    return dict(grain=12, vig=1.0)


def sc_oldman(c, T, lt, S):
    first = S["lines"][0]["id"]
    beat = 0 if first == "l02" else 2
    scared = [0.5, 0.95][beat // 2] + 0.2 * ramp(T, S["t0"], S["t1"])
    def look(T):
        a = smooth(ramp(T, S["t0"], S["t0"] + 0.5))
        if beat == 2:
            return (lerp(-0.2, 0.9, a), lerp(0.1, 0.25, a))
        return (lerp(0.0, -1.0, a), 0.1)
    z, cx, cy = [(1.2, 540, 840), None, (1.15, 600, 880)][beat]
    c.save(); c.translate(cx, cy); c.scale(z, z); c.translate(-540, -860)
    light = (lambda T: 0.85 + 0.06 * vnoise(T * 14, 9)) if beat == 0 else (lambda T: 0.55 + 0.25 * (vnoise(T * 9, 2) > -0.4))
    face_common(c, T, lt, S, "old", fear=scared, look=look, light_fn=light)
    c.restore()
    if beat == 2:
        c.drawRect(skia.Rect(0, 0, W, H), paint(shader=linear(0, H, 0, 0, [(0, BEAM, 0.18), (0.5, BEAM, 0.0)]), blend="screen"))
        return dict(grain=13, vig=1.0, ca=2, tint=(170, 190, 220, 0.35))
    return dict(grain=13, vig=1.0, ca=1)


def sc_shadows(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    # labels count up on «Одна..Пять»
    labels = 0.0
    for k in range(5):
        tk = wt("l04", 2 + k)
        labels += smooth(ramp(T, tk - 0.05, tk + 0.2))
    t_net = wt("l03", 7)  # «нет»
    c.clear(col((0, 0, 0)))
    z = lerp(1.05, 1.25, ease_io(lt / dur))
    c.save(); cam(c, 540, 860, z)
    crowd(c, T, light=0.85, beam_x=540 + 120 * math.sin(lt * 0.5), them_eyes=0.5 + 0.4 * smooth(ramp(T, t_net, t_net + 0.4)),
          labels=labels)
    # red «no shadow» marks over them after «нет»
    a = smooth(ramp(T, t_net, t_net + 0.5)) * (1 - smooth(ramp(T, wt("l04", 0), wt("l04", 0) + 0.6)))
    for j, x in enumerate(THEM_X):
        if a > 0.01:
            c.drawLine(x - 26, FLOOR + 30, x + 26, FLOOR + 30, paint(RED, a, stroke=5))
    c.restore()
    t5 = wt("l05", 4)  # «пятеро»
    if T > wt("l05", 0) - 0.1:
        a = smooth(ramp(T, wt("l05", 0), wt("l05", 0) + 0.3))
        big_number(c, "5", 400, 420, 200, YEL, a)
        label(c, "/", 540, 390, a, (150, 150, 150), 80, "InterDisplay-Light", 0)
        big_number(c, "5", 680, 420, 200, YEL, smooth(ramp(T, t5 - 0.1, t5 + 0.2)))
    return dict(grain=12, vig=0.95)


def sc_mom(c, T, lt, S):
    l = S["lines"][0]
    e = VE.at("l06", T)
    lean = ease_io(ramp(lt, 0.0, S["t1"] - S["t0"]))
    c.clear(col((0, 0, 0)))
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=linear(0, 0, 0, H, [(0, (120, 30, 8), 1), (0.55, (255, 92, 26), 1), (1, (160, 40, 10), 1)])))
    # door frame edges (dark) — we look through the open door
    c.drawRect(skia.Rect(0, 0, 150, H), paint((10, 10, 12), 1)); c.drawRect(skia.Rect(W - 150, 0, W, H), paint((10, 10, 12), 1))
    c.drawRect(skia.Rect(0, 1500, W, H), paint((14, 7, 4), 1))
    h = lerp(1300, 1700, lean)
    mother(c, 540, 1560 + 0.2 * h, h, paint((10, 4, 2), 1), 0.0, T, tall=1.1)
    hy = 1560 + 0.2 * h - h * 1.1 + 0.068 * h
    glow_eyes(c, 540, hy, 10 + 6 * lean, 0.8 + 0.2 * e, open_=0.7 + 0.3 * e)
    rings(c, 540, hy, 300, 300, 4, T, a=0.15 + 0.3 * e, rgb=(255, 200, 160), speed=0.35)
    return dict(grain=13, vig=1.0, ca=2)


def feet_pair(c, x, y, s, shadow=True, light_x=540, light_y=2400, a_sh=0.7):
    if shadow:
        ang = math.atan2(y - light_y, x - light_x)
        L_ = 520 * s
        sh = skia.Path()
        sh.moveTo(x - 50 * s, y); sh.lineTo(x + 50 * s, y)
        sh.lineTo(x + math.cos(ang) * L_ + 70 * s, y + math.sin(ang) * L_)
        sh.lineTo(x + math.cos(ang) * L_ - 70 * s, y + math.sin(ang) * L_); sh.close()
        c.drawPath(sh, paint((0, 0, 0), a_sh, blur=14))
    for dx in (-30, 30):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x + dx * s - 24 * s, y - 70 * s, x + dx * s + 24 * s, y + 10 * s), 20 * s, 20 * s), paint((6, 6, 7), 1))
        c.drawArc(skia.Rect(x + dx * s - 24 * s, y - 70 * s, x + dx * s + 24 * s, y + 10 * s), 190, 160, False, paint(BEAM, 0.35, stroke=3, blur=2))


def sc_feet(c, T, lt, S):
    t_look = wt("l07", 1)
    t_no = wt("l08", 2)  # «не»
    tilt = ease_io(ramp(T, t_look - 0.2, t_look + 0.9))
    c.clear(col((0, 0, 0)))
    # floor seen from above, torch light from below-centre
    c.drawImageRect(concrete(7, (40, 40, 44), 0.6), skia.Rect(-100, -100, W + 100, H + 100), SO, paint((255, 255, 255), 0.55))
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1500, 1100, [(0, BEAM, 0.35), (1, BEAM, 0.0)]), blend="screen"))
    c.save(); cam(c, 540, lerp(960, 1080, tilt), lerp(0.95, 1.08, tilt))
    for x, y in [(200, 820), (420, 700), (660, 700), (880, 820)]:
        feet_pair(c, x, y, 0.9)
    me_a = smooth(ramp(T, t_no, t_no + 0.2))
    feet_pair(c, 540, 1450, 1.4, shadow=False)
    # where his shadow should be: an empty, too-bright patch
    c.drawOval(skia.Rect(400, 1480, 680, 1820), paint(BEAM, 0.12 + 0.12 * me_a, blur=40))
    c.restore()
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 960, 1150, [(0, (0, 0, 0), 0), (0.7, (0, 0, 0), 0.4), (1, (0, 0, 0), 0.9)])))
    fx = dict(grain=13, vig=1.0)
    if T > t_no:
        fx["tint"] = (230, 120, 110, 0.35 * me_a)
        fx["glitch"] = 0.7 if T - t_no < 0.1 else 0
    return fx


def sc_ear(c, T, lt, S):
    l = S["lines"][0]
    e = VE.at("l10", T)
    c.clear(col((0, 0, 0)))
    appear = smooth(ramp(lt, 0.2, 1.0))
    hx, hy = 880, 900
    c.drawOval(skia.Rect(hx - 380, hy - 520, hx + 380, hy + 900), paint((8, 9, 12), appear, blur=40))
    rings(c, 700, 950, 600, 420, 6, T, a=0.22 * appear * (0.4 + e), speed=0.4)
    glow_eyes(c, hx - 60, hy, 34, appear * (0.7 + 0.3 * e), open_=0.8 - 0.4 * e, gap=1.25)
    # the back of Dima's head at left, frozen
    c.drawOval(skia.Rect(-220, 1050, 300, 1700), paint((0, 0, 0), 1))
    c.drawArc(skia.Rect(-220, 1050, 300, 1700), 270, 90, False, paint((120, 110, 96), 0.4, stroke=6, blur=5))
    return dict(grain=14, vig=1.0, ca=2 + 4 * e)


def sc_turn(c, T, lt, S):
    t_pov = wt("l11", 4)  # «повернулись»
    q = ease_io(ramp(T, t_pov - 0.2, t_pov + 0.9))
    eyes = smooth(ramp(T, t_pov + 0.3, t_pov + 1.2))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 820, lerp(1.0, 1.3, ease_io(lt / (S["t1"] - S["t0"]))))
    crowd(c, T, light=lerp(0.85, 0.6, q), turn=q, shadow_eyes=eyes, them_eyes=0.9)
    c.restore()
    return dict(grain=13, vig=1.0, glitch=0.6 if 0 <= T - (t_pov + 0.3) < 0.1 else 0, ca=2 * eyes)


def sc_endcard(c, T, lt, S):
    c.clear(col((0, 0, 0)))
    a = smooth(ramp(lt, 0.15, 0.5))
    rings(c, 540, 1180, 520, 150, 6, T, a=0.18 * a)
    label(c, "СЕРИЯ  5", 540, 800, a, RED, 34, "Inter-Bold", 14)
    f = font(92, "InterDisplay-Black")
    for i, txt in enumerate(["ГДЕ МОЯ", "ТЕНЬ?"]):
        w = f.measureText(txt)
        c.drawString(txt, 540 - w / 2, 950 + i * 110, f, paint(WHITE, a))
    label(c, "завтра в 10:00", 540, 1290, smooth(ramp(lt, 0.8, 1.3)) * 0.75, (190, 190, 190), 30, "Inter-Medium", 4)
    g = 0.8 * (1 - ramp(lt, 0.15, 0.5)) if lt < 0.5 else 0
    return dict(grain=9, vig=0.8, glitch=g)


SCENES = dict(hook=sc_hook, wall=sc_wall, oldman=sc_oldman, shadows=sc_shadows, mom=sc_mom, feet=sc_feet,
              ear=sc_ear, turn=sc_turn, endcard=sc_endcard)

SUB_Y = dict(hook=1700, wall=1700, oldman=1520, shadows=1700, mom=1700, feet=1780, ear=1520, turn=1700)
MUFFLED = {"l06"}




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
    c.drawString("СЕРИЯ 4 · БУНКЕР", 62, 71, f, paint((255, 255, 255), 0.85))
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
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-b:v", "6500k", "-maxrate", "9000k", "-bufsize", "18000k",
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
