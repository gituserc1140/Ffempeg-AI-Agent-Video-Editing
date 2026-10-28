# Pixel versus shorts

`python3 render.py` builds a 1080x1920, 30 fps vertical short in retro pixel art from code alone. There is no filming and no generated imagery. The default topic is "Wood PLA vs Metal PLA: Which One Wins?".

Requirements: Python 3, `pip install -r requirements.txt` (Pillow, numpy, edge-tts), and `ffmpeg` / `ffprobe` on `PATH`. The first run needs network access for the edge-tts voice. Voice clips are then cached in `build/tts`.

## What it writes

| File | What |
| --- | --- |
| `output/<name>.mp4` | H.264 yuv420p + AAC 48 kHz stereo |
| `output/<name>-contact.png` | A frame every 0.75 s with the TikTok safe-zone lines drawn on |
| `output/<name>-qc.json` | Timeline, word timings, on-screen text vs voice, ffprobe and ebur128 results |

`render.py` exits non-zero if any check fails.

## How it works

1. `timeline.py` synthesises each script line with edge-tts (`en-US-AndrewMultilingualNeural`, `+20%`) and keeps the WordBoundary events. Scene lengths come from the speech. Each `cues` entry in the config names a word, and the scene fires that event when the word is spoken.
2. `scenes.py` has one draw function and one event function per beat: `hook`, `look`, `printing`, `finishing`, `weight`, `verdict`. The events are the sound effects and screen shakes for the same cues.
3. Frames are drawn on a 108x192 palette image with Pillow (`pixel.py`, `sprites.py`, `font.py`). The palette has 16 colours and the bitmap font is 5x7 at integer scales. Each frame is upscaled 10x with NEAREST. Poses change 12 times a second and are held for 3 then 2 frames at 30 fps.
4. `captions.py` draws word-by-word captions around y=1440, with the spoken word in yellow.
5. `audio.py` writes a 120 bpm A-minor loop (triangle bass, square stabs and arpeggio, noise drums) and the effects: bell, impact, whoosh, blips, sandpaper rasp, metal clank, grind. Music ducks about 11 dB under the voice. The mix is normalised to -14 LUFS through a look-ahead limiter, then the AAC file is checked with `ffmpeg ebur128`. True peak must stay below -1 dBFS.
6. `qc.py` does the following:
   - checks every drawn text box against the safe zones (y<230, y>1536, and x>900 for y 800-1500) and the frame edges
   - flags overlapping text
   - checks every on-screen word against the voiceover, and that it appears no earlier than 0.5 s before it is spoken
   - flags stretches longer than 1 s with almost no motion
   - runs ffprobe
   - builds the contact sheet

## Changing the topic or text

The reusable brief is [`pixel_video_prompt.md`](../pixel_video_prompt.md). Copy `topics/template.json` to a new file and fill it in. `topics/wood_vs_metal_pla.json` is the finished example. Do not render `template.json` as it is: the lines are placeholders, and the cue words have to match the script exactly.

- `voice`, `rate`, `handle`, `left` / `right` names, and `output`.
- Each beat's `line` is what is spoken. Its `cues` map event names to spoken words: `"metal"`, or `"metal#2"` for the second time it is said. Its `labels` set the on-screen words.
- `window` is the beat's preferred length. Spare time is spread toward it when the speech runs short.

Then run `python3 render.py --config path/to/topic.json`.

The six scene types draw this matchup's props (spools, nozzles, blocks, see-saw). A different A-vs-B comparison can reuse them with new text. A topic that needs different props needs a new scene function in `scenes.py` and a `SCENES` entry.
