"""Quality checks: safe zones, overlaps, text vs voiceover, dead air, ffprobe, contact sheet."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import palette as P
from .font import text_points
from .pixel import OUT_H, OUT_W, SAFE_BOTTOM, SAFE_TOP, STRIP_X, STRIP_Y0, STRIP_Y1, box_violations
from .timeline import Timeline, norm

ALIASES = {"vs": "versus", "1": "one", "2": "two", "3": "three", "4": "four", "&": "and"}
# Captions are the WordBoundary words themselves; the badge, round number
# and handle are channel furniture rather than claims about the topic.
UNCHECKED_KINDS = {"caption", "handle", "badge", "round"}


def text_issues(records: list[dict]) -> list[str]:
    issues = []
    seen = set()
    by_pose: dict[float, list[dict]] = {}
    for r in records:
        by_pose.setdefault(r["t"], []).append(r)
        problems = box_violations(tuple(r["box"]))
        if r["kind"] in ("moving", "round"):
            problems = [p for p in problems if p != "clipped by frame edge"]
        for p in problems:
            key = (r["text"], p)
            if key not in seen:
                seen.add(key)
                issues.append(f"{r['t']:.2f}s '{r['text']}' ({r['kind']}): {p}")
    card_kinds = {"round", "card", "moving"}
    for t, recs in sorted(by_pose.items()):
        for i, a in enumerate(recs):
            for b in recs[i + 1 :]:
                covered = a["beat"] != b["beat"] and (a["kind"] in card_kinds or b["kind"] in card_kinds)
                if not covered and _overlap(a["box"], b["box"]):
                    key = ("overlap", a["text"], b["text"])
                    if key not in seen:
                        seen.add(key)
                        issues.append(f"{t:.2f}s overlap: '{a['text']}' ({a['kind']}) and '{b['text']}' ({b['kind']})")
    return issues


def _overlap(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _tokens(text: str) -> list[str]:
    out = []
    for raw in re.split(r"[\s\-]+", text):
        if raw == "&":
            out.append("and")
            continue
        tok = norm(raw).replace("-", "")
        if tok:
            out.append(ALIASES.get(tok, tok))
    return out


def voice_issues(tl: Timeline, records: list[dict]) -> tuple[list[str], list[dict]]:
    issues, table = [], []
    for beat in tl.beats:
        spoken = {}
        for w in beat.words:
            for tok in _tokens(w.text):
                spoken.setdefault(tok, w.t0)
        script = [tok for tok in _tokens(beat.line)]
        said = [tok for w in beat.words for tok in _tokens(w.text)]
        if script != said:
            issues.append(f"beat {beat.cfg['id']}: TTS words {said} differ from script {script}")
        shown: dict[str, float] = {}
        for r in records:
            if r["beat"] == beat.cfg["id"] and r["kind"] not in UNCHECKED_KINDS:
                shown.setdefault(r["text"], r["t"])
        for text, first in shown.items():
            toks = _tokens(text)
            missing = [tok for tok in toks if tok not in spoken]
            spoken_at = max((spoken[tok] for tok in toks if tok in spoken), default=None)
            early = spoken_at is not None and first < spoken_at - 0.5
            table.append({"beat": beat.cfg["id"], "text": text, "shown": round(first, 2), "spoken": None if spoken_at is None else round(spoken_at, 2)})
            if missing:
                issues.append(f"beat {beat.cfg['id']}: on-screen '{text}' has words not in the voiceover: {missing}")
            if early:
                issues.append(f"beat {beat.cfg['id']}: '{text}' shows at {first:.2f}s, before it is said at {spoken_at:.2f}s")
    return issues, table


def dead_air(changes: list[tuple[float, int]], min_pixels: int = 12, seconds: float = 1.0) -> list[str]:
    issues, run_start = [], None
    for t, changed in changes:
        if changed < min_pixels:
            run_start = t if run_start is None else run_start
            if t - run_start > seconds:
                issues.append(f"little motion from {run_start:.2f}s")
                run_start = None
        else:
            run_start = None
    return issues


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,sample_rate,channels,duration:format=duration,size,bit_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    a = next(s for s in data["streams"] if s["codec_type"] == "audio")
    dur = float(data["format"]["duration"])
    checks = {
        "resolution 1080x1920": (v["width"], v["height"]) == (1080, 1920),
        "30 fps": v["r_frame_rate"] == "30/1" and v["avg_frame_rate"] == "30/1",
        "h264 yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
        "aac 48 kHz stereo": a["codec_name"] == "aac" and a["sample_rate"] == "48000" and a["channels"] == 2,
        "duration 24-27 s": 24.0 <= dur <= 27.0,
    }
    return {"video": v, "audio": a, "format": data["format"], "checks": checks}


def contact_sheet(video: Path, out: Path, duration: float, step: float = 0.75, cols: int = 7) -> int:
    times = [round(i * step, 2) for i in range(int(duration / step) + 1) if i * step < duration - 0.02]
    tw, th = OUT_W // 4, OUT_H // 4
    label_h = 22
    rows = (len(times) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 6, rows * (th + label_h) + (rows + 1) * 6 + 30), P.COLORS[P.NAVY])
    d = ImageDraw.Draw(sheet)
    _bitmap(d, "CONTACT SHEET  EVERY 0.75S  RED: UI SAFE LINES", 6, 8, 2, P.COLORS[P.CREAM])
    for k, t in enumerate(times):
        frame = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True,
        ).stdout
        img = Image.frombytes("RGB", (OUT_W, OUT_H), frame).resize((tw, th), Image.Resampling.BOX)
        fd = ImageDraw.Draw(img)
        fd.line([(0, SAFE_TOP // 4), (tw, SAFE_TOP // 4)], fill=(255, 40, 40), width=2)
        fd.line([(0, SAFE_BOTTOM // 4), (tw, SAFE_BOTTOM // 4)], fill=(255, 40, 40), width=2)
        fd.rectangle([STRIP_X // 4, STRIP_Y0 // 4, tw - 1, STRIP_Y1 // 4], outline=(40, 230, 255), width=2)
        r, c = divmod(k, cols)
        x = 6 + c * (tw + 6)
        y = 36 + r * (th + label_h + 6)
        sheet.paste(img, (x, y))
        _bitmap(d, f"{t:05.2f}S", x + 2, y + th + 4, 2, P.COLORS[P.YELLOW])
    sheet.save(out)
    return len(times)


def _bitmap(d: ImageDraw.ImageDraw, text: str, x: int, y: int, scale: int, color) -> None:
    for px, py in text_points(text, 0, 0, 1):
        d.rectangle([x + px * scale, y + py * scale, x + px * scale + scale - 1, y + py * scale + scale - 1], fill=color)
