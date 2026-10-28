# Reusable prompt: pixel-art 3D printing short (TikTok, 1080x1920)

This prompt matches the pipeline in this repo. A new short is a new topic file plus, only when the pictures change, edits to `shorts/sprites.py` and `shorts/scenes.py`.

## How to use

1. Copy `shorts/topics/template.json` to `shorts/topics/<name>.json`.
2. Paste the prompt below into a new chat with the BRIEF filled in. Delete anything that does not apply.
3. If the chat gets long, work in stages: "do step 1 and 2 only", then "now step 3 and 4".

The finished example is `shorts/topics/wood_vs_metal_pla.json`, built with `python3 render.py`.

---

## PROMPT (copy from here)

You are a motion-graphics programmer. Reuse this repo's pipeline. Do not rewrite modules that do not need to change. Add a new topic file. Leave `shorts/topics/wood_vs_metal_pla.json` and `output/wood-vs-metal-pla.mp4` as they are.

### Files

Leave these alone unless a fixed rule below is actually broken: `render.py`, `shorts/audio.py`, `shorts/qc.py`, `shorts/captions.py`, `shorts/font.py`, `shorts/timeline.py`, `shorts/pixel.py`.

Edit for every new short:

- `shorts/topics/<name>.json` is the config. There is no `config.py`.

Edit only when the pictures or colours change:

- `shorts/scenes.py` has one draw function and one event function per beat, registered in `SCENES`. The built-in beats are `hook`, `look`, `printing`, `finishing`, `weight`, `verdict`.
- `shorts/sprites.py` holds the props those beats draw.
- `shorts/palette.py` holds the 16 colours. `pixel.build_background()` in `shorts/pixel.py` paints the wood and steel split. There is no `background.py`.
- Voice synthesis lives in `shorts/timeline.py`. There is no `tts.py` and no offline ffmpeg voice. If edge-tts fails, say so and stop.
- Frame encoding lives in `render.py`. There is no `frames.py`.

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
- Rules: [general terms only, no numbers, temperatures or brand names | numbers allowed]

### Topic file

Copy `shorts/topics/template.json`. Set `title`, `output`, `handle`, `left`, `right`, and one beat per spoken line.

- `line` is spoken aloud by edge-tts.
- `cues` map an event name to a word in that line. `"metal#2"` means the second time "metal" is said. The scene and the sound effects read those cues. Nothing may appear more than half a second before its word.
- `labels` are the on-screen words. They must be words the line actually says. `ROUND` and `VS` are the exceptions.
- `scene` is a key in `SCENES`. Reuse one when the motion fits. Add a function pair in `scenes.py` when it does not.
- `window` is the preferred length in seconds. Speech decides the real length. Saying "Round one" in every line made a 60-word script run past 27 seconds, so the sample says "Looks." and the card shows `ROUND 1`.

Run it with:

```bash
python3 render.py --config shorts/topics/<name>.json
```

### Fixed rules (do not change)

- Code-only. No filming and no AI image or video generation. It must look hand-made.
- Draw every frame on a 108x192 canvas with Pillow, a palette of 14-16 colours, then upscale exactly 10x with NEAREST to 1080x1920. No smoothing. Bitmap font at integer scales only.
- Output: 1080x1920, 30 fps, H.264 yuv420p, AAC 48 kHz stereo, 24-27 s.
- 12 fps feel: hold each pose 2 or 3 frames. Small screen shake on impacts, sparkle pixels, sprite loops of 2-4 poses. Round cards slide in with a bell where that fits the format.
- TikTok safe zones: no text in the top 12% (y<230), the bottom 20% (y>1536), or the right button strip (x>900, y 800-1500).
- Voice: edge-tts `en-US-AndrewMultilingualNeural`, rate `+20%`, with WordBoundary timings. Build the timeline from the audio so scenes and icons follow the spoken words. Word-by-word captions near y=1450, current word in yellow.
- Audio: chiptune at 120 bpm in a minor key, plus retro sound effects timed to the cues. Duck the music under the voice. Master to about -14 LUFS with true peak below -1 dBFS, and verify with ffmpeg ebur128.
- On-screen text must match the voiceover. Round labels are fine.
- `render.py` exits non-zero when a check fails. The report next to the mp4 (`<name>-qc.json`) lists the failures. `<name>-contact.png` is a frame every 0.75 s with the safe-zone lines drawn on.

### Steps

1. Copy `shorts/topics/template.json` and fill in the script, cues, labels, names, and handle.
2. Change `sprites.py`, `scenes.py`, and `palette.py` only for visuals the current beats cannot show. Keep one scene function per beat.
3. Put each new sound on the same cue as the picture, in that beat's event function. The effect names are `bell`, `impact`, `whoosh`, `blip`, `blip_hi`, `ting`, `rasp`, `clank`, `grind`.
4. Run `python3 render.py --config shorts/topics/<name>.json`. Look at the contact sheet. Fix overlaps, weak contrast, clipped text, and any stretch over 1 second with almost no motion.
5. Read the `<name>-qc.json` beside the mp4. Fix every failed ffprobe, loudness, safe-zone, or voiceover check.
6. Deliver the `.mp4`, the contact sheet, and the topic file. Keep the reply short.

---

## Format ideas that fit the same engine

- Battle: PLA vs PETG, matte vs silk, a fine nozzle vs a coarse one. Stay in general terms when the brief says so.
- Troubleshooting: stringing, warping, layer shift. Show the problem, a fix icon, then a check mark. The printing beat already has a clog burst and a green check.
- Tip: "3 tips for first layers". Number cards slide in instead of rounds.
- Before/after: a rough print becomes sanded or painted. The finishing beat already sands, stains, and polishes.
- Spotlight: one material, one strength, one weakness, best uses.

## Tips for a short chat

- Point at this repo. Do not ask for a new renderer.
- Ask for stages, and ask for one render at a time.
- Keep the BRIEF concrete: exact script lines, and one visual per beat tied to one spoken word.
- Skip extra polish until the first render looks right.
