"""Voiceover synthesis and the audio-driven timeline.

Each script line is synthesised on its own with edge-tts so its
WordBoundary timings stay exact. Scene lengths come from the speech, with
spare time spread toward each beat's target window.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SR = 48000
TICKS = 10_000_000


@dataclass
class Word:
    text: str
    display: str
    t0: float
    t1: float


@dataclass
class Beat:
    index: int
    cfg: dict
    start: float
    end: float
    vstart: float
    vend: float
    words: list[Word] = field(default_factory=list)
    voice: np.ndarray | None = None

    @property
    def scene(self) -> str:
        return self.cfg["scene"]

    @property
    def line(self) -> str:
        return self.cfg["line"]

    def cue(self, name: str) -> float:
        spec = self.cfg.get("cues", {}).get(name)
        if spec is None:
            raise KeyError(f"beat {self.cfg['id']} has no cue {name!r}")
        word, _, nth = spec.partition("#")
        want = norm(word)
        hits = [w for w in self.words if norm(w.text) == want]
        if not hits:
            hits = [w for w in self.words if norm(w.text).startswith(want)]
        index = int(nth) - 1 if nth else 0
        if index >= len(hits):
            raise KeyError(f"cue {name!r} -> {spec!r} not spoken in: {self.line}")
        return hits[index].t0

    def label(self, name: str) -> str:
        return self.cfg["labels"][name]


@dataclass
class Timeline:
    cfg: dict
    beats: list[Beat]
    duration: float

    def beat_at(self, t: float) -> Beat:
        for beat in self.beats:
            if beat.start <= t < beat.end:
                return beat
        return self.beats[-1]

    @property
    def words(self) -> list[Word]:
        return [w for b in self.beats for w in b.words]


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9\-]", "", text.lower()).strip("-")


async def _synth(text: str, voice: str, rate: str, mp3: Path) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    marks: list[dict] = []
    with mp3.open("wb") as handle:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                handle.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                marks.append({"text": chunk["text"], "offset": chunk["offset"], "duration": chunk["duration"]})
    return marks


def synth_line(text: str, voice: str, rate: str, cache: Path) -> tuple[Path, list[dict]]:
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]
    mp3, meta = cache / f"{key}.mp3", cache / f"{key}.json"
    if mp3.is_file() and meta.is_file() and mp3.stat().st_size > 0:
        return mp3, json.loads(meta.read_text())
    last: Exception | None = None
    for _ in range(3):
        try:
            marks = asyncio.run(_synth(text, voice, rate, mp3))
            if marks and mp3.stat().st_size > 0:
                meta.write_text(json.dumps(marks, indent=1))
                return mp3, marks
            last = RuntimeError("edge-tts returned no audio or word boundaries")
        except Exception as exc:  # network hiccups are common; retry
            last = exc
    raise RuntimeError(f"edge-tts failed for {text!r}: {last}")


def decode(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(out, np.float32).copy()


def _display_words(line: str, marks: list[dict]) -> list[str]:
    tokens = line.split()
    out, j = [], 0
    for mark in marks:
        want = norm(mark["text"])
        shown = mark["text"].upper()
        for k in range(j, len(tokens)):
            if norm(tokens[k]) == want or norm(tokens[k]).startswith(want):
                shown = tokens[k].upper().rstrip(".:;")
                j = k + 1
                break
        out.append(shown)
    return out


def build(cfg: dict, cache: Path) -> Timeline:
    voice, rate = cfg["voice"], cfg["rate"]
    shared = {
        "left_name": cfg["left"]["name"],
        "right_name": cfg["right"]["name"],
        "left_short": cfg["left"]["short"],
        "right_short": cfg["right"]["short"],
        "left_mat": cfg["left"].get("material", "wood"),
        "right_mat": cfg["right"].get("material", "metal"),
        "handle": cfg["handle"],
    }
    clips = []
    for raw_cfg in cfg["beats"]:
        beat_cfg = {**shared, **raw_cfg}
        mp3, marks = synth_line(beat_cfg["line"], voice, rate, cache)
        audio = decode(mp3)
        speech_end = max((m["offset"] + m["duration"]) / TICKS for m in marks)
        clips.append((beat_cfg, marks, audio, speech_end))

    gap = cfg.get("gap", 0.3)
    natural, windows = [], []
    for beat_cfg, _marks, _audio, speech_end in clips:
        lead = beat_cfg.get("lead", 0.25)
        natural.append(lead + speech_end + gap + beat_cfg.get("tail", 0.0))
        windows.append(beat_cfg.get("window", 0.0))
    target = cfg.get("target_duration", 25.5)
    lengths = list(natural)
    spare = target - sum(natural)
    if spare > 0:
        extra = [max(0.0, w - n) for w, n in zip(windows, natural)]
        weights = extra if sum(extra) > 0 else [1.0] * len(lengths)
        total_w = sum(weights)
        lengths = [n + spare * w / total_w for n, w in zip(natural, weights)]

    beats, t = [], 0.0
    for i, ((beat_cfg, marks, audio, speech_end), length) in enumerate(zip(clips, lengths)):
        vstart = t + beat_cfg.get("lead", 0.25)
        shown = _display_words(beat_cfg["line"], marks)
        words = [
            Word(m["text"], s, vstart + m["offset"] / TICKS, vstart + (m["offset"] + m["duration"]) / TICKS)
            for m, s in zip(marks, shown)
        ]
        beats.append(Beat(i, beat_cfg, t, t + length, vstart, vstart + speech_end, words, audio))
        t += length
    duration = round(t * 30) / 30
    beats[-1].end = duration
    return Timeline(cfg, beats, duration)
