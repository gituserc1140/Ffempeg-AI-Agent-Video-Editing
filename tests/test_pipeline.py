import json
import shutil
import tempfile
import os
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from pipeline import config as C
from pipeline import publish, run
from pipeline.font import CHARSET, GLYPHS, text_width
from pipeline.pixel import Canvas
from pipeline.sprites import ICONS
from pipeline.timeline import build
from pipeline.validate import normalize, script_words, validate

TOPICS = json.loads((Path(run.HERE) / "topics.json").read_text())


class FontAndSprites(unittest.TestCase):
    def test_glyphs_are_5x7(self):
        for ch, rows in GLYPHS.items():
            self.assertEqual(len(rows), 7, ch)

    def test_icons_are_square_pixel_art(self):
        for name, rows in ICONS.items():
            self.assertEqual(len({len(r) for r in rows}), 1, name)
            self.assertIn(len(rows), {12, 28}, name)

    def test_detailed_spool_fits_canvas_and_palette(self):
        c = Canvas()
        c.sprite("spool", 27, 62, 1, tint=(13, 14))
        self.assertEqual(c.img.getpixel((27, 62)), C.PALETTE[0])
        self.assertLessEqual(c.color_count(), 16)

    def test_text_stays_in_palette_and_records_box(self):
        c = Canvas()
        c.text("HELLO", 10, 40, 3, scale=2)
        self.assertEqual(c.boxes[0]["x1"] - c.boxes[0]["x0"] + 1, text_width("HELLO", 2) + 2)
        self.assertLessEqual(c.color_count(), 16)

    def test_text_is_kept_out_of_right_strip(self):
        c = Canvas()
        c.text("WIDE WORD HERE", 80, 100, 3, scale=1)
        self.assertLess(c.boxes[0]["x1"], C.STRIP_X)


class Validation(unittest.TestCase):
    def test_topic_bank_is_valid(self):
        for topic in TOPICS:
            self.assertEqual(validate(normalize(topic)), [], topic["slug"])

    def test_rejects_digits_and_brands(self):
        brief = normalize(json.loads(json.dumps(TOPICS[1])))
        brief["beats"][1]["line"] = "First, print at 200 degrees with a Prusa for the best result."
        errs = " ".join(validate(brief))
        self.assertIn("digits", errs)
        self.assertIn("brand", errs)

    def test_trigger_must_be_spoken(self):
        brief = normalize(json.loads(json.dumps(TOPICS[0])))
        brief["beats"][2]["trigger"] = "banana"
        self.assertTrue(any("trigger" in e for e in validate(brief)))

    def test_smart_punctuation_is_normalised(self):
        brief = json.loads(json.dumps(TOPICS[0]))
        brief["beats"][0]["line"] = "Which filament should you pick for your next print\u2014today?"
        self.assertTrue(set(normalize(brief)["beats"][0]["line"].upper()) <= CHARSET)


class Timeline(unittest.TestCase):
    def _voice(self, brief, seconds_per_line=3.2):
        sr = C.SAMPLE_RATE
        out = []
        for b in brief["beats"]:
            toks = b["line"].split()
            step = seconds_per_line / len(toks)
            out.append(dict(text=b["line"], audio=np.zeros(int(seconds_per_line * sr), np.float32),
                            words=[(t, (i * step, (i + 1) * step)) for i, t in enumerate(toks)]))
        return out

    def test_beats_follow_voice_and_duration_is_in_range(self):
        brief = normalize(TOPICS[0])
        plan = build(brief, self._voice(brief))
        self.assertTrue(24.0 <= plan.duration <= 27.0)
        starts = [b["start"] for b in plan.beats]
        self.assertEqual(starts, sorted(starts))
        for b in plan.beats:
            self.assertLess(b["start"], b["trig"])
            self.assertLess(b["trig"], b["end"])
        self.assertTrue(any(n == "bell" for _, n in plan.sfx))

    def test_overlong_script_is_rejected(self):
        brief = normalize(TOPICS[0])
        with self.assertRaises(ValueError):
            build(brief, self._voice(brief, seconds_per_line=6))


class Fallback(unittest.TestCase):
    def test_least_used_topic_is_picked(self):
        used = [{"topic": t["slug"]} for t in TOPICS[:-1]]
        self.assertEqual(run.fallback_topic(used)["slug"], TOPICS[-1]["slug"])


class Publish(unittest.TestCase):
    def test_buffer_mutation_escapes_text_and_returns_post_id(self):
        resp = mock.Mock()
        resp.json.return_value = {"data": {"createPost": {"post": {"id": "p1"}}}}
        with mock.patch.object(publish.requests, "post", return_value=resp) as post:
            pid = publish.buffer_draft('Say "hi" #3dprinting', "https://x/y.mp4", "chan", "key")
        self.assertEqual(pid, "p1")
        query = post.call_args.kwargs["json"]["query"]
        self.assertIn('\\"hi\\"', query)
        self.assertIn("saveToDraft: true", query)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer " + "key")

    def test_buffer_error_is_reported_not_raised(self):
        with mock.patch.object(publish, "upload", return_value="https://x/y.mp4"), \
                mock.patch.object(publish, "buffer_draft", side_effect=RuntimeError("nope")), \
                mock.patch.dict("os.environ", {"BUFFER_CHANNEL_ID": "c", "BUFFER_API_KEY": "k",
                                         "S3_BUCKET": "b"}):
            out = publish.publish("v.mp4", "k.mp4", "caption")
        self.assertEqual(out["url"], "https://x/y.mp4")
        self.assertIn("buffer failed", out["error"])

    def test_release_upload_used_without_bucket(self):
        env = {"BUFFER_CHANNEL_ID": "c", "BUFFER_API_KEY": "k"}
        with mock.patch.object(publish, "upload_release", return_value="https://dl/a.mp4") as up, \
                mock.patch.object(publish, "buffer_draft", return_value="p1"), \
                mock.patch.dict("os.environ", env):
            os.environ.pop("S3_BUCKET", None)
            out = publish.publish("v.mp4", "shorts/a.mp4", "caption")
        up.assert_called_once()
        self.assertEqual(out["post_id"], "p1")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("espeak-ng"),
                     "needs ffmpeg and espeak-ng")
class EndToEnd(unittest.TestCase):
    def test_render_and_qc_with_fallback_voice(self):
        from pipeline import qc
        from pipeline.render import render

        with tempfile.TemporaryDirectory() as tmp:
            render(TOPICS[2], tmp, force_fallback_voice=True)
            report = qc.run(tmp)
            failed = {k: v["detail"] for k, v in report["checks"].items() if not v["ok"]}
            self.assertEqual(failed, {})
            self.assertEqual(report["voice_engine"], "espeak-ng (fallback)")


if __name__ == "__main__":
    unittest.main()
