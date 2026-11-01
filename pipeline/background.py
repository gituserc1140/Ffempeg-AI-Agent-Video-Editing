"""Animated, textured backdrops for the pixel-art scenes."""
import math
import random

from . import config as C

_rnd = random.Random(7)
_STARS = [(_rnd.randint(3, 104), _rnd.randint(26, 100), _rnd.randint(0, 3)) for _ in range(16)]


def _split(c, p, brief):
    a = C.FAMILIES[brief["subject_a"]["color"]]
    b = C.FAMILIES[brief["subject_b"]["color"]]
    c.rect(0, 0, C.W - 1, C.H - 1, 0)
    c.rect(0, 36, 52, 136, 0)
    c.rect(55, 36, 107, 136, 5)

    for y0 in range(0, 136, 18):
        pts = []
        for x in range(-2, 56, 4):
            y = y0 + (4 if (x // 4) % 2 else 0)
            pts.append((x, y))
        for (x0, y0p), (x1, y1) in zip(pts, pts[1:]):
            steps = max(abs(x1 - x0), abs(y1 - y0p))
            for i in range(steps + 1):
                x = round(x0 + (x1 - x0) * i / steps)
                y = round(y0p + (y1 - y0p) * i / steps)
                c.px(x, y, a[1])
        for x in range(4, 53, 12):
            c.px(x + (y0 // 18 % 2) * 4, y0 + 8, a[0])

    for row, y in enumerate(range(0, 137, 9)):
        offset = 0 if row % 2 == 0 else 8
        c.rect(55, y, 107, y, 1)
        for x in range(55 + offset, 108, 16):
            c.rect(x, y, x, min(y + 7, 136), 1)
            c.px(x + 2, y + 2, 4)
        for x in range(60 + offset, 108, 16):
            c.px(x, min(y + 6, 136), b[1])

    for y in range(37, 136):
        x = 53 + (1 if (y // 5) % 2 else 0)
        c.rect(x, y, x + 1, y, 12 if y % 9 < 3 else 2)
    for x in range(5, 103):
        if (x // 3) % 2 == 0:
            c.px(x, 129, 12)
    c.rect(0, 137, 107, 138, 5)
    c.rect(0, 139, 107, 139, 2)

    for x, y, ph in _STARS:
        if y < 36 or y > 126:
            continue
        state = (p + ph) % 4
        if state == 0:
            c.px(x, y, 3)
        elif state in (1, 3):
            c.px(x, y, a[0] if x < 53 else b[0])


def _single(c, p, brief):
    t = C.FAMILIES[brief["subject_a"]["color"]]
    c.rect(0, 0, C.W - 1, C.H - 1, 0)
    shift = (p // 3) % 12
    for k in range(-12, 24):
        x = k * 12 + shift
        c.line(x, 0, x - 136, 136, 1, 4)
    c.rect(0, 0, C.W - 1, 21, 0)
    c.circle(54, 70, 36, 1, fill=True)
    c.circle(54, 70, 36, 2)
    c.circle(54, 70, 40, t[1])
    for k in range(24):
        ang = k * 6.2832 / 24 + p * 0.03
        c.px(54 + round(math.cos(ang) * 44), 70 + round(math.sin(ang) * 44), t[0] if k % 2 else t[1])
    for x, y, ph in _STARS:
        if y < 44 or y > 92:
            continue
        state = (p + ph) % 4
        if state == 0:
            c.px(x, y, 3)
        elif state in (1, 3):
            c.px(x, y, t[0])
    c.rect(0, 103, C.W - 1, 135, 1)
    c.rect(0, 103, C.W - 1, 104, t[1])
    off = p % 12
    for k in range(-1, 4):
        y = 106 + k * 12 + off
        if 105 <= y <= 135:
            c.rect(0, y, C.W - 1, y, 2)
    for x in range(-12 + (p // 2) % 12, C.W, 12):
        c.rect(x, 105, x, 135, 2)
    c.rect(0, 136, C.W - 1, 137, 5)


def draw(c, p, brief=None):
    c.rect(0, 0, C.W - 1, C.H - 1, 0)
    if brief and brief.get("layout") == "split" and brief.get("subject_b"):
        _split(c, p, brief)
        return
    if brief:
        _single(c, p, brief)
        return
    c.rect(0, 100, C.W - 1, 135, 1)
    off = p % 12
    for k in range(-1, 5):
        y = 102 + k * 12 + off
        if 100 <= y <= 135:
            c.rect(0, y, C.W - 1, y, 2)
    for x in range(-12 + (p // 2) % 12, C.W, 12):
        c.rect(x, 100, x, 135, 2)
    for x, y, ph in _STARS:
        state = (p + ph) % 4
        if state == 0:
            c.px(x, y, 3)
        elif state in (1, 3):
            c.px(x, y, 4)
    c.rect(0, 136, C.W - 1, 137, 5)
