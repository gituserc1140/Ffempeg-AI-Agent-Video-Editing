#!/usr/bin/env python3
"""Stdio MCP server that exposes local FFmpeg edits to Cursor and Claude."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ffempeg.edit import (  # noqa: E402
    SAMPLE_URL,
    EditError,
    compress,
    extract_audio,
    ffmpeg_status,
    make_gif,
    probe,
    thumbnail,
    trim,
)

SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "check_ffmpeg",
        "description": "Check that ffmpeg and ffprobe are installed and return the version line.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "probe_media",
        "description": (
            "Inspect a local file or public http(s) URL with ffprobe. "
            f"Example source: {SAMPLE_URL}"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Local path or http(s) URL"}
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "make_gif",
        "description": "Make a GIF of up to 15 seconds from a video. Defaults to the first 3 seconds at 320px wide.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "start": {"type": ["number", "string"], "description": "Start time in seconds or HH:MM:SS"},
                "duration": {"type": ["number", "string"]},
                "width": {"type": "integer", "minimum": 64, "maximum": 640},
                "output": {"type": "string", "description": "Optional .gif path"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "trim_media",
        "description": "Cut a clip and re-encode it to H.264 MP4.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "start": {"type": ["number", "string"]},
                "duration": {"type": ["number", "string"]},
                "output": {"type": "string"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_audio",
        "description": "Extract audio to MP3.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "start": {"type": ["number", "string"]},
                "duration": {"type": ["number", "string"]},
                "output": {"type": "string"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "thumbnail",
        "description": "Grab one JPEG frame at a timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "timestamp": {"type": ["number", "string"]},
                "output": {"type": "string"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compress_media",
        "description": "Re-encode a video to H.264 with a CRF quality value (default 28).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "crf": {"type": "integer", "minimum": 0, "maximum": 51},
                "output": {"type": "string"},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
]


def main() -> None:
    while True:
        message = _read_message()
        if message is None:
            return
        response = _handle(message)
        if response is not None:
            _send(response)


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}
    if method and method.startswith("notifications/"):
        return None
    if method == "initialize":
        requested = str(params.get("protocolVersion") or "2024-11-05")
        version = requested if requested in SUPPORTED else "2024-11-05"
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ffempeg", "version": "0.1.0"},
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        return _result(msg_id, _call_tool(str(params.get("name") or ""), params.get("arguments") or {}))
    if msg_id is None:
        return None
    return _error(msg_id, -32601, f"unknown method: {method}")


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(arguments, dict):
            raise EditError("tool arguments must be an object")
        payload = _dispatch(name, arguments)
    except EditError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    except Exception as exc:  # noqa: BLE001 — surface unexpected failures to the client
        return {"content": [{"type": "text", "text": f"unexpected error: {exc}"}], "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}], "isError": False}


def _dispatch(name: str, arguments: dict[str, Any]) -> Any:
    if name == "check_ffmpeg":
        return ffmpeg_status()
    source = arguments.get("source")
    if name == "probe_media":
        return probe(_source(source))
    if name == "make_gif":
        return make_gif(
            _source(source),
            start=arguments.get("start", 0),
            duration=arguments.get("duration", 3),
            width=int(arguments.get("width", 320)),
            output=arguments.get("output"),
        )
    if name == "trim_media":
        return trim(
            _source(source),
            start=arguments.get("start", 0),
            duration=arguments.get("duration", 3),
            output=arguments.get("output"),
        )
    if name == "extract_audio":
        return extract_audio(
            _source(source),
            start=arguments.get("start", 0),
            duration=arguments.get("duration"),
            output=arguments.get("output"),
        )
    if name == "thumbnail":
        return thumbnail(
            _source(source),
            timestamp=arguments.get("timestamp", 1),
            output=arguments.get("output"),
        )
    if name == "compress_media":
        return compress(_source(source), crf=int(arguments.get("crf", 28)), output=arguments.get("output"))
    raise EditError(f"unknown tool: {name}")


def _source(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EditError("source is required")
    return value


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _read_message() -> dict[str, Any] | None:
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if not line.strip():
            continue
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
            while True:
                header = sys.stdin.buffer.readline()
                if header in (b"\r\n", b"\n", b""):
                    break
            body = sys.stdin.buffer.read(length)
            return json.loads(body)
        return json.loads(line.decode())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
