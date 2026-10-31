"""Render one brief to an mp4 + contact sheet.  python -m pipeline.render brief.json outdir"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from . import audio, config as C
from .frames import render_pose
from .timeline import build
from .tts import synthesize
from .validate import normalize, script_words, validate


def contact_sheet(thumbs, path, cols=9):
    tw, th = C.W * 2, C.H * 2
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, (t, img) in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(img.resize((tw, th), Image.NEAREST), (x, y))
        red = (255, 0, 0)
        d.line([x, y + C.SAFE_TOP * 2, x + tw, y + C.SAFE_TOP * 2], fill=red)
        d.line([x, y + (C.SAFE_BOTTOM + 1) * 2, x + tw, y + (C.SAFE_BOTTOM + 1) * 2], fill=red)
        d.rectangle([x + C.STRIP_X * 2, y + C.STRIP_Y0 * 2, x + tw, y + C.STRIP_Y1 * 2], outline=red)
        d.text((x + 3, y + 2), f"{t:.2f}s", fill=(255, 255, 0))
    sheet.save(path)


def _tame_peaks(mp4, mastered, duration, outdir):
    """AAC can overshoot the mastered peak by ~2 dB. If the muxed file is too hot,
    re-encode only the audio (video stream copied) a little quieter."""
    drop = 0.0
    for _ in range(3):
        _, peak = audio.measure(mp4)
        if peak <= C.TRUE_PEAK_LIMIT - 0.4:
            return
        drop += peak - (C.TRUE_PEAK_LIMIT - 0.8)
        fixed = outdir / "video_fixed.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-i", str(mastered), "-map", "0:v",
             "-map", "1:a", "-c:v", "copy", "-af", f"volume=-{drop:.2f}dB", "-c:a", "aac",
             "-b:a", "320k", "-ar", str(C.SAMPLE_RATE), "-ac", "2", "-t", f"{duration:.4f}",
             "-movflags", "+faststart", str(fixed)], check=True)
        fixed.replace(mp4)


def render(brief, outdir, force_fallback_voice=False):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    brief = normalize(brief)
    errs = validate(brief)
    if errs:
        raise ValueError("invalid brief: " + "; ".join(errs))

    engine, voice = synthesize([b["line"] for b in brief["beats"]], force_fallback_voice)
    plan = build(brief, voice)

    wav, mastered = outdir / "mix.wav", outdir / "master.wav"
    audio.write_wav(wav, audio.mix(plan))
    audio.master(wav, mastered)

    mp4 = outdir / "video.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{C.OUT_W}x{C.OUT_H}", "-r", str(C.FPS), "-i", "-", "-i", str(mastered),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-r", str(C.FPS), "-c:a", "aac", "-b:a", "320k", "-ar", str(C.SAMPLE_RATE),
         "-ac", "2", "-t", f"{plan.duration:.4f}", "-movflags", "+faststart", str(mp4)],
        stdin=subprocess.PIPE)

    boxes, thumbs, palette_ok = [], [], True
    last_pose, data, next_thumb = None, None, 0.0
    for n in range(plan.frames):
        p = int(n * C.POSE_FPS / C.FPS)
        if p != last_pose:
            c = render_pose(plan, p)
            data = c.upscaled_bytes()
            last_pose = p
            t = p / C.POSE_FPS
            palette_ok &= c.color_count() <= 16
            for b in c.boxes:
                boxes.append(dict(b, t=round(t, 3)))
            if t >= next_thumb:
                thumbs.append((t, c.img.copy()))
                next_thumb += 0.75
        ff.stdin.write(data)
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg encode failed")
    _tame_peaks(mp4, mastered, plan.duration, outdir)

    contact_sheet(thumbs, outdir / "contact_sheet.png")
    meta = dict(slug=brief["slug"], title=brief["title"], caption=brief["caption"],
                voice_engine=engine, duration=plan.duration, palette_ok=palette_ok,
                script=" ".join(script_words(brief)), boxes=boxes)
    (outdir / "meta.json").write_text(json.dumps(meta))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("outdir")
    ap.add_argument("--fallback-voice", action="store_true")
    args = ap.parse_args()
    meta = render(json.loads(Path(args.brief).read_text()), args.outdir, args.fallback_voice)
    print(f"rendered {meta['duration']:.2f}s with {meta['voice_engine']}")


if __name__ == "__main__":
    sys.exit(main())
