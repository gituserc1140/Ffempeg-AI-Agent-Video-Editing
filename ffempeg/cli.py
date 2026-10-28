#!/usr/bin/env python3
"""Command line for the same edits the MCP server exposes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ffempeg.edit import (  # noqa: E402
    SAMPLE_URL,
    EditError,
    compress,
    extract_audio,
    ffmpeg_status,
    make_gif,
    probe,
    thumbnail,
    trim,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ffempeg", description="Local FFmpeg edits for the agent project.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="show the ffmpeg version")

    probe_cmd = sub.add_parser("probe", help="show duration, size, and codecs")
    probe_cmd.add_argument("source", nargs="?", default=SAMPLE_URL)

    gif_cmd = sub.add_parser("gif", help="make a short GIF")
    _source_args(gif_cmd)
    gif_cmd.add_argument("--start", default="0")
    gif_cmd.add_argument("--duration", default="3")
    gif_cmd.add_argument("--width", type=int, default=320)
    gif_cmd.add_argument("--output")

    trim_cmd = sub.add_parser("trim", help="cut an H.264 MP4 clip")
    _source_args(trim_cmd)
    trim_cmd.add_argument("--start", default="0")
    trim_cmd.add_argument("--duration", default="3")
    trim_cmd.add_argument("--output")

    audio_cmd = sub.add_parser("audio", help="extract MP3 audio")
    _source_args(audio_cmd)
    audio_cmd.add_argument("--start", default="0")
    audio_cmd.add_argument("--duration")
    audio_cmd.add_argument("--output")

    thumb_cmd = sub.add_parser("thumbnail", help="save one JPEG frame")
    _source_args(thumb_cmd)
    thumb_cmd.add_argument("--timestamp", default="1")
    thumb_cmd.add_argument("--output")

    compress_cmd = sub.add_parser("compress", help="re-encode with libx264")
    _source_args(compress_cmd)
    compress_cmd.add_argument("--crf", type=int, default=28)
    compress_cmd.add_argument("--output")

    args = parser.parse_args(argv)
    try:
        result = _run(args)
    except EditError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", nargs="?", default=SAMPLE_URL)


def _run(args: argparse.Namespace) -> object:
    if args.cmd == "check":
        return ffmpeg_status()
    if args.cmd == "probe":
        return probe(args.source)
    if args.cmd == "gif":
        return make_gif(args.source, start=args.start, duration=args.duration, width=args.width, output=args.output)
    if args.cmd == "trim":
        return trim(args.source, start=args.start, duration=args.duration, output=args.output)
    if args.cmd == "audio":
        return extract_audio(args.source, start=args.start, duration=args.duration, output=args.output)
    if args.cmd == "thumbnail":
        return thumbnail(args.source, timestamp=args.timestamp, output=args.output)
    if args.cmd == "compress":
        return compress(args.source, crf=args.crf, output=args.output)
    raise EditError(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    sys.exit(main())
