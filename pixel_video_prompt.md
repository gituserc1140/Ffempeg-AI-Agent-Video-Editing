# Reusable prompt: pixel-art 3D printing short (TikTok, 1080x1920)

## How to use
1. Start a new chat and attach the latest pipeline zip (for example `pla_vs_tpu_pipeline.zip`).
2. Paste the prompt below and fill in the BRIEF. Delete anything that doesn't apply.
3. If you hit limits, work in stages: "do step 1 and 2 only", then "now step 3 and 4".

---

## PROMPT (copy from here)

You are a motion-graphics programmer. Reuse the attached pipeline (config.py, pixel.py, background.py, sprites.py, scenes.py, timeline.py, tts.py, audio.py, frames.py, qc.py, render.py) to build a new vertical short. Do not rewrite modules that don't need to change. Work in a copy of the project folder so the original stays intact.

### BRIEF (fill in)
- Topic / title:
- Format: [battle (A vs B) | explainer | tip | troubleshooting | one-material spotlight | before/after]
- Layout: [split-screen with VS badge | single full-width stage]
- Subject A (left) and colour family:
- Subject B (right) and colour family (or "none"):
- Script: 5-6 lines, about 60-70 words, one line per beat. Say the key term once clearly.
- Visual idea per beat (one sentence each, with the spoken word that triggers it):
  1. Hook:
  2.
  3.
  4.
  5. Verdict / takeaway + end card:
- Handle for end card: @STUDIORK3DPS
- Rules: [general terms only - no numbers, temperatures or brand names | numbers allowed]

### Fixed rules (do not change)
- Code-only. No filming and no AI image or video generation. It must look hand-made.
- Draw every frame on a 108x192 canvas with Pillow, 14-16 colour palette, then upscale exactly 10x with NEAREST to 1080x1920. No smoothing. Bitmap font at integer scales only.
- Visual quality: use layered, textured backdrops, detailed multi-shade focal sprites, a clear title hierarchy and a framed caption rail. Avoid large blank fields and isolated generic icons; keep the main subject large and readable.
- Output: 1080x1920, 30 fps, H.264 yuv420p, AAC 48 kHz stereo, 24-27 s.
- 12 fps feel: hold each pose 2-3 frames. Small screen shake on impacts, sparkle pixels, 2-4 frame sprite loops. Round cards slide in with a bell where it fits the format.
- TikTok safe zones: no text in the top 12% (y<230), bottom 20% (y>1536) or the right button strip (x>900, y 800-1500).
- Voice: edge-tts en-US-AndrewMultilingualNeural, rate +20%, with WordBoundary timings. If edge-tts is unavailable, use the offline ffmpeg fallback and tell me so. Build the timeline from the audio so scenes and icons follow the spoken words. Word-by-word captions near y=1450 with the current word highlighted.
- Audio: generated chiptune (120 bpm, minor key) plus retro sfx timed to visual events, music ducked under the voice, -14 LUFS with true peak below -1 dBFS, verified with ebur128.
- On-screen text must match the voiceover (round labels are fine).

### Steps
1. Copy the project, update config.py (script, cues, titles, labels, palette, handle).
2. Update background.py, sprites.py and scenes.py for the new visuals, keeping one scene function per beat.
3. Update timeline.py sfx events for the new cues.
4. Run render.py, then look at the contact sheet (a frame every 0.75 s with safe-zone lines). Fix overlaps, low contrast, clipped text and any dead stretch over 1 s.
5. Run the QC checks (ffprobe, loudness, safe zones, text vs voiceover) and fix failures.
6. Deliver: the .mp4, the contact sheet, and the project zip. Keep the reply short and say what is approximate (for example the fallback voice).

---

## Format ideas that fit the same engine
- Battle: PLA vs PETG, matte vs silk, 0.4 vs 0.6 nozzle (general terms only).
- Troubleshooting: stringing, warping, layer shift. Show the problem, a fix icon, then a check mark.
- Tip: "3 tips for first layers". Number cards slide in instead of rounds.
- Before/after: rough print becomes sanded or painted.
- Spotlight: one material, one strength, one weakness, best uses.

## Tips for the free tier
- Attach the zip so the model edits instead of rewriting everything.
- Ask for stages, and ask for one render at a time.
- Keep the BRIEF concrete: exact script lines and one visual per beat.
- Skip extra polish passes until the first render looks right.
