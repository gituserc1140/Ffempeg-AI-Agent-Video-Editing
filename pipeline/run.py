"""Daily entry point: brief -> render -> QC -> publish.  python -m pipeline.run"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import brief as brief_mod, publish, qc, trends
from . import config as C
from .render import render

BASE_RATE = C.VOICE_RATE

HERE = Path(__file__).parent
USED = HERE / "used.json"
TOPICS = HERE / "topics.json"


def _load_used():
    return json.loads(USED.read_text()) if USED.exists() else []


def ranked_topics(used):
    """Topic bank, least-used first."""
    topics = json.loads(TOPICS.read_text())
    counts = {t["slug"]: 0 for t in topics}
    for u in used:
        base = u.get("topic")
        if base in counts:
            counts[base] += 1
    return sorted(topics, key=lambda t: counts[t["slug"]])


def fallback_topic(used):
    return ranked_topics(used)[0]


def _summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as fh:
            fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-trends", action="store_true", help="skip the news/trends topic lookup")
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--fallback-voice", action="store_true")
    ap.add_argument("--format", choices=brief_mod.FORMATS)
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    slot = now.hour // 8
    fmt = args.format or brief_mod.FORMATS[(now.timetuple().tm_yday * 3 + slot) % len(brief_mod.FORMATS)]
    used = _load_used()

    candidates = []
    trend = None
    if not args.no_llm:
        if not args.no_trends:
            trend = trends.pick([u.get("trend") for u in used])
            print(f"[run] trend: {trend or 'none found, letting the LLM choose'}")
        generated = brief_mod.generate(fmt, [u["title"] for u in used], trend=trend)
        if generated:
            candidates.append(("llm", generated))
    candidates += [("topic bank", dict(t)) for t in ranked_topics(used)]

    out = Path(args.out)
    chosen = report = meta = None
    for source, brief in candidates:
        meta = report = None
        # A slower real voice can push a script over the limit; retry once with faster speech.
        for rate in (C.VOICE_RATE, "+32%"):
            C.VOICE_RATE = rate
            try:
                meta = render(brief, out, args.fallback_voice)
                report = qc.run(out)
                break
            except Exception as exc:
                print(f"[run] {source} brief '{brief.get('title')}' failed at rate {rate}: {exc}")
                if "too long" not in str(exc):
                    break
        C.VOICE_RATE = BASE_RATE
        if not report:
            continue
        print(f"[run] {source} brief '{brief['title']}' QC ok={report['ok']}")
        for name, r in report["checks"].items():
            if not r["ok"]:
                print(f"[run] QC fail {name}: {r['detail']}")
        if report["ok"]:
            chosen = (source, brief)
            break
    if not chosen:
        _summary(["### Render failed", "No brief passed QC. See the uploaded artifact."])
        return 1

    source, brief = chosen
    stamp = now.strftime("%Y%m%d-%H%M")
    key = f"shorts/{stamp}-{brief['slug']}.mp4"
    result = {"url": None, "post_id": None, "error": "publishing skipped"}
    robotic = "fallback" in meta["voice_engine"] and not args.fallback_voice
    if robotic:
        print("::warning::edge-tts failed, so the robotic fallback voice is not published")
    if not args.no_publish and not robotic:
        result = publish.publish(out / "video.mp4", key, brief["caption"])
        if result["error"]:
            print(f"::warning::{result['error']}")

    entry = dict(date=now.isoformat(timespec="minutes"), title=brief["title"], slug=brief["slug"],
                 topic=brief["slug"] if source == "topic bank" else None, source=source,
                 trend=trend if source == "llm" else None,
                 voice=meta["voice_engine"], buffer_post=result["post_id"])
    USED.write_text(json.dumps(_load_used() + [entry], indent=2) + "\n")

    _summary([f"### {brief['title']}", f"- Brief source: **{source}**",
              f"- Trend headline: {trend if source == 'llm' and trend else 'none'}",
              f"- Voice: **{meta['voice_engine']}**", f"- Duration: {meta['duration']:.2f}s",
              f"- Buffer draft: {result['post_id'] or 'not created'}",
              f"- Publish status: {result['error'] or 'ok'}", "",
              *[f"- {'PASS' if r['ok'] else 'FAIL'} {n}: {r['detail']}" for n, r in report["checks"].items()]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
