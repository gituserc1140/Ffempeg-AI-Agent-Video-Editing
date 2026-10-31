"""Draws one pose (12 fps clock) as a 108x192 canvas."""
from . import background, config as C
from .pixel import Canvas
from .scenes import SCENES

POSE = C.POSE_FPS


def _beat_index(plan, t):
    for i, b in enumerate(plan.beats):
        if b["start"] <= t < b["end"]:
            return i
    return len(plan.beats) - 1


def _active_chunk(plan, t):
    started = [i for i, w in enumerate(plan.words) if w["start"] <= t]
    if not started:
        return None
    cur = started[-1]
    if t > plan.words[cur]["end"] + 0.35 and cur == len(plan.words) - 1:
        return None
    for chunk in plan.chunks:
        for line in chunk:
            for w in line:
                if w is plan.words[cur]:
                    return chunk, cur
    return None


def _captions(c, plan, t):
    hit = _active_chunk(plan, t)
    if not hit:
        return
    chunk, cur = hit
    n = len(chunk)
    y0 = 145 - (7 * n + 2 * (n - 1)) // 2
    for li, line in enumerate(chunk):
        y = y0 + li * 9
        total = sum(len(w["text"]) for w in line) + len(line) - 1
        x = 46 - (total * 6 - 1) // 2
        for w in line:
            col = 12 if w is plan.words[cur] else 3
            c.text(w["text"], x, y, col, 1, kind="voice", clamp=False)
            x += (len(w["text"]) + 1) * 6


def render_pose(plan, p):
    t = p / POSE
    c = Canvas()
    background.draw(c, p)
    bi = _beat_index(plan, t)
    beat = plan.beats[bi]
    dx, dy = SCENES[beat["scene"]](c, plan, bi, max(0.0, t - beat["start"]))
    c.shift(dx, dy)
    _captions(c, plan, t)
    return c
