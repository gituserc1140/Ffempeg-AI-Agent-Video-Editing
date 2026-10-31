"""Animated backdrop: scrolling grid, twinkling stars, floor."""
import random

from . import config as C

_rnd = random.Random(7)
_STARS = [(_rnd.randint(3, 104), _rnd.randint(26, 100), _rnd.randint(0, 3)) for _ in range(16)]


def draw(c, p):
    c.rect(0, 0, C.W - 1, C.H - 1, 0)
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
