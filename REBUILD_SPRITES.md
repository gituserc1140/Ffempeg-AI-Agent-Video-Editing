# Rebuild guide and session notes: GPT-5 sprites

Saved 2026-11-01. This is a summary of the session, not a verbatim transcript. The general rebuild guide is [REBUILD.md](REBUILD.md).

## Goal

The daily-video workflow (`.github/workflows/daily-videos.yml`) only used preset sprites. The aim was for GPT-5 to draw topic-specific sprites for each video, similar to how an AI agent would build sprites on the fly.

## Session history

1. A previous session was cut off. The workspace still held uncommitted edits that used OpenAI's image-generation model, not GPT-5.
2. Chosen approach: GPT-5 returns 24x24 palette-letter grids through the Responses API with a strict JSON schema, not an image.
3. `pipeline/art.py` was rewritten to do this, with a disk cache and a fallback to built-in icons on any failure.
4. The workflow, brief prompt, validation, run summary, README and tests were updated to match.
5. All 31 tests passed before the push, and the work was committed and pushed to `main` as `c13e8e0`. The tests were not re-run after rebasing onto the bot's latest commit.

## What changed

| File | Change |
| --- | --- |
| `pipeline/art.py` (new) | Calls GPT-5 at `https://api.openai.com/v1/responses`, validates a 24x24 grid, caches it in `media/art_cache` |
| `.github/workflows/daily-videos.yml` | Passes `OPENAI_API_KEY` and sets `OPENAI_SPRITE_MODEL: gpt-5` |
| `pipeline/brief.py` | When the key is set, the prompt asks for two sprite descriptions |
| `pipeline/sprites.py` | `register_custom` draws and registers sprites, and `check_sprite` validates them |
| `pipeline/validate.py` | A failed sprite falls back to the `gear` icon, and every generated sprite must be used in a beat |
| `pipeline/run.py` | The run summary lists the topic-specific sprites |
| `tests/test_pipeline.py` | Tests for the GPT-5 call, the missing key and the fallback |

## Rebuild from scratch

```bash
git clone https://github.com/gituserc1140/Ffempeg-AI-Agent-Video-Editing
cd Ffempeg-AI-Agent-Video-Editing
pip install -r pipeline/requirements.txt   # also needs ffmpeg and espeak-ng
python3 -m unittest discover -s tests -v
python3 -m pipeline.run --no-llm --no-publish --out out
```

To exercise the GPT-5 sprites locally, run `export OPENAI_API_KEY=<your key>` and then
`python3 -m pipeline.run --no-publish --out out`. Never commit the key.

## Actions setup

- Repository secret `OPENAI_API_KEY` enables GPT-5 sprites. Without it the run still works and uses only the built-in sprites.
- Other secrets: `COHERE_API_KEY`, `BUFFER_API_KEY`, `BUFFER_CHANNEL_ID`, optional `NTFY_TOPIC`.
- Run **Actions > Daily videos > Run workflow**. Videos appear in the `videos` release, and the run summary shows the "Topic-specific sprites" line.

## Status at end of session 1 (2026-11-01 night)

- Live Actions runs confirmed GPT-5 sprites work: `[art] generated 'tooling' with gpt-5`, and the run summary shows "Topic-specific sprites: tooling".
- First live attempt returned empty replies because the 1800-token cap was used up by reasoning. Fixed with a 12000-token cap and `reasoning: low` (`4aa92e1`).
- In the rendered video the sprite had a dotted rectangular box around it, because GPT-5 filled the backdrop with black pixels. `_clear_background` in `pipeline/art.py` now makes border-connected black/slate pixels transparent.
- Roughly one of the two sprites per video was rejected with "must be a 24x24 grid using the pipeline palette". A malformed grid now gets one retry with the exact error in the prompt (`011b027`).
- Those last two fixes were pushed but not yet confirmed by a live run.

## Next steps

1. Run Actions > Daily videos and check the log for `[art] attempt 1 ... failed` followed by `generated` (retry working) and that both sprites appear.
2. Download the video and check whether the dotted box is gone.
3. Sprite quality is still basic next to the hand-drawn stage art. Options: tune the prompt, allow 32x32, or give GPT-5 an example sprite.
4. Cohere briefs often fail validation (bad round modules and triggers), which is separate from sprites.

## Resume prompt

> Continue the GPT-5 sprite work in this repo. Read REBUILD_SPRITES.md, then check the latest Daily videos run log with `gh run view --log` for the `[art]` lines.
