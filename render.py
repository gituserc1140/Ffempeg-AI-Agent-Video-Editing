#!/usr/bin/env python3
"""Build the pixel-art versus short: voice, timeline, music, frames, mux, QC.

    python3 render.py                       # default topic
    python3 render.py --config shorts/topics/other.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from shorts import audio, captions, palette, qc, scenes, timeline
from shorts.pixel import (
    FPS,
    OUT_H,
    OUT_W,
    Canvas,
    build_background,
    pose_of_frame,
    pose_time,
    poses_since,
    shaken,
    shine_streak,
    to_output,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "shorts" / "topics" / "wood_vs_metal_pla.json"
SHAKE_PATTERN = ((1, -1), (-1, 1), (1, 0))


def shake_offset(t: float, shakes: list[tuple[float, int]]) -> tuple[int, int]:
    best = (0, 0)
    for ts, strength in shakes:
        n = poses_since(t, ts)
        if 0 <= n < len(SHAKE_PATTERN):
            s = max(1, strength - (1 if n == 2 else 0))
            dx, dy = SHAKE_PATTERN[n]
            if s > abs(best[0]):
                best = (dx * s, dy * min(s, 1))
    return best


def collect_events(tl: timeline.Timeline) -> tuple[list[audio.Sfx], list[tuple[float, int]]]:
    sfx, shakes = [], []
    for beat in tl.beats:
        _draw, events = scenes.SCENES[beat.scene]
        s, k = events(beat)
        sfx += scenes.card_events(beat) + s
        shakes += k
    return sfx, shakes


def voice_track(tl: timeline.Timeline, n: int) -> np.ndarray:
    out = np.zeros(n, np.float32)
    for beat in tl.beats:
        i = int(round(beat.vstart * audio.SR))
        clip = beat.voice[: max(0, n - i)]
        out[i : i + len(clip)] += clip
    return out


def render_pose(t: float, tl: timeline.Timeline, bg, shakes) -> tuple[Canvas, Canvas]:
    beat = tl.beat_at(t)
    shown = beat if scenes.entered(beat, t) else tl.beats[beat.index - 1]
    cv = Canvas.from_background(bg)
    shine_streak(cv, t)
    draw, _events = scenes.SCENES[shown.scene]
    cv.owner = shown.cfg["id"]
    scenes.small_badge(cv, shown, t)
    draw(cv, t, shown)
    if shown is not beat:
        scenes.round_card(cv, t, shown)
    cv.owner = beat.cfg["id"]
    scenes.round_card(cv, t, beat)
    dx, dy = shake_offset(t, shakes)
    for rec in cv.texts:
        x0, y0, x1, y1 = rec.box
        rec.box = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    final = Canvas(shaken(cv.img, bg, dx, dy), texts=cv.texts, owner="captions")
    captions.draw(final, t, tl)
    return final, cv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--build", type=Path, default=ROOT / "build")
    args = ap.parse_args()

    started = time.time()
    cfg = json.loads(args.config.read_text())
    out_mp4 = ROOT / cfg["output"]
    out_dir = out_mp4.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    work = args.build / out_mp4.stem
    work.mkdir(parents=True, exist_ok=True)

    theme = cfg.get("theme", "wood-metal")
    palette.apply_theme(theme)
    print(f"[1/5] voiceover: {cfg['voice']} {cfg['rate']}  palette {theme}")
    tl = timeline.build(cfg, args.build / "tts")
    n_frames = int(round(tl.duration * FPS))
    duration = n_frames / FPS
    words = sum(len(b.line.split()) for b in tl.beats)
    print(f"      {len(tl.beats)} lines, {words} words, video {duration:.2f}s")
    for b in tl.beats:
        print(f"      {b.cfg['id']:<10} {b.start:6.2f}-{b.end:6.2f}s  voice {b.vstart:5.2f}-{b.vend:5.2f}s  {b.line}")

    print("[2/5] music, effects, mix, loudness")
    sfx, shakes = collect_events(tl)
    n_samples = int(round(duration * audio.SR))
    voice = voice_track(tl, n_samples)
    mixed = audio.mix(duration, voice, sfx, end_hit=tl.beats[-1].cue("follow"))
    m4a, loud = audio.master(mixed, work)
    print(f"      {loud['integrated_lufs']:.1f} LUFS, true peak {loud['true_peak_dbfs']:.1f} dBFS")

    print(f"[3/5] frames: {n_frames} at {FPS} fps, {OUT_W}x{OUT_H}")
    bg = build_background(theme=theme)
    enc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-framerate", str(FPS), "-i", "-",
            "-i", str(m4a),
            "-map", "0:v", "-map", "1:a",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "copy", "-t", f"{duration:.3f}", "-movflags", "+faststart",
            str(out_mp4),
        ],
        stdin=subprocess.PIPE,
    )
    records, changes = [], []
    last_pose, frame_bytes, prev = -1, b"", None
    for f in range(n_frames):
        pose = pose_of_frame(f)
        if pose != last_pose:
            t = pose_time(pose)
            final, _scene = render_pose(t, tl, bg, shakes)
            for rec in final.texts:
                records.append({"t": round(t, 3), "beat": rec.owner, "text": rec.text, "box": list(rec.box), "kind": rec.kind})
            idx = np.asarray(final.img)
            if prev is not None:
                changes.append((t, int(np.count_nonzero(idx != prev))))
            prev = idx
            frame_bytes = to_output(final.img).tobytes()
            last_pose = pose
        enc.stdin.write(frame_bytes)
    enc.stdin.close()
    if enc.wait() != 0:
        print("ffmpeg failed while encoding", file=sys.stderr)
        return 1

    print("[4/5] QC")
    sheet = out_dir / f"{out_mp4.stem}-contact.png"
    tiles = qc.contact_sheet(out_mp4, sheet, duration)
    probe = qc.ffprobe(
        out_mp4,
        min_duration=float(cfg.get("min_duration", 24)),
        max_duration=float(cfg.get("max_duration", 27)),
    )
    final_loud = audio.ebur128(["-i", str(out_mp4)])
    text_problems = qc.text_issues(records)
    vo_problems, vo_table = qc.voice_issues(tl, records)
    dead = qc.dead_air(changes)
    loud_ok = abs(final_loud["integrated_lufs"] + 14) <= 1.0 and final_loud["true_peak_dbfs"] < -1.0
    report = {
        "video": str(out_mp4.relative_to(ROOT)),
        "contact_sheet": str(sheet.relative_to(ROOT)),
        "contact_sheet_tiles": tiles,
        "duration_s": float(probe["format"]["duration"]),
        "ffprobe_checks": probe["checks"],
        "loudness": final_loud,
        "loudness_ok": loud_ok,
        "word_count": words,
        "timeline": [
            {"id": b.cfg["id"], "start": round(b.start, 2), "end": round(b.end, 2), "voice": [round(b.vstart, 2), round(b.vend, 2)], "line": b.line}
            for b in tl.beats
        ],
        "words": [{"word": w.display, "t0": round(w.t0, 3), "t1": round(w.t1, 3)} for w in tl.words],
        "on_screen_text": vo_table,
        "text_issues": text_problems,
        "voiceover_issues": vo_problems,
        "dead_air": dead,
    }
    (out_dir / f"{out_mp4.stem}-qc.json").write_text(json.dumps(report, indent=2))

    print("[5/5] summary")
    for name, ok in probe["checks"].items():
        print(f"      {'ok  ' if ok else 'FAIL'} {name}")
    print(f"      {'ok  ' if loud_ok else 'FAIL'} loudness {final_loud['integrated_lufs']:.1f} LUFS, true peak {final_loud['true_peak_dbfs']:.1f} dBFS")
    for label, items in (("text", text_problems), ("voiceover", vo_problems), ("dead air", dead)):
        print(f"      {'ok  ' if not items else 'FAIL'} {label}: {len(items)} issue(s)")
        for item in items[:12]:
            print(f"           - {item}")
    print(f"      wrote {out_mp4.relative_to(ROOT)}, {sheet.relative_to(ROOT)} in {time.time() - started:.0f}s")
    failed = not all(probe["checks"].values()) or not loud_ok or text_problems or vo_problems or dead
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
