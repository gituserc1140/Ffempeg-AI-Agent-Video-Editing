"""Hand-placed pixel sprites. Each takes a canvas and integer canvas coordinates."""

from __future__ import annotations

import math

import numpy as np

from . import palette as P
from .palette import MATERIALS
from .pixel import Canvas, sparkle


def spool(cv: Canvas, cx: int, cy: int, mat: str, phase: int = 0, r: int = 13) -> None:
    m = MATERIALS[mat]
    if mat == "tpu":
        cy += phase % 2
    cv.circle(cx, cy, r, fill=m["dark"], outline=P.NAVY)
    cv.circle(cx, cy, r - 2, fill=m["light"], outline=m["mid"])
    for rr in (r - 5, r - 8):
        if rr > 4:
            cv.circle(cx, cy, rr, outline=m["mid"])
    if mat in ("metal", "abs"):
        cv.pts([(cx - r + 4 + i, cy - r + 6 - i) for i in range(4)], P.SHINE)
        cv.px(cx - r + 5, cy - r + 7, P.WHITE)
    elif mat == "tpu":
        cv.pts([(cx - 3, cy - r + 5), (cx - 2, cy - r + 6), (cx + 2, cy + r - 6)], P.RED)
    else:
        cv.pts([(cx - 4 + i, cy - r + 4) for i in range(3)], P.AMBER)
    cv.circle(cx, cy, 4, fill=m["dark"], outline=P.NAVY)
    cv.circle(cx, cy, 1, fill=P.NAVY)
    for k in range(3):
        ang = (phase % 4) * math.pi / 6 + k * 2 * math.pi / 3
        hx = cx + round(math.cos(ang) * (r - 1))
        hy = cy + round(math.sin(ang) * (r - 1))
        hub = {"wood": P.CREAM, "tpu": P.YELLOW, "abs": P.WHITE}.get(mat, P.SHINE)
        cv.pts([(hx, hy), (hx + 1, hy)], hub)
    cv.line([(cx + r - 1, cy + 2), (cx + r + 3, cy + 6)], m["light"], width=2)


def tile(cv: Canvas, cx: int, cy: int, mat: str, t: float, size: int = 24, shine: bool = True) -> None:
    m = MATERIALS[mat]
    x0, y0 = cx - size // 2, cy - size // 2
    x1, y1 = x0 + size - 1, y0 + size - 1
    cv.box(x0, y0, x1, y1, fill=m["light"])
    if mat == "wood":
        for k in range(4):
            yy = y0 + 4 + k * 5
            pts = [(x, yy + round(1.2 * math.sin(x / 3 + k))) for x in range(x0 + 2, x1 - 1)]
            cv.pts(pts, m["mid"])
        cv.ellipse(cx + 2, cy - 2, cx + 6, cy + 4, outline=m["dark"])
        cv.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], m["mid"])
    else:
        cv.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], P.SHINE)
        cv.line([(x0 + 1, y0 + 1), (x0 + 1, y1 - 1)], P.SHINE)
        cv.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], m["mid"])
        cv.line([(x1 - 1, y0 + 1), (x1 - 1, y1 - 1)], m["mid"])
        u = (t % 1.2) / 0.6
        if shine and u <= 1:
            sx = x0 - 6 + int(u * (size + 12))
            band = []
            for y in range(y0 + 2, y1 - 1):
                for off in range(3):
                    x = sx + off - (y - y0) // 2
                    if x0 + 2 <= x <= x1 - 2:
                        band.append((x, y))
            cv.pts(band, P.WHITE)


def nozzle(
    cv: Canvas,
    cx: int,
    top: int,
    mat: str,
    pose: int,
    erosion: float = 0.0,
    hardened: bool = False,
    feeding: bool = True,
    jitter: int = 0,
) -> tuple[int, int]:
    """Hot end with filament feeding in. Returns the nozzle tip (x, y)."""
    m = MATERIALS[mat]
    cx += jitter
    cv.rect(cx - 1, top - 12, cx, top - 1, fill=m["light"])
    if feeding:
        for k in range(3):
            yy = top - 12 + ((pose + k * 4) % 12)
            cv.px(cx - 1, yy, m["dark"])
    cv.box(cx - 8, top, cx + 7, top + 7, fill=P.STEEL2)
    cv.rect(cx - 6, top + 2, cx - 3, top + 4, fill=P.RED)
    cv.line([(cx - 7, top + 1), (cx + 6, top + 1)], P.SHINE)
    body = P.STEEL0 if hardened else P.AMBER
    edge = P.STEEL2 if hardened else P.YELLOW
    cv.box(cx - 5, top + 8, cx + 4, top + 10, fill=body)
    cut = int(round(erosion * 3))
    tip_y = top + 16 - cut
    half = 1 + cut
    cv.poly([(cx - 4, top + 11), (cx + 3, top + 11), (cx + half, tip_y), (cx - 1 - half, tip_y)], fill=body, outline=P.NAVY)
    cv.px(cx - 3, top + 12, edge)
    if erosion > 0.05 and not hardened:
        rng = np.random.default_rng(3)
        for i in range(2 + cut):
            cv.px(cx - 1 - half + int(rng.integers(0, 2 * half + 2)), tip_y + 1, P.NAVY)
    return cx, tip_y


def print_bed(cv: Canvas, cx: int, y: int, mat: str, layers: int) -> None:
    m = MATERIALS[mat]
    cv.box(cx - 15, y, cx + 14, y + 3, fill=P.NAVY2)
    for i in range(min(layers, 8)):
        yy = y - 1 - i
        cv.rect(cx - 7, yy, cx + 6, yy, fill=m["light"] if i % 2 else m["mid"])
    if layers:
        cv.px(cx - 8, y - 1, P.NAVY)
        cv.px(cx + 7, y - 1, P.NAVY)


def strand(cv: Canvas, x: int, y0: int, y1: int, mat: str) -> None:
    if y1 > y0:
        cv.rect(x - 1, y0, x, y1, fill=MATERIALS[mat]["light"])


def clog_blob(cv: Canvas, x: int, y: int, pose: int) -> None:
    wob = pose % 2
    cv.ellipse(x - 4, y, x + 4 + wob, y + 6, fill=P.WOOD0, outline=P.NAVY)
    cv.pts([(x - 2, y + 2), (x + 1, y + 1)], P.WOOD1)


def burst(cv: Canvas, cx: int, cy: int, r: int, pose: int, fill: int = P.RED, outline: int = P.NAVY) -> None:
    pts = []
    spikes = 10
    rot = (pose % 2) * math.pi / spikes
    for i in range(spikes * 2):
        rr = r if i % 2 == 0 else r * 0.62
        ang = rot + i * math.pi / spikes
        pts.append((cx + math.cos(ang) * rr * 1.25, cy + math.sin(ang) * rr * 0.8))
    cv.poly(pts, fill=fill, outline=outline)


def check(cv: Canvas, cx: int, cy: int) -> None:
    cv.circle(cx, cy, 6, fill=P.GREEN, outline=P.NAVY)
    cv.line([(cx - 3, cy), (cx - 1, cy + 2), (cx + 3, cy - 2)], P.WHITE, width=2)


def wood_block(cv: Canvas, cx: int, cy: int, rough: float, stain: float, w: int = 30, h: int = 18) -> None:
    x0, y0 = cx - w // 2, cy - h // 2
    x1, y1 = x0 + w - 1, y0 + h - 1
    cv.box(x0, y0, x1, y1, fill=P.WOOD2)
    if stain > 0:
        sx = x0 + 1 + int(round(stain * (w - 2))) - 1
        cv.rect(x0 + 1, y0 + 1, min(sx, x1 - 1), y1 - 1, fill=P.STAIN)
    for k in range(3):
        yy = y0 + 4 + k * 5
        pts = [(x, yy + round(math.sin(x / 4 + k))) for x in range(x0 + 2, x1 - 1)]
        stained = [(x, y) for x, y in pts if stain > 0 and x <= x0 + stain * (w - 2)]
        plain = [p for p in pts if p not in stained]
        cv.pts(plain, P.WOOD1)
        cv.pts(stained, P.WOOD0)
    if rough > 0:
        rng = np.random.default_rng(11)
        for _ in range(26):
            sx = int(rng.integers(x0 + 1, x1))
            sy = int(rng.integers(y0 + 1, y1))
            if rng.random() < rough:
                cv.px(sx, sy, P.WOOD0)
        for i, x in enumerate(range(x0 + 1, x1, 3)):
            if rng.random() < rough:
                cv.px(x, y0 - 1, P.WOOD2)
                cv.px(x, y0 - 2, P.NAVY)
    if stain >= 1 and rough <= 0:
        cv.line([(x0 + 2, y0 + 1), (x1 - 2, y0 + 1)], P.WOOD1)


def metal_block(cv: Canvas, cx: int, cy: int, polish: float, t: float, w: int = 30, h: int = 18) -> None:
    x0, y0 = cx - w // 2, cy - h // 2
    x1, y1 = x0 + w - 1, y0 + h - 1
    base = P.STEEL1 if polish < 0.5 else P.STEEL2
    cv.box(x0, y0, x1, y1, fill=base)
    rng = np.random.default_rng(5)
    for _ in range(30):
        sx = int(rng.integers(x0 + 1, x1))
        sy = int(rng.integers(y0 + 1, y1))
        if rng.random() > polish:
            cv.px(sx, sy, P.STEEL0)
    if polish >= 0.5:
        cv.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], P.SHINE)
        cv.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], P.STEEL1)
    if polish >= 0.95:
        u = (t % 1.0) / 0.5
        if u <= 1:
            sx = x0 - 8 + int(u * (w + 16))
            band = [(sx + off - (y - y0) // 2, y) for y in range(y0 + 2, y1 - 1) for off in range(4)]
            cv.pts([(x, y) for x, y in band if x0 + 1 < x < x1 - 1], P.WHITE)


def sandpaper(cv: Canvas, cx: int, y: int) -> None:
    cv.box(cx - 8, y - 6, cx + 7, y, fill=P.AMBER)
    cv.pts([(cx - 6 + 3 * i, y - 1) for i in range(5)], P.WOOD0)
    cv.box(cx - 5, y - 10, cx + 4, y - 7, fill=P.RED)


def cloth(cv: Canvas, cx: int, y: int) -> None:
    cv.poly([(cx - 7, y), (cx + 6, y), (cx + 4, y - 7), (cx - 5, y - 6)], fill=P.CREAM, outline=P.NAVY)
    cv.line([(cx - 3, y - 2), (cx + 2, y - 4)], P.STEEL2)


def seesaw(cv: Canvas, cx: int, cy: int, tilt: int, span: int = 42) -> None:
    cv.poly([(cx - 8, cy + 12), (cx + 7, cy + 12), (cx, cy + 1)], fill=P.STEEL0, outline=P.NAVY)
    cv.rect(cx - 11, cy + 12, cx + 10, cy + 14, fill=P.NAVY)
    ends = [(cx - span, cy - tilt), (cx + span, cy + tilt)]
    cv.line(ends, P.NAVY, width=5)
    cv.line(ends, P.WOOD2, width=3)
    cv.circle(cx, cy, 2, fill=P.STEEL2, outline=P.NAVY)


def plank_y(cx: int, cy: int, tilt: int, x: int, span: int = 42) -> int:
    return int(round(cy + tilt * (x - cx) / span))


def cube(cv: Canvas, cx: int, bottom: int, mat: str, w: int = 14, h: int = 11) -> None:
    m = MATERIALS[mat]
    x0, x1 = cx - w // 2, cx - w // 2 + w - 1
    y0 = bottom - h + 1
    cv.box(x0, y0, x1, bottom, fill=m["light"])
    cv.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], P.SHINE if mat == "metal" else P.AMBER)
    if mat == "metal":
        for rx in (x0 + 2, x1 - 2):
            cv.px(rx, y0 + 3, P.STEEL0)
            cv.px(rx, bottom - 2, P.STEEL0)
    else:
        cv.line([(x0 + 2, y0 + 5), (x1 - 2, y0 + 6)], m["mid"])


def sign(cv: Canvas, cx: int, cy: int) -> None:
    cv.rect(cx - 7, cy, cx - 6, cy + 5, fill=P.WOOD0)
    cv.rect(cx + 5, cy, cx + 6, cy + 5, fill=P.WOOD0)
    cv.box(cx - 10, cy - 8, cx + 9, cy + 2, fill=P.WOOD2)
    cv.line([(cx - 7, cy - 5), (cx + 2, cy - 5)], P.WOOD0)
    cv.line([(cx - 7, cy - 2), (cx + 5, cy - 2)], P.WOOD0)


def vase(cv: Canvas, cx: int, cy: int) -> None:
    cv.ellipse(cx - 6, cy - 3, cx + 5, cy + 9, fill=P.WOOD2, outline=P.NAVY)
    cv.box(cx - 3, cy - 8, cx + 2, cy - 2, fill=P.WOOD1)
    cv.line([(cx - 5, cy + 3), (cx + 4, cy + 3)], P.STAIN)
    cv.line([(cx - 1, cy - 9), (cx - 3, cy - 11)], P.GREEN)
    cv.line([(cx, cy - 9), (cx + 2, cy - 12)], P.GREEN)


def knob(cv: Canvas, cx: int, cy: int) -> None:
    cv.rect(cx - 1, cy + 5, cx, cy + 10, fill=P.STEEL0)
    cv.circle(cx, cy, 6, fill=P.STEEL2, outline=P.NAVY)
    cv.line([(cx, cy - 4), (cx, cy - 1)], P.STEEL0)
    cv.pts([(cx - 3, cy - 3), (cx - 2, cy - 4)], P.WHITE)


def trophy(cv: Canvas, cx: int, cy: int) -> None:
    cv.ellipse(cx - 9, cy - 8, cx - 3, cy - 2, fill=P.NAVY)
    cv.ellipse(cx - 8, cy - 7, cx - 4, cy - 3, fill=P.STEEL1)
    cv.ellipse(cx + 2, cy - 8, cx + 8, cy - 2, fill=P.NAVY)
    cv.ellipse(cx + 3, cy - 7, cx + 7, cy - 3, fill=P.STEEL1)
    cv.poly([(cx - 6, cy - 9), (cx + 5, cy - 9), (cx + 3, cy + 1), (cx - 4, cy + 1)], fill=P.STEEL2, outline=P.NAVY)
    cv.box(cx - 2, cy + 1, cx + 1, cy + 6, fill=P.STEEL2)
    cv.box(cx - 5, cy + 6, cx + 4, cy + 9, fill=P.STEEL0)
    cv.pts([(cx - 4, cy - 7), (cx - 4, cy - 6), (cx - 3, cy - 5)], P.WHITE)


def crown(cv: Canvas, cx: int, y: int) -> None:
    cv.poly(
        [(cx - 6, y + 5), (cx - 6, y), (cx - 3, y + 3), (cx, y - 1), (cx + 3, y + 3), (cx + 6, y), (cx + 6, y + 5)],
        fill=P.YELLOW,
        outline=P.NAVY,
    )
    cv.px(cx, y + 3, P.RED)


def up_arrow(cv: Canvas, cx: int, y: int) -> None:
    cv.poly([(cx, y), (cx - 3, y + 3), (cx + 3, y + 3)], fill=P.CREAM, outline=P.NAVY)
    cv.rect(cx - 1, y + 4, cx, y + 6, fill=P.CREAM)


def vs_badge(cv: Canvas, cx: int, cy: int, big: bool, flash: bool = False) -> None:
    if big:
        r = 13
        pts = [(cx + math.cos(a) * r, cy + math.sin(a) * r) for a in np.linspace(0, 2 * math.pi, 9)[:-1] + math.pi / 8]
        cv.poly(pts, fill=P.YELLOW if flash else P.RED, outline=P.NAVY)
        inner = [(cx + math.cos(a) * (r - 3), cy + math.sin(a) * (r - 3)) for a in np.linspace(0, 2 * math.pi, 9)[:-1] + math.pi / 8]
        cv.poly(inner, outline=P.RED if flash else P.YELLOW)
        cv.text("VS", cx, cy - 6, color=P.CREAM if flash else P.YELLOW, scale=2, kind="badge", clamp=False)
    else:
        cv.box(cx - 9, cy - 6, cx + 8, cy + 6, fill=P.RED)
        cv.rect(cx - 8, cy - 5, cx + 7, cy - 5, fill=P.YELLOW)
        cv.text("VS", cx, cy - 3, color=P.CREAM, kind="badge", clamp=False)


def flex_bar(cv: Canvas, cx: int, y0: int, bend: int, mat: str = "tpu", length: int = 26) -> None:
    """A vertical bar. `bend` bows it sideways, in canvas pixels."""
    m = MATERIALS[mat]
    for i in range(length):
        off = round(math.sin(i / (length - 1) * math.pi) * bend)
        x = cx + off
        y = y0 + i
        cv.pts([(x - 2, y), (x + 2, y)], P.NAVY)
        cv.pts([(x - 1, y), (x, y)], m["light"])
        cv.px(x + 1, y, m["mid"])
    cv.pts([(cx - 1, y0), (cx, y0), (cx + 1, y0)], P.NAVY)


def rigid_bar(cv: Canvas, cx: int, y0: int, mat: str = "abs", length: int = 26) -> None:
    m = MATERIALS[mat]
    cv.box(cx - 3, y0, cx + 3, y0 + length, fill=m["light"])
    cv.line([(cx - 2, y0 + 1), (cx + 2, y0 + 1)], P.WHITE)
    cv.line([(cx - 2, y0 + length - 1), (cx + 2, y0 + length - 1)], m["mid"])


def ooze(cv: Canvas, x: int, y0: int, y1: int, pose: int, mat: str = "tpu") -> None:
    color = MATERIALS[mat]["light"]
    for strand in range(3):
        pts = []
        for y in range(y0, y1, 2):
            pts.append((x - 3 + strand * 3 + round(math.sin((y + pose * 3 + strand) / 2) * 2), y))
        cv.pts(pts, color if strand != 1 else MATERIALS[mat]["mid"])


def warp_part(cv: Canvas, cx: int, bed_y: int, lift: int, mat: str = "abs") -> None:
    m = MATERIALS[mat]
    cv.box(cx - 15, bed_y, cx + 14, bed_y + 3, fill=P.NAVY2)
    for i in range(8):
        rise = int(round(lift * (i / 7)))
        y = bed_y - 1 - i
        cv.line([(cx - 10, y - rise), (cx + 8, y)], m["light"] if i % 2 else m["mid"], width=1)
    if lift:
        cv.px(cx - 10, bed_y - 8 - lift, P.NAVY)
        cv.px(cx - 9, bed_y - 7 - lift, P.RED)


def grip_pad(cv: Canvas, cx: int, cy: int) -> None:
    m = MATERIALS["tpu"]
    cv.box(cx - 12, cy - 8, cx + 11, cy + 8, fill=m["mid"])
    for row in range(3):
        for col in range(4):
            cv.circle(cx - 8 + col * 5, cy - 4 + row * 5, 1, fill=m["dark"])


def plastic_block(cv: Canvas, cx: int, cy: int, rough: float, shine: float) -> None:
    m = MATERIALS["abs"]
    x0, y0, x1, y1 = cx - 14, cy - 9, cx + 13, cy + 8
    cv.box(x0, y0, x1, y1, fill=m["light"] if shine > 0.4 else m["mid"])
    rng = np.random.default_rng(4)
    for _ in range(24):
        sx = int(rng.integers(x0 + 1, x1))
        sy = int(rng.integers(y0 + 1, y1))
        if rng.random() < rough:
            cv.px(sx, sy, m["dark"])
    if shine > 0.4:
        cv.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], P.WHITE)
    if shine >= 1:
        cv.line([(x0 + 3, y0 + 3), (x1 - 4, y0 + 3)], P.SHINE)


def phone_case(cv: Canvas, cx: int, cy: int) -> None:
    m = MATERIALS["tpu"]
    cv.box(cx - 7, cy - 11, cx + 7, cy + 10, fill=m["light"])
    cv.rect(cx - 2, cy - 8, cx + 2, cy - 5, fill=P.NAVY)
    cv.px(cx, cy + 7, m["dark"])


def grip_handle(cv: Canvas, cx: int, cy: int) -> None:
    """A ribbed sleeve, the sort of grip you print in a soft filament."""
    m = MATERIALS["tpu"]
    cv.box(cx - 2, cy - 10, cx + 2, cy + 8, fill=m["dark"])
    for y in range(cy - 8, cy + 7, 3):
        cv.rect(cx - 6, y, cx + 6, y + 1, fill=m["light"])


def bracket(cv: Canvas, cx: int, cy: int) -> None:
    m = MATERIALS["abs"]
    cv.box(cx - 10, cy + 2, cx + 8, cy + 7, fill=m["light"])
    cv.box(cx - 10, cy - 10, cx - 5, cy + 7, fill=m["light"])
    cv.px(cx - 8, cy - 6, P.NAVY)
    cv.px(cx + 4, cy + 4, P.NAVY)


def shell(cv: Canvas, cx: int, cy: int) -> None:
    m = MATERIALS["abs"]
    cv.box(cx - 9, cy - 8, cx + 8, cy + 7, fill=P.NAVY)
    cv.rect(cx - 7, cy - 6, cx + 6, cy + 5, fill=m["light"])
    cv.line([(cx - 7, cy - 6), (cx + 6, cy - 6)], P.WHITE)


def bat(cv: Canvas, cx: int, cy: int, pose: int) -> None:
    wing = 5 if pose % 2 == 0 else 2
    cy += pose % 2
    cv.line([(cx - 1, cy), (cx - wing, cy - wing)], P.NAVY)
    cv.line([(cx + 1, cy), (cx + wing, cy - wing)], P.NAVY)
    cv.pts([(cx - 1, cy), (cx, cy), (cx + 1, cy), (cx, cy + 1)], P.NAVY)
    cv.px(cx - 1, cy, P.RED)


def night_bits(cv: Canvas, pose: int) -> None:
    """Bats and blinking stars, so a quiet beat still moves."""
    stars = ((6, 50), (18, 72), (100, 46), (92, 68), (10, 100), (98, 96))
    for i, (x, y) in enumerate(stars):
        if (pose + i) % 3 != 0:
            cv.px(x, y, P.WHITE if i % 2 == 0 else P.CREAM)
    bat(cv, 10 + (pose % 8), 84, pose)
    bat(cv, 96 - (pose % 6), 76, pose + 1)


def workshop_bed(cv: Canvas, y: int = 122) -> None:
    cv.box(14, y, 93, y + 5, fill=P.STEEL0, outline=P.NAVY)
    cv.line([(15, y), (92, y)], P.STEEL2)
    cv.line([(15, y + 1), (92, y + 1)], P.SHINE)


def jack_o_lantern(
    cv: Canvas,
    cx: int,
    base: int,
    rows: int,
    eyes: bool = False,
    grin: bool = False,
    stem: bool = False,
    glow: bool = False,
    pose: int = 0,
) -> None:
    """A pumpkin built from horizontal print layers, bottom up."""
    rows = max(0, min(34, int(rows)))
    for i in range(rows):
        y = base - i
        ny = (i - 16.5) / 17.0
        half = max(2, int(round(18 * math.sqrt(max(0.0, 1.0 - ny * ny)))))
        col = P.WOOD2 if (i // 2) % 2 == 0 else P.WOOD1
        cv.line([(cx - half, y), (cx + half, y)], col)
        cv.px(cx - half, y, P.NAVY)
        cv.px(cx + half, y, P.NAVY)
        rib = max(2, half // 2)
        cv.px(cx - rib, y, P.WOOD0)
        cv.px(cx + rib, y, P.WOOD0)
        if glow and 6 < i < 28 and half > 5:
            hot = P.YELLOW if pose % 2 == 0 else P.AMBER
            cv.line([(cx - half + 4, y), (cx + half - 4, y)], hot)
    if eyes and rows > 22:
        lit = P.YELLOW if glow else P.NAVY
        _pumpkin_eye(cv, cx - 8, base - 24, lit)
        _pumpkin_eye(cv, cx + 8, base - 24, lit)
    if grin and rows > 14:
        lit = P.YELLOW if glow else P.NAVY
        _pumpkin_grin(cv, cx, base - 12, lit)
    if stem and rows >= 34:
        top = base - 33
        cv.rect(cx - 2, top - 8, cx + 1, top, fill=P.GREEN)
        cv.px(cx - 2, top - 7, P.NAVY)
        cv.rect(cx + 1, top - 6, cx + 8, top - 4, fill=P.GREEN)
        cv.px(cx + 5, top - 7, P.STAIN)


def _pumpkin_eye(cv: Canvas, cx: int, cy: int, color: int) -> None:
    cv.poly([(cx, cy - 4), (cx + 4, cy + 2), (cx - 4, cy + 2)], fill=color, outline=P.NAVY)


def _pumpkin_grin(cv: Canvas, cx: int, cy: int, color: int) -> None:
    cv.poly([(cx - 10, cy - 2), (cx + 10, cy - 2), (cx + 6, cy + 3), (cx - 6, cy + 3)], fill=color, outline=P.NAVY)
    for x in (cx - 6, cx, cx + 6):
        cv.line([(x, cy - 2), (x, cy + 2)], P.NAVY)


def printing_nozzle(cv: Canvas, cx: int, base: int, rows: int, pose: int) -> None:
    top = base - max(rows, 0)
    nx = cx + int(round(math.sin(pose / 2.0) * 14))
    tip_x, tip_y = nozzle(cv, nx, max(36, top - 20), "pumpkin", pose, hardened=True)
    if rows < 34 and tip_y < top:
        strand(cv, tip_x, tip_y, top, "pumpkin")
