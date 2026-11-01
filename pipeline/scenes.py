"""One scene function per beat type. Each takes (canvas, plan, beat_index, t) and
returns a (dx, dy) screen-shake offset. `t` is seconds into the beat, already
quantised to the 12 fps pose clock."""
import math
import random

from . import config as C
from .font import text_width
from . import stages
from .rounds import DRAW as ROUND_DRAW
from .sprites import ICONS

POSE = C.POSE_FPS
SHAKE = [(1, 0), (-1, 1), (0, -1)]


def tints(brief):
    a = C.FAMILIES[brief["subject_a"]["color"]]
    sb = brief.get("subject_b")
    b = C.FAMILIES[sb["color"]] if sb else a
    return a, b


def _bob(pb):
    return (0, -1, -1, 0)[pb % 4]


def _pop(base, ps):
    seq = (max(1, base - 2), base + 1, base)
    return seq[ps] if ps < len(seq) else base


def _slots(brief, side, base=None):
    ta, tb = tints(brief)
    if brief["layout"] != "split":
        return [dict(cx=54, base=base or 94, s=4, tint=ta, who="a", span=(14, 94))]
    a = dict(cx=27, base=base or 96, s=3, tint=ta, who="a", span=(3, 51))
    b = dict(cx=81, base=base or 96, s=3, tint=tb, who="b", span=(57, 105))
    return {"a": [a], "b": [b]}.get(side, [a, b])


def _scale(name, slot, ps=None):
    """Integer scale so the icon fills the slot whatever its native size."""
    art = ICONS[name]
    base = max(1, round(12 * slot["s"] / len(art[0])))
    if ps is None:
        return base
    if ps < 0:
        return max(1, base - 1) if len(art[0]) == 12 else base
    return _pop(base, ps) if len(art[0]) == 12 else base


def _cy(name, slot, scale, pb=0):
    """Centre y that puts the icon's feet on the platform."""
    return slot["base"] - len(ICONS[name]) * scale // 2 + _bob(pb)


def _platform(c, slots):
    for slot in slots:
        top = slot["base"]
        x0, x1 = slot["span"]
        tint = slot["tint"][0]
        c.rect(x0, top, x1, top + 8, 0)
        c.rect(x0 + 1, top + 1, x1 - 1, top + 2, tint)
        c.rect(x0 + 2, top + 3, x1 - 2, top + 6, 5)
        c.rect(x0 + 4, top + 7, x1 - 4, top + 8, 2)
        for x in range(x0 + 4, x1 - 2, 8):
            c.rect(x, top + 4, x + 2, top + 4, 12)


def _idle_slots(brief, active):
    """Split layout: the side that is not part of the beat keeps its subject icon."""
    if brief["layout"] != "split":
        return []
    have = {s["who"] for s in active}
    return [s for s in _slots(brief, "both") if s["who"] not in have]


TAGS = {"troubleshooting": "FIX IT", "tip": "QUICK TIP", "spotlight": "SPOTLIGHT",
        "before-after": "BEFORE/AFTER", "explainer": "EXPLAINED"}


def _banner(c, brief):
    tag = TAGS.get(brief.get("format"), "3D PRINT")
    scale = 2 if text_width(tag, 2) <= 80 else 1
    c.rect(10, 26, 97, 46, 0)
    c.rect(10, 26, 97, 27, 12)
    c.rect(10, 45, 97, 46, 14)
    c.rect(10, 28, 12, 44, 13)
    c.rect(95, 28, 97, 44, 6)
    c.text_center(tag, 54, 29 if scale == 2 else 33, 12, scale, kind="label")


def _chrome(c, brief, p, show_vs, show_title=False):
    if brief["layout"] != "split":
        _banner(c, brief)
        return
    ta, tb = tints(brief)
    c.rect(0, 23, 52, 36, 0)
    c.rect(0, 25, 52, 35, ta[1])
    c.rect(0, 25, 52, 26, ta[0])
    c.rect(55, 23, 107, 36, 0)
    c.rect(55, 25, 107, 35, tb[1])
    c.rect(55, 25, 107, 26, tb[0])
    c.rect(1, 37, 51, 38, ta[0])
    c.rect(56, 37, 106, 38, tb[0])
    for y in range(36, 100, 4):
        c.rect(53, y, 54, y + 1, 2)
    c.text_center(brief["subject_a"]["label"], 27, 27, 3, kind="label")
    c.text_center(brief["subject_b"]["label"], 81, 27, 3, kind="label")
    if show_title:
        title = f'{brief["subject_a"]["label"]} VS {brief["subject_b"]["label"]}'
        c.rect(8, 42, 99, 58, 0)
        c.rect(8, 42, 99, 43, 12)
        c.rect(8, 57, 99, 58, 14)
        c.rect(8, 44, 10, 56, 13)
        c.rect(97, 44, 99, 56, 6)
        scale = 2 if text_width(title, 2) <= 84 else 1
        c.text_center(title, 54, 46, 12, scale, kind="label")
    if show_vs:
        c.rect(43, 53, 64, 75, 0)
        c.rect(44, 54, 63, 74, 12)
        c.rect(46, 56, 61, 72, 11)
        c.text_center("VS", 54, 59, 3, kind="label", clamp=False)


def _sparkles(c, ps, pb, cx, cy, seed):
    rnd = random.Random(seed)
    for k in range(8):
        ang = rnd.random() * 6.283
        r0 = rnd.randint(16, 24)
        if 0 <= ps < 7 + k % 3:
            x = cx + int(math.cos(ang) * (r0 + ps))
            y = cy + int(math.sin(ang) * (r0 + ps) * 0.8)
        elif ps >= 7 and (pb + k) % 3 == 0:
            x = cx + int(math.cos(ang) * (r0 + 6))
            y = cy + int(math.sin(ang) * (r0 + 6) * 0.8)
        else:
            continue
        col = (12, 3, 12, 13)[(ps + k) % 4]
        c.px(x, y, col)
        if (ps + k) % 2 == 0:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c.px(x + dx, y + dy, col)


def _ring(c, ps, cx, cy, half):
    if 0 <= ps <= 3:
        r = half + 2 + ps * 3
        c.rect(cx - r, cy - r, cx + r, cy - r, 12)
        c.rect(cx - r, cy + r, cx + r, cy + r, 12)
        c.rect(cx - r, cy - r, cx - r, cy + r, 12)
        c.rect(cx + r, cy - r, cx + r, cy + r, 12)


def _keyword(c, plan, b, ps, y, cx=54, col=3):
    if ps < 0:
        return
    word = b["keyword"]
    scale = 2 if text_width(word, 2) <= 80 else 1
    x, w = c.text_center(word, cx, y, col, scale)
    c.rect(x, y + 7 * scale + 3, x + w - 1, y + 7 * scale + 3, 12)


def _beat_state(b, t):
    tt = b["trig"] - b["start"]
    ps = int((t - tt) * POSE) if t >= tt else -1
    pb = int(t * POSE)
    return ps, pb


def _shake(ps):
    return SHAKE[ps] if 0 <= ps < len(SHAKE) else (0, 0)


def _stage_w(slot):
    return min(76, slot["span"][1] - slot["span"][0] - 2)


def _draw(c, name, slot, ps, pb, tint=None, ghost=False, fixed=False):
    """Draw one icon (animated stage when one exists) standing on its platform.
    Returns (cx, cy, half) for effects."""
    tint = tint or slot["tint"]
    if name in stages.STAGES:
        sheet = stages.render(name, _stage_w(slot), pb, tint[0], tint[1], fixed=fixed, ghost=ghost)
        stages.blit(c, sheet, slot["cx"], slot["base"])
        return slot["cx"], slot["base"] - stages.HEIGHT // 2, stages.HEIGHT // 2 - 2
    scale = _scale(name, slot, ps)
    cy = _cy(name, slot, scale, pb)
    c.sprite(name, slot["cx"], cy, scale, tint=tint, ghost=ghost)
    return slot["cx"], cy, len(ICONS[name]) * scale // 2


def _show(c, name, slot, ps, pb, recolor=None):
    return _draw(c, name, slot, ps, pb, tint=recolor, ghost=ps < 0)


def _idle(c, brief, slots, pb):
    for s in _idle_slots(brief, slots):
        _draw(c, brief["subject_" + s["who"]]["icon"], s, -1, pb)


def hook(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    split = brief["layout"] == "split"
    _chrome(c, brief, pb, show_vs=ps >= 0, show_title=split)
    slots = _slots(brief, "both")
    _platform(c, slots)
    names = [brief[k]["icon"] for k in ("subject_a", "subject_b")] if split else [b["icon"]]
    for slot, name in zip(slots, names):
        cx, cy, half = _show(c, name, slot, ps, pb)
        _sparkles(c, ps, pb, cx, cy, seed=bi * 7 + cx)
        _ring(c, ps, cx, cy, half)
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


def icon(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=True)
    slots = _slots(brief, b["side"])
    _platform(c, _slots(brief, "both"))
    _idle(c, brief, slots, pb)
    for s in slots:
        cx, cy, half = _show(c, b["icon"], s, ps, pb)
        _sparkles(c, ps, pb, cx, cy, seed=bi * 11 + cx)
        _ring(c, ps, cx, cy, half)
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


def card(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=True)
    slots = _slots(brief, b["side"])
    _platform(c, _slots(brief, "both"))
    _idle(c, brief, slots, pb)
    for s in slots:
        cx, cy, _ = _show(c, b["icon"], s, ps, pb)
        _sparkles(c, ps, pb, cx, cy, seed=bi * 13 + cx)
    if ps >= 0:
        x0 = int(-70 + (14 + 70) * min(ps, 3) / 3)
        c.rect(x0 + 2, 108, x0 + 62, 130, 12)
        c.rect(x0, 110, x0 + 64, 128, 12)
        c.rect(x0 + 2, 110, x0 + 62, 128, 2)
        c.rect(x0, 112, x0 + 64, 126, 2)
        label = b["label"]
        scale = 2 if text_width(label, 2) <= 58 else 1
        if ps >= 3:
            c.text(label, x0 + 32 - text_width(label, scale) // 2, 119 - (7 * scale) // 2 + 1,
                   3, scale, kind="label", clamp=False)
    return _shake(ps)


def fix(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=True)
    slots = _slots(brief, b["side"])
    _platform(c, _slots(brief, "both"))
    _idle(c, brief, slots, pb)
    for s in slots:
        if ps < 0:
            cx, cy, half = _draw(c, b["icon"], s, ps, pb, tint=(11, 7))
            c.sprite("cross", cx + half, cy - half + (pb % 2), 2)
        else:
            cx, cy, half = _draw(c, b["icon"], s, ps, pb, tint=(10, 15), fixed=True)
            c.sprite("check", cx + half, cy - half, _pop(2, ps))
            _sparkles(c, ps, pb, cx, cy, seed=bi * 17 + s["cx"])
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


RESULT_POSE = 14
PIP_Y = 38


def _pips(c, plan, bi, ps):
    rounds = [i for i, b in enumerate(plan.beats) if b["scene"] == "round"]
    ta, tb = tints(plan.brief)
    x = 54 - (len(rounds) * 8 - 3) // 2
    for i in rounds:
        win = plan.beats[i].get("win")
        done = i < bi or (i == bi and ps >= RESULT_POSE)
        col = 5
        if done and win:
            col = {"a": ta[0], "b": tb[0]}.get(win, 4)
        c.rect(x, PIP_Y, x + 4, PIP_Y + 4, 3 if i == bi else 4)
        c.rect(x + 1, PIP_Y + 1, x + 3, PIP_Y + 3, col)
        x += 8


def round_(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=False)
    _pips(c, plan, bi, ps)
    _keyword(c, plan, b, ps, 48)
    ta, tb = tints(brief)
    draw = ROUND_DRAW[b["module"]]
    draw(c, 27, b["fx_a"], ps, ta, pb)
    draw(c, 81, b["fx_b"], ps, tb, pb)
    if ps >= RESULT_POSE and b.get("win") in ("a", "b"):
        for who, cx in (("a", 27), ("b", 81)):
            c.sprite("check" if b["win"] == who else "cross", cx, 114,
                     _pop(1, ps - RESULT_POSE), tint=ta)
    return _shake(ps)


def _verdict(c, brief, b, ps):
    rows = b["verdict"]
    ta, tb = tints(brief)
    x0, x1, y0 = 12, 88, 76
    y1 = y0 + 4 + 20 * len(rows)
    c.rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2, 12)
    c.rect(x0, y0, x1, y1, 1)
    for i, row in enumerate(rows):
        if ps < i * 4:
            continue
        y = y0 + 4 + i * 20
        c.text_center(row["trait"], 50, y, 3, 1, kind="label")
        tint = ta if row["pick"] == "a" else tb
        label = brief["subject_" + row["pick"]]["label"]
        w = text_width(label, 1)
        c.rect(50 - w // 2 - 3, y + 9, 50 + (w + 1) // 2 + 2, y + 17, tint[0])
        c.text_center(label, 50, y + 10, 0, 1, kind="label", shadow=False)


def end(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=False)
    split = brief["layout"] == "split"
    slot = dict(cx=54, base=94, s=3 if split else 4, tint=tints(brief)[0], who="a", span=(14, 94))
    _platform(c, [slot])
    cx, cy, half = _show(c, b["icon"], slot, ps, pb)
    _sparkles(c, ps, pb, cx, cy, seed=bi * 19)
    _ring(c, ps, cx, cy, half)
    if b.get("verdict") and ps >= 0:
        _verdict(c, brief, b, ps)
    else:
        _keyword(c, plan, b, ps, 104)
    if pb >= 4:
        col = 12 if (pb // 3) % 2 == 0 else 3
        c.text_center(brief["handle"], 45, 128 if b.get("verdict") else 124, col, 1, kind="handle")
    return _shake(ps)


SCENES = {"hook": hook, "icon": icon, "card": card, "fix": fix, "round": round_, "end": end}
