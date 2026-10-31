"""Fixed rules for the pixel-art short pipeline (see pixel_video_prompt.md)."""

W, H = 108, 192
SCALE = 10
OUT_W, OUT_H = W * SCALE, H * SCALE
FPS = 30
POSE_FPS = 12
SAMPLE_RATE = 48000

VOICE = "en-US-AndrewMultilingualNeural"
VOICE_RATE = "+20%"

LEAD_IN = 0.5
LINE_GAP = 0.2
MIN_DUR = 24.0
MAX_DUR = 26.8
END_TAIL_MIN = 1.8

HANDLE = "@STUDIORK3DPS"

# TikTok safe zones in canvas pixels (canvas is 1/10 of the output)
SAFE_TOP = 23          # y < 230
SAFE_BOTTOM = 153      # y > 1536
STRIP_X, STRIP_Y0, STRIP_Y1 = 90, 80, 150  # x > 900, y 800-1500

TARGET_LUFS = -14.0
TRUE_PEAK_LIMIT = -1.0

PALETTE = [
    (16, 14, 32),     # 0 bg
    (28, 26, 56),     # 1 bg2
    (46, 42, 84),     # 2 grid
    (240, 240, 250),  # 3 white
    (140, 140, 170),  # 4 grey
    (74, 72, 104),    # 5 dark grey
    (255, 140, 40),   # 6 orange
    (170, 80, 20),    # 7 orange dark
    (60, 200, 230),   # 8 cyan
    (30, 110, 150),   # 9 cyan dark
    (90, 220, 110),   # 10 green
    (240, 70, 80),    # 11 red
    (255, 226, 80),   # 12 yellow
    (255, 120, 200),  # 13 pink
    (130, 90, 220),   # 14 purple / pink dark
    (40, 130, 60),    # 15 green dark
]

FAMILIES = {
    "orange": (6, 7),
    "cyan": (8, 9),
    "green": (10, 15),
    "pink": (13, 14),
}
