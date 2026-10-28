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

MATERIALS = {
    "wood": {"dark": WOOD0, "mid": WOOD1, "light": WOOD2, "accent": AMBER, "shine": WOOD2},
    "metal": {"dark": STEEL0, "mid": STEEL1, "light": STEEL2, "accent": SHINE, "shine": WHITE},
}
