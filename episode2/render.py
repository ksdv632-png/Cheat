"""Episode 2 renderer.  python3 render.py [--preview t1,t2,...] [--out file.mp4] [--from T --to T]"""
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


def shake_events():
    """(time, strength, decay) camera impulses"""
    ev = []
    l14 = L("l14")
    k0 = wt("l14", 4, True) + 0.12
    for i in range(3):
        ev.append((k0 + i * 0.42, 1.0, 7.0))
    ev.append((wt("l10", 2), 0.8, 5.0))          # "не я!"
    ev.append((wt("l10", 6), 0.6, 5.0))          # "впускал!"
    ev.append((L("l19")["end"] - 0.05, 1.0, 4.0))  # turn smash-cut
    return ev


_EV = None


def shake(T):
    global _EV
    if _EV is None:
        _EV = shake_events()
    a = 0.0
    for t0, s, d in _EV:
        if T >= t0:
            a += s * math.exp(-(T - t0) * d)
    return a


def knock_times():
    k0 = wt("l14", 4, True) + 0.12
    return [k0, k0 + 0.42, k0 + 0.84]


# ============================================================== wall (people + shadows) world
PX = [150, 306, 462, 618, 774, 930]
VICTOR = 3
FEET = 1250
PH = 330
WALL_BASE = 1150


def shadow_x(x):
    return 540 + (x - 540) * 1.22


def wall_world(c, T, *, light=1.0, people=None, sh=None, thing=True, raise_p=None, raise_thing=0.0,
               thing_dx=0.0, thing_head=0.0, thing_a=1.0, labels=None, beam_x=540, red_thing=0.0,
               victor_pos=None, victor_gone=False, shadows_follow=None):
    """people: list of indices present. raise_p: arm raise per person (shadows copy their owner)."""
    people = list(range(6)) if people is None else people
    raise_p = raise_p or [0.0] * 6
    # wall
    c.drawImageRect(concrete(3, (52, 56, 62), 0.5), skia.Rect(-200, -200, W + 200, WALL_BASE + 60), SO, paint((255, 255, 255), 1))
    # flashlight pool on the wall (warm), slightly breathing
    flick = 1.0 + 0.03 * vnoise(T * 9, 5)
    pool = radial(beam_x, 820, 900, [(0, BEAM, 0.55 * light * flick), (0.45, BEAM, 0.22 * light * flick), (1, BEAM, 0.0)])
    c.drawRect(skia.Rect(-200, -200, W + 200, WALL_BASE + 60), paint(shader=pool, blend="screen"))
    # darken away from light
    c.drawRect(skia.Rect(-200, -200, W + 200, WALL_BASE + 60),
               paint(shader=radial(beam_x, 820, 1100, [(0, (0, 0, 0), 0.0), (0.7, (0, 0, 0), 0.55), (1, (0, 0, 0), 0.9)])))
    c.drawRect(skia.Rect(-200, 0, W + 200, H + 200), paint((0, 0, 0), 1 - light))
    # floor
    c.drawRect(skia.Rect(-200, WALL_BASE, W + 200, H + 200),
               paint(shader=linear(0, WALL_BASE, 0, H, [(0, (22, 22, 24), light), (0.4, (10, 10, 11), light), (1, (4, 4, 5), 1)])))
    c.drawRect(skia.Rect(-200, WALL_BASE - 3, W + 200, WALL_BASE + 3), paint((0, 0, 0), 0.6, blur=3))
    # shadows
    shp = paint((8, 8, 10), 0.80 * light, blur=7)
    for i in range(6):
        if sh is not None and i not in sh:
            continue
        x = PX[i]
        sx = shadow_x(x)
        if shadows_follow is not None and i in shadows_follow:
            sx = lerp(sx, shadows_follow[i][0], shadows_follow[i][1])
        p = person_path(sx, WALL_BASE + 10, PH * 1.38, wide=1.12 if i == VICTOR else 1.0)
        c.drawPath(p, shp)
        arm(c, sx, WALL_BASE + 10, PH * 1.38, raise_p[i], p=shp)
    if thing and thing_a > 0:
        tx = shadow_x(PX[VICTOR]) + 96 + thing_dx
        tp = paint((3, 3, 4), 0.92 * light * thing_a, blur=4)
        c.drawPath(person_path(tx, WALL_BASE + 10, PH * 1.47, head_stretch=1.14, neck=0.8, head_dx=thing_head), tp)
        arm(c, tx, WALL_BASE + 10, PH * 1.47, raise_thing, p=tp)
        if red_thing > 0:
            glow_eyes(c, tx + thing_head, WALL_BASE + 10 - PH * 1.47 * 0.85, 13, red_thing)
    # people (black, slight warm rim from the flashlight)
    for i in people:
        x, yb, s = PX[i], FEET, 1.0
        if i == VICTOR and victor_pos is not None:
            x, yb, s = victor_pos
        if i == VICTOR and victor_gone:
            continue
        p = person_path(x, yb, PH * s, wide=1.12 if i == VICTOR else 1.0)
        c.drawPath(p, paint(BEAM, (0.18 + (0.25 if (i == VICTOR and victor_pos) else 0)) * light, blur=10))
        c.drawPath(p, paint((5, 5, 6), 1))
        arm(c, x, yb, PH * s, raise_p[i], p=paint((5, 5, 6), 1))
        if i == VICTOR:  # jacket collar notch, visible as a sliver of rim light
            c.drawLine(x - 30 * s, yb - PH * s * 0.61, x, yb - PH * s * 0.55, paint(BEAM, 0.25 * light, stroke=3))
            c.drawLine(x + 30 * s, yb - PH * s * 0.61, x, yb - PH * s * 0.55, paint(BEAM, 0.25 * light, stroke=3))
    # floor contact shadows
    for i in people:
        if i == VICTOR and victor_gone:
            continue
        x = PX[i] if not (i == VICTOR and victor_pos) else victor_pos[0]
        yb = FEET if not (i == VICTOR and victor_pos) else victor_pos[1]
        c.drawOval(skia.Rect(x - 80, yb - 8, x + 80, yb + 14), paint((0, 0, 0), 0.8, blur=8))


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


# ============================================================== scenes
def sc_cold(c, T, lt, S):
    l0 = S["lines"][0]
    c.clear(col((9, 11, 16)))
    z = 1.0 + 0.06 * lt / S["t1"]
    c.save(); cam(c, 540, 1100, z)
    # the figure from the end of episode 1
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 900, 900, [(0, (30, 36, 48), 1), (1, (6, 7, 10), 1)])))
    rings(c, 540, 1400, 520, 150, 7, T, a=0.35)
    fig = person_path(540, 1700, 1000, wide=0.85, head_stretch=1.1)
    c.drawPath(fig, paint((22, 26, 34), 0.9, blur=24))
    c.drawPath(fig, paint((40, 46, 60), 0.25, blur=60))
    ea = smooth(ramp(T, 0.6, 1.4)) * (1 - smooth(ramp(T, l0["end"] + 0.15, l0["end"] + 0.5)))
    e = VE.at("l00", T)
    glow_eyes(c, 540, 1700 - 1000 * 0.86, 15, ea * (0.75 + 0.25 * e), open_=1 - 0.4 * e)
    c.restore()
    return dict(grain=12, vig=0.9)


def title_card(c, T, lt, dur):
    c.clear(col((0, 0, 0)))
    a_in = smooth(ramp(lt, 0.25, 0.6)); a_out = 1 - smooth(ramp(lt, dur - 0.35, dur - 0.05))
    a = a_in * a_out
    label(c, "СЕРИЯ  2", 540, 860, a, RED, 34, "Inter-Bold", 14)
    f = font(118, "InterDisplay-Black")
    txt = "ВПУСТИВШИЙ"
    w = f.measureText(txt)
    c.drawString(txt, 540 - w / 2, 1000, f, paint(WHITE, 0.25 * a, blur=18))
    c.drawString(txt, 540 - w / 2, 1000, f, paint(WHITE, a))
    c.drawLine(540 - 60 * a, 1060, 540 + 60 * a, 1060, paint(RED, a, stroke=4))
    g = 0.0
    if lt < 0.6: g = 0.9 * (1 - lt / 0.6)
    if lt > dur - 0.35: g = 0.8 * ramp(lt, dur - 0.35, dur)
    if 1.2 < lt < 1.27: g = 0.7
    return dict(glitch=g, grain=9, vig=0.6)


def sc_back(c, T, lt, S):
    l1, l2 = S["lines"]
    title_dur = l1["start"] - S["t0"] - 0.25
    if lt < title_dur:
        return title_card(c, T, lt, title_dur)
    c.clear(col((4, 4, 6)))
    # corridor ahead: a soft pool of torch light on the far wall, the beam trembles with his hand
    jitter = fbm(T * 1.3, 2) * (1.5 + 4.5 * ramp(T, l2["start"], l2["end"]))
    jy = fbm(T * 1.1, 5) * (1.0 + 3.0 * ramp(T, l2["start"], l2["end"]))
    px_, py_ = 470 + jitter * 9, 820 + jy * 9
    ox, oy = 860, 1640
    masked(c, lambda: c.drawImageRect(concrete(21, (78, 78, 80), 0.7), skia.Rect(-100, -100, W + 100, H + 100), SO, paint((255, 255, 255), 1)),
           radial(px_, py_, 640, [(0, (0, 0, 0), 1.0), (0.5, (0, 0, 0), 0.45), (1, (0, 0, 0), 0.0)]))
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(px_, py_, 520, [(0, BEAM, 0.30), (1, BEAM, 0.0)]), blend="screen"))
    ang = math.degrees(math.atan2(px_ - ox, -(py_ - oy)))
    beam(c, ox, oy, ang, 1000, 17, 0.45)
    # dust motes inside the beam
    for k in range(26):
        u = hash01(k, 1); v = (hash01(k, 2) + T * 0.02 * (0.5 + hash01(k, 3))) % 1.0
        bx_ = lerp(ox, px_, v) + (u - 0.5) * 360 * v
        by_ = lerp(oy, py_, v) + 30 * math.sin(T * 0.7 + k)
        c.drawCircle(bx_, by_, 1.5 + 2 * hash01(k, 4), paint(BEAM, 0.25 * math.sin(v * math.pi), blur=1))
    # narrator from behind: shoulders + back of head. Head almost turns on "обернулся", then stops.
    turn = 0.0
    tw = wt("l01", 2)  # "обернулся"
    turn = 14 * smooth(ramp(T, tw - 0.3, tw + 0.15)) - 14 * smooth(ramp(T, tw + 0.35, tw + 1.2))
    breath_cycle = 2.6 if T < l2["start"] else lerp(2.6, 3.6, ramp(T, l2["start"], l2["end"]))
    bphase = (T / breath_cycle) % 1.0
    nb = math.sin(bphase * 2 * math.pi)
    body = skia.Path()
    body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-160, 1560 + nb * 4, W + 160, H + 400), 380, 380))
    c.drawPath(body, paint((0, 0, 0), 1))
    c.drawPath(body, paint((120, 110, 96), 0.4, stroke=6, blur=6))
    c.save(); c.translate(540 + turn, 1400 + nb * 3); c.rotate(turn * 0.35)
    c.drawRect(skia.Rect(-70, 40, 70, 200), paint((0, 0, 0), 1))
    c.drawOval(skia.Rect(-175, -215, 175, 215), paint((0, 0, 0), 1))
    c.drawArc(skia.Rect(-175, -215, 175, 215), 190, 160, False, paint((150, 138, 118), 0.55, stroke=7, blur=5))
    # ear, catching the light
    c.drawOval(skia.Rect(160, -40, 195, 40), paint((0, 0, 0), 1))
    c.drawArc(skia.Rect(160, -40, 195, 40), 250, 120, False, paint((110, 100, 90), 0.5, stroke=3))
    c.restore()
    # breath of something right behind him (at the camera): mist puffs drifting to his neck
    bstr = smooth(ramp(T, l1["end"] - 0.2, l2["start"] + 0.8))
    for k in range(3):
        ph = (bphase + k * 0.12) % 1.0
        if ph < 0.55:
            q = ph / 0.55
            x = lerp(80, 470, q); y = lerp(1900, 1450, q)
            r = lerp(60, 160, q)
            c.drawOval(skia.Rect(x - r, y - r * 0.6, x + r, y + r * 0.6), paint((200, 205, 215), 0.10 * bstr * math.sin(q * math.pi), blur=40))
    breath_vig = 0.15 * bstr * (0.5 + 0.5 * nb)
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1000, 1150, [(0, (0, 0, 0), 0), (0.6, (0, 0, 0), breath_vig), (1, (0, 0, 0), 0.4 + breath_vig * 2)])))
    return dict(grain=11, vig=0.85)


def sc_wall_line(c, T, lt, S):
    l = S["lines"][0]
    c.clear(col((0, 0, 0)))
    # people step back to the wall one by one (staggered), beam sweeps
    bx = 540 + 260 * math.sin(lt * 0.9 - 1.0)
    c.save()
    shake_amt = 0.0
    cam(c, 540, 1000, 1.08 - 0.06 * smooth(lt / S["t1"] if S["t1"] else 0))
    c.restore()
    c.save(); cam(c, 540, 1000, 1.08 - 0.08 * smooth(lt / (S["t1"] - S["t0"])))
    k_start = wt("l03", 2)  # "Все"
    pos = []
    for i in range(6):
        q = ease_out(ramp(T, k_start + i * 0.22 - 0.4, k_start + i * 0.22 + 0.7))
        pos.append(q)
    # draw world with people positions interpolated toward the wall
    wall_world_moving(c, T, pos, beam_x=bx)
    c.restore()
    return dict(grain=11, vig=0.9)


def wall_world_moving(c, T, pos, beam_x=540):
    """people walk backwards from the camera to the wall (pos 0 -> 1)."""
    # reuse wall_world without people/shadows, then draw people manually
    wall_world(c, T, people=[], sh=[], thing=False, beam_x=beam_x)
    order = sorted(range(6), key=lambda i: pos[i])  # far ones first
    shp = paint((8, 8, 10), 0.8, blur=7)
    for i in range(6):
        q = pos[i]
        x0 = 540 + (PX[i] - 540) * 1.7
        x = lerp(x0, PX[i], q)
        s = lerp(1.9, 1.0, q)
        sx = shadow_x(x)
        hs = PH * lerp(3.2, 1.38, q)
        c.drawPath(person_path(sx, WALL_BASE + 10, hs, wide=1.12 if i == VICTOR else 1.0), paint((8, 8, 10), 0.8 * q ** 0.5, blur=lerp(30, 7, q)))
    for i in order[::-1][::-1]:
        q = pos[i]
        x0 = 540 + (PX[i] - 540) * 1.7
        x = lerp(x0, PX[i], q)
        s = lerp(1.9, 1.0, q)
        yb = lerp(2250, FEET, q)
        p = person_path(x, yb, PH * s, wide=1.12 if i == VICTOR else 1.0)
        c.drawPath(p, paint(BEAM, 0.18, blur=10))
        c.drawPath(p, paint((5, 5, 6), 1))


def sc_count(c, T, lt, S):
    l = S["lines"][0]
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 930, 1.0 + 0.04 * lt)
    wall_world(c, T)
    # count marks
    t_people = wt("l04", 0); t_sh = wt("l04", 2)
    for i in range(6):
        a = smooth(ramp(T, t_people - 0.25 + i * 0.11, t_people - 0.1 + i * 0.11))
        label(c, str(i + 1), PX[i], FEET + 70, a, YEL, 40, "InterDisplay-Black", 0)
    shx = [shadow_x(x) for x in PX] + [shadow_x(PX[VICTOR]) + 96]
    order = [0, 1, 2, 3, 6, 4, 5]
    for n, i in enumerate(order):
        a = smooth(ramp(T, t_sh - 0.2 + n * 0.1, t_sh - 0.05 + n * 0.1))
        yy = WALL_BASE + 10 - PH * (1.47 if i == 6 else 1.38) * 0.96 - 26
        label(c, str(n + 1), shx[i], yy, a, RED if n == 6 else (240, 140, 130), 38, "InterDisplay-Black", 0)
    c.restore()
    a6 = smooth(ramp(T, t_people, t_people + 0.2))
    a7 = smooth(ramp(T, t_sh, t_sh + 0.2))
    big_number(c, "6", 400 if a7 > 0 else 540, 360, 230, YEL, a6)
    if a7 > 0:
        label(c, "/", 540, 330, a7, (150, 150, 150), 90, "InterDisplay-Light", 0)
        big_number(c, "7", 680, 360, 230, RED, a7, glow=0.9)
    return dict(grain=11, vig=0.9, glitch=0.5 if 0 < T - t_sh < 0.08 else 0)


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


def sc_oldman(c, T, lt, S):
    def look(T):
        return (0.15 * vnoise(T * 0.7, 3), 0.15)
    face_common(c, T, lt, S, "old", fear=0.2, look=look)
    return dict(grain=12, vig=0.95)


def sc_oldman_door(c, T, lt, S):
    l = S["lines"][0]
    t_so = wt("l16", 2)  # "Так"
    def look(T):
        a = smooth(ramp(T, S["t0"], S["t0"] + 0.4)) * (1 - smooth(ramp(T, t_so - 0.2, t_so + 0.2)))
        return (lerp(0.0, -1.0, a), lerp(0.0, 0.1, a))
    face_common(c, T, lt, S, "old", fear=0.6, look=look, light_fn=lambda T: 0.82 + 0.06 * vnoise(T * 14, 9))
    return dict(grain=13, vig=1.0)


def hands_world(c, T, raise6, raise7, red=0.0, desat=False):
    rp = [raise6] * 6
    wall_world(c, T, raise_p=rp, raise_thing=raise7, red_thing=red)


def sc_hands(c, T, lt, S):
    l = S["lines"][0]
    t_up = wt("l06", 2) - 0.1   # "поднялись"
    r6 = ramp(T, t_up, t_up + 0.45)
    r7 = ramp(T, t_up + 0.5, t_up + 0.8)
    t_pochti = wt("l06", 4)
    frz = T >= t_pochti - 0.05
    if frz:
        Tf = t_pochti - 0.05
        r6 = ramp(Tf, t_up, t_up + 0.45); r7 = ramp(Tf, t_up + 0.5, t_up + 0.8)
    z = lerp(1.25, 1.35, ramp(T, S["t0"], t_pochti))
    cx, cy = 540, 640
    if frz:
        q = ease_io(ramp(T, t_pochti - 0.05, t_pochti + 0.6))
        z = lerp(z, 2.1, q)
        cx = lerp(540, shadow_x(PX[VICTOR]) + 96, q); cy = lerp(640, 620, q)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, cx, cy, z)
    hands_world(c, T, r6, r7, red=0.0)
    c.restore()
    fx = dict(grain=11, vig=0.9)
    if frz:
        fx["tint"] = (190, 200, 215, 0.6 * ramp(T, t_pochti, t_pochti + 0.3))
        fx["glitch"] = 0.6 if T - t_pochti < 0.07 else 0.0
    return fx


def sc_hands_late(c, T, lt, S):
    l = S["lines"][0]
    dur = S["t1"] - S["t0"]
    # slow-motion replay of the raise, focused on the late shadow
    r = ramp(lt, 0.2, dur - 0.6)
    tt = r * 1.4  # replay seconds 0..1.4 of real time
    r6 = ramp(tt, 0.1, 0.55)
    r7 = ramp(tt, 0.6, 0.9)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, shadow_x(PX[VICTOR]) + 30, 640, 1.75)
    hands_world(c, T, r6, r7)
    # highlight ring around the late arm
    tx = shadow_x(PX[VICTOR]) + 96
    pulse = 0.5 + 0.5 * math.sin(lt * 7)
    c.drawCircle(tx - 0.15 * PH * 1.47, WALL_BASE + 10 - PH * 1.47 * 0.53, 120 + 8 * pulse,
                 paint(RED, 0.55 * smooth(ramp(tt, 0.5, 0.6)), stroke=4))
    c.restore()
    # replay HUD: timer and two bars
    a = smooth(ramp(lt, 0.0, 0.3))
    f = font(34, "Inter-SemiBold")
    c.drawString("ПОВТОР  ×0.25", 60, 230, f, paint(WHITE, 0.75 * a))
    c.drawCircle(42, 219, 8, paint(RED, a * (0.5 + 0.5 * (int(lt * 2) % 2))))
    secs = f"{tt * 1.0:0.2f} с"
    c.drawString(secs, W - 60 - f.measureText(secs), 230, f, paint(WHITE, 0.75 * a))
    # bars
    bx0, bx1 = 120, W - 120
    for k, (rv, rgb, yy, name) in enumerate([(r6, WHITE, 330, "6 теней"), (r7, RED, 410, "7-я тень")]):
        c.drawRect(skia.Rect(bx0, yy, bx1, yy + 10), paint((60, 60, 60), 0.7 * a))
        c.drawRect(skia.Rect(bx0, yy, lerp(bx0, bx1, rv), yy + 10), paint(rgb, 0.95 * a))
        c.drawString(name, bx0, yy - 14, font(28, "Inter-Medium"), paint(rgb, 0.8 * a))
    d = smooth(ramp(tt, 0.55, 0.62))
    lbl = "+0,5 с"
    c.drawString(lbl, bx1 - font(44, "InterDisplay-Black").measureText(lbl), 395, font(44, "InterDisplay-Black"), paint(RED, a * d))
    return dict(grain=12, vig=0.95, tint=(200, 205, 220, 0.55), scan=0.25)


def sc_victor_reveal(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    q = ease_io(ramp(lt, 0.0, dur * 0.7))
    cx = lerp(shadow_x(PX[VICTOR]) + 96, PX[VICTOR] + 20, q)
    cy = lerp(620, 1000, q)
    z = lerp(2.1, 1.7, q)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, cx, cy, z)
    wall_world(c, T, raise_p=[1 - smooth(ramp(lt, 0, 0.6))] * 6, raise_thing=1 - smooth(ramp(lt, 0.4, 1.4)),
               thing_head=-18 * smooth(ramp(lt, 1.2, 2.4)))
    t_v = wt("l08", 3)
    a = smooth(ramp(T, t_v - 0.1, t_v + 0.25))
    x = PX[VICTOR]; y = FEET - PH * 1.02
    c.drawLine(x, y + 10, x, y + 50, paint(YEL, a, stroke=3))
    label(c, "ВИКТОР", x, y - 6, a, YEL, 30, "Inter-Bold", 7)
    c.restore()
    return dict(grain=11, vig=0.95)


def sc_eyes(c, T, lt, S):
    c.clear(col((0, 0, 0)))
    # victor in a cone of light, everybody else only eyes
    tr = 3 * vnoise(T * 12, 1)
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(540, 1250, 520, [(0, (60, 56, 50), 1), (1, (0, 0, 0), 1)])))
    beam(c, 540, -100, 180, 1500, 15, 0.7)
    c.drawPath(person_path(540 + tr, 1500, 640, wide=1.12), paint((0, 0, 0), 1))
    c.drawPath(person_path(540 + tr, 1500, 640, wide=1.12), paint(BEAM, 0.3, stroke=4, blur=3))
    c.drawOval(skia.Rect(340, 1480, 740, 1530), paint((0, 0, 0), 0.9, blur=10))
    eyes = [(170, 520, 0), (900, 640, 1), (120, 1060, 2), (960, 1160, 3), (300, 300, 4)]
    words = [l["words"] for l in S["lines"]][0]
    for k, (ex, ey, seed) in enumerate(eyes):
        tw = words[min(len(words) - 1, k % len(words))]["t0"] + 0.12 * k
        snap = ease_out(ramp(T, tw, tw + 0.12))
        ap = smooth(ramp(lt, 0.05 * k, 0.4 + 0.05 * k))
        dx, dy = 540 - ex, 1150 - ey
        d = math.hypot(dx, dy)
        lookx, looky = dx / d * snap, dy / d * snap
        for side in (-1, 1):
            x = ex + side * 34
            c.drawOval(skia.Rect(x - 26, ey - 13, x + 26, ey + 13), paint((225, 222, 212), 0.9 * ap))
            c.drawCircle(x + lookx * 13 + vnoise(T * 3, seed) * 4 * (1 - snap), ey + looky * 6, 9, paint((0, 0, 0), ap))
        bl = 0
        c.drawOval(skia.Rect(ex - 75, ey - 30, ex + 75, ey + 30), paint((0, 0, 0), 0.4, blur=14))
    # the thing joins in, last, from the dark
    t_last = S["lines"][0]["words"][-1]["t0"]
    glow_eyes(c, 760, 380, 14, smooth(ramp(T, t_last + 0.2, t_last + 0.8)) * 0.9)
    return dict(grain=12, vig=1.0)


def sc_victor_face(c, T, lt, S):
    shk = shake(T)
    c.save(); c.translate(vnoise(T * 30, 1) * 26 * shk + vnoise(T * 9, 3) * 5, vnoise(T * 30, 2) * 20 * shk)
    def look(T):
        return (0.9 * math.copysign(1, vnoise(T * 2.5, 8)) * min(1, abs(vnoise(T * 2.5, 8)) * 3), -0.1)
    face_common(c, T, lt, S, "victor", fear=1.0, look=look)
    c.restore()
    red = max(0.0, shk - 0.3) * 0.35
    if red > 0:
        c.drawRect(skia.Rect(0, 0, W, H), paint(RED, red, blend="screen"))
    return dict(grain=12, vig=0.95, ca=3 + 8 * shk, glitch=0.5 if shk > 0.75 else 0.0)


def sc_step(c, T, lt, S):
    l = S["lines"][0]
    t_step = wt("l11", 2) - 0.1   # "шаг"
    q = ease_io(ramp(T, t_step, t_step + 0.9))
    vp = (lerp(PX[VICTOR], 900, q), lerp(FEET, 1520, q), lerp(1.0, 1.45, q))
    t_ost = wt("l11", 9)  # "осталась"
    push = ease_io(ramp(T, t_ost - 0.6, S["t1"]))
    cx = lerp(540, shadow_x(PX[VICTOR]) + 40, push); cy = lerp(1000, 760, push); z = lerp(1.0, 1.6, push)
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, cx, cy, z)
    wall_world(c, T, victor_pos=vp, thing_head=-18 + 10 * smooth(ramp(T, t_ost, t_ost + 1.0)))
    c.restore()
    return dict(grain=11, vig=0.95, tint=(180, 190, 210, 0.35 * push))


def sc_flicker(c, T, lt, S):
    l = S["lines"][0]
    t_m = wt("l12", 1)
    # strobe pattern (seconds relative to "мигнул"): on/off
    pattern = [(0.00, 0), (0.10, 1), (0.16, 0), (0.42, 1), (0.50, 0), (0.95, 1), (1.02, 0), (1.55, 1)]
    st = 1
    rel = T - t_m
    for t0, s in pattern:
        if rel >= t0:
            st = s
    k = sum(1 for t0, s in pattern if rel >= t0 and s == 1)  # how many re-lit flashes we've had
    c.clear(col((0, 0, 0)))
    if st == 0:
        # darkness: only eyes, closer each time
        n = sum(1 for t0, s in pattern if rel >= t0 and s == 0)
        glow_eyes(c, lerp(760, 640, n / 4), lerp(520, 980, n / 4), 12 + n * 5, 0.95)
        return dict(grain=16, vig=1.0)
    gone = rel >= 1.55
    if rel < 0:
        wall_world(c, T, victor_pos=(900, 1520, 1.45), thing_head=-8)
        return dict(grain=11, vig=0.95, tint=(180, 190, 210, 0.35))
    follow = {VICTOR: (820, min(1.0, k * 0.4))}
    tdx = min(1.0, k * 0.4) * 160
    c.save()
    z = 1.0 + 0.03 * (T - S["t0"])
    cam(c, 540, 1000, z)
    wall_world(c, T, victor_pos=(900, 1520, 1.45), victor_gone=gone, shadows_follow=None if gone else follow,
               thing_dx=0 if gone else tdx, light=0.75 if not gone else 0.7)
    c.restore()
    return dict(grain=12, vig=0.95, glitch=0.6 if 0 <= rel - 1.55 < 0.08 else 0.0, tint=(180, 190, 210, 0.35))


def sc_five(c, T, lt, S):
    l = S["lines"][0]
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 930, 1.0)
    wall_world(c, T, people=[0, 1, 2, 4, 5], light=0.7)
    c.restore()
    t5 = wt("l13", 2)  # "пятеро"
    t7 = wt("l13", 7)  # "семь"
    flip = T >= t5
    big_number(c, "5" if flip else "6", 400, 360, 230, YEL, 1.0)
    label(c, "/", 540, 330, 1, (150, 150, 150), 90, "InterDisplay-Light", 0)
    pulse = 0.85 + 0.15 * math.sin(T * 8) if T >= t7 else 1.0
    big_number(c, "7", 680, 360, 230 * (1 + 0.06 * smooth(ramp(T, t7, t7 + 0.1)) * (1 - smooth(ramp(T, t7 + 0.1, t7 + 0.5)))), RED, pulse, 0.9)
    g = 0.7 if 0 <= T - t5 < 0.1 else (0.5 if 0 <= T - t7 < 0.06 else 0)
    # empty place where victor stood
    return dict(grain=12, vig=0.95, glitch=g, tint=(180, 190, 210, 0.35))


def dust(c, T, t0, seed, n=40):
    if T < t0:
        return
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x = rng.uniform(0, W); v = rng.uniform(300, 900); s = rng.uniform(2, 6)
        delay = rng.uniform(0, 0.25)
        tt = T - t0 - delay
        if tt < 0:
            continue
        y = 380 + v * tt + 400 * tt * tt
        a = max(0.0, 0.7 - tt * 0.5)
        c.drawCircle(x + 20 * math.sin(tt * 3 + x), y, s, paint((170, 170, 165), a, blur=1.5))


def sc_knock(c, T, lt, S):
    kt = knock_times()
    shk = shake(T)
    jolt = sum(0.05 * math.exp(-(T - k) * 6) for k in kt if T >= k)
    light = 0.8 + 0.2 * (1 - min(1, shk))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 900, 1.08 + 0.04 * lt)
    door(c, T, shake=shk, light=light, wheel_rot=0.3 + jolt)
    for i, k in enumerate(kt):
        dust(c, T, k, 100 + i)
    c.restore()
    return dict(grain=12, vig=0.95, ca=4 * shk)


def sc_door_voice(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    fr = smooth(ramp(lt, 0.2, dur))
    c.clear(col((0, 0, 0)))
    c.save(); cam(c, 540, 900, 1.12 + 0.12 * ease_io(lt / dur))
    door(c, T, light=0.75, wheel_rot=0.3, seam_glow=0.35 * fr, frost=fr * 1.4)
    c.restore()
    # breath of cold through the seam
    return dict(grain=12, vig=1.0, tint=(170, 195, 230, 0.35 * fr))


def sc_flashback(c, T, lt, S):
    dur = S["t1"] - S["t0"]
    lines = S["lines"]
    weave = (vnoise(T * 6, 1) * 6, vnoise(T * 6, 2) * 4)
    c.clear(col((0, 0, 0)))
    c.save(); c.translate(*weave)
    z = 1.0 + 0.02 * lt
    if S["name"] == "flashback_mom":
        q = ease_io(ramp(lt, 0, dur * 0.8))
        cam(c, lerp(540, 190, q), lerp(960, 1080, q), lerp(1.02, 2.4, q))
    else:
        cam(c, 540, 960, z)
    flashback_world(c, T, lt, S)
    c.restore()
    # light leak
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=radial(980, 200, 700, [(0, (255, 150, 60), 0.35), (1, (255, 120, 40), 0)]), blend="screen"))
    flick = 0.92 + 0.08 * vnoise(T * 20, 7)
    return dict(grain=20, vig=1.0, scan=0.35, bright=flick, ca=3)


_FB_T0 = None


def flashback_world(c, T, lt, S):
    t0 = L("l17")["scene_t0"]
    ft = T - t0
    # time freezes once mom calls
    t_mom = L("l18")["start"]
    run_t = ft if T < t_mom else (t_mom - t0) + (T - t_mom) * 0.08
    # orange sky, cloud ellipses like episode 1
    c.drawRect(skia.Rect(-400, -400, W + 400, H + 400),
               paint(shader=linear(0, 0, 0, H, [(0, (120, 30, 8), 1), (0.55, (255, 90, 25), 1), (1, (200, 60, 15), 1)])))
    for i, (x, y, w, h) in enumerate([(200, 420, 500, 50), (800, 560, 420, 40), (350, 760, 600, 55), (900, 880, 380, 35)]):
        xx = (x + run_t * (12 + i * 5)) % (W + 600) - 300
        c.drawOval(skia.Rect(xx - w / 2, y - h / 2, xx + w / 2, y + h / 2), paint((150, 40, 10), 0.45, blur=10))
    # ground
    gp = skia.Path(); gp.moveTo(-400, 1330)
    for i in range(12):
        gp.lineTo(-400 + i * 170, 1330 + 18 * math.sin(i * 1.3))
    gp.lineTo(W + 400, H + 400); gp.lineTo(-400, H + 400); gp.close()
    c.drawPath(gp, paint((20, 8, 4), 1))
    # the hatch, glowing red squares
    hx, hy = 620, 1470
    for k in range(4):
        s = 1 + k * 0.55 + (run_t * 0.5 % 0.55)
        c.drawRect(skia.Rect(hx - 90 * s, hy - 32 * s, hx + 90 * s, hy + 32 * s), paint(RED, 0.5 / (1 + k), stroke=4))
    c.drawRect(skia.Rect(hx - 90, hy - 32, hx + 90, hy + 32), paint((255, 60, 30), 0.9, blur=6))
    # running people toward the hatch
    runners = [(-150, 1.0, 0.0), (1250, 0.9, 1.7), (-420, 1.05, 3.1), (1400, 0.95, 4.2), (-650, 1.0, 5.3)]
    for i, (x0, sp, ph) in enumerate(runners):
        dirn = 1 if x0 < hx else -1
        x = x0 + dirn * run_t * 240 * sp
        if (dirn == 1 and x > hx - 40) or (dirn == -1 and x < hx + 40):
            continue  # reached hatch
        c.save()
        if dirn == -1:
            c.translate(x, 0); c.scale(-1, 1); c.translate(-x, 0)
        stickman(c, x, 1500, 300, run_t * 11 * sp + ph, paint((12, 6, 4), 1))
        c.restore()
    # mom on the horizon, standing still, far away (left)
    t_mama = wt("l17", 8)  # "маму"
    ma = smooth(ramp(T, t_mama - 0.4, t_mama + 0.4))
    mx, my = 190, 1330
    if ma > 0:
        beckon = smooth(ramp(T, L("l18")["start"] - 0.2, L("l18")["start"] + 0.6))
        mother(c, mx, my + 4, 190, paint((25, 10, 6), ma), beckon, T)
        t_name = wt("l17", 13)  # "имени"
        ra = smooth(ramp(T, t_name - 0.6, t_name))
        rings(c, mx, my - 170, 260, 260, 5, T, a=0.35 * ra, rgb=(255, 210, 170), speed=0.35)


def sc_turn(c, T, lt, S):
    l = S["lines"][0]
    t_turn = wt("l19", 2)  # "обернулся"
    cut = l["end"] - 0.02
    if T >= cut:
        c.clear(col((0, 0, 0)))
        return dict(grain=8, vig=1.0, glitch=0.9 if T - cut < 0.08 else 0.0)
    c.clear(col((0, 0, 0)))
    pan = ease_in(ramp(T, t_turn - 0.25, t_turn + 0.1))
    reveal = T > t_turn + 0.1
    if not reveal:
        c.save(); c.translate(pan * 1600, 0)
        flashback_world(c, T, lt, S)
        c.restore()
        # motion-blur streaks
        for i in range(30):
            y = hash01(i, 3) * H
            c.drawRect(skia.Rect(0, y, W, y + 3 + 10 * hash01(i, 4)), paint((255, 160, 90), 0.25 * pan, blur=6))
        return dict(grain=18, vig=1.0, scan=0.35, ca=10 * pan)
    # she is right here. Too tall. Eyes open.
    c.drawRect(skia.Rect(0, 0, W, H), paint(shader=linear(0, 0, 0, H, [(0, (120, 30, 8), 1), (0.6, (255, 90, 25), 1), (1, (120, 30, 8), 1)])))
    q = ease_out(ramp(T, t_turn + 0.1, t_turn + 0.6))
    mx, my = 540, 2500
    s = lerp(6.5, 7.4, q)
    mother(c, mx, my, 190 * s, paint((14, 5, 3), 1), 0.0, T, tall=lerp(1.0, 1.12, q))
    eo = smooth(ramp(T, t_turn + 0.35, t_turn + 0.7))
    glow_eyes(c, mx, my - 190 * s * lerp(1.0, 1.12, q) + 0.068 * 190 * s, 4.2 * s, eo, open_=eo)
    return dict(grain=18, vig=1.0, scan=0.3, ca=4)


def sc_ear(c, T, lt, S):
    l = S["lines"][0]
    c.clear(col((0, 0, 0)))
    die_t = l["end"] + 0.55
    # flashlight lying on the floor, dying
    lvl = 0.55 * (1 - 0.6 * ramp(T, S["t0"], die_t))
    fl = lvl * (1 if vnoise(T * 25, 4) > -0.55 else 0.15)
    if T > die_t:
        fl = 0.0 if (T - die_t) > 0.35 or int((T - die_t) * 30) % 3 == 0 else lvl * 0.4
    c.drawRect(skia.Rect(0, 1300, W, H), paint(shader=linear(0, 1300, 0, H, [(0, (14, 14, 16), 1), (1, (4, 4, 5), 1)])))
    beam(c, 980, 1560, -78, 1300, 9, fl * 1.6)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(950, 1530, 1100, 1590), 14, 14), paint((25, 25, 28), 1))
    c.drawCircle(955, 1560, 26, paint(BEAM, fl * 0.9, blur=8))
    # something right at your ear: huge, out of focus, left edge
    e = VE.at("l20", T)
    appear = smooth(ramp(lt, 0.3, 1.4))
    hx, hy = 60, 860
    c.drawOval(skia.Rect(hx - 420, hy - 520, hx + 300, hy + 900), paint((10, 12, 16), appear, blur=40))
    rings(c, 360, 900, 640, 420, 6, T, a=0.22 * appear * (0.4 + e), speed=0.4)
    glow_eyes(c, hx + 170, hy, 34, appear * (0.7 + 0.3 * e), open_=0.8 - 0.4 * e, gap=1.25)
    return dict(grain=14, vig=1.0, ca=2 + 4 * e)


def sc_door_mom(c, T, lt, S):
    l = S["lines"][0]
    c.clear(col((0, 0, 0)))
    if T < l["start"] - 1.3:
        return dict(grain=10, vig=1.0)
    a = smooth(ramp(T, l["start"] - 1.3, l["start"] - 0.6))
    y = 1250
    # light under the door
    c.drawRect(skia.Rect(-20, y - 4, W + 20, y + 4), paint((255, 170, 60), 0.95 * a, blur=2))
    c.drawRect(skia.Rect(-20, y - 26, W + 20, y + 30), paint((255, 140, 40), 0.25 * a, blur=26))
    c.drawRect(skia.Rect(-20, y + 4, W + 20, y + 300), paint(shader=linear(0, y, 0, y + 300, [(0, (255, 140, 40), 0.22 * a), (1, (0, 0, 0), 0)])))
    # faint door edge + wheel catching the slit light
    c.drawRect(skia.Rect(80, 300, W - 80, y - 6), paint((255, 150, 60), 0.05 * a, stroke=3))
    t_mama = wt("l21", 3)  # "мама"
    rot = 0.3 + 0.35 * ease_io(ramp(T, t_mama + 0.4, t_mama + 1.6))
    wheel(c, W / 2, 760, 200, rot, 0.06 * a + 0.04 * ramp(T, t_mama, t_mama + 1.0), (255, 170, 90))
    # feet: two... then more
    feet = [(470, 0), (610, 0)]
    if T > t_mama + 0.05: feet += [(330, 1), (750, 1)]
    if T > t_mama + 0.45: feet += [(210, 2), (880, 2), (540, 2)]
    for fx_, k in feet:
        wob = 6 * vnoise(T * 2 + fx_, k)
        c.drawRect(skia.Rect(fx_ - 34 + wob, y - 6, fx_ + 34 + wob, y + 6), paint((0, 0, 0), 1))
        c.drawRect(skia.Rect(fx_ - 40 + wob, y + 5, fx_ + 40 + wob, y + 90), paint((0, 0, 0), 0.45 * a, blur=16))
    return dict(grain=12, vig=1.0)


def sc_endcard(c, T, lt, S):
    c.clear(col((0, 0, 0)))
    dur = S["t1"] - S["t0"]
    a = smooth(ramp(lt, 0.3, 0.8))
    rings(c, 540, 1180, 520, 150, 6, T, a=0.18 * a)
    label(c, "СЕРИЯ  3", 540, 800, a, RED, 34, "Inter-Bold", 14)
    f = font(92, "InterDisplay-Black")
    for i, txt in enumerate(["КТО ОТКРОЕТ", "ДВЕРЬ?"]):
        w = f.measureText(txt)
        c.drawString(txt, 540 - w / 2, 950 + i * 110, f, paint(WHITE, a))
    label(c, "продолжение следует", 540, 1290, smooth(ramp(lt, 1.4, 2.0)) * 0.7, (190, 190, 190), 30, "Inter-Medium", 4)
    g = 0.8 * (1 - ramp(lt, 0.3, 0.7)) if lt < 0.7 else 0
    return dict(grain=9, vig=0.8, glitch=g)


SCENES = dict(cold=sc_cold, back=sc_back, wall_line=sc_wall_line, count=sc_count, oldman=sc_oldman,
              hands=sc_hands, hands_late=sc_hands_late, victor_reveal=sc_victor_reveal, eyes=sc_eyes,
              victor_face=sc_victor_face, step=sc_step, flicker=sc_flicker, five=sc_five, knock=sc_knock,
              door_voice=sc_door_voice, oldman_door=sc_oldman_door, flashback=sc_flashback,
              flashback_mom=sc_flashback, turn=sc_turn, ear=sc_ear, door_mom=sc_door_mom, endcard=sc_endcard)

SUB_Y = dict(oldman=1520, oldman_door=1520, victor_face=1520, hands_late=1600, count=1520, five=1520,
             wall_line=1560, step=1560, flicker=1560, victor_reveal=1560, hands=1420,
             flashback=1700, flashback_mom=1700, turn=1700, door_mom=1520, knock=1700, door_voice=1700,
             eyes=1700, ear=1350, back=1060, cold=1260)
MUFFLED = {"l15", "l21", "l18"}


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
    c.drawString("СЕРИЯ 2 · БУНКЕР", 62, 71, f, paint((255, 255, 255), 0.85))
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
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
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
