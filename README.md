# Ffempeg AI agent video editing

## Considerations - please read 

- Claude works with the config in this repo but is limited and made separate config in G-drive and Claude storage.
- Cursor is set up the same way, through `.cursor/mcp.json`. Need premium for cloud agent - free tier cannot do 
- ChatGPT does not. RunwayML and Canva are the alternatives for poster videos.
- VS Code has `.vscode/mcp.json`.
- GitHub Code spaces Codex can but low quality might struggle with high quality sometimes
- Github agent can but low quality might struggle with high quality sometimes
- **Could possibly automate with a cron job**
- cron job helps automate but videos lower quality might struggle with high quality sometimes
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

Brief source order: a current 3D-printing headline picked at random from free Google News / Google Trends RSS feeds (no API key; headlines already in `used.json` are skipped) is given to Cohere, then GitHub Models; if no headline or no valid brief is available, `pipeline/topics.json` is the fallback. Google Trends' "trending now" feed covers all subjects, so only entries mentioning 3D printing are used from it; Google News search is the main source. Skip the lookup with `--no-trends`.

Hosting: Buffer needs a public URL, so the repo must be **public**. Each video is attached to a rolling `videos` GitHub Release (assets older than 14 days are pruned) using the built-in token, so no storage account is needed.

Repository secrets:

- `COHERE_API_KEY`: primary brief writer.
- `BUFFER_API_KEY` and `BUFFER_CHANNEL_ID`: draft creation.
- Every run also opens an issue assigned to and mentioning the repo owner (then closes it), so GitHub emails and pushes an alert. Needs the `issues: write` permission, already set in the workflow.
- Optional `NTFY_TOPIC`: sends a phone alert (via the free ntfy.sh app) after every run, with the video title, topic and Buffer status. Pick a long random topic name, subscribe to it in the ntfy app, and keep it secret.
- Optional instead of Releases (e.g. for a private repo): `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, plus `PUBLIC_BASE_URL` (otherwise 7-day presigned URLs).

Run locally:

```bash
pip install -r pipeline/requirements.txt   # also needs ffmpeg and espeak-ng
python -m pipeline.run --no-llm --no-publish --fallback-voice --out out
python -m unittest tests.test_pipeline
```

Scheduled workflows only run from the default branch, and GitHub pauses them after 60 days without repo activity (the `used.json` commits keep it active).

## Battle rounds

Battle briefs can use `round` beats (module `bend`, `heat`, `speed`, `drop` or `detail`, plus `fx_a`, `fx_b` and `win`) and a `verdict` plaque on the last beat. The split layout has a textured background, score pips and a check or cross per round. See `tpu-vs-abs` in `pipeline/topics.json` and `pipeline/rounds.py`. edge-tts now retries with a backoff because the service throttles bursts.

## Status

The cron in `daily-videos.yml` runs three times a day and picks a random format (battle, troubleshooting, tip, spotlight or before-after); manual runs can choose a format or leave it on `random`. If edge-tts fails and only the robotic espeak-ng voice is available, the video is still rendered and uploaded as an artifact but is not sent to Buffer. Check the "Brief source" and "Voice" lines in the run summary.

- Cohere briefs for battles pass validation only some of the time; failures fall back to the topic bank (`pipeline/topics.json`), so add more battle topics there to avoid repeats.
- Local key setup: put `COHERE_API_KEY=...` in `.env` (gitignored, no spaces or quotes), then `set -a; . ./.env; set +a`.

## Tool-changer explainer (`toolchanger/`)

Standalone 26 s explainer ("Nine tools? What a tool changer actually does"): 19-colour pixel art, edge-tts voice, code-made chiptune + SFX.

- Local: `python3 -m toolchanger.render --out out` (needs ffmpeg; add `--rate "+25%"` if the voice runs past the end card).
- Actions: run **tool-changer-video** (workflow_dispatch) and download the artifact. It does not publish to Buffer.
- Outputs: `tool-changer.mp4`, `tool-changer-contact.png`, `tool-changer-qc.json`, `tool-changer-textboxes.jsonl` (every text box per frame).
- The render exits non-zero on any safe-zone, loudness, peak, format or voice failure.
- Script and beats live in `toolchanger/timeline.py` and `toolchanger/scenes.py`.
