# Ffempeg AI agent video editing

Local FFmpeg tools for Cursor, Claude, and any other MCP client, plus the [FFmpeg API](https://ffmpeg-api.com/mcp) connector. The connector signs in with the Google account on ffmpeg-api.com.

FFmpeg and FFprobe need to be on `PATH`. Python 3.11+ is enough; the tools use the standard library.

## Cursor, Claude, and VS Code

This repo already registers two servers:

| Server | Where it runs | Sign-in |
| --- | --- | --- |
| `ffempeg` | This machine, `ffempeg/mcp_server.py` | None |
| `ffmpeg-api` | `https://mcp.ffmpeg-api.com/mcp` | Google account, or an API key |

- Cursor reads `.cursor/mcp.json`. Enable both servers under Settings → MCP. For `ffmpeg-api`, approve the Google sign-in when Cursor asks.
- Claude Code reads `.mcp.json`. Run `/mcp` and sign in to `ffmpeg-api` the same way.
- VS Code reads `.vscode/mcp.json`.

An API key from the ffmpeg-api dashboard can replace Google sign-in. Add it as an `Authorization: Bearer <key>` header on the `ffmpeg-api` server. A header is not committed here, because an empty bearer token blocks the Google login prompt.

Cloud calls need `mcp.ffmpeg-api.com` and `*.r2.cloudflarestorage.com` reachable. Google sign-in also needs `accounts.google.com`.

## Try the sample

```bash
python3 -m ffempeg.cli probe https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v
python3 -m ffempeg.cli gif https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v --duration 3 --output bunny.gif
python3 -m ffempeg.cli thumbnail https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v --timestamp 1 --output bunny.jpg
```

The first command downloads the clip into `media/in` (gitignored) and prints codecs, size, and duration. The GIF is the first 3 seconds.

In chat, once the local server is enabled:

> Probe https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v and make a 3-second GIF from the first scene.

## Pixel-art versus shorts

`python3 render.py` builds the Wood PLA versus Metal PLA short. `python3 render.py --config shorts/topics/tpu_vs_abs.json` builds TPU versus ABS on an orange rubber and blue plastic stage. `python3 render.py --config shorts/topics/halloween_pumpkin.json` builds a Halloween short of a pumpkin being printed. See [`shorts/README.md`](shorts/README.md).

## Local tools

`check_ffmpeg`, `probe_media`, `make_gif`, `trim_media`, `extract_audio`, `thumbnail`, `compress_media`.

GIFs stay at or under 15 seconds and 640 pixels wide. Outputs go to `media/out` unless you pass a path inside the project or `/tmp`.

```bash
python3 -m unittest discover -s tests -v
```

## Considerations

- Claude works with the config in this repo. Cursor is set up the same way, through `.cursor/mcp.json`.
- ChatGPT does not. RunwayML and Canva are the alternatives for poster videos.
- VS Code has `.vscode/mcp.json`. GitHub Codespaces with Codex is still untried.
- Social posting goes through Buffer.
- New pixel-art shorts start from [`pixel_video_prompt.md`](pixel_video_prompt.md) and [`shorts/topics/template.json`](shorts/topics/template.json).
