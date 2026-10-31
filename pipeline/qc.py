"""Deterministic QC. python -m pipeline.qc outdir  (exit 1 on failure)"""
import json
import re
import subprocess
import sys
from pathlib import Path

from . import audio, config as C
from .tts import normalize_token


def _probe(mp4):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(mp4)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _freezes(mp4):
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-an", "-vf",
         "freezedetect=n=-60dB:d=1", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", err)]


def _in_safe_zone(b):
    if b["y0"] < C.SAFE_TOP or b["y1"] > C.SAFE_BOTTOM or b["x0"] < 0 or b["x1"] >= C.W:
        return False
    return not (b["x1"] >= C.STRIP_X and b["y1"] >= C.STRIP_Y0 and b["y0"] <= C.STRIP_Y1)


def run(outdir):
    outdir = Path(outdir)
    mp4 = outdir / "video.mp4"
    meta = json.loads((outdir / "meta.json").read_text())
    info = _probe(mp4)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    dur = float(info["format"]["duration"])
    lufs, peak = audio.measure(mp4)
    results = {}

    def check(name, ok, detail):
        results[name] = dict(ok=bool(ok), detail=detail)

    check("video_format", (v["width"], v["height"]) == (C.OUT_W, C.OUT_H)
          and v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p"
          and v["r_frame_rate"] == "30/1",
          f"{v['width']}x{v['height']} {v['codec_name']} {v['pix_fmt']} {v['r_frame_rate']}")
    check("audio_format", a["codec_name"] == "aac" and a["sample_rate"] == "48000"
          and a["channels"] == 2, f"{a['codec_name']} {a['sample_rate']}Hz x{a['channels']}")
    check("duration", 24.0 <= dur <= 27.0, f"{dur:.2f}s")
    check("loudness", abs(lufs - C.TARGET_LUFS) <= 1.0, f"{lufs:.1f} LUFS")
    check("true_peak", peak < C.TRUE_PEAK_LIMIT, f"{peak:.1f} dBTP")
    check("palette", meta["palette_ok"], "<=16 colours per frame")

    bad = [b for b in meta["boxes"] if not _in_safe_zone(b)]
    check("safe_zones", not bad,
          f"{len(bad)} violations" + (f", e.g. {bad[0]['text']!r} at t={bad[0]['t']}" if bad else ""))

    spoken = {normalize_token(w) for w in meta["script"].split()}
    stray = sorted({w for b in meta["boxes"] if b["kind"] == "voice"
                    for w in b["text"].split() if normalize_token(w) not in spoken
                    and normalize_token(w)})
    check("text_matches_voiceover", not stray, f"stray words: {stray}" if stray else "all words spoken")

    freezes = _freezes(mp4)
    check("no_dead_stretch", not freezes, f"{len(freezes)} frozen stretch(es) over 1s")

    ok = all(r["ok"] for r in results.values())
    report = dict(ok=ok, voice_engine=meta["voice_engine"], checks=results)
    (outdir / "qc.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    report = run(sys.argv[1])
    for name, r in report["checks"].items():
        print(("PASS " if r["ok"] else "FAIL ") + f"{name}: {r['detail']}")
    print(f"voice: {report['voice_engine']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
