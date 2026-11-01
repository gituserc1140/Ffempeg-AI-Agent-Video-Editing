"""Chiptune (~94 bpm, D major: D - Bm - G - A), code-made SFX, ducking and mastering."""
import numpy as np

from pipeline import audio as A
from pipeline.audio import SR, _add, _sweep, midi, noise, square, triangle

BPM = 94
BEAT = 60 / BPM
S16 = BEAT / 4
SWING = 0.58                      # first 16th of each pair takes 58% of the pair
CHORDS = [(50, 54, 57), (47, 50, 54), (55, 59, 62), (57, 61, 64)]  # D, Bm, G, A (root + triad)
ROOTS = [38, 35, 43, 45]


def _t(d):
    return np.arange(int(d * SR)) / SR


def step_time(k):
    pair, odd = divmod(k, 2)
    return pair * 2 * S16 + (2 * S16 * SWING if odd else 0)


def music(duration):
    buf = np.zeros(int(duration * SR) + SR)
    steps = int(duration / S16) + 1
    for k in range(steps):
        t0 = step_time(k)
        bar = (k // 16) % 4
        pos = k % 16
        chord, root = CHORDS[bar], ROOTS[bar]
        # nine-step arpeggio: triad tones climbing over three octaves, cycles every 9 sixteenths
        i = k % 9
        note = chord[i % 3] + 12 * (i // 3 + 1)
        _add(buf, t0, square(midi(note), S16 * 0.95, duty=0.25, tau=0.07), 0.10)
        # bass: square + triangle on eighth-note pattern
        if pos in (0, 3, 6, 8, 11, 14):
            n = root + (12 if pos in (6, 14) else 0)
            _add(buf, t0, square(midi(n), S16 * 1.7, duty=0.5, tau=0.18), 0.12)
            _add(buf, t0, triangle(midi(n), S16 * 1.9, tau=0.3), 0.30)
        # triangle kick on 1 and 3 (+ a pickup)
        if pos in (0, 8, 10):
            t = _t(0.16)
            ph = np.cumsum(45 + 120 * np.exp(-t / 0.03)) / SR
            _add(buf, t0, (2 * np.abs(2 * (ph % 1) - 1) - 1) * np.exp(-t / 0.07), 0.55)
        # noise snare on 2 and 4
        if pos in (4, 12):
            _add(buf, t0, noise(0.14, tau=0.045), 0.20)
            _add(buf, t0, triangle(190, 0.08, tau=0.03), 0.10)
        if pos % 2 == 0:
            _add(buf, t0, noise(0.025, tau=0.01), 0.04)
    return buf[: int(duration * SR)]


def _sfx(name):
    if name == "whirr":   # stepper motor: pulsed square rising in pitch
        t = _t(0.5)
        f = 140 + 90 * t / 0.5
        ph = np.cumsum(f) / SR
        pulse = ((t * 38) % 1 < 0.5) * 0.6 + 0.4
        return (((ph % 1) < 0.5) * 2.0 - 1) * pulse * np.minimum(1, t / 0.03) * np.minimum(1, (0.5 - t) / 0.08) * 0.28
    if name == "clack":
        t = _t(0.16)
        return (noise(0.16, tau=0.018) * 0.7 + np.sin(2 * np.pi * 220 * t) * np.exp(-t / 0.04)) * 0.9
    if name == "latch":
        out = np.zeros(int(0.22 * SR))
        _add(out, 0.0, noise(0.04, tau=0.01), 0.7)
        _add(out, 0.09, noise(0.05, tau=0.012), 0.8)
        _add(out, 0.09, square(1300, 0.06, tau=0.03), 0.25)
        return out
    if name == "purge":
        n = noise(0.7, tau=0.5)
        k = 14
        lp = np.convolve(n, np.ones(k) / k, mode="same")
        t = _t(0.7)
        return lp * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * t)) * 2.4 * np.hanning(len(t)) ** 0.5 * 0.5
    if name == "plop":
        t = _t(0.14)
        f = 700 - 500 * t / 0.14
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * 0.6
    if name == "chime":
        t = _t(0.9)
        s = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1175, 1), (1760, .6), (2349, .3)))
        return s * np.exp(-t / 0.25) * 0.26
    if name == "pop":
        return _sweep(380, 980, 0.1, tau=0.07) * 0.5
    if name == "sparkle":
        out = np.zeros(int(0.4 * SR))
        for i, f in enumerate((1568, 2093, 2349, 2637, 3136, 4186)):
            _add(out, i * 0.05, triangle(f, 0.06, tau=0.035), 0.4)
        return out
    if name == "sting":
        out = np.zeros(int(1.4 * SR))
        for n in (62, 66, 69, 74):
            _add(out, 0.0, square(midi(n), 1.2, duty=0.25, tau=0.5), 0.2)
        _add(out, 0.0, triangle(midi(38), 1.2, tau=0.6), 0.5)
        return out
    if name == "whoosh":
        n = noise(0.3, tau=0.12)
        return np.convolve(n, np.ones(40) / 40, mode="same") * 2.2 * np.hanning(len(n)) * 0.7
    raise KeyError(name)


def duck_gain(voice, depth=0.55):
    return A.duck_gain(voice, depth)


def mix(duration, voice_lines, sfx):
    """voice_lines: [(start, mono float array)], sfx: [(t, name)] -> stereo array."""
    n = int(duration * SR)
    voice = np.zeros(n)
    for t0, sig in voice_lines:
        _add(voice, t0, sig.astype(np.float64))
    mus = music(duration + 1)[:n]
    mus = mus * duck_gain(voice)
    fx = np.zeros(n)
    for t, name in sfx:
        _add(fx, t, _sfx(name), 1.0)
    # the end card has no voice, so lift the music there to keep loudness level
    t = np.arange(n) / SR
    mus = mus * (1 + 0.8 * np.clip((t - (duration - 2.6)) / 0.3, 0, 1))
    mono = voice + mus * 0.6 + fx * 0.6
    mono /= max(1.0, np.abs(mono).max() / 0.9)
    left = mono * 0.98 + np.roll(mus, 40) * 0.04
    right = mono * 0.98 + np.roll(mus, -40) * 0.04
    return np.stack([left, right], axis=1)
