"""Builds the beat/word/sfx timeline from the generated audio."""
import math
from dataclasses import dataclass, field

from . import config as C
from .tts import normalize_token

SR = C.SAMPLE_RATE


@dataclass
class Plan:
    brief: dict
    beats: list = field(default_factory=list)
    words: list = field(default_factory=list)      # {text, start, end, line}
    lines: list = field(default_factory=list)      # {start, end, audio}
    sfx: list = field(default_factory=list)        # (time, name)
    duration: float = 0.0
    frames: int = 0
    chunks: list = field(default_factory=list)


def _chunk_words(words, max_chars=14):
    """Group words into caption chunks of at most two lines of max_chars."""
    chunks, cur_lines, cur = [], [], []
    line_len = 0

    def flush():
        nonlocal cur_lines, cur, line_len
        if cur:
            cur_lines.append(cur)
        if cur_lines:
            chunks.append(cur_lines)
        cur_lines, cur, line_len = [], [], 0

    for w in words:
        n = len(w["text"])
        add = n + (1 if cur else 0)
        if cur and line_len + add > max_chars:
            cur_lines.append(cur)
            cur, line_len = [], 0
            add = n
            if len(cur_lines) == 2:
                flush()
        cur.append(w)
        line_len += add
    flush()
    return chunks


def build(brief, voice):
    plan = Plan(brief=brief)
    t = C.LEAD_IN
    for li, ln in enumerate(voice):
        dur = len(ln["audio"]) / SR
        plan.lines.append(dict(start=t, end=t + dur, audio=ln["audio"], text=ln["text"]))
        for tok, (a, b) in ln["words"]:
            plan.words.append(dict(text=tok, start=t + a, end=t + b, line=li))
        t += dur + C.LINE_GAP
    voice_end = plan.lines[-1]["end"]
    total = max(C.MIN_DUR, voice_end + C.END_TAIL_MIN)
    if total > C.MAX_DUR:
        raise ValueError(f"video would run {total:.1f}s (max {C.MAX_DUR}s); script too long")
    plan.frames = math.ceil(total * C.FPS)
    plan.duration = plan.frames / C.FPS

    starts = [0.0] + [max(0.0, ln["start"] - 0.05) for ln in plan.lines[1:]]
    for i, beat in enumerate(brief["beats"]):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(starts) else plan.duration
        trig = None
        for w in plan.words:
            if w["line"] == i and normalize_token(w["text"]) == normalize_token(beat["trigger"]):
                trig = w["start"]
                break
        if trig is None:
            trig = plan.lines[i]["start"]
        trig = min(max(trig, start + 0.2), end - 0.3)
        plan.beats.append(dict(beat, start=start, end=end, trig=trig,
                               keyword=beat["trigger"].upper()))
    plan.sfx = _sfx(plan)
    plan.chunks = _chunk_words(plan.words)
    return plan


def _sfx(plan):
    ev = []
    for b in plan.beats:
        s, tr = b["start"], b["trig"]
        kind = b["scene"]
        if kind == "hook":
            ev += [(tr, "pop"), (tr + 0.02, "impact"), (tr + 0.1, "sparkle")]
        elif kind == "icon":
            ev += [(tr, "pop"), (tr + 0.02, "impact")]
        elif kind == "card":
            ev += [(tr - 0.05, "whoosh"), (tr + 0.12, "bell")]
        elif kind == "fix":
            ev += [(s + 0.15, "fail"), (tr, "success"), (tr + 0.05, "sparkle")]
        elif kind == "end":
            ev += [(tr, "success"), (tr + 0.1, "sparkle"), (tr + 0.02, "impact")]
    return sorted((max(0.0, t), n) for t, n in ev)
