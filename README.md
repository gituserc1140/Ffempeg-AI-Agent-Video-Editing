# Ffempeg AI agent video editing

## Considerations - please read 

- Claude works with the config in this repo but is limited and made separate config in G-drive and Claude storage.
- Cursor is set up the same way, through `.cursor/mcp.json`. Need premium for cloud agent - free tier cannot do 
- ChatGPT does not. RunwayML and Canva are the alternatives for poster videos.
- VS Code has `.vscode/mcp.json`. GitHub Codespaces with Codex is still untried.
- **Could possibly automate with a cron job** 
- Social posting goes through Buffer.
- New pixel-art shorts start from [`pixel_video_prompt.md`](pixel_video_prompt.md).

# Intro 

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

## Local tools

`check_ffmpeg`, `probe_media`, `make_gif`, `trim_media`, `extract_audio`, `thumbnail`, `compress_media`.

GIFs stay at or under 15 seconds and 640 pixels wide. Outputs go to `media/out` unless you pass a path inside the project or `/tmp`.

```bash
python3 -m unittest discover -s tests -v
```



## Automated daily videos

`.github/workflows/daily-videos.yml` renders about 3 pixel-art shorts a day (rules in `pixel_video_prompt.md`), runs deterministic QC, and saves them as Buffer drafts.

Brief source order: Cohere, then GitHub Models, then `pipeline/topics.json`.

Hosting: Buffer needs a public URL, so the repo must be **public**. Each video is attached to a rolling `videos` GitHub Release (assets older than 14 days are pruned) using the built-in token, so no storage account is needed.

Repository secrets:

- `COHERE_API_KEY`: primary brief writer.
- `BUFFER_API_KEY` and `BUFFER_CHANNEL_ID`: draft creation.
- Optional instead of Releases (e.g. for a private repo): `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, plus `PUBLIC_BASE_URL` (otherwise 7-day presigned URLs).

Run locally:

```bash
pip install -r pipeline/requirements.txt   # also needs ffmpeg and espeak-ng
python -m pipeline.run --no-llm --no-publish --fallback-voice --out out
python -m unittest tests.test_pipeline
```

Scheduled workflows only run from the default branch, and GitHub pauses them after 60 days without repo activity (the `used.json` commits keep it active).
