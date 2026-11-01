"""Word-synced timeline: places each spoken sentence, finds trigger words and derives scene windows."""
from dataclasses import dataclass, field

import numpy as np

from pipeline.tts import normalize_token

SCRIPT = [
    "A printer with nine heads is about to be revealed.",
    "Here's why people care.",
    "A normal single-nozzle printer changes colour by pushing the old colour out first.",
    "That leaves a pile of waste.",
    "A tool changer parks whole heads and picks up the next one, so less colour gets pushed out.",
    "The trade-offs: more parts, a bigger machine, and the price is still unknown.",
    "Reveal's on the third of November.",
    "Which colour goes in slot nine?",
]
LEAD_IN, LINE_GAP = 0.3, 0.2
TOTAL = 26.0
CARD_MIN = 23.8
SR = 48000


@dataclass
class Plan:
    duration: float
    lines: list
    words: list           # flat [(display, start, end, line_index)]
    ev: dict
    scenes: list          # [(name, t0, t1)]
    sfx: list = field(default_factory=list)


def trim(ln):
    """Drop the silent tail the TTS leaves after the last word."""
    keep = int((ln["words"][-1][1][1] + 0.2) * SR)
    audio = ln["audio"][:keep].copy()
    fade = min(len(audio), int(0.05 * SR))
    audio[-fade:] *= np.linspace(1, 0, fade)
    return dict(ln, audio=audio)


def build(lines):
    lines = [trim(ln) for ln in lines]
    placed, t = [], LEAD_IN
    for ln in lines:
        placed.append(t)
        t += len(ln["audio"]) / SR + LINE_GAP
    words = []
    for i, (ln, t0) in enumerate(zip(lines, placed)):
        for tok, (s, e) in ln["words"]:
            words.append((tok, t0 + s, t0 + e, i))
    voice_end = max(w[2] for w in words)

    def w(line, key, nth=0):
        hits = [x for x in words if x[3] == line and normalize_token(x[0]) == key]
        if len(hits) <= nth:
            raise KeyError((line, key, nth))
        return hits[nth][1]

    card = max(voice_end + 0.3, CARD_MIN)
    ev = {
        "nine": w(0, "nine"), "revealed": w(0, "revealed"), "why": w(1, "here's"),
        "s3": placed[2], "single": w(2, "singlenozzle"), "colour": w(2, "colour"),
        "pushing": w(2, "pushing"),
        "s4": placed[3], "waste": w(3, "waste"),
        "s5": placed[4], "parks": w(4, "parks"), "picks": w(4, "picks"), "less": w(4, "so"),
        "s6": placed[5], "more": w(5, "more"), "bigger": w(5, "bigger"),
        "price": w(5, "price"), "unknown": w(5, "unknown"),
        "s7": placed[6], "third": w(6, "third"), "november": w(6, "november"),
        "s8": placed[7], "slot": w(7, "slot"), "end": voice_end, "card": card,
    }
    scenes = [("hook", 0.0, ev["s3"] - 0.05), ("single", ev["s3"] - 0.05, ev["s4"] - 0.05),
              ("waste", ev["s4"] - 0.05, ev["s5"] - 0.05), ("changer", ev["s5"] - 0.05, ev["less"] - 0.05),
              ("less", ev["less"] - 0.05, ev["s6"] - 0.05), ("trade", ev["s6"] - 0.05, ev["s7"] - 0.05),
              ("reveal", ev["s7"] - 0.05, card), ("card", card, TOTAL)]
    return Plan(TOTAL, lines, words, ev, scenes)


def scene_at(plan, t):
    for i, (name, a, b) in enumerate(plan.scenes):
        if a <= t < b:
            return i, name, a, b
    n = len(plan.scenes) - 1
    return n, plan.scenes[n][0], plan.scenes[n][1], plan.scenes[n][2]
