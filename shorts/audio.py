"""Chiptune music, retro sound effects, mixing and loudness, all in numpy."""

from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 48000


@dataclass
class Sfx:
    t: float
    name: str
    gain: float = 1.0
    pan: float = 0.0


def midi_hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def square(phase: np.ndarray, duty: float = 0.5) -> np.ndarray:
    return np.where((phase % 1.0) < duty, 1.0, -1.0)


def triangle(phase: np.ndarray) -> np.ndarray:
    return 4.0 * np.abs((phase % 1.0) - 0.5) - 1.0


def noise(n: int, seed: int, hold: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.repeat(rng.uniform(-1, 1, n // hold + 1), hold)[:n]


def env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / max(decay, 1e-4))


def place(buf: np.ndarray, t0: float, sig: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(round(t0 * SR))
    if i >= len(buf) or len(sig) == 0:
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), len(buf) - i)
    ang = (max(-1.0, min(1.0, pan)) + 1) * math.pi / 4
    buf[i : i + n, 0] += sig[:n] * gain * math.cos(ang) * math.sqrt(2)
    buf[i : i + n, 1] += sig[:n] * gain * math.sin(ang) * math.sqrt(2)


def sweep_phase(f0: float, f1: float, dur: float, curve: float = 6.0) -> np.ndarray:
    t = _t(dur)
    f = f1 + (f0 - f1) * np.exp(-t * curve / dur)
    return np.cumsum(f) / SR


# Music --------------------------------------------------------------------

CHORDS = [(57, (0, 3, 7)), (53, (0, 4, 7)), (55, (0, 4, 7)), (52, (0, 4, 7))]  # Am F G E
BASS = (0, 0, 12, 0, 0, 12, 0, 7)
STABS = (0, 3, 6, 8, 11, 14)


def kick() -> np.ndarray:
    ph = sweep_phase(170, 42, 0.16, 5.0)
    return triangle(ph) * env(len(ph), 0.001, 0.07)


def snare(seed: int) -> np.ndarray:
    n = int(0.16 * SR)
    body = triangle(np.cumsum(np.full(n, 190.0)) / SR) * env(n, 0.001, 0.03)
    return 0.8 * noise(n, seed, 2) * env(n, 0.001, 0.05) + 0.5 * body


def hat(seed: int, open_: bool = False) -> np.ndarray:
    n = int((0.12 if open_ else 0.04) * SR)
    x = noise(n, seed, 1)
    x = np.diff(x, prepend=0.0)
    return x * env(n, 0.0005, 0.05 if open_ else 0.012)


def tone(freq: float, dur: float, wave: str, duty: float = 0.5, decay: float = 0.1) -> np.ndarray:
    ph = freq * _t(dur)
    sig = triangle(ph) if wave == "tri" else square(ph, duty)
    e = env(len(ph), 0.002, decay)
    tail = min(len(e), int(0.01 * SR))
    if tail:
        e[-tail:] *= np.linspace(1, 0, tail)
    return sig * e


def music(duration: float, bpm: float = 120.0, end_hit: float | None = None) -> np.ndarray:
    buf = np.zeros((int(round(duration * SR)), 2))
    step = 60.0 / bpm / 4
    bar = step * 16
    for b in range(int(math.ceil(duration / bar)) + 1):
        root, triad = CHORDS[b % len(CHORDS)]
        t_bar = b * bar
        for i, off in enumerate(BASS):
            place(buf, t_bar + i * step * 2, tone(midi_hz(root - 24 + off), step * 1.8, "tri", decay=0.12), 0.55)
        for k, s in enumerate(STABS):
            for j, iv in enumerate(triad):
                place(
                    buf,
                    t_bar + s * step,
                    tone(midi_hz(root + 12 + iv), step * 0.8, "sq", 0.25, 0.05),
                    0.07,
                    -0.35 if k % 2 else 0.35,
                )
        for s in range(16):
            iv = (triad + (12,))[s % 4]
            place(buf, t_bar + s * step, tone(midi_hz(root + 24 + iv), step * 0.6, "sq", 0.125, 0.03), 0.025, 0.4)
        for s in (0, 8, 10):
            place(buf, t_bar + s * step, kick(), 0.75)
        for s in (4, 12):
            place(buf, t_bar + s * step, snare(b * 16 + s), 0.32)
        for s in range(0, 16, 2):
            place(buf, t_bar + s * step, hat(b * 31 + s, open_=(s == 14)), 0.18, 0.2)
    if end_hit is not None:
        root, triad = CHORDS[0]
        for iv in triad:
            place(buf, end_hit, tone(midi_hz(root + iv), 1.2, "sq", 0.5, 0.45), 0.08)
        place(buf, end_hit, kick(), 0.9)
        place(buf, end_hit, hat(99, open_=True), 0.3)
    fade = int(0.6 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return buf


# Sound effects ------------------------------------------------------------


def sfx_bell() -> np.ndarray:
    out = np.zeros(int(1.3 * SR))
    for start in (0.0, 0.2):
        t = _t(1.1)
        f = 1046.5
        s = (
            np.sin(2 * math.pi * f * t) * np.exp(-t * 3.5)
            + 0.5 * np.sin(2 * math.pi * f * 2.76 * t) * np.exp(-t * 6)
            + 0.25 * square(f * 4.07 * t, 0.5) * np.exp(-t * 18)
        )
        i = int(start * SR)
        out[i : i + len(s)] += s * (1.0 if start == 0 else 0.8)
    return out / 1.6


def sfx_impact() -> np.ndarray:
    n = int(0.35 * SR)
    boom = triangle(sweep_phase(130, 35, 0.35, 4.0)) * env(n, 0.001, 0.12)
    crunch = noise(n, 41, 6) * env(n, 0.001, 0.05)
    return 0.9 * boom + 0.6 * crunch


def sfx_whoosh(dur: float = 0.35, seed: int = 5) -> np.ndarray:
    n = int(dur * SR)
    x = noise(n, seed, 1)
    shape = np.sin(np.linspace(0, math.pi, n)) ** 2
    cutoff = 0.04 + 0.4 * np.sin(np.linspace(0, math.pi, n))
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += cutoff[i] * (x[i] - acc)
        y[i] = acc
    return y * shape * 2.2


def sfx_blip(high: bool = False) -> np.ndarray:
    a = tone(1320 if high else 880, 0.04, "sq", 0.5, 0.05)
    b = tone(1760 if high else 1175, 0.06, "sq", 0.5, 0.05)
    return np.concatenate([a, b]) * 0.6


def sfx_ting() -> np.ndarray:
    parts = [tone(midi_hz(n), 0.07, "sq", 0.125, 0.05) for n in (84, 88, 91, 96)]
    return np.concatenate(parts) * 0.5


def sfx_rasp(dur: float = 0.9) -> np.ndarray:
    n = int(dur * SR)
    x = np.diff(noise(n, 77, 2), prepend=0.0)
    t = _t(dur)
    strokes = np.abs(np.sin(2 * math.pi * 6.0 * t)) ** 1.5
    fade = np.minimum(1, np.minimum(t / 0.03, (dur - t) / 0.08))
    return x * strokes * fade * 0.7


def sfx_clank() -> np.ndarray:
    t = _t(0.5)
    s = sum(
        g * square(f * t, 0.5) * np.exp(-t * d)
        for f, g, d in ((523, 0.5, 9), (1187, 0.35, 14), (1790, 0.25, 20), (2630, 0.15, 30))
    )
    click = noise(len(t), 9, 1) * np.exp(-t * 120)
    return (s + 0.6 * click) * 0.6


def sfx_grind(dur: float = 0.8) -> np.ndarray:
    t = _t(dur)
    buzz = square(np.cumsum(220 + 60 * np.sin(2 * math.pi * 9 * t)) / SR, 0.3)
    fade = np.minimum(1, np.minimum(t / 0.02, (dur - t) / 0.1))
    return (0.4 * buzz + 0.5 * sfx_rasp(dur)) * fade * 0.7


SFX_BANK = {
    "bell": sfx_bell,
    "impact": sfx_impact,
    "whoosh": sfx_whoosh,
    "blip": sfx_blip,
    "blip_hi": lambda: sfx_blip(True),
    "ting": sfx_ting,
    "rasp": sfx_rasp,
    "clank": sfx_clank,
    "grind": sfx_grind,
}


# Mixing -------------------------------------------------------------------


def _smooth(x: np.ndarray, seconds: float) -> np.ndarray:
    k = max(1, int(seconds * SR))
    return np.convolve(x, np.ones(k) / k, mode="same")


def duck_curve(voice: np.ndarray, depth_db: float = -11.0) -> np.ndarray:
    level = _smooth(np.abs(voice), 0.03)
    active = (level > 0.015).astype(float)
    active = np.clip(_smooth(active, 0.25) * 2.0, 0, 1)
    return 1.0 - (1.0 - 10 ** (depth_db / 20)) * active


def limiter(x: np.ndarray, ceiling_db: float) -> np.ndarray:
    """Look-ahead brickwall on sample peaks. The gain never rises above 1."""
    c = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x), axis=1)
    g = np.minimum(1.0, c / np.maximum(peak, 1e-9))
    m = g.copy()
    w = 1
    while w < 128:
        m = np.minimum(m, np.minimum(np.roll(m, w), np.roll(m, -w)))
        w *= 2
    smooth = np.convolve(m, np.ones(96) / 96, mode="same")
    return x * smooth[:, None]


def mix(duration: float, voice: np.ndarray, events: list[Sfx], end_hit: float) -> np.ndarray:
    n = int(round(duration * SR))
    voice = voice[:n] if len(voice) >= n else np.pad(voice, (0, n - len(voice)))
    peak = np.max(np.abs(voice)) or 1.0
    voice = voice / peak * 0.9
    m = music(duration, end_hit=end_hit)[:n]
    m *= 0.5 * duck_curve(voice)[:, None]
    fx = np.zeros((n, 2))
    cache: dict[str, np.ndarray] = {}
    for ev in events:
        if ev.name not in cache:
            cache[ev.name] = SFX_BANK[ev.name]()
        place(fx, ev.t, cache[ev.name], 0.42 * ev.gain, ev.pan)
    out = m + fx
    out[:, 0] += voice
    out[:, 1] += voice
    return out


def write_raw(x: np.ndarray, path: Path) -> None:
    path.write_bytes(np.ascontiguousarray(x, dtype=np.float32).tobytes())


RAW_IN = ["-f", "f32le", "-ar", str(SR), "-ac", "2"]


def ebur128(input_args: list[str]) -> dict[str, float]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", *input_args, "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-800:])
    summary = proc.stderr.rsplit("Summary:", 1)[-1]
    i_match = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", summary)
    peak = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not i_match or not peak:
        raise RuntimeError(f"could not parse ebur128 summary:\n{summary[-800:]}")
    return {
        "integrated_lufs": float(i_match.group(1)),
        "true_peak_dbfs": float(peak.group(1)),
        "lra_lu": float(lra.group(1)) if lra else float("nan"),
    }


def master(x: np.ndarray, work: Path, target: float = -14.0, tp_max: float = -1.0) -> tuple[Path, dict]:
    """Normalise to `target` LUFS with true peak under `tp_max`, encode AAC, verify."""
    raw = work / "mix.raw"
    m4a = work / "mix.m4a"
    ceiling = tp_max - 1.0
    stats: dict = {}
    for _attempt in range(4):
        y = x.copy()
        for _ in range(3):
            write_raw(y, raw)
            measured = ebur128([*RAW_IN, "-i", str(raw)])["integrated_lufs"]
            y = limiter(y * 10 ** ((target - measured) / 20), ceiling)
        write_raw(y, raw)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", *RAW_IN, "-i", str(raw), "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2", str(m4a)],
            check=True,
        )
        stats = ebur128(["-i", str(m4a)])
        stats["limiter_ceiling_dbfs"] = ceiling
        if stats["true_peak_dbfs"] < tp_max and abs(stats["integrated_lufs"] - target) <= 1.0:
            break
        ceiling -= 0.5
    return m4a, stats
