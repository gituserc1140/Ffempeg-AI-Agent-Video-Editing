"""Word-by-word pixel captions driven by edge-tts WordBoundary timings."""

from __future__ import annotations

from . import palette as P
from .font import ADVANCE
from .pixel import Canvas, poses_since
from .timeline import Timeline, Word

MAX_CHARS = 13
CENTER_X = 46
BOX = (3, 89)
TWO_ROWS = (135, 145)
ONE_ROW = (142,)
LEAD, HOLD = 0.08, 0.35


def paginate(words: list[Word]) -> list[list[list[int]]]:
    rows: list[list[int]] = []
    current: list[int] = []
    length = 0
    for i, w in enumerate(words):
        add = len(w.display) + (1 if current else 0)
        if current and length + add > MAX_CHARS:
            rows.append(current)
            current, length = [], 0
            add = len(w.display)
        current.append(i)
        length += add
    if current:
        rows.append(current)
    return [rows[i : i + 2] for i in range(0, len(rows), 2)]


def draw(cv: Canvas, t: float, tl: Timeline) -> None:
    for beat in tl.beats:
        words = beat.words
        if not words or not (words[0].t0 - LEAD <= t < words[-1].t1 + HOLD):
            continue
        spoken = [i for i, w in enumerate(words) if w.t0 <= t]
        current = spoken[-1] if spoken else 0
        page = next(p for p in paginate(words) if any(current in row for row in p))
        ys = TWO_ROWS if len(page) == 2 else ONE_ROW
        top = ys[0] - 3 if len(page) == 2 else ys[0] - 4
        cv.box(BOX[0], top, BOX[1], 152, fill=P.NAVY, outline=P.NAVY2)
        for row, y in zip(page, ys):
            text_len = sum(len(words[i].display) for i in row) + len(row) - 1
            x = CENTER_X - (text_len * ADVANCE - 1) // 2
            for i in row:
                lit = bool(spoken) and i == current
                dy = -1 if lit and poses_since(t, words[i].t0) == 0 else 0
                color = P.YELLOW if lit else (P.CREAM if i <= current or not spoken else P.STEEL2)
                cv.text(words[i].display, x, y + dy, color=color, kind="caption", align="left", clamp=False)
                x += (len(words[i].display) + 1) * ADVANCE
        return
