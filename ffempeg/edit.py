"""FFmpeg operations used by the CLI and the MCP server.

Inputs may be a local path or an http(s) URL. URL downloads are cached
under media/in. Outputs go under media/out unless an absolute path inside
the workspace, the cache, the output directory, or /tmp is given.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_URL = "https://samples.ffmpeg-api.com/BigBuckBunny_640x360.m4v"


class EditError(Exception):
    """A user-facing media error. The message is safe to show to an agent."""


def cache_dir() -> Path:
    return Path(os.environ.get("FFEMPEG_CACHE_DIR", ROOT / "media" / "in"))


def output_dir() -> Path:
    return Path(os.environ.get("FFEMPEG_OUTPUT_DIR", ROOT / "media" / "out"))


def require_bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise EditError(f"{name} is not on PATH. Install FFmpeg and try again.")
    return path


def ffmpeg_status() -> dict[str, str]:
    ffmpeg = require_bin("ffmpeg")
    ffprobe = require_bin("ffprobe")
    version = _run([ffmpeg, "-version"], 20).stdout.splitlines()[0]
    return {"ffmpeg": ffmpeg, "ffprobe": ffprobe, "version": version}


def probe(source: str) -> dict[str, Any]:
    src = resolve_input(source)
    proc = _run(
        [
            require_bin("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name,bit_rate",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels,bit_rate",
            "-of",
            "json",
            str(src),
        ],
        90,
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise EditError(f"ffprobe returned unreadable output: {exc}") from exc
    data["path"] = str(src)
    data["source"] = source
    return data


def make_gif(
    source: str,
    start: str | float | int = 0,
    duration: str | float | int = 3,
    width: int = 320,
    output: str | None = None,
) -> dict[str, Any]:
    src = resolve_input(source)
    start_s = parse_time(start)
    duration_s = parse_time(duration)
    if duration_s <= 0 or duration_s > 15:
        raise EditError("gif duration must be between 0 and 15 seconds")
    if width < 64 or width > 640:
        raise EditError("gif width must be between 64 and 640")
    dest = _dest(output, src, ".gif", f"{_stamp(start_s, duration_s)}.gif")
    command = [
        require_bin("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        _seconds(start_s),
        "-t",
        _seconds(duration_s),
        "-i",
        str(src),
        "-vf",
        f"fps=12,scale={width}:-2:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer",
        "-loop",
        "0",
        str(dest),
    ]
    _run(command, 180)
    return _artifact(dest, command)


def trim(
    source: str,
    start: str | float | int = 0,
    duration: str | float | int = 3,
    output: str | None = None,
) -> dict[str, Any]:
    src = resolve_input(source)
    start_s = parse_time(start)
    duration_s = parse_time(duration)
    if duration_s <= 0 or duration_s > 3600:
        raise EditError("trim duration must be between 0 and 3600 seconds")
    dest = _dest(output, src, ".mp4", f"trim-{_stamp(start_s, duration_s)}.mp4")
    command = [
        require_bin("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        _seconds(start_s),
        "-t",
        _seconds(duration_s),
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command, 300)
    return _artifact(dest, command)


def extract_audio(
    source: str,
    start: str | float | int = 0,
    duration: str | float | int | None = None,
    output: str | None = None,
) -> dict[str, Any]:
    src = resolve_input(source)
    start_s = parse_time(start)
    duration_s = None if duration is None else parse_time(duration)
    if duration_s is not None and (duration_s <= 0 or duration_s > 3600):
        raise EditError("audio duration must be between 0 and 3600 seconds")
    dest = _dest(output, src, ".mp3", "audio.mp3")
    command = [
        require_bin("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        _seconds(start_s),
    ]
    if duration_s is not None:
        command.extend(["-t", _seconds(duration_s)])
    command.extend(
        [
            "-i",
            str(src),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(dest),
        ]
    )
    _run(command, 300)
    return _artifact(dest, command)


def thumbnail(
    source: str,
    timestamp: str | float | int = 1,
    output: str | None = None,
) -> dict[str, Any]:
    src = resolve_input(source)
    at = parse_time(timestamp)
    dest = _dest(output, src, ".jpg", f"thumb-{_seconds(at).replace('.', '_')}.jpg")
    command = [
        require_bin("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        _seconds(at),
        "-i",
        str(src),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(dest),
    ]
    _run(command, 90)
    return _artifact(dest, command)


def compress(
    source: str,
    crf: int = 28,
    output: str | None = None,
) -> dict[str, Any]:
    src = resolve_input(source)
    if crf < 0 or crf > 51:
        raise EditError("crf must be between 0 and 51")
    dest = _dest(output, src, ".mp4", "compressed.mp4")
    command = [
        require_bin("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command, 600)
    return _artifact(dest, command)


def resolve_input(source: str) -> Path:
    text = source.strip()
    if text.startswith(("https://", "http://")):
        return _download(text)
    if "://" in text:
        raise EditError("only http(s) URLs and local paths are supported")
    path = Path(text).expanduser().resolve()
    if not path.is_file():
        raise EditError(f"input not found: {path}")
    return path


def parse_time(value: str | float | int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise EditError(f"bad timestamp: {value!r}")
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = value.strip()
        if not text:
            raise EditError("timestamp is empty")
        if ":" in text:
            parts = text.split(":")
            if len(parts) not in (2, 3):
                raise EditError(f"bad timestamp: {value}")
            try:
                nums = [float(part) for part in parts]
            except ValueError as exc:
                raise EditError(f"bad timestamp: {value}") from exc
            if len(nums) == 3:
                seconds = nums[0] * 3600 + nums[1] * 60 + nums[2]
            else:
                seconds = nums[0] * 60 + nums[1]
        else:
            try:
                seconds = float(text)
            except ValueError as exc:
                raise EditError(f"bad timestamp: {value}") from exc
    if seconds < 0:
        raise EditError("time must be zero or greater")
    return seconds


def _download(url: str) -> Path:
    name = url.rsplit("/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name).strip("._")
    if not safe:
        safe = "download.bin"
    folder = cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    dest = (folder / safe).resolve()
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    request = urllib.request.Request(url, headers={"User-Agent": "ffempeg/0.1"})
    try:
        response = urllib.request.urlopen(request, timeout=180)
    except Exception as exc:
        raise EditError(f"could not download {url}: {exc}") from exc
    fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".download-")
    tmp_path = Path(tmp_name)
    try:
        with response, os.fdopen(fd, "wb") as handle:
            shutil.copyfileobj(response, handle)
        if tmp_path.stat().st_size <= 0:
            raise EditError(f"download was empty: {url}")
        tmp_path.replace(dest)
    except EditError:
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise EditError(f"could not download {url}: {exc}") from exc
    return dest


def _dest(output: str | None, src: Path, suffix: str, leaf: str) -> Path:
    folder = output_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if output:
        path = Path(output).expanduser()
        if not path.is_absolute():
            path = folder / path
        path = path.resolve()
        if path.suffix.lower() != suffix:
            raise EditError(f"output must use the {suffix} extension")
    else:
        path = (folder / f"{src.stem}-{leaf}").resolve()
    _ensure_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_writable(path: Path) -> None:
    roots = [output_dir().resolve(), cache_dir().resolve(), Path("/tmp").resolve(), ROOT.resolve()]
    if any(path == root or root in path.parents for root in roots):
        return
    raise EditError(f"refusing to write outside the project or /tmp: {path}")


def _artifact(path: Path, command: list[str]) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise EditError(f"ffmpeg did not write {path}")
    return {"output": str(path), "bytes": path.stat().st_size, "command": command}


def _stamp(start: float, duration: float) -> str:
    return f"{_seconds(start).replace('.', '_')}-{_seconds(duration).replace('.', '_')}"


def _seconds(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise EditError(f"{command[0]} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        tail = detail[-1500:] if detail else f"exit {proc.returncode}"
        raise EditError(tail)
    return proc
