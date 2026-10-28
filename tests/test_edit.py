import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ffempeg.edit import (
    EditError,
    compress,
    extract_audio,
    make_gif,
    parse_time,
    probe,
    resolve_input,
    thumbnail,
    trim,
)


def _synthetic(folder: Path) -> Path:
    from ffempeg.edit import _run, require_bin

    dest = folder / "clip.mp4"
    _run(
        [
            require_bin("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(dest),
        ],
        60,
    )
    return dest


class EditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        os.environ["FFEMPEG_CACHE_DIR"] = str(root / "in")
        os.environ["FFEMPEG_OUTPUT_DIR"] = str(root / "out")
        self.clip = _synthetic(root)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("FFEMPEG_CACHE_DIR", None)
        os.environ.pop("FFEMPEG_OUTPUT_DIR", None)

    def test_probe_reports_video_and_audio(self) -> None:
        info = probe(str(self.clip))
        types = {stream["codec_type"] for stream in info["streams"]}
        self.assertEqual(types, {"video", "audio"})
        self.assertGreater(float(info["format"]["duration"]), 1)

    def test_gif_trim_audio_thumbnail_compress(self) -> None:
        gif = make_gif(str(self.clip), duration=1, width=160)
        clip = trim(str(self.clip), start=0.2, duration=1)
        audio = extract_audio(str(self.clip), duration=1)
        still = thumbnail(str(self.clip), timestamp=0.5)
        smaller = compress(str(self.clip), crf=32)
        for result, suffix in (
            (gif, ".gif"),
            (clip, ".mp4"),
            (audio, ".mp3"),
            (still, ".jpg"),
            (smaller, ".mp4"),
        ):
            path = Path(result["output"])
            self.assertTrue(path.is_file())
            self.assertGreater(result["bytes"], 100)
            self.assertEqual(path.suffix, suffix)

    def test_rejects_escape_and_bad_duration(self) -> None:
        with self.assertRaises(EditError):
            make_gif(str(self.clip), output="/etc/passwd.gif")
        with self.assertRaises(EditError):
            make_gif(str(self.clip), duration=30)
        with self.assertRaises(EditError):
            probe("missing-file.mp4")

    def test_parse_time(self) -> None:
        self.assertEqual(parse_time("1:02.5"), 62.5)
        self.assertEqual(parse_time("00:00:03"), 3)

    def test_download_caches_http_file(self) -> None:
        payload = b"sample-bytes"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, fmt: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/BigBuckBunny_640x360.m4v"
            first = resolve_input(url)
            second = resolve_input(url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(first, second)
        self.assertEqual(first.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
