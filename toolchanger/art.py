"""Palette, canvas and small drawing helpers. Everything is drawn on a 108x192 canvas
with flat colours only; the render step upscales it 10x with nearest-neighbour."""
from PIL import Image, ImageDraw

from pipeline.font import GLYPHS, text_width

W, H, SCALE = 108, 192, 10

HEX = {
    "k0": "#07090f", "k1": "#0f1420", "k2": "#1a2233", "k3": "#2c3a54",
    "b0": "#1546e0", "b1": "#2e8cff", "b2": "#8fd0ff",
    "w": "#f4f8ff", "g0": "#aeb9cc", "g1": "#5d6a82",
    "red": "#ff3048", "orange": "#ff8a1c", "yellow": "#ffd81a", "lime": "#a4e22d",
    "green": "#1fcf6a", "cyan": "#1fd8e6", "blue": "#4a72ff", "violet": "#a253ff",
    "magenta": "#ff5cc8",
}
COL = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in HEX.items()}
HEADS = ["red", "orange", "yellow", "lime", "green", "cyan", "blue", "violet", "magenta"]

# TikTok safe zones in canvas pixels (x10 = output pixels)
SAFE_TOP, SAFE_BOTTOM = 23, 153           # y>=230, y<=1536
STRIP_X, STRIP_Y0, STRIP_Y1 = 90, 80, 150  # x>900, y 800-1500
LABEL_BOTTOM = 138                        # non-caption text ends above y=1380
CAPTION_Y = 145                           # captions near y=1450


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), COL["k1"])
        self.d = ImageDraw.Draw(self.img)
        self.boxes = []

    def rect(self, x0, y0, x1, y1, col):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        self.d.rectangle([x0, y0, x1, y1], fill=COL[col])

    def px(self, x, y, col):
        if 0 <= x < W and 0 <= y < H:
            self.img.putpixel((x, y), COL[col])

    def line(self, x0, y0, x1, y1, col):
        self.d.line([x0, y0, x1, y1], fill=COL[col])

    def box(self, x0, y0, x1, y1, fill, outline="k0"):
        self.rect(x0, y0, x1, y1, outline)
        if x1 - x0 > 1 and y1 - y0 > 1:
            self.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)

    def _glyphs(self, s, x, y, col, scale):
        cx = x
        for ch in s:
            g = GLYPHS[ch]
            for j, row in enumerate(g):
                for i, v in enumerate(row):
                    if v == "#":
                        self.rect(cx + i * scale, y + j * scale,
                                  cx + (i + 1) * scale - 1, y + (j + 1) * scale - 1, col)
            cx += (len(g[0]) + 1) * scale

    def text(self, s, x, y, col, scale=1, kind="ui", shadow=True, rec=True):
        s = s.upper()
        w, h = text_width(s, scale), 7 * scale
        if shadow:
            self._glyphs(s, x + 1, y + 1, "k0", scale)
        self._glyphs(s, x, y, col, scale)
        if rec:
            self.boxes.append(dict(kind=kind, text=s, x0=x, y0=y,
                                   x1=x + w - 1 + int(shadow), y1=y + h - 1 + int(shadow)))
        return w

    def text_center(self, s, cx, y, col, scale=1, **kw):
        return self.text(s, cx - text_width(s, scale) // 2, y, col, scale, **kw)

    def upscaled(self):
        return self.img.resize((W * SCALE, H * SCALE), Image.NEAREST).tobytes()


def fit_scale(s, maxw, smax):
    for sc in range(smax, 0, -1):
        if text_width(s, sc) <= maxw:
            return sc
    return 1


def headline(c, lines, col="w", y=26, smax=3, gap=2, cx=54, mixed=False):
    """Stacked big headline; it sits above y=800 so the full width is usable.
    Lines share one scale unless mixed=True."""
    common = min(fit_scale(s, 104, smax) for s in lines)
    for line in lines:
        sc = fit_scale(line, 104, smax) if mixed else common
        c.text_center(line, cx, y, col, sc, kind="headline")
        y += 7 * sc + gap
    return y


def label(c, lines, cx, y, fg="w", bg="b0", smax=2, maxw=80):
    sc = min(fit_scale(s, maxw, smax) for s in lines)
    w = max(text_width(s, sc) for s in lines) + 6
    h = len(lines) * 7 * sc + (len(lines) - 1) * 2 + 6
    x0 = cx - w // 2
    c.box(x0, y, x0 + w - 1, y + h - 1, bg)
    yy = y + 3
    for s in lines:
        c.text_center(s, cx, yy, fg, sc, kind="label", shadow=False)
        yy += 7 * sc + 2
    return h


def head(c, x, y, col):
    """Tool head 8 wide, 14 tall (tip at y+13)."""
    c.rect(x, y, x + 7, y + 10, "k0")
    c.rect(x + 1, y + 1, x + 6, y + 9, col)
    c.rect(x + 1, y + 1, x + 6, y + 2, "g1")
    c.rect(x + 1, y + 11, x + 6, y + 12, "k0")
    c.rect(x + 2, y + 11, x + 5, y + 12, "g0")
    c.rect(x + 3, y + 13, x + 4, y + 13, "g1")


def background(c, progress):
    c.rect(0, 0, W - 1, H - 1, "k1")
    for y in range(26, 138, 6):
        for x in range(3, W, 6):
            c.px(x, y, "k3")
    c.rect(0, 0, W - 1, 21, "k0")
    c.rect(0, 22, W - 1, 22, "b0")
    for i in range(3):
        c.rect(5 + i * 5, 8, 7 + i * 5, 10, "k3")
    c.rect(24, 8, 101, 10, "k2")
    c.rect(24, 8, 24 + int(77 * progress), 10, "b1")
    c.rect(24, 8, 24 + int(77 * progress), 8, "b2")
    for x in range(24, 102, 8):
        c.px(x, 13, "g1")
    c.rect(0, 139, W - 1, H - 1, "k0")
    c.rect(0, 139, W - 1, 139, "k2")


def bench(c, y=118):
    c.rect(0, y, W - 1, y, "b1")
    c.rect(0, y + 1, W - 1, y + 1, "b0")
    c.rect(0, y + 2, W - 1, y + 9, "k2")
    c.rect(0, y + 10, W - 1, y + 10, "k0")
