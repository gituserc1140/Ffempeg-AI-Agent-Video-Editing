"""Pixel-art icons. 'a'/'A' = subject colour (main/dark); other letters are fixed colours."""
import math
import re

CHARS = {
    "w": 3, "g": 4, "d": 5, "o": 6, "O": 7, "c": 8, "C": 9, "n": 10,
    "r": 11, "y": 12, "p": 13, "u": 14, "N": 15, "k": 0, "b": 1,
}

ICONS = {
    "printer": [
        "gggggggggggg", "g..........g", "g....aa....g", "g....aa....g",
        "g....AA....g", "g.....A....g", "g..........g", "g..aaaaaa..g",
        "g..aaaaaa..g", "gggggggggggg", "dddddddddddd", "............",
    ],
    "spool": [
        "...aaaaaa...", "..aaaaaaaa..", ".aaaAAAAaaa.", "aaaAA..AAaaa",
        "aaAA....AAaa", "aaAA....AAaa", "aaAA....AAaa", "aaaAA..AAaaa",
        ".aaaAAAAaaa.", "..aaaaaaaa..", "...aaaaaa...", "............",
    ],
    "nozzle": [
        "..gggggggg..", "..gwwwwwwg..", "...gggggg...", "...gddddg...",
        "...gddddg...", "....gddg....", "....gaag....", ".....aa.....",
        ".....AA.....", ".....aa.....", "....a..a....", "............",
    ],
    "flame": [
        ".....r......", ".....rr.....", "....rrr.r...", "...rrrrrr...",
        "..rrrooorr..", "..rroooorr..", ".rrooyyoorr.", ".rrooyyoorr.",
        ".rrooyyyorr.", "..rooyyyor..", "..rrooooorr.", "...rrrrrr...",
    ],
    "snow": [
        ".....cc.....", "..c..cc..c..", "...c.cc.c...", "....cccc....",
        "cccccccccccc", "cccccccccccc", "....cccc....", "...c.cc.c...",
        "..c..cc..c..", ".....cc.....", "............", "............",
    ],
    "check": [
        "............", "..........nn", ".........nnn", "........nnn.",
        "nn.....nnn..", "nnn...nnn...", ".nnn.nnn....", "..nnnnn.....",
        "...nnn......", "....n.......", "............", "............",
    ],
    "cross": [
        "rr........rr", "rrr......rrr", ".rrr....rrr.", "..rrr..rrr..",
        "...rrrrrr...", "....rrrr....", "....rrrr....", "...rrrrrr...",
        "..rrr..rrr..", ".rrr....rrr.", "rrr......rrr", "rr........rr",
    ],
    "star": [
        ".....yy.....", ".....yy.....", "....yyyy....", "yyyyyyyyyyyy",
        ".yyyyyyyyyy.", "..yyyyyyyy..", "...yyyyyy...", "..yyyyyyyy..",
        "..yyy..yyy..", ".yy......yy.", ".y........y.", "............",
    ],
    "heart": [
        "............", ".rrr....rrr.", "rrrrr..rrrrr", "rrwrrrrrrrrr",
        "rrrrrrrrrrrr", "rrrrrrrrrrrr", ".rrrrrrrrrr.", "..rrrrrrrr..",
        "...rrrrrr...", "....rrrr....", ".....rr.....", "............",
    ],
    "bolt": [
        "......yyyy..", ".....yyyy...", "....yyyy....", "...yyyy.....",
        "..yyyyyyyy..", "....yyyyyy..", "......yyy...", ".....yyy....",
        "....yyy.....", "...yy.......", "..y.........", "............",
    ],
    "layers": [
        "............", "............", "..aaaaaaaa..", "..AAAAAAAA..",
        "..aaaaaaaa..", "..AAAAAAAA..", "..aaaaaaaa..", "..AAAAAAAA..",
        "..aaaaaaaa..", "..AAAAAAAA..", "............", "............",
    ],
    "strand": [
        "............", ".aaaa..aaaa.", ".aaaa..aaaa.", ".aaaaaaaaaa.",
        "..aaaw.aaa..", "..a.w..a.a..", "..a..w.a.a..", ".a..w...a.a.",
        ".a.w..w..a..", "..a...w.a...", ".AAA.AAAAAA.", "............",
    ],
    "warp": [
        "............", "............", "a..........a", "aa........aa",
        ".aa......aa.", "..aaaaaaaa..", "............", "gggggggggggg",
        "dddddddddddd", "............", "............", "............",
    ],
    "drop": [
        ".....aa.....", ".....aa.....", "....aaaa....", "....aaaa....",
        "...aaaaaa...", "..aaaaaaaa..", "..aawaaaaa..", "..aawaaaaa..",
        "..aaaaaaaa..", "...aaaaaa...", "....aaaa....", "............",
    ],
    "shield": [
        ".aaaaaaaaaa.", ".aAAAAAAAAa.", ".aAaaaaaaAa.", ".aAaaaaaaAa.",
        ".aAaaaaaaAa.", "..aAaaaaAa..", "..aAaaaaAa..", "...aAaaAa...",
        "....aAAa....", ".....aa.....", "............", "............",
    ],
    "gear": [
        ".....aa.....", ".a..aaaa..a.", ".aaaaaaaaaa.", "..aaa..aaa..",
        "..aa....aa..", "aaaa....aaaa", "aaaa....aaaa", "..aa....aa..",
        "..aaa..aaa..", ".aaaaaaaaaa.", ".a..aaaa..a.", ".....aa.....",
    ],
    "wave": [
        "............", "............", ".aa.....aa..", "aaaa...aaaa.",
        "a..aa.aa..aa", "....aaa.....", "............", "............",
        "............", "............", "............", "............",
    ],
    "hard": [
        "............", ".gggggggggg.", ".gwwwwwwwwg.", ".gwggggggwg.",
        ".gwgddddgwg.", ".gwgddddgwg.", ".gwggggggwg.", ".gwwwwwwwwg.",
        ".gggggggggg.", "............", "............", "............",
    ],
}


def _detailed_spool():
    rows = []
    for y in range(28):
        row = []
        for x in range(28):
            dx, dy = x - 13.5, y - 13.5
            radius = math.hypot(dx, dy)
            if radius > 13.5:
                ch = "."
            elif radius > 12:
                ch = "k"
            elif radius > 10:
                ch = "w" if y < 5 and x % 4 in (1, 2) else "a"
            elif radius > 8.5:
                ch = "A"
            elif radius > 6:
                ch = "y" if (x + y) % 7 == 0 else "a"
            elif radius > 4.5:
                ch = "k"
            else:
                ch = "b" if x < 13 else "k"
            if 10 < radius <= 12 and y > 19 and (x + y) % 5 == 0:
                ch = "A"
            row.append(ch)
        rows.append("".join(row))
    return rows


ICONS["spool"] = _detailed_spool()

for _name, _rows in ICONS.items():
    assert _rows and len({len(r) for r in _rows}) == 1, _name


CUSTOM_SIZES = (12, 16, 24, 32)
MAX_CUSTOM = 2
BUILTIN = frozenset(ICONS)


def check_sprite(name, rows):
    """Return a list of problems with a custom sprite (empty when it is usable)."""
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]{2,15}", name) or name in BUILTIN:
        return ["sprite name must be new, lowercase letters/digits, 3-16 chars"]
    if not isinstance(rows, list) or len(rows) not in CUSTOM_SIZES or \
            not all(isinstance(r, str) and len(r) == len(rows) for r in rows):
        return ["sprite must be a square grid of 12, 16, 24 or 32 strings"]
    chars = {ch for r in rows for ch in r}
    if not chars <= set(CHARS) | {"a", "A", "."}:
        return ["sprite uses unknown characters"]
    filled = sum(ch != "." for r in rows for ch in r) / (len(rows) ** 2)
    if not 0.15 <= filled <= 0.9 or len(chars - {"."}) < 3:
        return ["sprite is too empty, too full or too flat"]
    return []


def register_custom(raw):
    """Draw (via GPT-5) and register custom sprites from {name: description}.
    Returns the names that could not be made so callers can fall back to built-in icons."""
    from . import art
    bad = set()
    items = list(raw.items()) if isinstance(raw, dict) else []
    for k, (name, desc) in enumerate(items):
        rows = art.draw(name, desc) if k < MAX_CUSTOM and isinstance(desc, str) else None
        if rows and not check_sprite(name, rows):
            ICONS[name] = rows
        else:
            bad.add(name)
    return bad
