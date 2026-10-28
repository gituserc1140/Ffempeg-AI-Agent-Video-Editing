"""Pixel drawing helpers for the 108x192 canvas.

Every primitive goes through Pillow ImageDraw on a palette ("P") image,
which never anti-aliases. Text is placed through `Canvas.text`, which keeps
it inside the TikTok safe zones and records where it landed for QC.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

from . import palette as P
from .font import text_height, text_points, text_width

W, H = 108, 192
SCALE = 10
OUT_W, OUT_H = W * SCALE, H * SCALE
FPS = 30
POSE_FPS = 12

# TikTok UI safe zones in output pixels.
SAFE_TOP = 230
SAFE_BOTTOM = 1536
STRIP_X = 900
STRIP_Y0, STRIP_Y1 = 800, 1500

SPLIT_X = 54
SHAKE_MARGIN = 2


def split_x(y: int) -> int:
    """x of the jagged centre seam at row y."""
    k = y % 12
    return SPLIT_X - 3 + (k if k <= 6 else 12 - k)


@dataclass
class TextRecord:
    text: str
    box: tuple[int, int, int, int]
    kind: str
    color: int
    owner: str = ""


@dataclass
class Canvas:
    img: Image.Image
    texts: list[TextRecord] = field(default_factory=list)
    owner: str = ""

    def __post_init__(self) -> None:
        self.d = ImageDraw.Draw(self.img)

    @classmethod
    def from_background(cls, bg: Image.Image) -> "Canvas":
        return cls(bg.copy())

    def rect(self, x0, y0, x1, y1, fill=None, outline=None) -> None:
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        if x1 < x0 or y1 < y0:
            return
        self.d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline)

    def box(self, x0, y0, x1, y1, fill, outline=P.NAVY) -> None:
        self.rect(x0, y0, x1, y1, fill=fill, outline=outline)

    def circle(self, cx, cy, r, fill=None, outline=None) -> None:
        cx, cy, r = int(round(cx)), int(round(cy)), int(round(r))
        if r <= 0:
            self.px(cx, cy, fill if fill is not None else outline)
            return
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None) -> None:
        self.d.ellipse([int(x0), int(y0), int(x1), int(y1)], fill=fill, outline=outline)

    def poly(self, points, fill=None, outline=None) -> None:
        pts = [(int(round(x)), int(round(y))) for x, y in points]
        self.d.polygon(pts, fill=fill, outline=outline)

    def line(self, points, fill, width=1) -> None:
        pts = [(int(round(x)), int(round(y))) for x, y in points]
        self.d.line(pts, fill=fill, width=width)

    def px(self, x, y, color) -> None:
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H and color is not None:
            self.d.point((x, y), fill=color)

    def pts(self, points, color) -> None:
        inside = [(int(x), int(y)) for x, y in points if 0 <= x < W and 0 <= y < H]
        if inside:
            self.d.point(inside, fill=color)

    def text(
        self,
        text: str,
        cx: float,
        y: int,
        color: int = P.CREAM,
        scale: int = 1,
        outline: int | None = P.NAVY,
        kind: str = "label",
        align: str = "center",
        margin: int = SHAKE_MARGIN,
        plaque: int | None = None,
        clamp: bool = True,
    ) -> TextRecord:
        """Draw outlined bitmap text and record its bounding box.

        `margin` is extra canvas pixels kept clear of the safe-zone edges, so
        screen shake cannot push the text across them. With `plaque` set, a
        filled box is drawn one pixel outside the outline.
        """
        w = text_width(text, scale)
        h = text_height(scale)
        x = int(round(cx - w / 2)) if align == "center" else int(round(cx))
        y = int(round(y))
        px_pad, py_pad = (3, 2) if plaque is not None else (1, 1)
        if clamp:
            x, y = safe_place(x, y, w, h, px_pad + margin, py_pad + margin)
        if plaque is not None:
            self.box(x - 3, y - 2, x + w + 2, y + h + 1, fill=plaque, outline=P.NAVY)
        points = text_points(text, x, y, scale)
        if outline is not None:
            ring = {(px + dx, py + dy) for px, py in points for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            self.pts(ring, outline)
        self.pts(points, color)
        record = TextRecord(
            text, (x - px_pad, y - py_pad, x + w - 1 + px_pad, y + h - 1 + py_pad), kind, color, self.owner
        )
        self.texts.append(record)
        return record


def safe_place(x: int, y: int, w: int, h: int, xpad: int, ypad: int) -> tuple[int, int]:
    """Shift a text box so it, plus padding, stays inside the safe zones."""
    top = SAFE_TOP // SCALE
    bottom = SAFE_BOTTOM // SCALE - 1
    y = max(y, top + ypad)
    y = min(y, bottom - ypad - h + 1)
    x = max(x, xpad)
    x = min(x, W - 1 - xpad - w + 1)
    y0, y1 = y - ypad, y + h - 1 + ypad
    if (y1 + 1) * SCALE > STRIP_Y0 and y0 * SCALE < STRIP_Y1:
        right = STRIP_X // SCALE - 1
        x = min(x, right - xpad - w + 1)
    return x, y


def box_violations(box: tuple[int, int, int, int]) -> list[str]:
    """Safe-zone and clipping problems for a canvas-space text box."""
    x0, y0, x1, y1 = box
    issues = []
    if y0 * SCALE < SAFE_TOP:
        issues.append("top UI zone")
    if (y1 + 1) * SCALE > SAFE_BOTTOM:
        issues.append("bottom UI zone")
    if (x1 + 1) * SCALE > STRIP_X and (y1 + 1) * SCALE > STRIP_Y0 and y0 * SCALE < STRIP_Y1:
        issues.append("right button strip")
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H:
        issues.append("clipped by frame edge")
    return issues


def build_background(seed: int = 7) -> Image.Image:
    """Static split background: wood planks left, riveted steel right."""
    rng = np.random.default_rng(seed)
    a = np.zeros((H, W), np.uint8)
    seam = np.array([split_x(y) for y in range(H)])
    cols = np.arange(W)[None, :]
    left = cols < seam[:, None]
    a[left] = P.WOOD1
    a[~left] = P.STEEL1

    for k in range(8):
        base = 3 + k * 7
        for y in range(H):
            x = int(round(base + 1.6 * math.sin(y / 11 + k * 1.7) + 0.8 * math.sin(y / 4.3 + k)))
            if 0 <= x < seam[y] - 2:
                a[y, x] = P.WOOD0
            if 0 <= x + 1 < seam[y] - 2 and (y + k) % 3 == 0:
                a[y, x + 1] = P.WOOD2
    for _ in range(140):
        y = int(rng.integers(0, H))
        x = int(rng.integers(0, max(1, seam[y] - 2)))
        a[y, x] = P.WOOD2 if rng.random() < 0.6 else P.WOOD0

    for y in range(H):
        for x in range(seam[y] + 2, W):
            if rng.random() < 0.025:
                run = int(rng.integers(2, 5))
                a[y, x : min(W, x + run)] = P.STEEL2 if rng.random() < 0.55 else P.STEEL0
    for seam_y in (46, 94, 142, 190):
        for y_off, color in ((0, P.STEEL0), (1, P.STEEL2)):
            yy = seam_y + y_off
            if yy < H:
                a[yy, seam[yy] + 2 :] = color
        for rx in (62, 100):
            for ry in (seam_y - 4, seam_y + 4):
                if 0 <= ry < H - 1:
                    a[ry : ry + 2, rx : rx + 2] = P.STEEL2
                    a[ry + 1, rx + 1] = P.STEEL0

    for y in range(H):
        a[y, seam[y] - 1 : seam[y] + 2] = P.NAVY

    img = Image.fromarray(a, mode="P")
    img.putpalette(P.FLAT)
    d = ImageDraw.Draw(img)
    for kx, ky in ((14, 84), (38, 150), (10, 34), (34, 120)):
        d.ellipse([kx - 3, ky - 5, kx + 3, ky + 5], fill=P.WOOD1, outline=P.WOOD0)
        d.ellipse([kx - 1, ky - 2, kx + 1, ky + 2], fill=P.WOOD0)
    return img


def to_output(img: Image.Image) -> Image.Image:
    return img.convert("RGB").resize((OUT_W, OUT_H), Image.Resampling.NEAREST)


def shaken(img: Image.Image, bg: Image.Image, dx: int, dy: int) -> Image.Image:
    if not dx and not dy:
        return img
    out = bg.copy()
    out.paste(img, (dx, dy))
    return out


def pose_of_frame(frame: int) -> int:
    """30 fps frames held 3,2,3,2... so poses change at 12 per second."""
    return (frame * 2) // 5


def pose_time(pose: int) -> float:
    return pose / POSE_FPS


def poses_since(t: float, t0: float) -> int:
    return int(math.floor((t - t0) * POSE_FPS + 1e-6))


def ease_out(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def ease_in(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * u


def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def pop_dy(t: float, t0: float) -> int | None:
    """Vertical offset for an element popping in at t0; None before it appears."""
    n = poses_since(t, t0)
    if n < 0:
        return None
    return (-2, -1)[n] if n < 2 else 0


def sparkle(cv: Canvas, x: int, y: int, phase: int, color: int = P.WHITE, size: int = 2) -> None:
    """A four-pose twinkle loop."""
    p = phase % 4
    if p == 0:
        cv.px(x, y, color)
    elif p == 1:
        cv.pts([(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], color)
    elif p == 2:
        arm = [(x + i, y) for i in range(-size, size + 1)] + [(x, y + i) for i in range(-size, size + 1)]
        cv.pts(arm, P.SHINE if color == P.WHITE else color)
        cv.px(x, y, P.WHITE)
    else:
        cv.pts([(x - 1, y - 1), (x + 1, y + 1), (x - 1, y + 1), (x + 1, y - 1)], color)


def particles(
    cv: Canvas,
    t: float,
    t0: float,
    x: float,
    y: float,
    seed: int,
    colors: tuple[int, ...],
    count: int = 10,
    speed: float = 40.0,
    life: float = 0.5,
    gravity: float = 60.0,
    spread: tuple[float, float] = (0.0, 2 * math.pi),
) -> None:
    dt = t - t0
    if dt < 0 or dt > life:
        return
    rng = np.random.default_rng(seed)
    for i in range(count):
        ang = rng.uniform(*spread)
        v = speed * rng.uniform(0.5, 1.0)
        px = x + math.cos(ang) * v * dt
        py = y + math.sin(ang) * v * dt + 0.5 * gravity * dt * dt
        if dt < life * rng.uniform(0.6, 1.0):
            cv.px(px, py, colors[i % len(colors)])


def shine_streak(cv: Canvas, t: float, period: float = 3.0, sweep: float = 0.6) -> None:
    """Diagonal shine that sweeps across the metal half every `period` seconds."""
    u = (t % period) / sweep
    if u > 1:
        return
    x0 = int(lerp(40, 130, u))
    pts_a, pts_b = [], []
    for y in range(H):
        xs = x0 - (y // 2)
        for off, bucket in ((0, pts_a), (1, pts_a), (2, pts_b), (-1, pts_b)):
            x = xs + off
            if split_x(y) + 2 <= x < W:
                bucket.append((x, y))
    cv.pts(pts_b, P.STEEL2)
    cv.pts(pts_a, P.SHINE)
