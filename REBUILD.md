# Rebuild guide

How to get this project and its GitHub Actions automation working again from scratch.
No secrets are stored in this file. Add them yourself (step 3).

## What the system does

```
Google News / Trends RSS  ->  random unused 3D-printing headline  (pipeline/trends.py)
        |  (falls back to pipeline/topics.json if feeds fail)
        v
Cohere (then GitHub Models) writes a JSON brief  (pipeline/brief.py)
        v
Render: pixel-art frames + edge-tts voice + chiptune -> video.mp4 via ffmpeg  (pipeline/render.py)
        v
QC: safe zones, loudness, duration, format  (pipeline/qc.py)  -> fails = not published
        v
Upload to a rolling GitHub Release (or S3) -> Buffer draft  (pipeline/publish.py)
        v
Record the topic in pipeline/used.json (committed by the workflow)
```

Entry point: `python -m pipeline.run`. Rules for the videos: `pixel_video_prompt.md`.

## 1. Restore the code

```bash
git clone https://github.com/gituserc1140/Ffempeg-AI-Agent-Video-Editing.git
cd Ffempeg-AI-Agent-Video-Editing
```

The repo must stay **public**. Buffer needs a public video URL, and public repos get free Actions minutes.

## 2. Local requirements

- Python 3.11+ (the workflow uses 3.12)
- `ffmpeg` and `espeak-ng` (`sudo apt-get install -y ffmpeg espeak-ng`)
- `pip install -r pipeline/requirements.txt`

Quick check:

```bash
python3 -m unittest tests.test_pipeline            # 21 tests
python3 -m pipeline.run --no-llm --no-publish --fallback-voice --out out
```

Local keys: create `.env` (gitignored; no spaces or quotes) with `COHERE_API_KEY=...`, then `set -a; . ./.env; set +a`.

## 3. GitHub secrets

Settings -> Secrets and variables -> Actions -> **Repository secrets**:

| Secret | Needed | Used for |
| --- | --- | --- |
| `COHERE_API_KEY` | yes | writes the brief (primary) |
| `BUFFER_API_KEY` | yes | creates the draft |
| `BUFFER_CHANNEL_ID` | yes | which Buffer channel gets the draft |
| `GITHUB_TOKEN` | automatic | GitHub Models fallback, release upload |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `PUBLIC_BASE_URL` | optional | host videos on S3-style storage instead of Releases (needed for a private repo) |
| `OPENAI_API_KEY` | not used | stored but no code reads it |

The Google News / Trends RSS lookup needs no key.

## 4. Workflow settings

Settings -> Actions -> General:

- Actions permissions: allow actions and reusable workflows.
- Workflow permissions: **Read and write permissions** (the workflow commits `pipeline/used.json` and publishes the `videos` release).
- Scheduled workflows only run from the **default branch** (`main`). GitHub pauses them after 60 days of repo inactivity; the `used.json` commits keep it active.

## 5. The workflows

### Daily videos - `.github/workflows/daily-videos.yml`

- Triggers: cron `17 6`, `17 12`, `17 18` (UTC, so UK time except during BST) plus manual `workflow_dispatch` (inputs: `format`, default `random`, and `publish`). A random format is chosen when none is passed.
- Permissions: `contents: write`, `models: read`. Concurrency group `daily-videos` (no overlapping runs).
- Steps: checkout -> setup-python 3.12 (pip cache) -> apt install `ffmpeg espeak-ng` -> `pip install -r pipeline/requirements.txt` -> `python -m pipeline.run --out out --format <format>` (adds `--no-publish` when the input is false) -> upload artifact `video-<run_id>` (mp4, contact sheet, qc.json, 14 days) -> commit `pipeline/used.json` as `github-actions[bot]` (`git pull --rebase` then push).
- Env passed to the run step: all secrets in section 3, plus `FORMAT_INPUT` and `PUBLISH_INPUT`.

### tool-changer-video - `.github/workflows/tool-changer.yml`

- Manual only (`workflow_dispatch`, input `rate`, default `+20%`). One-off explainer video; does **not** publish to Buffer.
- Runs `python -m toolchanger.render --out out --rate "<rate>"` and uploads the artifact `tool-changer-video`.

If the YAML is lost, recover it from git history: `git log --oneline -- .github/workflows/` then `git checkout <commit> -- .github/workflows/`.

## 6. Verify a rebuild

1. Actions -> **Daily videos** -> Run workflow, `publish` = false.
2. Open the run summary. Check "Brief source", "Trend headline", "Voice" and all QC lines show PASS.
3. Download the `video-<run_id>` artifact and watch it.
4. Run again with `publish` = true; confirm a draft appears in Buffer and a `videos` release exists.

## 7. Troubleshooting

- **Brief source is "topic bank"**: Cohere failed validation or the feeds returned nothing. Normal occasionally; add more topics to `pipeline/topics.json`.
- **Video renders but is not sent to Buffer**: edge-tts failed and only the robotic espeak-ng voice was available (by design, those are not published).
- **"buffer failed" in the summary**: check `BUFFER_API_KEY`, `BUFFER_CHANNEL_ID`, and that the video URL is public.
- **Push rejected**: the bot committed `used.json`; run `git pull --rebase` then push.
- **No trends found**: Google may be throttling the feeds; the pipeline falls back automatically. Use `--no-trends` to skip the lookup.

## 8. Tuning

- Topic filtering (keywords, blocked words, brands): `pipeline/trends.py`.
- Prompt and script rules for the LLM: `pipeline/brief.py` (`SYSTEM`), validation in `pipeline/validate.py`.
- Voice and timing constants: `pipeline/config.py`.
- Schedule: the `cron` lines in `daily-videos.yml`.

## 9. Optional: ffmpeg MCP tools

`ffempeg/` is a local MCP server for ad hoc edits. Config lives in `.mcp.json`, `.cursor/mcp.json` and `.vscode/mcp.json`. The cloud `ffmpeg-api` connector is separate and is not used by the Actions workflow. See `README.md`.
