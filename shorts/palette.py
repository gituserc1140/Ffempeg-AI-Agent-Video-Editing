"""The fixed 16-colour palette. Every pixel in every frame is one of these."""

NAVY = 0
NAVY2 = 1
CREAM = 2
WHITE = 3
WOOD0 = 4
WOOD1 = 5
WOOD2 = 6
AMBER = 7
STEEL0 = 8
STEEL1 = 9
STEEL2 = 10
SHINE = 11
RED = 12
GREEN = 13
YELLOW = 14
STAIN = 15

COLORS = [
    (18, 20, 44),
    (42, 48, 92),
    (247, 236, 204),
    (255, 255, 255),
    (84, 46, 26),
    (142, 86, 44),
    (198, 134, 70),
    (238, 170, 60),
    (58, 70, 94),
    (104, 122, 148),
    (164, 182, 204),
    (222, 234, 246),
    (214, 58, 64),
    (84, 196, 104),
    (255, 214, 72),
    (112, 50, 40),
]

FLAT = [channel for rgb in COLORS for channel in rgb] + [0] * (768 - 3 * len(COLORS))

# Same 16 slots. The TPU theme turns the wood slots orange and the right-hand
# field blue. Nozzle metal (STEEL0, STEEL2, SHINE) stays grey in both themes.
# GREEN and STAIN are the ABS dark and light slots in the TPU theme.
THEMES = {
    "wood-metal": [tuple(rgb) for rgb in COLORS],
    "tpu-abs": [
        (14, 8, 32),
        (46, 26, 78),
        (255, 236, 220),
        (255, 255, 255),
        (132, 40, 6),
        (214, 82, 14),
        (255, 146, 36),
        (255, 196, 70),
        (46, 50, 62),
        (18, 64, 168),
        (168, 176, 190),
        (214, 222, 232),
        (228, 42, 58),
        (8, 32, 112),
        (255, 214, 64),
        (110, 196, 255),
    ],
}
THEME = "wood-metal"

MATERIALS = {
    "wood": {"dark": WOOD0, "mid": WOOD1, "light": WOOD2, "accent": AMBER, "shine": WOOD2},
    "metal": {"dark": STEEL0, "mid": STEEL1, "light": STEEL2, "accent": SHINE, "shine": WHITE},
    "tpu": {"dark": WOOD0, "mid": WOOD1, "light": WOOD2, "accent": AMBER, "shine": AMBER},
    "abs": {"dark": GREEN, "mid": STEEL1, "light": STAIN, "accent": WHITE, "shine": WHITE},
}


def apply_theme(name: str) -> None:
    """Point the shared palette at a theme. Call once, before any frame is drawn."""
    global THEME
    if name not in THEMES:
        raise ValueError(f"unknown palette theme {name!r}")
    THEME = name
    COLORS[:] = THEMES[name]
    flat = [channel for rgb in COLORS for channel in rgb] + [0] * (768 - 3 * len(COLORS))
    FLAT[:] = flat
