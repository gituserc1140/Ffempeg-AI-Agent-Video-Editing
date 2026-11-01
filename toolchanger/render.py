"""Render the tool-changer explainer: voice -> timeline -> frames -> audio -> mp4 + contact sheet + audits."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from pipeline import config as C
from pipeline import tts
from pipeline.audio import SR, master, measure, write_wav

from . import art, scenes
from . import audio as TA
from . import timeline as TL

FPS = 30
W_OUT, H_OUT = art.W * art.SCALE, art.H * art.SCALE


def schedule(plan):
    """(time, sfx) pairs derived from the same events the visuals use."""
    ev = plan.ev
    s = []
    for _, name, t0, _ in [(i, n, a, b) for i, (n, a, b) in enumerate(plan.scenes)][1:]:
        s.append((t0, "whoosh"))
    for i in range(9):
        if i % 2 == 0:
            s.append((ev["nine"] + i * 0.11, "plop"))
    s += [(ev["revealed"] - 0.2, "pop"), (ev["why"], "pop")]
    s += [(ev["colour"], "pop"), (ev["pushing"], "whirr"), (ev["pushing"] + 0.55, "purge"),
          (ev["pushing"] + 1.1, "plop"), (ev["pushing"] + 1.5, "plop")]
    s += [(ev["waste"] - 0.15, "chime"), (ev["s4"] + 0.5, "whirr")]
    s += [(ev["s5"] + 0.1, "whirr"), (ev["parks"] + 0.4, "clack"), (ev["parks"] + 0.55, "whirr"),
          (ev["picks"] + 0.4, "latch"), (ev["picks"] + 0.55, "whirr")]
    s += [(ev["less"] + (ev["s6"] - ev["less"]) - 0.5, "sparkle")]
    s += [(ev["more"] - 0.1, "pop"), (ev["bigger"] - 0.1, "pop"), (ev["price"] - 0.1, "pop"),
          (ev["unknown"] - 0.05, "clack")]
    s += [(ev["third"] - 0.1, "clack"), (ev["november"], "pop"), (ev["s8"] - 0.05, "whoosh"),
          (ev["s8"] + 0.3, "chime"), (ev["card"] + 0.05, "sparkle"), (ev["card"] + 0.2, "sting")]
    return sorted((t, n) for t, n in s if 0 <= t < plan.duration - 0.2)


def audit_boxes(boxes):
    """Return a list of violation strings for one frame's text boxes (output pixels)."""
    bad = []
    for b in boxes:
        x0, y0, x1, y1 = b["x0"] * 10, b["y0"] * 10, (b["x1"] + 1) * 10, (b["y1"] + 1) * 10
        tag = f'{b["kind"]}:{b["text"]}'
        if x0 < 0 or x1 > W_OUT:
            bad.append(f"{tag} outside frame width")
        if y0 < 230:
            bad.append(f"{tag} above y=230 ({y0})")
        if y1 > 1536:
            bad.append(f"{tag} below y=1536 ({y1})")
        if x1 > 900 and y0 < 1500 and y1 > 800:
            bad.append(f"{tag} in right strip (x1={x1}, y {y0}-{y1})")
        if b["kind"] != "caption" and y1 > 1380:
            bad.append(f"{tag} non-caption text below y=1380 ({y1})")
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a["x0"] <= b["x1"] and b["x0"] <= a["x1"] and a["y0"] <= b["y1"] and b["y0"] <= a["y1"]:
                bad.append(f'overlap {a["kind"]}:{a["text"]} x {b["kind"]}:{b["text"]}')
    return bad


def render(out, rate="+20%", fallback=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    C.VOICE_RATE = rate
    engine, lines = tts.synthesize(TL.SCRIPT, force_fallback=fallback)
    plan = TL.build(lines)
    lines = plan.lines
    chunks = scenes.caption_chunks(plan)
    print(f"[voice] {engine} rate={rate} voice_end={plan.ev['end']:.2f}s card={plan.ev['card']:.2f}s")

    n = int(round(plan.duration * FPS))
    mp4_silent = out / "_video.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W_OUT}x{H_OUT}",
         "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(mp4_silent)], stdin=subprocess.PIPE)
    violations, log = [], []
    sheet, colors = [], set()
    cache = {}
    for f in range(n):
        t = f / FPS
        c = scenes.frame(plan, chunks, t)
        bad = audit_boxes(c.boxes)
        log.append({"f": f, "t": round(t, 3), "boxes": c.boxes, "violations": bad})
        violations += [f"frame {f} t={t:.2f}: {v}" for v in bad]
        key = c.img.tobytes()
        if key not in cache:
            cache = {key: c.upscaled()}
        ff.stdin.write(cache[key])
        if f % round(0.75 * FPS) == 0:
            sheet.append(c.img.copy())
        colors |= {px for _, px in c.img.getcolors(maxcolors=256)}
    ff.stdin.close()
    ff.wait()

    wav, mastered = out / "_mix.wav", out / "_master.wav"
    sfx = schedule(plan)
    stereo = TA.mix(plan.duration, [(t, ln["audio"]) for t, ln in zip(_starts(plan), lines)], sfx)
    write_wav(wav, stereo)
    master(wav, mastered)
    final = out / "tool-changer.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4_silent), "-i", str(mastered),
                    "-c:v", "copy", "-af", "alimiter=limit=0.7:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(final)], check=True)
    for p in (mp4_silent, wav, mastered):
        p.unlink()

    cols, pad = 7, 6
    tw, th = art.W * 2, art.H * 2
    rows = (len(sheet) + cols - 1) // cols
    img = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (7, 9, 15))
    for i, fr in enumerate(sheet):
        img.paste(fr.resize((tw, th), Image.NEAREST), (pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)))
    img.save(out / "tool-changer-contact.png")
    (out / "tool-changer-textboxes.jsonl").write_text("\n".join(json.dumps(r) for r in log))

    report = qc(final, plan, violations, colors, engine)
    (out / "tool-changer-qc.json").write_text(json.dumps(report, indent=2))
    return report


def _starts(plan):
    t, out = TL.LEAD_IN, []
    for ln in plan.lines:
        out.append(t)
        t += len(ln["audio"]) / SR + TL.LINE_GAP
    return out


def qc(path, plan, violations, colors, engine):
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout)
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    lufs, peak = measure(path)
    dur = float(probe["format"]["duration"])
    silent = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=n=-45dB:d=0.7",
                             "-f", "null", "-"], capture_output=True, text=True).stderr.count("silence_start")
    tail = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(plan.ev["card"] + 0.2), "-i", str(path), "-vn",
                           "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    speech = subprocess.run(["ffmpeg", "-hide_banner", "-ss", "1", "-t", "8", "-i", str(path), "-vn",
                             "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = lambda s: float(s.split("mean_volume:")[1].split("dB")[0])
    faststart = path.read_bytes()[:64].find(b"ftyp") >= 0 and \
        path.read_bytes().find(b"moov") < path.read_bytes().find(b"mdat")
    checks = {
        "1080x1920": (v["width"], v["height"]) == (1080, 1920),
        "30fps": v["r_frame_rate"] == "30/1",
        "h264+aac": (v["codec_name"], a["codec_name"]) == ("h264", "aac"),
        "duration 24-27s": 24 <= dur <= 27,
        "loudness ~-14 LUFS": abs(lufs + 14) <= 1.0,
        "true peak < -1 dBFS": peak < -1.0,
        "no long silent gaps": silent == 0,
        "end card within 5 dB of speech": mean(tail) > mean(speech) - 5,
        "faststart": faststart,
        "safe zones (every frame)": not violations,
        "voice ends before card": plan.ev["end"] < plan.ev["card"],
        "real neural voice": engine == "edge-tts",
    }
    for k, ok in checks.items():
        print(("OK  " if ok else "FAIL"), k)
    print(f"duration={dur:.2f}s lufs={lufs:.1f} peak={peak:.1f} colours={len(colors)} violations={len(violations)}")
    for vmsg in violations[:25]:
        print("  violation:", vmsg)
    return {"checks": checks, "lufs": lufs, "true_peak": peak, "duration": dur, "colours": len(colors),
            "violations": violations[:200], "engine": engine}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--rate", default="+20%")
    ap.add_argument("--fallback", action="store_true")
    a = ap.parse_args()
    rep = render(a.out, a.rate, a.fallback)
    sys.exit(0 if all(rep["checks"].values()) else 1)


if __name__ == "__main__":
    main()
