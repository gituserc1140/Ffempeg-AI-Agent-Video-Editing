"""Generated chiptune, retro sfx, voice ducking and loudness mastering."""
import json
import re
import subprocess
import wave

import numpy as np

from . import config as C

SR = C.SAMPLE_RATE
BPM = 120
BEAT = 60 / BPM
RNG = np.random.default_rng(3)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(n, attack=0.004, tau=0.15, release=0.01):
    t = np.arange(n) / SR
    e = np.minimum(1, t / attack) * np.exp(-t / tau)
    r = int(release * SR)
    if n > r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def square(freq, dur, duty=0.5, tau=0.15):
    t = _t(dur)
    return (((t * freq) % 1 < duty) * 2.0 - 1) * _env(len(t), tau=tau)


def triangle(freq, dur, tau=0.4):
    t = _t(dur)
    return (2 * np.abs(2 * ((t * freq) % 1) - 1) - 1) * _env(len(t), tau=tau)


def noise(dur, tau=0.05):
    n = int(dur * SR)
    return RNG.uniform(-1, 1, n) * _env(n, attack=0.001, tau=tau)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _add(buf, t0, sig, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G


def music(duration):
    buf = np.zeros(int(duration * SR) + SR)
    step = BEAT / 4
    for k in range(int(duration / step)):
        t0 = k * step
        bar = int(t0 / (BEAT * 4))
        chord = CHORDS[bar % 4]
        tone = chord[(0, 1, 2, 1)[k % 4]] + 12
        _add(buf, t0, square(midi(tone), step * 0.9, duty=0.25, tau=0.06), 0.16)
        if k % 2 == 0:
            _add(buf, t0, triangle(midi(chord[0] - 12), step * 1.8), 0.34)
        if k % 2 == 0:
            _add(buf, t0, noise(0.03, tau=0.01), 0.05)
        beat_pos = (k // 4) % 4
        if k % 4 == 0 and beat_pos in (0, 2):
            t = _t(0.14)
            _add(buf, t0, np.sin(2 * np.pi * (140 * t - 500 * t * t)) * np.exp(-t / 0.06), 0.45)
        if k % 4 == 0 and beat_pos in (1, 3):
            _add(buf, t0, noise(0.12, tau=0.04), 0.16)
    return buf[: int(duration * SR)]


def _sweep(f0, f1, dur, wave_fn="square", tau=0.08):
    t = _t(dur)
    f = f0 + (f1 - f0) * t / dur
    ph = np.cumsum(f) / SR
    base = (ph % 1 < 0.5) * 2.0 - 1 if wave_fn == "square" else 2 * (ph % 1) - 1
    return base * _env(len(t), tau=tau)


def _sfx(name):
    if name == "pop":
        return _sweep(380, 980, 0.1, tau=0.07) * 0.5
    if name == "impact":
        t = _t(0.18)
        return (noise(0.18, tau=0.04) * 0.5 + np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.07)) * 0.7
    if name == "bell":
        t = _t(0.9)
        s = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((880, 1), (1760, .5), (2640, .25)))
        return s * np.exp(-t / 0.25) * 0.28
    if name == "whoosh":
        n = noise(0.3, tau=0.12)
        k = 40
        return np.convolve(n, np.ones(k) / k, mode="same") * 2.2 * np.hanning(len(n))
    if name == "sparkle":
        out = np.zeros(int(0.3 * SR))
        for i, f in enumerate((1568, 2093, 2637, 3136)):
            _add(out, i * 0.045, triangle(f, 0.05, tau=0.03), 0.4)
        return out
    if name == "success":
        out = np.zeros(int(0.5 * SR))
        for i, n in enumerate((72, 76, 79, 84)):
            _add(out, i * 0.07, square(midi(n), 0.12, duty=0.25, tau=0.09), 0.38)
        return out
    if name == "fail":
        return _sweep(300, 120, 0.28, wave_fn="saw", tau=0.2) * 0.35
    raise KeyError(name)


def voice_track(plan):
    n = int(plan.duration * SR)
    buf = np.zeros(n)
    for ln in plan.lines:
        _add(buf, ln["start"], ln["audio"].astype(np.float64))
    return buf


def duck_gain(voice, depth=0.62):
    win = int(0.05 * SR)
    env = np.convolve(np.abs(voice), np.ones(win) / win, mode="same")
    active = (env > 0.01).astype(float)
    smooth = int(0.18 * SR)
    mask = np.convolve(active, np.ones(smooth) / smooth, mode="same")
    return 1 - depth * np.clip(mask * 1.6, 0, 1)


def mix(plan):
    n = int(plan.duration * SR)
    voice = voice_track(plan)
    mus = music(plan.duration + 1)[:n]
    mus = mus * duck_gain(voice)
    sfx = np.zeros(n)
    for t, name in plan.sfx:
        _add(sfx, t, _sfx(name), 1.0)
    mono = voice * 1.0 + mus * 0.55 + sfx * 0.55
    mono /= max(1.0, np.abs(mono).max() / 0.9)
    left = mono * 0.98 + np.roll(mus, 40) * 0.04
    right = mono * 0.98 + np.roll(mus, -40) * 0.04
    return np.stack([left, right], axis=1)


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# Glue compression + peak limiting before loudnorm so -14 LUFS fits under the peak ceiling.
PRE = "acompressor=threshold=0.12:ratio=3.5:attack=5:release=120:makeup=3,alimiter=limit=0.55:attack=3:release=60:level=false"


def master(src, dst):
    """Compress, then two-pass EBU R128 loudnorm to -14 LUFS with true peak <= -2 dBTP."""
    target = f"I={C.TARGET_LUFS}:TP=-2.0:LRA=11"
    first = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
         f"{PRE},loudnorm={target}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True).stderr
    stats = json.loads(first[first.rindex("{"):first.rindex("}") + 1])
    af = (f"{PRE},loudnorm={target}:measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
          f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
          f":offset={stats['target_offset']}:linear=true,alimiter=limit=0.8:level=false")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af,
                    "-ar", str(SR), "-ac", "2", str(dst)], check=True)


def measure(path):
    """Returns (integrated LUFS, true peak dBTP) using ebur128."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
         "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, check=True).stderr
    summary = err[err.rindex("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return lufs, peak
