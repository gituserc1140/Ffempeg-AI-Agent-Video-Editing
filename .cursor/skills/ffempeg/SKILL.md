---
name: ffempeg
description: Edit or inspect video and audio with the local ffempeg tools or the FFmpeg API MCP. Use when the user asks to probe, trim, compress, thumbnail, extract audio, or make a GIF from a video file or URL.
---

# FFmpeg editing

Prefer the local `ffempeg` MCP tools (`check_ffmpeg`, `probe_media`, `make_gif`, `trim_media`, `extract_audio`, `thumbnail`, `compress_media`). They shell out to `ffmpeg` / `ffprobe` on PATH and accept a local path or an http(s) URL.

The public sample used by FFmpeg API is `https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v`.

From a shell, the same operations are:

```bash
python3 -m ffempeg.cli probe <path-or-url>
python3 -m ffempeg.cli gif <path-or-url> --start 0 --duration 3 --width 320
python3 -m ffempeg.cli trim <path-or-url> --start 0 --duration 3
python3 -m ffempeg.cli audio <path-or-url>
python3 -m ffempeg.cli thumbnail <path-or-url> --timestamp 1
python3 -m ffempeg.cli compress <path-or-url> --crf 28
```

GIFs are capped at 15 seconds and 640px wide. Downloads are cached in `media/in`. Outputs land in `media/out`.

`ffmpeg-api` (`https://mcp.ffmpeg-api.com/mcp`) is the cloud connector. It stays unauthorized until the user signs in with the Google account on ffmpeg-api.com, or sets an API key. Use the local tools when that login is not available.
