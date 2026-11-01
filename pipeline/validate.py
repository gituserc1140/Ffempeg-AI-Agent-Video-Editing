"""Brief schema validation. A brief is the JSON that drives one video."""
import re

from . import config as C
from .font import CHARSET, text_width
from .rounds import MODULES
from .sprites import ICONS
from .tts import normalize_token

SCENES_MID = {"icon", "card", "fix", "round"}
SIDES = {"a", "b", "both"}
BRANDS = {
    "prusa", "bambu", "creality", "ender", "polymaker", "sunlu", "esun", "hatchbox",
    "overture", "elegoo", "anycubic", "formlabs", "ultimaker", "makerbot", "flashforge",
}
SMART = {"\u2019": "'", "\u2018": "'", "\u201c": "", "\u201d": "", "\u2014": "-",
         "\u2013": "-", "\u2026": "."}


def clean_text(s):
    for a, b in SMART.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def normalize(brief):
    """Tidy typographic characters and fill defaults before validating."""
    brief = dict(brief)
    brief["handle"] = C.HANDLE
    brief["beats"] = [dict(b, line=clean_text(b.get("line", "")),
                           trigger=clean_text(b.get("trigger", "")),
                           label=clean_text(b.get("label", "")).upper(),
                           **({"verdict": [dict(r, trait=clean_text(r.get("trait", "")).upper())
                                           for r in b["verdict"]]}
                              if isinstance(b.get("verdict"), list) else {}))
                      for b in brief.get("beats", [])]
    return brief


def script_words(brief):
    return [w for b in brief["beats"] for w in b["line"].split()]


def validate(brief, allow_numbers=False):
    """Returns a list of human-readable problems (empty list = valid)."""
    errs = []
    for key in ("slug", "title", "caption", "layout", "subject_a", "beats"):
        if key not in brief:
            errs.append(f"missing '{key}'")
    if errs:
        return errs
    if not re.fullmatch(r"[a-z0-9-]{3,60}", brief["slug"]):
        errs.append("slug must be lowercase letters, digits and hyphens")
    if brief["layout"] not in ("split", "single"):
        errs.append("layout must be 'split' or 'single'")
    subjects = [("subject_a", brief["subject_a"])]
    if brief["layout"] == "split":
        if not brief.get("subject_b"):
            errs.append("split layout needs subject_b")
        else:
            subjects.append(("subject_b", brief["subject_b"]))
    for name, s in subjects:
        if s.get("color") not in C.FAMILIES:
            errs.append(f"{name}.color must be one of {sorted(C.FAMILIES)}")
        if s.get("icon") not in ICONS:
            errs.append(f"{name}.icon must be one of {sorted(ICONS)}")
        label = s.get("label", "")
        if not label or any(ch not in CHARSET for ch in label.upper()) or text_width(label, 1) > 50:
            errs.append(f"{name}.label must be short text (<=8 chars) using plain characters")

    beats = brief["beats"]
    if not 5 <= len(beats) <= 6:
        errs.append("need 5-6 beats")
    words = 0
    for i, b in enumerate(beats):
        tag = f"beat {i + 1}"
        line = b.get("line", "")
        words += len(line.split())
        if any(ch not in CHARSET for ch in line.upper()):
            bad = sorted({ch for ch in line.upper() if ch not in CHARSET})
            errs.append(f"{tag}: unsupported characters {bad}")
        if len(line.split()) < 6:
            errs.append(f"{tag}: line too short")
        if any(len(w) > 14 for w in line.split()):
            errs.append(f"{tag}: word longer than 14 characters")
        if b.get("icon") not in ICONS:
            errs.append(f"{tag}: icon must be one of {sorted(ICONS)}")
        if b.get("side") not in SIDES:
            errs.append(f"{tag}: side must be a, b or both")
        want = "hook" if i == 0 else "end" if i == len(beats) - 1 else None
        if want and b.get("scene") != want:
            errs.append(f"{tag}: scene must be '{want}'")
        if not want and b.get("scene") not in SCENES_MID:
            errs.append(f"{tag}: scene must be one of {sorted(SCENES_MID)}")
        trig = normalize_token(b.get("trigger", ""))
        if not trig or trig not in [normalize_token(w) for w in line.split()]:
            errs.append(f"{tag}: trigger must be a word spoken in the line")
        elif len(trig) > 14:
            errs.append(f"{tag}: trigger too long")
        if b.get("scene") == "card":
            label = b.get("label", "")
            if not label or any(ch not in CHARSET for ch in label) or text_width(label, 1) > 58:
                errs.append(f"{tag}: card needs a short label like 'ROUND 1'")
        if b.get("scene") == "round":
            mod = b.get("module")
            if brief["layout"] != "split":
                errs.append(f"{tag}: round scenes need the split layout")
            elif mod not in MODULES:
                errs.append(f"{tag}: module must be one of {sorted(MODULES)}")
            else:
                for k in ("fx_a", "fx_b"):
                    if b.get(k) not in MODULES[mod]:
                        errs.append(f"{tag}: {k} must be one of {list(MODULES[mod])} for {mod}")
            if b.get("win", "tie") not in ("a", "b", "tie"):
                errs.append(f"{tag}: win must be a, b or tie")
        if b.get("verdict") is not None:
            rows = b["verdict"]
            if want != "end" or not isinstance(rows, list) or not 1 <= len(rows) <= 2:
                errs.append(f"{tag}: verdict is 1-2 rows on the last beat")
            else:
                spoken = [normalize_token(w) for w in line.split()]
                for row in rows:
                    if row.get("pick") not in ("a", "b") or \
                            normalize_token(row.get("trait", "")) not in spoken or \
                            text_width(row.get("trait", ""), 1) > 70:
                        errs.append(f"{tag}: verdict rows need a spoken trait word and pick a or b")
        if not allow_numbers and re.search(r"\d", line.replace("3D", "").replace("3d", "")):
            errs.append(f"{tag}: no digits allowed, spell numbers out")
        low = {normalize_token(w) for w in line.split()}
        if low & BRANDS:
            errs.append(f"{tag}: brand names are not allowed")
    if not 56 <= words <= 74:
        errs.append(f"script has {words} words, need about 60-70")
    return errs
