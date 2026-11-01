"""Animated, topic-specific mini scenes ("stages") drawn procedurally on a transparent
sheet and blitted onto the canvas. Only palette colours are used, so the 16-colour
rule still holds. Every stage takes (sheet, pb, a, A, fixed): pb is the 12 fps pose
counter, a/A the subject colours and fixed=True once a problem has been solved."""
import math

from PIL import Image, ImageDraw

from . import config as C

PAL = C.PALETTE
HEIGHT = 46


class Sheet:
    def __init__(self, w, h=HEIGHT, ghost=False):
        self.w, self.h, self.ghost = w, h, ghost
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _c(self, col):
        return PAL[5 if self.ghost else col] + (255,)

    def rect(self, x0, y0, x1, y1, col):
        if x1 >= x0 and y1 >= y0:
            self.d.rectangle([x0, y0, x1, y1], fill=self._c(col))

    def px(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.img.putpixel((int(x), int(y)), self._c(col))

    def line(self, x0, y0, x1, y1, col, width=1):
        self.d.line([(x0, y0), (x1, y1)], fill=self._c(col), width=width)

    def poly(self, pts, col):
        self.d.polygon(pts, fill=self._c(col))

    def circle(self, cx, cy, r, col):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self._c(col))


def _solid(s, x0, y0, x1, y1, fill, hi=None):
    """Filled block with a dark outline and optional top highlight row."""
    s.rect(x0, y0, x1, y1, 0)
    s.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)
    if hi is not None:
        s.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, hi)


def _bed(s):
    _solid(s, 3, s.h - 4, s.w - 4, s.h - 1, 5, hi=4)


def printer(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx, left, right, base = w // 2, 3, w - 4, h - 1
    _solid(s, left, base - 5, right, base, 5, hi=4)
    for x in (left + 2, right - 5):
        _solid(s, x, 5, x + 3, base - 6, 4, hi=3)
    _solid(s, left + 2, 2, right - 2, 7, 5, hi=4)
    mw = min(24, w // 2)
    layers = min(10, (pb // 2) % 14)
    top = base - 6 - 2 * layers
    x0 = cx - mw // 2
    for i in range(layers):
        y = base - 7 - 2 * i
        s.rect(x0 - 1, y - 1, x0 + mw, y, 0)
        s.rect(x0, y - 1, x0 + mw - 1, y, a if i % 2 else A)
    gy = top - 11
    _solid(s, left + 5, gy, right - 5, gy + 3, 4, hi=3)
    nx = cx + int(math.sin(pb * 0.9) * (mw // 2 - 2))
    _solid(s, nx - 3, gy - 2, nx + 3, gy + 6, 12, hi=3)
    s.rect(nx - 1, gy + 7, nx + 1, gy + 8, 4)
    s.px(nx, gy + 9, 6)


def nozzle(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx = w // 2
    _bed(s)
    span = max(4, w - 24)
    nx = 12 + (pb * 2) % span
    s.rect(nx - 8, 2, nx + 7, 13, 0)
    s.rect(nx - 7, 2, nx + 6, 13, 5)
    for y in (3, 6, 9, 12):
        s.rect(nx - 7, y, nx + 6, y, 4)
    for y in range(0, 14):
        if (y + pb) % 4 == 0:
            s.rect(nx - 1, y, nx + 1, y, A)
        else:
            s.rect(nx - 1, y, nx + 1, y, a)
    _solid(s, nx - 8, 14, nx + 7, 22, 6, hi=12)
    s.rect(nx - 6, 18, nx + 5, 19, 7)
    s.poly([(nx - 5, 23), (nx + 5, 23), (nx + 1, 29), (nx - 1, 29)], 0)
    s.poly([(nx - 4, 23), (nx + 4, 23), (nx + 1, 28), (nx - 1, 28)], 12)
    s.rect(nx, 29, nx, h - 9, a)
    s.rect(4, h - 8, nx, h - 6, 0)
    s.rect(4, h - 8, nx, h - 7, a)
    s.rect(4, h - 6, nx, h - 6, A)
    s.rect(4, h - 8, nx, h - 8, 3 if not s.ghost else 5)


def layers(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx = w // 2
    _bed(s)
    mw = min(w - 12, 40)
    x0 = cx - mw // 2
    count = 1 + (pb // 3) % 7
    for i in range(count):
        y1 = h - 5 - 4 * i
        y0 = y1 - 3
        s.rect(x0 - 1, y0, x0 + mw, y1, 0)
        s.rect(x0, y0, x0 + mw - 1, y0 + 1, a)
        s.rect(x0, y0 + 2, x0 + mw - 1, y1 - 1, A)
    top = h - 5 - 4 * count + 1
    nx = cx + int(math.sin(pb * 0.8) * (mw // 2 - 3))
    _solid(s, nx - 3, top - 9, nx + 3, top - 4, 4, hi=3)
    s.poly([(nx - 3, top - 3), (nx + 3, top - 3), (nx, top - 1)], 12)


def warp(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx = w // 2
    _bed(s)
    mw = min(w - 10, 56)
    amp = 0.0 if fixed else 0.6 + 0.4 * math.sin(pb * 0.5)
    for x in range(cx - mw // 2, cx + mw // 2 + 1):
        d = abs(x - cx) / (mw / 2)
        lift = int(amp * (max(0.0, d - 0.45) * 1.8) ** 2 * 13)
        bottom = h - 6 - lift
        top = bottom - 4
        edge = x in (cx - mw // 2, cx + mw // 2)
        s.rect(x, top, x, bottom, 0 if edge else A)
        if not edge:
            s.rect(x, top, x, top + 1, a)
            s.px(x, bottom, 0)
    if amp > 0.35:
        for sign in (-1, 1):
            ax = cx + sign * (mw // 2)
            ay = h - 23 - int(amp * 4)
            s.poly([(ax, ay - 5), (ax - 3, ay), (ax + 3, ay)], 11)
            s.rect(ax - 1, ay, ax + 1, ay + 4, 11)


def strand(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx = w // 2
    _bed(s)
    gap = min(w - 24, 34)
    xl, xr = cx - gap // 2, cx + gap // 2
    for x in (xl - 5, xr):
        _solid(s, x, 24, x + 5, h - 5, A, hi=a)
        s.rect(x + 1, 25, x + 4, 26, a)
    for i, sag in enumerate((2, 4, 6)):
        pts = []
        steps = max(8, gap)
        for k in range(steps + 1):
            t = k / steps
            y = 25 + i + sag * math.sin(math.pi * t) + math.sin(pb * 0.6 + i + t * 6) * (0.0 if fixed else 1.2)
            pts.append((xl + 1 + (xr - xl - 1) * t, y))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            s.line(x0, y0, x1, y1, 3)
    nx = xl + (pb * 2) % (gap + 1)
    _solid(s, nx - 3, 3, nx + 3, 12, 4, hi=3)
    s.poly([(nx - 3, 13), (nx + 3, 13), (nx, 17)], 12)
    s.line(nx, 18, nx if nx < cx else nx, 24, a)


def _flame_layer(s, cx, base, tipy, radius, col, sway):
    for y in range(int(tipy), int(base) + 1):
        t = min(1.0, max(0.0, (y - tipy) / max(1.0, base - tipy)))
        hw = radius * (t ** 0.6) * math.sqrt(max(0.0, 1 - t ** 4))
        off = sway * (1 - t)
        s.rect(round(cx + off - hw), y, round(cx + off + hw), y, col)


def flame(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx, base = w // 2, h - 6
    _solid(s, cx - 15, h - 5, cx + 15, h - 1, 7, hi=6)
    sway = 2.5 * math.sin(pb * 0.7)
    tip = 4 + 2 * math.sin(pb * 1.3)
    _flame_layer(s, cx, base, tip, 12, A, sway)
    _flame_layer(s, cx, base - 1, tip + 7, 9, a, sway * 0.8)
    _flame_layer(s, cx, base - 3, tip + 15, 6, 12, sway * 0.5)
    _flame_layer(s, cx, base - 5, tip + 22, 3, 3, sway * 0.3)
    for i in range(3):
        y = base - 14 - ((pb * 2 + i * 9) % 28)
        s.px(cx + (-1) ** i * (6 + i * 2) + int(sway), y, 12)


def snow(s, pb, a, A, fixed):
    cx, cy = s.w // 2, s.h // 2
    for k in range(6):
        ang = pb * 0.08 + k * math.pi / 3
        ex, ey = cx + 19 * math.cos(ang), cy + 19 * math.sin(ang)
        s.line(cx, cy, ex, ey, a, 3)
        mx, my = cx + 11 * math.cos(ang), cy + 11 * math.sin(ang)
        for side in (-1, 1):
            bx = mx + 6 * math.cos(ang + side * 0.9)
            by = my + 6 * math.sin(ang + side * 0.9)
            s.line(mx, my, bx, by, A, 2)
        s.line(cx, cy, cx + 17 * math.cos(ang), cy + 17 * math.sin(ang), 3)
    s.circle(cx, cy, 4, 3)
    s.circle(cx, cy, 2, a)


def drop(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx = w // 2
    s.rect(3, h - 8, w - 4, h - 1, 0)
    s.rect(4, h - 7, w - 5, h - 1, A)
    s.rect(4, h - 7, w - 5, h - 7, a)
    phase = pb % 20
    if phase < 12:
        y = 2 + int((phase / 12) ** 2 * (h - 28))
        s.poly([(cx, y), (cx - 6, y + 11), (cx + 6, y + 11)], 0)
        s.circle(cx, y + 13, 7, 0)
        s.poly([(cx, y + 1), (cx - 5, y + 11), (cx + 5, y + 11)], a)
        s.circle(cx, y + 13, 6, a)
        s.circle(cx + 2, y + 15, 3, A)
        s.rect(cx - 4, y + 11, cx - 3, y + 14, 3)
    else:
        r = 3 + (phase - 12) * 3
        s.d.ellipse([cx - r, h - 11, cx + r, h - 5], outline=s._c(3), width=1)
        if phase < 16:
            s.rect(cx - 1, h - 17 - (phase - 12) * 2, cx + 1, h - 10, a)


def _gear(s, cx, cy, r, teeth, rot, a, A):
    for grow, col in ((1.5, 0), (0, a)):
        s.circle(cx, cy, r * 0.74 + grow, col)
        for k in range(teeth):
            ang = rot + k * 2 * math.pi / teeth
            pts = []
            for rad, da in ((r * 0.68, -0.28), (r + grow, -0.17), (r + grow, 0.17), (r * 0.68, 0.28)):
                pts.append((cx + rad * math.cos(ang + da), cy + rad * math.sin(ang + da)))
            s.poly(pts, col)
    s.circle(cx, cy, r * 0.46, A)
    s.circle(cx, cy, r * 0.22, 0)


def gear(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cx, cy = w // 2, h // 2
    if w >= 60:
        _gear(s, cx - 12, cy, 17, 8, pb * 0.12, a, A)
        _gear(s, cx + 21, cy + 8, 10, 6, -pb * 0.2 + 0.3, a, A)
    else:
        _gear(s, cx, cy, 17, 8, pb * 0.12, a, A)


def wave(s, pb, a, A, fixed):
    w, h = s.w, s.h
    cy = h // 2
    for x in range(4, w - 4):
        y = cy + int(9 * math.sin((x + pb * 2) * 0.28))
        s.rect(x, y, x, y + 1, 3)
        s.rect(x, y + 2, x, y + 3, a)
        s.rect(x, y + 4, x, y + 5, A)
        y2 = cy + 12 + int(4 * math.sin((x - pb * 2) * 0.4))
        s.px(x, y2, 5 if s.ghost else 4)


STAGES = {
    "printer": printer, "nozzle": nozzle, "layers": layers, "warp": warp,
    "strand": strand, "flame": flame, "snow": snow, "drop": drop,
    "gear": gear, "wave": wave,
}


def render(name, w, pb, a, A, fixed=False, ghost=False):
    s = Sheet(w, HEIGHT, ghost=ghost)
    STAGES[name](s, pb, a, A, fixed)
    return s


def blit(canvas, sheet, cx, base):
    """Paste the sheet so its bottom edge sits on `base` and it is centred on cx."""
    canvas.img.paste(sheet.img, (cx - sheet.w // 2, base - sheet.h), sheet.img)
