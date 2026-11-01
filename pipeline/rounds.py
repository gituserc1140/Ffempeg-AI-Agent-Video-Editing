"""Round modules for battle videos. Each draws one side's test animation.
draw(c, cx, fx, ps, tint, pb): cx = centre x, fx = outcome, ps = poses since the
trigger word (negative = not yet), pb = poses since the beat started."""

MODULES = {
    "bend": ("bend", "snap", "hold"),
    "heat": ("sag", "hold"),
    "speed": ("fast", "slow"),
    "drop": ("crack", "bounce", "hold"),
    "detail": ("chunky", "sharp"),
}

BEND = [0, 3, 6, 9, 12, 10, 7, 5, 3, 2, 1, 1]
BOUNCE = [0, -9, -13, -9, 0, -3, 0]
FALL_Y = [66, 68, 73, 80, 86]


def _bend(c, cx, fx, ps, tint, pb):
    k = max(0, min(ps, len(BEND) - 1))
    c.rect(cx - 20, 98, cx - 10, 101, 4)
    c.rect(cx - 18, 72, cx - 14, 98, 5)
    length, x0, y0 = 30, cx - 14, 74
    snapped = fx == "snap" and ps >= 5
    depth = {"bend": BEND[k], "snap": min(k * 2, 8), "hold": 0}[fx]
    fall = min((ps - 5) ** 2 * 2, 18) if snapped else 0
    for i in range(length):
        dy = int(depth * (i / length) ** 2)
        y = y0 + dy + (fall if snapped and i >= 16 else 0)
        c.rect(x0 + i, y, x0 + i, y + 1, tint[0])
        c.px(x0 + i, y + 2, tint[1])
    if snapped and 5 <= ps <= 8:
        for dx, dy, col in ((0, 0, 12), (2, -2, 3), (-2, 2, 11), (3, 3, 12)):
            c.px(x0 + 16 + dx, y0 + 3 + dy, col)


def _heat(c, cx, fx, ps, tint, pb):
    sx, sy = cx, 68
    c.rect(sx - 3, sy - 4, sx + 3, sy + 4, 12)
    c.rect(sx - 4, sy - 3, sx + 4, sy + 3, 12)
    if pb % 2 == 0:
        for dx, dy in ((-7, 0), (7, 0), (0, -7), (-5, -5), (5, -5)):
            c.px(sx + dx, sy + dy, 12)
    c.rect(cx - 20, 84, cx - 17, 100, 4)
    c.rect(cx + 17, 84, cx + 20, 100, 4)
    sag = 0 if fx == "hold" else int(9 * min(1, max(ps, 0) / 8))
    for i in range(35):
        dy = int(sag * (1 - ((i - 17) / 17) ** 2))
        x = cx - 17 + i
        c.rect(x, 82 + dy, x, 83 + dy, tint[0])
        c.px(x, 84 + dy, tint[1])
    if ps >= 0:
        for k in range(4):
            c.px(cx - 12 + k * 8, 76 + (pb + k) % 3, 11)


def _speed(c, cx, fx, ps, tint, pb):
    dur = 4 if fx == "fast" else 14
    n = int(40 * min(1, max(ps, 0) / dur))
    x0 = cx - 20
    c.rect(x0 - 2, 96, x0 + 42, 99, 5)
    c.rect(x0, 94, x0 + n, 95, tint[0])
    nx = x0 + n
    c.rect(nx - 3, 80, nx + 3, 86, 4)
    c.rect(nx - 3, 80, nx + 3, 81, 3)
    c.rect(nx - 1, 87, nx + 1, 92, 6)
    if fx == "fast" and 0 <= ps < dur:
        for k in range(3):
            c.px(nx - 6 - k * 3, 83, 4)


def _drop(c, cx, fx, ps, tint, pb):
    c.rect(cx - 14, 97, cx + 14, 100, 5)
    j = ps - 5
    if ps < 5:
        y = FALL_Y[max(ps, 0)]
    elif fx == "bounce":
        y = 86 + BOUNCE[min(j, len(BOUNCE) - 1)]
    else:
        y = 86
    c.rect(cx - 5, y, cx + 5, y + 10, tint[0])
    c.rect(cx - 5, y + 9, cx + 5, y + 10, tint[1])
    c.rect(cx + 5, y, cx + 5, y + 10, tint[1])
    if j >= 0 and fx == "crack":
        for k in range(10):
            c.px(cx - 1 + (k % 3) - 1 + (k // 3), y + k, 11)
        for k, (dx, dy) in enumerate(((8, -2), (-8, -3), (10, 1), (-10, 0))):
            c.px(cx + dx + (min(j, 4) * (1 if dx > 0 else -1)), y + 3 + dy - (k % 2), tint[0])
    elif j in (0, 1, 2) and fx == "hold":
        for s in (-1, 1):
            x = cx + s * (9 + j * 2)
            c.rect(min(x, x + s * 2), 94, max(x, x + s * 2), 95, 4)


def _detail(c, cx, fx, ps, tint, pb):
    r, cy = 11, 84
    rows = 24 if ps >= 8 else (max(ps, 0) + 1) * 3
    step = 4 if fx == "chunky" else 1
    for yy in range(-r, r + 1):
        if yy + r >= rows:
            break
        for xx in range(-r, r + 1):
            qx, qy = (xx // step) * step + step / 2, (yy // step) * step + step / 2
            d = (qx * qx + qy * qy) ** 0.5
            if d > r + 0.5:
                continue
            c.px(cx + xx, cy + yy, tint[1] if d > r - 1.5 and step == 1 else tint[0])
    if fx == "sharp" and rows >= 24:
        c.px(cx - 4, cy - 5, 3)
        c.px(cx - 3, cy - 5, 3)


DRAW = {"bend": _bend, "heat": _heat, "speed": _speed, "drop": _drop, "detail": _detail}
