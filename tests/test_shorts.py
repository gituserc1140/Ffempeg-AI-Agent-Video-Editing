import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from shorts import audio, captions
from shorts import palette as P
from shorts.font import GLYPHS, text_points, text_width
from shorts.pixel import Canvas, box_violations, build_background, pose_of_frame, safe_place, to_output
from shorts.qc import _tokens
from shorts.timeline import Word, norm


class PixelTests(unittest.TestCase):
    def test_palette_is_fixed_and_small(self) -> None:
        self.assertLessEqual(len(P.COLORS), 16)
        self.assertEqual(len(P.FLAT), 768)

    def test_glyphs_are_5x7_and_scale_by_integers(self) -> None:
        for ch, pts in GLYPHS.items():
            self.assertTrue(all(0 <= x < 5 and 0 <= y < 7 for x, y in pts), ch)
        self.assertEqual(len(text_points("A", 0, 0, 2)), 4 * len(GLYPHS["A"]))
        self.assertEqual(text_width("ABC", 2), 34)
        with self.assertRaises(ValueError):
            text_points("A", 0, 0, 1.5)

    def test_safe_place_keeps_text_out_of_ui_zones(self) -> None:
        for x, y in ((100, 5), (100, 100), (0, 150), (80, 70)):
            nx, ny = safe_place(x, y, 47, 7, 1, 1)
            self.assertEqual(box_violations((nx - 1, ny - 1, nx + 47, ny + 7)), [])

    def test_canvas_uses_only_palette_indices_and_nearest_upscale(self) -> None:
        cv = Canvas.from_background(build_background())
        cv.text("VS", 54, 96, color=P.YELLOW, scale=2)
        idx = np.asarray(cv.img)
        self.assertLessEqual(int(idx.max()), 15)
        out = np.asarray(to_output(cv.img))
        self.assertEqual(out.shape, (1920, 1080, 3))
        block = out[960:970, 540:550].reshape(-1, 3)
        self.assertTrue((block == block[0]).all())
        self.assertLessEqual(len(Image.fromarray(out).getcolors(1 << 16)), 16)

    def test_tpu_theme_recolours_slots_and_restores(self) -> None:
        original = [tuple(rgb) for rgb in P.COLORS]
        try:
            P.apply_theme("tpu-abs")
            self.assertEqual(tuple(P.COLORS[P.WOOD1]), (214, 82, 14))
            self.assertEqual(tuple(P.COLORS[P.STEEL1]), (18, 64, 168))
            self.assertEqual(tuple(P.COLORS[P.STEEL0]), (46, 50, 62))
            self.assertEqual(len(P.COLORS), 16)
            rubber = np.asarray(build_background(theme="tpu-abs"))
            planks = np.asarray(build_background(theme="wood-metal"))
            self.assertEqual(int((rubber[:, :40] == P.STEEL1).sum()), 0)
            self.assertGreater(int((rubber[:, 70:] == P.GREEN).sum()), 200)
            self.assertGreater(int((planks[:, :40] == P.WOOD1).sum()), int((rubber[:, :40] == P.WOOD1).sum()))
            with self.assertRaises(ValueError):
                P.apply_theme("nope")
        finally:
            P.apply_theme("wood-metal")
        self.assertEqual([tuple(rgb) for rgb in P.COLORS], original)
        self.assertEqual(P.THEME, "wood-metal")

    def test_halloween_theme_is_a_night_sky(self) -> None:
        original = [tuple(rgb) for rgb in P.COLORS]
        try:
            P.apply_theme("halloween")
            self.assertEqual(tuple(P.COLORS[P.WOOD1]), (204, 78, 14))
            self.assertEqual(tuple(P.COLORS[P.STEEL0]), (46, 50, 62))
            self.assertEqual(len({tuple(rgb) for rgb in P.COLORS}), 16)
            sky = np.asarray(build_background(theme="halloween"))
            self.assertGreater(int((sky[:100] == P.NAVY2).sum()), 8000)
            self.assertGreater(int((sky == P.CREAM).sum()), 20)
        finally:
            P.apply_theme("wood-metal")
        self.assertEqual([tuple(rgb) for rgb in P.COLORS], original)

    def test_poses_hold_two_or_three_frames(self) -> None:
        holds, last, run = [], 0, 0
        for f in range(60):
            p = pose_of_frame(f)
            if p != last:
                holds.append(run)
                last, run = p, 0
            run += 1
        self.assertEqual(set(holds), {2, 3})


class CaptionTests(unittest.TestCase):
    def test_pages_fit_two_rows_of_thirteen(self) -> None:
        words = [Word(w, w.upper(), i * 0.3, i * 0.3 + 0.2) for i, w in enumerate("wood is warm and matte metal is shiny and cool".split())]
        for page in captions.paginate(words):
            self.assertLessEqual(len(page), 2)
            for row in page:
                self.assertLessEqual(sum(len(words[i].display) for i in row) + len(row) - 1, captions.MAX_CHARS)

    def test_tokens_alias_badges_and_numbers(self) -> None:
        self.assertEqual(_tokens("WEIGHT & SHINE?"), ["weight", "and", "shine"])
        self.assertEqual(_tokens("metal-fill PLA"), ["metal", "fill", "pla"])


class TopicTests(unittest.TestCase):
    def test_every_cue_word_is_in_its_line(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in (root / "shorts" / "topics").glob("*.json"):
            for beat in json.loads(path.read_text())["beats"]:
                spoken = [norm(tok) for tok in beat["line"].split()]
                for spec in beat.get("cues", {}).values():
                    word, _, nth = spec.partition("#")
                    count = spoken.count(norm(word))
                    need = int(nth) if nth else 1
                    self.assertGreaterEqual(count, need, f"{path.name} {beat['id']} cue {spec!r}")


class AudioTests(unittest.TestCase):
    def test_limiter_holds_ceiling(self) -> None:
        x = np.random.default_rng(1).uniform(-2, 2, (48000, 2))
        y = audio.limiter(x, -2.0)
        self.assertLessEqual(float(np.max(np.abs(y))), 10 ** (-2.0 / 20) + 1e-6)

    def test_music_and_effects_are_finite(self) -> None:
        m = audio.music(2.0)
        self.assertEqual(m.shape, (96000, 2))
        self.assertEqual(len(audio.music(18.9)), int(round(18.9 * audio.SR)))
        self.assertTrue(np.isfinite(m).all())
        for name, make in audio.SFX_BANK.items():
            s = make()
            self.assertTrue(len(s) > 0 and np.isfinite(s).all(), name)


if __name__ == "__main__":
    unittest.main()
