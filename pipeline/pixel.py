"""Pillow canvas helpers: palette-only drawing on 108x192, exact 10x NEAREST upscale."""
from PIL import Image, ImageDraw

from . import config as C
from .font import GLYPHS, text_width
from .sprites import CHARS, ICONS

PAL = C.PALETTE
DARK = {3: 4, 4: 5, 6: 7, 8: 9, 10: 15, 11: 7, 12: 6, 13: 14}


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (C.W, C.H), PAL[0])
        self.d = ImageDraw.Draw(self.img)
        self.boxes = []

    def rect(self, x0, y0, x1, y1, col):
        self.d.rectangle([x0, y0, x1, y1], fill=PAL[col])

    def px(self, x, y, col):
        if 0 <= x < C.W and 0 <= y < C.H:
            self.img.putpixel((x, y), PAL[col])

    def line(self, x0, y0, x1, y1, col, width=1):
        self.d.line([(x0, y0), (x1, y1)], fill=PAL[col], width=width)

    def circle(self, cx, cy, r, col, fill=False):
        box = [cx - r, cy - r, cx + r, cy + r]
        if fill:
            self.d.ellipse(box, fill=PAL[col])
        else:
            self.d.ellipse(box, outline=PAL[col])

    def sprite(self, name, cx, cy, scale, tint=(6, 7), ghost=False, recolor=None, shade=True):
        """Draw an icon centred on (cx, cy). Silhouette edges get a darker rim on the
        bottom/right and a dotted highlight on the top/left so shapes read as solid."""
        art = ICONS[name]
        rows, cols = len(art) * scale, len(art[0]) * scale
        x0, y0 = cx - cols // 2, cy - rows // 2
        grid = [[None] * cols for _ in range(rows)]
        for j, row in enumerate(art):
            for i, ch in enumerate(row):
                if ch == ".":
                    continue
                if ghost:
                    col = 5
                elif recolor is not None:
                    col = recolor[1] if ch == "A" else recolor[0]
                elif ch == "a":
                    col = tint[0]
                elif ch == "A":
                    col = tint[1]
                else:
                    col = CHARS[ch]
                for dy in range(scale):
                    for dx in range(scale):
                        grid[j * scale + dy][i * scale + dx] = col

        def empty(x, y):
            return not (0 <= y < rows and 0 <= x < cols) or grid[y][x] is None

        main = (recolor[0] if recolor else tint[0])
        dark = (recolor[1] if recolor else tint[1])
        for y in range(rows):
            for x in range(cols):
                col = grid[y][x]
                if col is None:
                    continue
                if shade and not ghost:
                    if empty(x, y + 1) or empty(x + 1, y):
                        col = dark if col == main else DARK.get(col, col)
                    elif (empty(x, y - 1) or empty(x - 1, y)) and (x + y) % 2 == 0:
                        col = 3 if col != 3 else 4
                self.px(x0 + x, y0 + y, col)

    def text(self, s, x, y, col, scale=1, kind="voice", shadow=True, clamp=True):
        s = s.upper()
        w = text_width(s, scale)
        h = 7 * scale
        ext = w + (scale if shadow else 0)
        if clamp:
            x = max(2, min(x, C.W - 2 - ext))
            if y + h + (scale if shadow else 0) > C.STRIP_Y0 and y <= C.STRIP_Y1 \
                    and x + ext >= C.STRIP_X:
                x = max(2, C.STRIP_X - ext - 1)  # 1px spare for screen shake
        if shadow:
            self._glyphs(s, x + scale, y + scale, 0, scale)
        self._glyphs(s, x, y, col, scale)
        self.boxes.append({"kind": kind, "text": s, "x0": x, "y0": y,
                           "x1": x + w - 1 + (scale if shadow else 0),
                           "y1": y + h - 1 + (scale if shadow else 0)})
        return x, w

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

    def text_center(self, s, cx, y, col, scale=1, **kw):
        return self.text(s, cx - text_width(s, scale) // 2, y, col, scale, **kw)

    def shift(self, dx, dy):
        if not (dx or dy):
            return
        out = Image.new("RGB", self.img.size, PAL[0])
        out.paste(self.img, (dx, dy))
        self.img = out
        self.d = ImageDraw.Draw(out)
        for b in self.boxes:
            b["x0"] += dx
            b["x1"] += dx
            b["y0"] += dy
            b["y1"] += dy

    def upscaled_bytes(self):
        return self.img.resize((C.OUT_W, C.OUT_H), Image.NEAREST).tobytes()

    def color_count(self):
        return len(self.img.getcolors(maxcolors=256) or [])
