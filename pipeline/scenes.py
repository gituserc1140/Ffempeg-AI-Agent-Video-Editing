"""One scene function per beat type. Each takes (canvas, plan, beat_index, t) and
returns a (dx, dy) screen-shake offset. `t` is seconds into the beat, already
quantised to the 12 fps pose clock."""
import math
import random

from . import config as C
from .font import text_width
from .sprites import SCALES

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


def _slots(brief, side):
    ta, tb = tints(brief)
    if brief["layout"] != "split":
        return [dict(cx=54, cy=68, s=4, tint=ta, who="a")]
    a = dict(cx=27, cy=76, s=3, tint=ta, who="a")
    b = dict(cx=81, cy=76, s=3, tint=tb, who="b")
    return {"a": [a], "b": [b]}.get(side, [a, b])


def _sprite_scale(name, slot, ps=None):
    if name in SCALES:
        return SCALES[name]
    if ps is None:
        return slot["s"]
    if ps < 0:
        return max(1, slot["s"] - 1)
    return _pop(slot["s"], ps)


def _platform(c, slots):
    for slot in slots:
        if slot["who"] == "a":
            x0, x1 = 3, 51
            tint = slot["tint"][0]
        elif slot["who"] == "b":
            x0, x1 = 57, 105
            tint = slot["tint"][0]
        else:
            x0, x1, tint = 8, 100, slot["tint"][0]
        c.rect(x0, 91, x1, 99, 0)
        c.rect(x0 + 1, 92, x1 - 1, 93, tint)
        c.rect(x0 + 2, 94, x1 - 2, 97, 5)
        c.rect(x0 + 4, 98, x1 - 4, 99, 2)
        for x in range(x0 + 4, x1 - 2, 8):
            c.rect(x, 95, x + 2, 95, 12)


def _idle_slots(brief, active):
    """Split layout: the side that is not part of the beat keeps its subject icon."""
    if brief["layout"] != "split":
        return []
    have = {s["who"] for s in active}
    return [s for s in _slots(brief, "both") if s["who"] not in have]


def _chrome(c, brief, p, show_vs, show_title=False):
    if brief["layout"] != "split":
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


def _ring(c, ps, cx, cy, s):
    if 0 <= ps <= 3:
        r = 6 * s + 2 + ps * 3
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


def hook(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    split = brief["layout"] == "split"
    _chrome(c, brief, pb, show_vs=ps >= 0, show_title=split)
    if split:
        slots = _slots(brief, "both")
        _platform(c, slots)
        for slot, subj in zip(slots, ("subject_a", "subject_b")):
            icon = brief[subj]["icon"]
            _draw_icon(c, icon, slot, ps, pb)
            _sparkles(c, ps, pb, slot["cx"], slot["cy"], seed=bi * 7 + slot["cx"])
            _ring(c, ps, slot["cx"], slot["cy"], _sprite_scale(icon, slot))
    else:
        slot = _slots(brief, "a")[0]
        _platform(c, [slot])
        _draw_icon(c, b["icon"], slot, ps, pb)
        _sparkles(c, ps, pb, slot["cx"], slot["cy"], seed=bi)
        _ring(c, ps, slot["cx"], slot["cy"], _sprite_scale(b["icon"], slot))
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


def _draw_icon(c, name, slot, ps, pb, recolor=None, ghost_before=True):
    scale = _sprite_scale(name, slot, ps)
    if ps < 0:
        if ghost_before:
            c.sprite(name, slot["cx"], slot["cy"] + _bob(pb), scale, ghost=True)
        return
    c.sprite(name, slot["cx"], slot["cy"] + _bob(pb), scale,
             tint=slot["tint"], recolor=recolor)


def icon(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=True)
    slots = _slots(brief, b["side"])
    _platform(c, _slots(brief, "both") if brief["layout"] == "split" else slots)
    for s in _idle_slots(brief, slots):
        icon_name = brief["subject_" + s["who"]]["icon"]
        c.sprite(icon_name, s["cx"], s["cy"] + _bob(pb), _sprite_scale(icon_name, s, -1), tint=s["tint"])
    for s in slots:
        _draw_icon(c, b["icon"], s, ps, pb)
        _sparkles(c, ps, pb, s["cx"], s["cy"], seed=bi * 11 + s["cx"])
        _ring(c, ps, s["cx"], s["cy"], _sprite_scale(b["icon"], s))
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


def card(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=True)
    slots = _slots(brief, b["side"])
    _platform(c, _slots(brief, "both") if brief["layout"] == "split" else slots)
    for s in _idle_slots(brief, slots):
        icon_name = brief["subject_" + s["who"]]["icon"]
        c.sprite(icon_name, s["cx"], s["cy"] + _bob(pb), _sprite_scale(icon_name, s, -1), tint=s["tint"])
    for s in slots:
        _draw_icon(c, b["icon"], s, ps, pb)
        _sparkles(c, ps, pb, s["cx"], s["cy"], seed=bi * 13 + s["cx"])
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
    _platform(c, _slots(brief, "both") if brief["layout"] == "split" else slots)
    for s in _idle_slots(brief, slots):
        icon_name = brief["subject_" + s["who"]]["icon"]
        c.sprite(icon_name, s["cx"], s["cy"] + _bob(pb), _sprite_scale(icon_name, s, -1), tint=s["tint"])
    for s in slots:
        if ps < 0:
            scale = _sprite_scale(b["icon"], s)
            c.sprite(b["icon"], s["cx"], s["cy"] + _bob(pb), scale, tint=s["tint"], recolor=(11, 7))
            c.sprite("cross", s["cx"] + 6 * scale, s["cy"] - 6 * scale + (pb % 2), 2)
        else:
            scale = _sprite_scale(b["icon"], s)
            c.sprite(b["icon"], s["cx"], s["cy"] + _bob(pb), scale, recolor=(10, 15))
            c.sprite("check", s["cx"] + 6 * scale, s["cy"] - 6 * scale, _pop(2, ps))
            _sparkles(c, ps, pb, s["cx"], s["cy"], seed=bi * 17 + s["cx"])
    _keyword(c, plan, b, ps, 106)
    return _shake(ps)


def end(c, plan, bi, t):
    brief, b = plan.brief, plan.beats[bi]
    ps, pb = _beat_state(b, t)
    _chrome(c, brief, pb, show_vs=False)
    slot = dict(cx=54, cy=58, s=4, tint=tints(brief)[0], who="a")
    if brief["layout"] == "split":
        slot["s"] = 3
    platform_slot = dict(slot, who="both")
    _platform(c, [platform_slot])
    _draw_icon(c, b["icon"], slot, ps, pb)
    _sparkles(c, ps, pb, slot["cx"], slot["cy"], seed=bi * 19)
    _ring(c, ps, slot["cx"], slot["cy"], _sprite_scale(b["icon"], slot))
    _keyword(c, plan, b, ps, 94)
    if pb >= 4:
        col = 12 if (pb // 3) % 2 == 0 else 3
        c.text_center(brief["handle"], 45, 118, col, 1, kind="handle")
    return _shake(ps)


SCENES = {"hook": hook, "icon": icon, "card": card, "fix": fix, "end": end}
