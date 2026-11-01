"""Scene drawing. Every scene is a pure function of time: scene(c, plan, t, tp, t0, t1)."""
import math

from . import art
from .art import Canvas, head, label, headline, bench, HEADS

BEAM_Y, HEAD_Y, PARK_Y = 82, 86, 66
OBJ_X0, OBJ_X1 = 53, 74
PILE_CX = 20


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ramp(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, k):
    return a + (b - a) * k


def pose_idx(t):
    return int(t * 12)


# ---------- shared pieces ----------
def printer(c, hx, hcol, hy=HEAD_Y, carriage=True):
    c.rect(2, BEAM_Y, 4, 117, "k3")
    c.rect(103, BEAM_Y, 105, 117, "k3")
    c.rect(2, BEAM_Y, 105, BEAM_Y + 2, "k3")
    c.rect(2, BEAM_Y, 105, BEAM_Y, "b1")
    if hcol:
        head(c, hx, hy, hcol)
    if carriage:
        c.rect(hx - 1, BEAM_Y - 2, hx + 8, BEAM_Y + 3, "k0")
        c.rect(hx, BEAM_Y - 1, hx + 7, BEAM_Y + 2, "g1")
        c.rect(hx, BEAM_Y - 1, hx + 7, BEAM_Y - 1, "g0")


def obj(c, red_h, blue_h):
    total = red_h + blue_h
    if total <= 0:
        return
    c.rect(OBJ_X0 - 1, 117 - total, OBJ_X1 + 1, 117, "k0")
    if red_h:
        c.rect(OBJ_X0, 118 - red_h, OBJ_X1, 117, "red")
    if blue_h:
        c.rect(OBJ_X0, 118 - total, OBJ_X1, 117 - red_h, "blue")


def tray(c):
    c.rect(6, 114, 36, 117, "k0")
    c.rect(7, 115, 35, 117, "k3")
    c.rect(7, 115, 35, 115, "g1")


def pile(c, h, cols=None, flash=False, ghost=False):
    """Mound standing in the tray; rows are coloured by when they were purged."""
    h = int(h)
    for r in range(h):
        hw = max(1, int(round((4 + 8 * min(1, h / 11)) * (1 - r / (h + 1)))))
        f = r / 11
        col = "g0" if ghost else ("red" if f < 0.34 else "g1" if f < 0.67 else "blue")
        if cols:
            col = cols
        if flash:
            col = "w"
        y = 113 - r
        c.rect(PILE_CX - hw - 1, y, PILE_CX + hw + 1, y, "k0")
        c.rect(PILE_CX - hw, y, PILE_CX + hw, y, col)
    if h:
        top = 113 - h
        c.rect(PILE_CX - 2, top, PILE_CX + 2, top, "k0")


def spool(c, col, dy=0):
    c.rect(84, 64 + dy, 95, 75 + dy, "k0")
    c.rect(85, 65 + dy, 94, 74 + dy, col)
    c.rect(88, 68 + dy, 91, 71 + dy, "k1")
    c.line(89, 76 + dy, 89, 80, "g1")


def tube(c, hx):
    c.line(89, 80, hx + 3, BEAM_Y - 2, "g1")


def stream(c, x, y0, y1, col):
    c.rect(x, y0, x + 1, y1, col)


def bay(c, x, parked=None, py=PARK_Y):
    c.rect(x - 2, 62, x + 9, 81, "k0")
    c.rect(x - 1, 63, x + 8, 81, "k3")
    c.rect(x, 64, x + 7, 81, "k1")
    c.rect(x - 1, 63, x + 8, 63, "b1")
    if parked:
        head(c, x, py, parked)


def sparkle(c, x, y, tp, size=4):
    on = pose_idx(tp) % 2
    col = "w" if on else "yellow"
    c.rect(x - size, y, x + size, y, col)
    c.rect(x, y - size, x, y + size, col)
    c.rect(x - 1, y - 1, x + 1, y + 1, "w")


def wipe(c, t, t0):
    u = (t - t0) / 0.3
    if not 0 <= u < 1:
        return
    y = int(lerp(23, 139, u))
    for yy in range(max(23, y - 12), min(139, y + 2)):
        c.rect(0, yy, art.W - 1, yy, ("b1", "b0")[yy % 2] if yy < y else "b2")


def rack_x(i, pitch=9.5, x0=3):
    return int(round(x0 + pitch * i))


# ---------- scenes ----------
def hook(c, plan, t, tp, t0, t1):
    ev = plan.ev
    headline(c, ["NINE"], "w", y=26, smax=3)
    headline(c, ["HEADS?"], "yellow", y=49, smax=2)
    c.rect(1, 90, 106, 93, "k0")
    c.rect(2, 91, 105, 93, "k3")
    c.rect(2, 90, 105, 90, "b1")
    for i, col in enumerate(HEADS):
        x = rack_x(i, 11.2, 4)
        dy = 0
        k = int((tp - (ev["nine"] + i * 0.11)) * 12)
        if 0 <= k < 4:
            dy = (-3, -5, -3, -1)[k]
        c.rect(x, 94, x + 7, 94, "k0")
        head(c, x, 94 + dy, col)
    if tp >= ev["revealed"] - 0.2 and tp < ev["why"] - 0.05:
        k = pose_idx(tp - (ev["revealed"] - 0.2))
        if k < 1:
            label(c, ["REVEAL COMING"], 54, 69, "w", "b0", smax=1, maxw=100)
        else:
            label(c, ["REVEAL COMING"], 54, 66, "w", "b0", smax=1, maxw=100)
        u = (tp - (ev["revealed"] - 0.2)) / 0.45
        if 0 <= u < 1:
            x = int(lerp(0, 106, u))
            c.rect(x, 24, x + 2, 138, "b2")
            c.rect(x - 3, 24, x - 1, 138, "b1")
    if tp >= ev["why"] - 0.05:
        label(c, ["WHY PEOPLE", "CARE"], 54, 66, "w", "b0", smax=1, maxw=100)
    return


def single(c, plan, t, tp, t0, t1):
    ev = plan.ev
    t_col, t_push = ev["colour"], ev["pushing"]
    if tp < t_col - 0.1:
        headline(c, ["SINGLE", "NOZZLE"], "w")
    elif tp < t_push - 0.1:
        headline(c, ["NEW", "COLOUR?"], "w")
    else:
        headline(c, ["PUSH OLD", "ONE OUT"], "yellow")
    bench(c)
    tray(c)
    travel0 = t_push
    travel1 = travel0 + 0.55
    q = ramp(tp, travel1, t1 - 0.05)
    swapped = tp >= t_col
    hcol = "blue" if tp >= travel0 and False else "red"
    hx = int(round(lerp(58 + 2 * math.sin(pose_idx(tp) * 1.2), 16, ramp(tp, travel0, travel1)))) \
        if tp >= travel0 else int(round(58 + 3 * math.sin(pose_idx(tp) * 1.3)))
    red_h = int(6 * ramp(tp, t0, t_col))
    obj(c, red_h, 0)
    flash = swapped and tp < t_col + 0.17
    spool(c, "w" if flash else ("blue" if swapped else "red"), dy=-1 if flash else 0)
    tube(c, hx)
    printer(c, hx, hcol)
    if q > 0:
        col = "red" if q < 0.34 else "g1" if q < 0.67 else "blue"
        ph = pose_idx(tp) % 2
        top = 113 - int(11 * min(1, q * 1.05))
        stream(c, hx + 3, HEAD_Y + 14, top, col)
        if ph:
            c.px(hx + 2, top, col)
            c.px(hx + 5, top, col)
    pile(c, 11 * min(1, q * 1.05))


def waste(c, plan, t, tp, t0, t1):
    ev = plan.ev
    u = tp - t0
    k = ramp(tp, t0 + 0.5, t1 - 0.05)
    hx = int(round(lerp(16, 58, k))) if tp >= t0 + 0.5 else 16
    blue_h = int(4 * ramp(tp, t0 + 1.0, t1 - 0.05))
    bench(c)
    tray(c)
    flash = pose_idx(tp) % 2 == 0 and u < 1.5
    pile(c, 11, flash=flash)
    obj(c, 6, blue_h)
    spool(c, "blue")
    tube(c, hx)
    printer(c, hx, "blue")
    if tp >= ev["waste"] - 0.15:
        label(c, ["WASTE"], 54, 28, "w", "red", smax=3)
        c.rect(19, 58, 20, 96, "red")
        for j, (a, b) in enumerate(((17, 22), (18, 21), (19, 20))):
            c.rect(a, 96 + j, b, 96 + j, "red")
        c.rect(19, 58, 19, 96, "w") if pose_idx(tp) % 2 else None
    else:
        headline(c, ["PUSH OLD", "ONE OUT"], "yellow")


def changer(c, plan, t, tp, t0, t1):
    ev = plan.ev
    tpk, tgr = ev["parks"], ev["picks"]
    if tp < tpk - 0.1:
        headline(c, ["TOOL", "CHANGER"], "w")
    elif tp < tgr - 0.1:
        headline(c, ["PARK THE", "HEAD"], "w")
    else:
        headline(c, ["GRAB THE", "NEXT"], "yellow")
    bench(c)
    bay(c, 12, None)
    bay(c, 80, "blue" if tp < tgr + 0.15 else None)
    # phases: carry red to bay, raise, travel empty, lower blue, carry blue back
    a1, a2 = t0 + 0.1, tpk + 0.1           # carry red left
    b1_, b2 = a2, a2 + 0.3                 # raise into dock
    c1, c2 = b2 + 0.1, tgr + 0.1           # empty travel right
    d1, d2 = c2, c2 + 0.3                  # lower blue head
    e1, e2 = d2 + 0.05, max(d2 + 0.5, t1 - 0.05)  # carry back
    red_done = tp >= b2
    blue_on = tp >= d2
    if tp < a2:
        hx, hy, col = int(round(lerp(58, 12, ramp(tp, a1, a2)))), HEAD_Y, "red"
    elif tp < c1:
        hx, hy, col = 12, int(round(lerp(HEAD_Y, PARK_Y, ramp(tp, b1_, b2)))), "red"
    elif tp < c2:
        hx, hy, col = int(round(lerp(12, 80, ramp(tp, c1, c2)))), None, None
    elif tp < d2:
        hx, hy, col = 80, int(round(lerp(PARK_Y, HEAD_Y, ramp(tp, d1, d2)))), "blue"
    else:
        hx, hy, col = int(round(lerp(80, 58, ramp(tp, e1, e2)))), HEAD_Y, "blue"
    if red_done and tp < c1 + 0.01:
        pass
    parked_red = tp >= b2
    obj(c, 6, int(4 * ramp(tp, e2 - 0.35, t1)) if blue_on and tp >= e2 - 0.35 else 0)
    printer(c, hx, None, carriage=False)
    if parked_red:
        head(c, 12, PARK_Y, "red")
    if col and hy is not None:
        head(c, hx, hy, col)
    c.rect(hx - 1, BEAM_Y - 2, hx + 8, BEAM_Y + 3, "k0")
    c.rect(hx, BEAM_Y - 1, hx + 7, BEAM_Y + 2, "g1")
    c.rect(hx, BEAM_Y - 1, hx + 7, BEAM_Y - 1, "g0")


def less(c, plan, t, tp, t0, t1):
    headline(c, ["LESS", "PUSHED", "OUT"], "green", smax=2, gap=1)
    bench(c)
    tray(c)
    k = ramp(tp, t0 + 0.1, t1 - 0.45)
    h = int(round(lerp(11, 2, k)))
    pile(c, h, ghost=True)
    obj(c, 6, 4)
    wob = int(round(58 + 2 * math.sin(pose_idx(tp) * 1.3)))
    printer(c, wob, "blue")
    if tp >= t1 - 0.45:
        sparkle(c, PILE_CX, 108, tp)


def _panel(c, x_off, y, lines, col):
    x0 = 3 + x_off
    c.box(x0, y, x0 + 85, y + 19, "k3", "k0")
    c.rect(x0 + 1, y + 1, x0 + 84, y + 1, "b1")
    if x0 + 6 >= 1:
        c.text(lines[0], x0 + 6, y + 3, col, 1, kind="label", shadow=False)
        c.text(lines[1], x0 + 6, y + 11, "w", 1, kind="label", shadow=False)
    return x0


def _gear(c, cx, cy, ph):
    c.rect(cx - 4, cy - 4, cx + 4, cy + 4, "k0")
    c.rect(cx - 3, cy - 3, cx + 3, cy + 3, "g0")
    c.rect(cx - 1, cy - 1, cx + 1, cy + 1, "k0")
    pts = ((0, -6), (0, 5), (-6, 0), (5, 0)) if ph == 0 else ((-5, -5), (4, -5), (-5, 4), (4, 4))
    for dx, dy in pts:
        c.rect(cx + dx, cy + dy, cx + dx + 1, cy + dy + 1, "g0")


def trade(c, plan, t, tp, t0, t1):
    ev = plan.ev
    if tp < ev["unknown"] - 0.05:
        headline(c, ["THE", "TRADE-OFFS"], "w", smax=2, mixed=True)
    else:
        headline(c, ["NOT OUT", "YET"], "red")
    specs = [("more", ["MORE", "PARTS"], 66), ("bigger", ["BIGGER", "MACHINE"], 88),
             ("price", ["PRICE:", "???"], 110)]
    for i, (key, lines, y) in enumerate(specs):
        ts = ev[key] - 0.1
        if tp < ts:
            continue
        slide = ramp(tp, ts, ts + 0.3)
        off = int(round(-95 * (1 - slide) ** 2))
        col = "yellow"
        if i == 2 and tp >= ev["unknown"] - 0.05 and pose_idx(tp) % 2:
            col = "red"
        x0 = _panel(c, off, y, lines, col)
        if i == 0:
            ph = pose_idx(tp) % 2
            _gear(c, x0 + 66, y + 10, ph)
            _gear(c, x0 + 77, y + 10, 1 - ph)
        elif i == 1:
            g = ramp(tp, ts + 0.2, ts + 1.0)
            w, h = int(lerp(7, 17, g)), int(lerp(5, 13, g))
            bx = x0 + 70 - w // 2
            by = y + 17 - h
            c.rect(bx, by, bx + w, y + 17, "k0")
            c.rect(bx + 1, by + 1, bx + w - 1, y + 16, "b1")
            c.rect(bx + 1, by + 1, bx + w - 1, by + 1, "b2")
        else:
            c.rect(x0 + 62, y + 5, x0 + 80, y + 15, "k0")
            c.rect(x0 + 63, y + 6, x0 + 79, y + 14, "yellow")
            c.rect(x0 + 64, y + 9, x0 + 65, y + 11, "k0")
            c.text("?", x0 + 70, y + 7, "k0", 1, kind="label", shadow=False)


def _calendar(c, tp, ev):
    x0, x1, yt = 25, 64, 66
    torn = ramp(tp, ev["third"] - 0.1, ev["third"] + 0.35)
    c.rect(x0 + 6, yt - 4, x0 + 8, yt, "g0")
    c.rect(x1 - 8, yt - 4, x1 - 6, yt, "g0")
    c.rect(x0, yt, x1, yt + 38, "k0")
    c.rect(x0 + 1, yt + 1, x1 - 1, yt + 14, "b0")
    c.rect(x0 + 1, yt + 15, x1 - 1, yt + 37, "w")
    c.text("3", 45 - 7, yt + 17, "b0", 3, kind="illus", shadow=False)
    if tp >= ev["november"]:
        sc = 1 if tp < ev["november"] + 0.17 else 2
        c.text_center("NOV", 45, yt + (4 if sc == 1 else 1), "w", sc, kind="illus", shadow=False)
    else:
        for i in range(3):
            c.rect(x0 + 14 + i * 5, yt + 7, x0 + 15 + i * 5, yt + 8, "b2")
    if torn < 1:
        k = int(torn * 4)
        dx, dy = 6 * k, 5 * k
        c.rect(x0 + dx, yt + 15 + dy, x1 + dx, yt + 37 + dy, "k0")
        c.rect(x0 + 1 + dx, yt + 16 + dy, x1 - 1 + dx, yt + 37 + dy, "w")
        c.text("?", 45 - 7 + dx, yt + 17 + dy, "red", 3, kind="illus", shadow=False, rec=False)


def reveal(c, plan, t, tp, t0, t1):
    ev = plan.ev
    after = tp >= ev["s8"] - 0.05
    if after:
        headline(c, ["WHICH", "COLOUR?"], "yellow")
    else:
        headline(c, ["REVEAL", "DAY"], "w")
    _calendar(c, tp, ev)
    k = ramp(tp, ev["s8"] - 0.05, ev["s8"] + 0.5)
    if k > 0:
        ry = int(round(lerp(142, 110, 1 - (1 - k) ** 2)))
        c.rect(1, ry - 3, 90, ry - 1, "k3")
        c.rect(1, ry - 3, 90, ry - 3, "b1")
        for i, col in enumerate(HEADS[:8]):
            head(c, rack_x(i), ry, col)
        x = rack_x(8)
        cyc = HEADS[(pose_idx(tp) // 1) % 9]
        c.rect(x, ry, x + 7, ry + 13, cyc)
        c.rect(x + 1, ry + 1, x + 6, ry + 12, "k0")
        if ry + 10 <= 137:
            c.text("?", x + 1, ry + 3, cyc, 1, kind="illus", shadow=False)
        if ry + 22 <= 137:
            c.text("9", x + 2, ry + 16, "w", 1, kind="label", shadow=False)


def card(c, plan, t, tp, t0, t1):
    headline(c, ["FOLLOW", "FOR MORE"], "w", y=26, smax=2)
    c.text_center("3D PRINTING NEWS", 54, 58, "g0", 1, kind="headline")
    label(c, ["@STUDIORK3DPS"], 54, 69, "w", "b0", smax=1, maxw=100)
    c.rect(1, 90, 106, 93, "k0")
    c.rect(2, 91, 105, 93, "k3")
    c.rect(2, 90, 105, 90, "b1")
    for i, col in enumerate(HEADS):
        x = rack_x(i, 11.2, 4)
        k = (pose_idx(tp) - i) % 9
        dy = (-4, -6, -4, -1)[k] if k < 4 else 0
        c.rect(x, 94, x + 7, 94, "k0")
        head(c, x, 94 + dy, col)
    bench(c)


SCENES = {"hook": hook, "single": single, "waste": waste, "changer": changer,
          "less": less, "trade": trade, "reveal": reveal, "card": card}


# ---------- captions ----------
def caption_chunks(plan):
    chunks, cur = [], []
    for tok, s, e, li in plan.words:
        word = "".join(ch for ch in tok.upper() if ch in art.GLYPHS and ch != " ")
        if not word:
            continue
        n = sum(len(w[0]) + 1 for w in cur) + len(word)
        if cur and (n > 14 or cur[-1][3] != li):
            chunks.append(cur)
            cur = []
        cur.append((word, s, e, li))
    if cur:
        chunks.append(cur)
    return chunks


def captions(c, plan, chunks, t):
    if t > plan.ev["end"] + 0.5:
        return
    active = None
    for i, ch in enumerate(chunks):
        nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else 1e9
        if ch[0][1] - 0.05 <= t < min(nxt - 0.02, ch[-1][2] + 0.45):
            active = ch
    if not active:
        return
    text = " ".join(w[0] for w in active)
    width = art.text_width(text)
    c.rect(1, 136, 89, 153, "k0")
    x = 45 - width // 2
    for word, s, e, _ in active:
        hot = s - 0.02 <= t < e + 0.04
        c.text(word, x, 142, "yellow" if hot else "w", 1, kind="caption", shadow=False)
        x += art.text_width(word) + 6


def frame(plan, chunks, t):
    c = Canvas()
    idx, name, t0, t1 = next((i, n, a, b) for i, (n, a, b) in enumerate(plan.scenes) if a <= t < b) \
        if t < plan.scenes[-1][2] else (len(plan.scenes) - 1, *plan.scenes[-1])
    tp = pose_idx(t) / 12
    art.background(c, t / plan.duration)
    SCENES[name](c, plan, t, tp, t0, t1)
    if idx:
        wipe(c, t, t0)
    captions(c, plan, chunks, t)
    return c
