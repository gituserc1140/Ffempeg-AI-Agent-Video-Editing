"""Voice: edge-tts with WordBoundary timings, offline espeak-ng fallback."""
import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from . import config as C

SR = C.SAMPLE_RATE


def _decode(path):
    """Any audio file -> mono float32 at 48 kHz."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
         "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def _spread(tokens, events, span):
    """Assign (start, end) to each token. Use real boundaries when counts match,
    otherwise spread tokens over the spoken span by character weight."""
    if events and len(events) == len(tokens):
        return [(s, e) for s, e in events]
    start, end = span
    weights = [len(t) + 1 for t in tokens]
    total = sum(weights)
    out, acc = [], 0
    for w in weights:
        a = start + (end - start) * acc / total
        acc += w
        out.append((a, start + (end - start) * acc / total))
    return out


def _speech_span(audio):
    env = np.abs(audio)
    idx = np.where(env > 0.02)[0]
    if len(idx) == 0:
        return 0.0, len(audio) / SR
    return idx[0] / SR, idx[-1] / SR


async def _edge_line(text, mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, C.VOICE, rate=C.VOICE_RATE, boundary="WordBoundary")
    events = []
    with open(mp3, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                events.append((s, s + chunk["duration"] / 1e7))
    return events


def _edge(lines, tmp):
    out = []
    for i, text in enumerate(lines):
        mp3 = Path(tmp) / f"line{i}.mp3"
        last = None
        for _ in range(3):
            try:
                events = asyncio.run(asyncio.wait_for(_edge_line(text, mp3), 45))
                if mp3.stat().st_size < 1000:
                    raise RuntimeError("empty audio")
                break
            except Exception as exc:  # network, rate limiting, bad IP range
                last = exc
        else:
            raise RuntimeError(f"edge-tts failed: {last}")
        audio = _decode(mp3)
        tokens = text.split()
        times = _spread(tokens, events, _speech_span(audio))
        out.append(dict(text=text, audio=audio, words=list(zip(tokens, times))))
    return out


def _espeak(lines, tmp):
    if not shutil.which("espeak-ng"):
        raise RuntimeError("neither edge-tts nor espeak-ng is available")
    out = []
    for i, text in enumerate(lines):
        wav = Path(tmp) / f"line{i}.wav"
        subprocess.run(["espeak-ng", "-v", "en-us+m3", "-s", "200", "-p", "38",
                        "-w", str(wav), text], check=True, capture_output=True)
        audio = _decode(wav)
        audio = audio / max(1e-6, np.abs(audio).max()) * 0.8
        tokens = text.split()
        out.append(dict(text=text, audio=audio,
                        words=list(zip(tokens, _spread(tokens, [], _speech_span(audio))))))
    return out


def synthesize(lines, force_fallback=False):
    """Returns (engine_name, [ {text, audio, words:[(token,(start,end))]} ])."""
    with tempfile.TemporaryDirectory() as tmp:
        if not force_fallback:
            try:
                return "edge-tts", _edge(lines, tmp)
            except Exception as exc:
                print(f"[tts] {exc}; using offline espeak-ng fallback")
        return "espeak-ng (fallback)", _espeak(lines, tmp)


def normalize_token(tok):
    return re.sub(r"[^a-z0-9']", "", tok.lower())
