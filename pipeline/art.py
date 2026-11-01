"""Generate topic-specific pixel sprites as palette grids with the OpenAI Responses API."""
import hashlib
import json
import os
from pathlib import Path

import requests

from .sprites import CHARS

URL = "https://api.openai.com/v1/responses"
MODEL = os.environ.get("OPENAI_SPRITE_MODEL", "gpt-5")
SIZE = 24
CACHE = Path("media/art_cache")

_PIXELS = set(CHARS) | {"a", "A", "."}
_FORMAT = {
    "type": "json_schema",
    "name": "pixel_sprite",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"rows": {"type": "array", "items": {"type": "string"}}},
        "required": ["rows"],
        "additionalProperties": False,
    },
}


def _valid_rows(rows):
    return (isinstance(rows, list) and len(rows) == SIZE and
            all(isinstance(row, str) and len(row) == SIZE and set(row) <= _PIXELS
                for row in rows))


def _response_rows(response):
    if not isinstance(response, dict):
        raise ValueError("response was not a JSON object")
    text = "".join(
        part["text"]
        for item in response.get("output", [])
        if isinstance(item, dict)
        for part in item.get("content", [])
        if isinstance(part, dict) and part.get("type") == "output_text"
        and isinstance(part.get("text"), str)
    )
    if not text:
        raise ValueError("response contained no sprite grid")
    payload = json.loads(text)
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not _valid_rows(rows):
        raise ValueError(f"sprite must be a {SIZE}x{SIZE} grid using the pipeline palette")
    return rows


def _prompt(description):
    return f"""Create one distinctive, highly readable pixel-art game sprite for this object:
{description}

Return exactly {SIZE} rows of {SIZE} characters each, top to bottom. Make one centered object
with a recognizable silhouette, a one-pixel dark outline, purposeful highlights and shadows,
and transparent padding. Use chunky pixel clusters, not noise or dithering. No visible text,
labels, numerals, border, background, gradients, antialiasing, or extra objects; grid characters
are palette codes only.

Use only this fixed character palette:
. transparent; a/A subject-color light/shadow; k black outline; b deep slate; w white;
g steel grey; d dark steel; o/O orange light/shadow; c/C cyan light/shadow; n green;
r red; y yellow; p pink; u violet; N dark green.
Make the shape and details specific to the described object, rather than a generic icon.
Output only the JSON object required by the schema."""


def draw(name, description):
    """Return a 24x24 palette sprite, or None so the caller can use a built-in icon."""
    key = os.environ.get("OPENAI_API_KEY")
    desc = " ".join(str(description).split())[:100]
    if not key or not desc:
        return None

    cache_id = hashlib.sha256(f"{MODEL}\0{desc}".encode()).hexdigest()[:20]
    path = CACHE / f"{cache_id}.json"
    if path.is_file():
        try:
            cached = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[art] ignoring unreadable sprite cache for '{name}': {exc}")
        else:
            if _valid_rows(cached):
                print(f"[art] reused cached sprite '{name}'")
                return cached
            print(f"[art] ignoring invalid sprite cache for '{name}'")

    try:
        response = requests.post(
            URL,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            timeout=120,
            json={
                "model": MODEL,
                "input": _prompt(desc),
                "text": {"format": _FORMAT},
                "max_output_tokens": 1800,
            },
        )
        response.raise_for_status()
        rows = _response_rows(response.json())
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        print(f"[art] could not generate '{name}' with {MODEL}: {exc}")
        return None

    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows))
    except OSError as exc:
        print(f"[art] could not cache '{name}': {exc}")
    print(f"[art] generated '{name}' with {MODEL}")
    return rows
