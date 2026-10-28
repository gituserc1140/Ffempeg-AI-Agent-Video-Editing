"""One draw function and one event function per beat.

Draw functions get the canvas, the pose time `t` in seconds, and the Beat,
whose `cue(name)` returns the moment the matching word is spoken. Event
functions return the sound effects and screen shakes for the same cues.
"""

from __future__ import annotations

from . import palette as P
from . import sprites as S
from .audio import Sfx
from .pixel import Canvas, ease_in, ease_out, lerp, particles, pop_dy, poses_since, sparkle
from .timeline import Beat

L, R = 27, 81
ROW1, ROW2 = 49, 62
HEADER1, HEADER2 = 27, 36
BADGE_Y = 96
CARD_SLIDE = 0.25

Shake = tuple[float, int]


def clamp01(u: float) -> float:
    return max(0.0, min(1.0, u))


def pose_no(t: float) -> int:
    return int(round(t * 12))


def label(
    cv: Canvas,
    b: Beat,
    key: str,
    t: float,
    cx: int,
    y: int,
    cue: str | None = None,
    color: int = P.CREAM,
    plaque: int | None = P.NAVY,
    bounce: bool = True,
) -> bool:
    dy = pop_dy(t, b.cue(cue or key))
    if dy is None:
        return False
    cv.text(b.label(key), cx, y + (dy if bounce else 0), color=color, plaque=plaque)
    return True


def slam_x(t: float, t_hit: float, x_from: int, x_to: int, travel: float = 0.25) -> int | None:
    if t < t_hit - travel:
        return None
    if t < t_hit:
        return round(lerp(x_from, x_to, ease_in((t - (t_hit - travel)) / travel)))
    n = poses_since(t, t_hit)
    sign = 1 if x_to > x_from else -1
    return x_to + sign * ((2, -1)[n] if n < 2 else 0)


# Round card ---------------------------------------------------------------


def card_times(b: Beat) -> tuple[float, float]:
    land = b.start + CARD_SLIDE
    topic = b.cue("topic")
    first = min(b.cue(k) for k in b.cfg.get("cues", {}) if k != "topic")
    out = max(land + 0.3, min(topic + 0.6, first - CARD_SLIDE - 0.05))
    return land, out


def round_card(cv: Canvas, t: float, b: Beat) -> None:
    if "round" not in b.cfg:
        return
    land, out = card_times(b)
    topic_dy = pop_dy(t, b.cue("topic"))
    if t < land:
        off = int(round(-112 * (1 - ease_out((t - b.start) / CARD_SLIDE))))
    elif t < out:
        off = 0
    elif t < out + CARD_SLIDE:
        off = int(round(118 * ease_in((t - out) / CARD_SLIDE)))
    else:
        cv.text(f"ROUND {b.cfg['round']}", 54, HEADER1, color=P.YELLOW, kind="round")
        cv.text(b.cfg["topic"], 54, HEADER2, color=P.CREAM, kind="header")
        return
    kind = "card" if off == 0 else "moving"
    cv.box(off - 2, 50, off + 109, 82, fill=P.NAVY, outline=P.NAVY)
    cv.rect(off - 2, 51, off + 109, 51, fill=P.RED)
    cv.rect(off - 2, 81, off + 109, 81, fill=P.RED)
    cv.rect(off - 2, 52, off + 109, 52, fill=P.YELLOW)
    cv.text(f"ROUND {b.cfg['round']}", 54 + off, 55, color=P.YELLOW, scale=2, kind="round", clamp=False)
    if topic_dy is not None:
        cv.text(b.cfg["topic"], 54 + off, 71, color=P.CREAM, kind=kind, clamp=False)


def card_events(b: Beat) -> list[Sfx]:
    if "round" not in b.cfg:
        return []
    land, out = card_times(b)
    return [Sfx(b.start, "whoosh", 0.7), Sfx(land, "bell", 1.0), Sfx(out, "whoosh", 0.5)]


# Hook ---------------------------------------------------------------------


def hook(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    tw, tv, tm, twin = (b.cue(k) for k in ("left", "vs", "right", "wins"))
    left, right = b.cfg["left_name"], b.cfg["right_name"]
    left_mat, right_mat = b.cfg.get("left_mat", "wood"), b.cfg.get("right_mat", "metal")
    title_color = {"wood": P.AMBER, "tpu": P.AMBER, "metal": P.SHINE, "abs": P.WHITE}

    if t >= tw - 0.01:
        cv.box(6, 25, 101, 61, fill=P.NAVY, outline=P.NAVY2)
    for name, cue_t, y, color in (
        (left, tw, 30, title_color[left_mat]),
        ("VS", tv, 41, P.RED),
        (right, tm, 52, title_color[right_mat]),
    ):
        dy = pop_dy(t, cue_t)
        if dy is not None:
            cv.text(name, 54, y + max(dy, -1), color=color, kind="title")

    fast = t >= twin
    for cue_t, x_from, x_to, mat, seed in ((tw, -24, 25, left_mat, 1), (tm, 132, 83, right_mat, 2)):
        x = slam_x(t, cue_t, x_from, x_to)
        if x is None:
            continue
        bob = (pose % 2) if mat == "tpu" and fast else 0
        S.spool(cv, x, 98 + bob, mat, pose if fast else pose // 3, r=15)
        m = P.MATERIALS[mat]
        particles(cv, t, cue_t, x_to, 112, seed, (m["light"], m["accent"], P.CREAM), count=14, speed=45, life=0.5)

    if t >= tv:
        n = poses_since(t, tv)
        flash = n < 2 or (fast and (pose // 2) % 2 == 0)
        S.vs_badge(cv, 54, 98, big=True, flash=flash)
    if fast:
        for i, (sx, sy) in enumerate(((12, 80), (40, 116), (70, 78), (98, 114), (54, 76))):
            sparkle(cv, sx, sy, pose + i, P.WHITE if i % 2 else P.YELLOW)


def hook_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    tw, tv, tm, twin = (b.cue(k) for k in ("left", "vs", "right", "wins"))
    sfx = [
        Sfx(tw - 0.25, "whoosh", 0.8, -0.5),
        Sfx(tw, "impact", 1.0, -0.4),
        Sfx(tv, "impact", 0.6),
        Sfx(tv, "blip_hi", 0.8),
        Sfx(tm - 0.25, "whoosh", 0.8, 0.5),
        Sfx(tm, "impact", 1.0, 0.4),
        Sfx(tm, "clank", 0.8, 0.4),
        Sfx(twin, "ting", 0.9),
    ]
    return sfx, [(tw, 2), (tv, 1), (tm, 2)]


# Round 1: look ------------------------------------------------------------


def look(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    if (dy := pop_dy(t, b.cue("left"))) is not None:
        S.tile(cv, L, 92 + dy, "wood", t)
        if t >= b.cue("left_a"):
            for i, (gx, gy) in enumerate(((12, 78), (42, 82), (14, 106), (41, 104))):
                if (pose + i) % 2 == 0:
                    cv.pts([(gx, gy), (gx, gy - 1)], P.AMBER)
                    cv.px(gx, gy - 2, P.YELLOW)
    label(cv, b, "left_a", t, L, ROW1, color=P.AMBER)
    label(cv, b, "left_b", t, L, ROW2)

    if (dy := pop_dy(t, b.cue("right"))) is not None:
        shiny = t >= b.cue("right_a")
        S.tile(cv, R, 92 + dy, "metal", t - b.cue("right_a") if shiny else 9.0, shine=shiny)
        if shiny:
            sparkle(cv, R - 9, 83, pose, P.WHITE)
            sparkle(cv, R + 8, 100, pose + 2, P.WHITE)
        if t >= b.cue("right_b"):
            for i, (gx, gy) in enumerate(((66, 76), (97, 80), (68, 108), (96, 107))):
                sparkle(cv, gx, gy, pose + i, P.STEEL2, size=1)
    label(cv, b, "right_a", t, R, ROW1, color=P.SHINE)
    label(cv, b, "right_b", t, R, ROW2, color=P.STEEL2)


def look_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    sfx = [
        Sfx(b.cue("left"), "impact", 0.45, -0.4),
        Sfx(b.cue("left_a"), "blip", 0.8, -0.3),
        Sfx(b.cue("left_b"), "blip", 0.7, -0.3),
        Sfx(b.cue("right"), "clank", 0.9, 0.4),
        Sfx(b.cue("right_a"), "ting", 0.9, 0.4),
        Sfx(b.cue("right_b"), "blip_hi", 0.7, 0.3),
    ]
    return sfx, [(b.cue("left"), 1), (b.cue("right"), 1)]


# Round 2: printing --------------------------------------------------------

NOZZLE_TOP = 74
BED_Y = 121


def printing(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    t_wood, t_clog = b.cue("left"), b.cue("clog")
    clogged = t >= t_clog
    jitter = (1 if pose % 2 else -1) if 0 <= t - t_clog < 0.5 else 0
    layers = int(clamp01((min(t, t_clog) - t_wood) / 0.8) * 6) if t >= t_wood else 0
    feeding = t_wood <= t < t_clog
    S.print_bed(cv, L, BED_Y, "wood", layers)
    x, tip = S.nozzle(cv, L, NOZZLE_TOP, "wood", pose, feeding=feeding, jitter=jitter)
    if feeding:
        S.strand(cv, x, tip + 1, BED_Y - 1 - layers, "wood")
    if clogged:
        S.clog_blob(cv, x - 1, tip, pose)
        if (dy := pop_dy(t, t_clog)) is not None:
            S.burst(cv, L, 108 + dy, 13, pose)
            cv.text(b.label("clog"), L, 105 + dy, color=P.YELLOW)
        particles(cv, t, t_clog, L, tip + 3, 21, (P.WOOD0, P.WOOD2, P.RED), count=10, speed=35)

    t_metal, t_wear, t_fix = b.cue("right"), b.cue("wear"), b.cue("fix")
    hardened = t >= t_fix
    erosion = 0.0 if hardened else clamp01((t - t_wear) / 0.8)
    worn_out = erosion >= 1.0 and not hardened
    feeding = t >= t_metal and not worn_out
    layers = int(clamp01((t - t_metal) / 1.6) * 7) if t >= t_metal else 0
    S.print_bed(cv, R, BED_Y, "metal", layers)
    pop = pop_dy(t, t_fix) if hardened else 0
    x, tip = S.nozzle(cv, R, NOZZLE_TOP + (pop or 0), "metal", pose, erosion=erosion, hardened=hardened, feeding=feeding)
    if feeding:
        S.strand(cv, x, tip + 1, BED_Y - 1 - layers, "metal")
    if t_wear <= t < t_wear + 0.9 and not hardened:
        for k in range(4):
            particles(cv, t, t_wear + k * 0.2, x, tip, 30 + k, (P.AMBER, P.YELLOW, P.WHITE), count=6, speed=30, life=0.3)
    if hardened:
        if (dy := pop_dy(t, t_fix + 0.08)) is not None:
            S.check(cv, R + 15, 84 + dy)
        sparkle(cv, x - 6, tip - 2, pose, P.WHITE)
    label(cv, b, "wear", t, R, ROW1, color=P.AMBER)
    label(cv, b, "fix", t, R, ROW2, color=P.GREEN)


def printing_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    sfx = [
        Sfx(b.cue("left"), "blip", 0.7, -0.4),
        Sfx(b.cue("clog"), "impact", 1.0, -0.4),
        Sfx(b.cue("clog"), "blip", 0.8, -0.4),
        Sfx(b.cue("right"), "blip_hi", 0.6, 0.4),
        Sfx(b.cue("wear"), "grind", 0.8, 0.4),
        Sfx(b.cue("fix") - 0.12, "whoosh", 0.5, 0.4),
        Sfx(b.cue("fix"), "clank", 0.9, 0.4),
        Sfx(b.cue("fix") + 0.1, "ting", 0.8, 0.4),
    ]
    return sfx, [(b.cue("clog"), 2), (b.cue("fix"), 1)]


# Round 3: finishing -------------------------------------------------------

BLOCK_Y = 96
SAND_TIME = 1.0
POLISH_TIME = 1.0


def finishing(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    ts, tst = b.cue("sand"), b.cue("stain")
    rough = 1.0 - clamp01((t - ts) / SAND_TIME)
    stain = clamp01((t - tst) / 0.6) if t >= tst else 0.0
    S.wood_block(cv, L, BLOCK_Y, rough, stain)
    if ts <= t < ts + SAND_TIME:
        S.sandpaper(cv, L + (-5, 0, 5, 0)[pose % 4], BLOCK_Y - 10)
        for k in range(5):
            particles(cv, t, ts + k * 0.2, L, BLOCK_Y - 9, 50 + k, (P.CREAM, P.WOOD2), count=6, speed=22, life=0.4)
    if 0 < stain < 1:
        bx = L - 15 + int(stain * 30)
        cv.box(bx - 2, BLOCK_Y - 14, bx + 1, BLOCK_Y - 9, fill=P.STAIN)
        cv.rect(bx - 1, BLOCK_Y - 20, bx, BLOCK_Y - 15, fill=P.WOOD0)
    label(cv, b, "sand", t, L, ROW1, color=P.AMBER)
    label(cv, b, "stain", t, L, ROW2, color=P.CREAM)

    tp, tsh = b.cue("polish"), b.cue("shine")
    polish = 1.0 if t >= tsh else clamp01((t - tp) / POLISH_TIME) if t >= tp else 0.0
    S.metal_block(cv, R, BLOCK_Y, polish, t - tsh if t >= tsh else 0.0)
    if tp <= t < min(tp + POLISH_TIME, tsh + 0.2):
        ox, oy = ((-6, 0), (0, -2), (6, 0), (0, 1))[pose % 4]
        S.cloth(cv, R + ox, BLOCK_Y - 9 + oy)
    if t >= tsh:
        sparkle(cv, R - 12, BLOCK_Y - 7, pose, P.WHITE, size=3)
        sparkle(cv, R + 11, BLOCK_Y + 6, pose + 2, P.WHITE)
        sparkle(cv, R + 4, BLOCK_Y - 13, pose + 1, P.YELLOW, size=1)
    label(cv, b, "polish", t, R, ROW1, color=P.SHINE)
    label(cv, b, "shine", t, R, ROW2, color=P.YELLOW)


def finishing_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    sfx = [
        Sfx(b.cue("sand"), "rasp", 1.0, -0.4),
        Sfx(b.cue("stain"), "whoosh", 0.5, -0.4),
        Sfx(b.cue("stain"), "blip", 0.6, -0.3),
        Sfx(b.cue("polish"), "rasp", 0.45, 0.4),
        Sfx(b.cue("shine"), "ting", 1.0, 0.4),
        Sfx(b.cue("shine"), "blip_hi", 0.5, 0.3),
    ]
    return sfx, []


# Round 4: weight and uses -------------------------------------------------

PIVOT = (54, 116)
WOOD_X, METAL_X = 22, 86


def _tilt(t: float, t_heavy: float) -> int:
    if t < t_heavy:
        return -4
    n = poses_since(t, t_heavy)
    seq = (2, 9, 6, 8, 7)
    return seq[n] if n < len(seq) else 7


def weight(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    cx, cy = PIVOT
    t_heavy, t_light = b.cue("heavy"), b.cue("light")
    t_fall = min(b.cue("drop"), t_heavy - 0.3)
    tilt = _tilt(t, t_heavy)
    S.seesaw(cv, cx, cy, tilt)
    wood_bottom = S.plank_y(cx, cy, tilt, WOOD_X) - 3
    S.cube(cv, WOOD_X, wood_bottom, "wood")
    if t >= t_light:
        for i in range(2):
            if (pose + i) % 3:
                S.up_arrow(cv, WOOD_X - 4 + 8 * i, wood_bottom - 20 + ((pose + i) % 2))
    if t >= t_fall:
        land = S.plank_y(cx, cy, -4, METAL_X) - 3
        if t < t_heavy:
            bottom = round(lerp(44, land, ease_in((t - t_fall) / max(0.05, t_heavy - t_fall))))
        else:
            bottom = S.plank_y(cx, cy, tilt, METAL_X) - 3
        S.cube(cv, METAL_X, bottom, "metal", w=16, h=13)
        particles(cv, t, t_heavy, METAL_X, bottom, 61, (P.SHINE, P.STEEL2, P.WHITE), count=12, speed=40, life=0.4)
    label(cv, b, "heavy", t, R, ROW1, color=P.SHINE)
    label(cv, b, "light", t, L, ROW1, color=P.CREAM)

    if (dy := pop_dy(t, b.cue("left_use"))) is not None:
        S.sign(cv, 15, 82 + dy)
        S.vase(cv, 38, 86 + dy)
    if (dy := pop_dy(t, b.cue("right_use"))) is not None:
        S.knob(cv, 70, 81 + dy)
        S.trophy(cv, 93, 83 + dy)
        sparkle(cv, 101, 75, pose, P.WHITE)
    label(cv, b, "left_use", t, L, ROW2, color=P.AMBER)
    label(cv, b, "right_use", t, R, ROW2, color=P.YELLOW)


def weight_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    t_heavy = b.cue("heavy")
    t_fall = min(b.cue("drop"), t_heavy - 0.3)
    sfx = [
        Sfx(t_fall, "whoosh", 0.6, 0.4),
        Sfx(t_heavy, "impact", 1.0, 0.4),
        Sfx(t_heavy, "clank", 0.9, 0.4),
        Sfx(b.cue("light"), "blip_hi", 0.7, -0.4),
        Sfx(b.cue("left_use"), "blip", 0.8, -0.4),
        Sfx(b.cue("right_use"), "ting", 0.9, 0.4),
    ]
    return sfx, [(t_heavy, 2)]


# Verdict and end card -----------------------------------------------------


def verdict(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    t_follow = b.cue("follow")
    end_card = t >= t_follow
    t_dep = b.cue("depends")

    S.vs_badge(cv, 54, 100, big=True, flash=0 <= t - t_dep < 0.17)
    for side, cx, mat_key, q_cue, win_cue in (
        (L, 25, "left_mat", "left_q", "left"),
        (R, 83, "right_mat", "right_q", "right"),
    ):
        mat = b.cfg.get(mat_key, "wood" if side == L else "metal")
        if (dy := pop_dy(t, b.cue(q_cue))) is not None:
            S.spool(cv, cx, 101 + dy, mat, pose // 2, r=12)
        if (dy := pop_dy(t, b.cue(win_cue))) is not None:
            S.crown(cv, cx, 82 + dy)
            cv.text(b.cfg[f"{'left' if side == L else 'right'}_short"], cx, 117 + dy, color=P.YELLOW, plaque=P.NAVY)
            sparkle(cv, cx + 8, 84, pose, P.WHITE)

    if not end_card:
        if (dy := pop_dy(t, b.cue("it"))) is not None:
            cv.text(b.label("verdict1"), 54, 27 + max(dy, 0), color=P.YELLOW, scale=2)
        if (dy := pop_dy(t, t_dep)) is not None:
            cv.text(b.label("verdict2"), 54, 43 + max(dy, 0), color=P.YELLOW, scale=2)
        if t >= b.cue("left_q"):
            cv.box(4, 59, 50, 69, fill=P.NAVY)
            label(cv, b, "left_q", t, L, 61, plaque=None, color=P.AMBER, bounce=False)
        if t >= b.cue("right_q"):
            paired = "right_q2" in b.cfg.get("cues", {})
            cv.box(56, 59, 104, 78 if paired else 69, fill=P.NAVY)
            label(cv, b, "right_q", t, 80, 61, plaque=None, color=P.SHINE, bounce=False)
            if paired:
                label(cv, b, "right_q2", t, 80, 70, plaque=None, color=P.SHINE, bounce=False)
        return

    cv.box(3, 24, 104, 68, fill=P.NAVY, outline=P.NAVY2)
    cv.text(f"{b.label('verdict1')} {b.label('verdict2')}", 54, 27, color=P.YELLOW)
    label(cv, b, "follow1", t, 54, 38, cue="follow", plaque=None, bounce=False)
    label(cv, b, "follow2", t, 54, 48, cue="filament", plaque=None, bounce=False)
    if (dy := pop_dy(t, b.cue("battles"))) is not None:
        cv.text(b.cfg["handle"], 54, 58 + max(dy, 0), color=P.YELLOW, kind="handle")
        for i, (sx, sy) in enumerate(((9, 75), (16, 30), (98, 75), (92, 30))):
            sparkle(cv, sx, sy, pose + i, P.WHITE if i % 2 else P.YELLOW)


def verdict_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    sfx = [
        Sfx(b.cue("it"), "blip", 0.6),
        Sfx(b.cue("depends"), "impact", 1.0),
        Sfx(b.cue("depends"), "bell", 0.5),
        Sfx(b.cue("left_q"), "blip", 0.7, -0.4),
        Sfx(b.cue("left"), "ting", 0.8, -0.4),
        Sfx(b.cue("right_q"), "blip", 0.7, 0.4),
        *([Sfx(b.cue("right_q2"), "blip_hi", 0.6, 0.4)] if "right_q2" in b.cfg.get("cues", {}) else []),
        Sfx(b.cue("right"), "clank", 0.7, 0.4),
        Sfx(b.cue("right"), "ting", 0.6, 0.4),
        Sfx(b.cue("follow") - 0.1, "whoosh", 0.7),
        Sfx(b.cue("filament"), "blip", 0.6),
        Sfx(b.cue("battles"), "ting", 0.9),
    ]
    return sfx, [(b.cue("depends"), 2)]


# TPU vs ABS ---------------------------------------------------------------

BAR_Y = 78


def feel(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    if t >= b.cue("left"):
        bend = (6, 11, 8, 12)[pose % 4] if t >= b.cue("left_b") else 3
        S.flex_bar(cv, L, BAR_Y, bend)
    if t >= b.cue("right"):
        S.rigid_bar(cv, R, BAR_Y)
        if t >= b.cue("right_b"):
            sparkle(cv, R + 8, BAR_Y + 4, pose, P.WHITE, size=1)
    label(cv, b, "left_a", t, L, ROW1, color=P.YELLOW)
    label(cv, b, "left_b", t, L, ROW2, color=P.AMBER)
    label(cv, b, "right_a", t, R, ROW1, color=P.WHITE)
    label(cv, b, "right_b", t, R, ROW2, color=P.SHINE)


def feel_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("left"), "blip", 0.7, -0.4),
        Sfx(b.cue("left_a"), "blip_hi", 0.5, -0.3),
        Sfx(b.cue("left_b"), "whoosh", 0.7, -0.4),
        Sfx(b.cue("right"), "clank", 0.9, 0.4),
        Sfx(b.cue("right_a"), "impact", 0.45, 0.4),
        Sfx(b.cue("right_b"), "ting", 0.7, 0.3),
    ], [(b.cue("left_b"), 1), (b.cue("right"), 1)]


def habits(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    if t >= b.cue("left"):
        slipping = t >= b.cue("slip")
        stringing = t >= b.cue("string")
        jitter = (pose % 3 - 1) if slipping else 0
        layers = 5 if not slipping else 3
        S.print_bed(cv, L, BED_Y, "tpu", layers)
        x, tip = S.nozzle(cv, L, NOZZLE_TOP, "tpu", pose, feeding=not slipping, jitter=jitter)
        if stringing:
            S.ooze(cv, x, tip + 1, BED_Y - layers, pose)
        else:
            S.strand(cv, x, tip + 1, BED_Y - 1 - layers, "tpu")
    label(cv, b, "string", t, L, ROW1, color=P.YELLOW)
    label(cv, b, "slip", t, L, ROW2, color=P.AMBER)

    if t >= b.cue("right"):
        lift = 0
        if t >= b.cue("warp"):
            lift = 3 + (3 if t >= b.cue("lift") else 0)
        S.warp_part(cv, R, BED_Y, lift)
        feeding = t < b.cue("warp")
        x, tip = S.nozzle(cv, R, NOZZLE_TOP, "abs", pose, feeding=feeding)
        if feeding:
            S.strand(cv, x, tip + 1, BED_Y - 6, "abs")
        elif 0 <= t - b.cue("lift") < 0.45:
            particles(cv, t, b.cue("lift"), R - 8, BED_Y - 8, 71, (P.WHITE, P.CREAM, P.RED), count=8, speed=28, life=0.4)
    label(cv, b, "warp", t, R, ROW1, color=P.WHITE)
    label(cv, b, "lift", t, R, ROW2, color=P.SHINE)


def habits_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("left"), "blip", 0.6, -0.4),
        Sfx(b.cue("string"), "rasp", 0.5, -0.4),
        Sfx(b.cue("slip"), "whoosh", 0.6, -0.3),
        Sfx(b.cue("right"), "blip_hi", 0.6, 0.4),
        Sfx(b.cue("warp"), "impact", 0.7, 0.4),
        Sfx(b.cue("lift"), "whoosh", 0.7, 0.4),
    ], [(b.cue("slip"), 1), (b.cue("warp"), 2), (b.cue("lift"), 1)]


def surface(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    if t >= b.cue("grip"):
        S.grip_pad(cv, L, 98)
        if t < b.cue("right"):
            S.sandpaper(cv, L + (4 if pose % 2 else -4), 84)
            particles(cv, t, b.cue("grip"), L, 88, 81, (P.YELLOW, P.AMBER), count=6, speed=18, life=0.35)
    label(cv, b, "grip", t, L, ROW1, color=P.YELLOW)
    if t >= b.cue("right"):
        sanding = b.cue("sand") <= t < b.cue("smooth")
        smooth = 1.0 if t >= b.cue("smooth") else (0.55 if sanding else 0.0)
        rough = 0.0 if t >= b.cue("smooth") else (0.35 if sanding else 1.0)
        S.plastic_block(cv, R, 98, rough, smooth)
        if sanding:
            S.sandpaper(cv, R + ((-6, 0, 6, 0)[pose % 4]), 82)
        if t >= b.cue("smooth"):
            sparkle(cv, R - 10, 90, pose, P.WHITE)
            sparkle(cv, R + 9, 104, pose + 2, P.WHITE)
    label(cv, b, "sand", t, R, ROW1, color=P.WHITE)
    label(cv, b, "smooth", t, R, ROW2, color=P.SHINE)


def surface_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("grip"), "blip", 0.7, -0.4),
        Sfx(b.cue("left"), "blip_hi", 0.4, -0.3),
        Sfx(b.cue("right"), "clank", 0.5, 0.4),
        Sfx(b.cue("sand"), "rasp", 0.9, 0.4),
        Sfx(b.cue("smooth"), "ting", 0.9, 0.4),
    ], []


def uses(cv: Canvas, t: float, b: Beat) -> None:
    pose = pose_no(t)
    if (dy := pop_dy(t, b.cue("grip"))) is not None:
        S.grip_handle(cv, 14, 90 + dy)
    if (dy := pop_dy(t, b.cue("case"))) is not None:
        S.phone_case(cv, 36, 90 + dy)
    if (dy := pop_dy(t, b.cue("bracket"))) is not None:
        S.bracket(cv, 76, 92 + dy)
    if (dy := pop_dy(t, b.cue("shell"))) is not None:
        S.shell(cv, 99, 92 + dy)
        sparkle(cv, 104, 78, pose, P.WHITE, size=1)
    label(cv, b, "grip", t, L, ROW1, color=P.YELLOW)
    label(cv, b, "case", t, L, ROW2, color=P.AMBER)
    label(cv, b, "bracket", t, R, ROW1, color=P.WHITE)
    label(cv, b, "shell", t, R, ROW2, color=P.SHINE)


def uses_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("left"), "blip", 0.5, -0.4),
        Sfx(b.cue("grip"), "blip", 0.7, -0.4),
        Sfx(b.cue("case"), "blip_hi", 0.7, -0.3),
        Sfx(b.cue("right"), "clank", 0.5, 0.4),
        Sfx(b.cue("bracket"), "clank", 0.8, 0.4),
        Sfx(b.cue("shell"), "ting", 0.8, 0.3),
    ], [(b.cue("bracket"), 1)]


# Halloween pumpkin -------------------------------------------------------

PUMPKIN_X, PUMPKIN_BASE = 54, 121


def _rows_since(t: float, t0: float, full: int = 34, seconds: float = 1.2, start: int = 0) -> int:
    if t < t0:
        return start
    u = min(1.0, (t - t0) / seconds)
    return start + int(round((full - start) * u))


def _pumpkin_world(cv: Canvas, t: float, rows: int, eyes=False, grin=False, stem=False, glow=False, nozzle=False) -> int:
    pose = pose_no(t)
    S.night_bits(cv, pose)
    S.workshop_bed(cv)
    bob = pose % 2 if glow else 0
    S.jack_o_lantern(cv, PUMPKIN_X, PUMPKIN_BASE - bob, rows, eyes, grin, stem, glow, pose)
    if nozzle:
        S.printing_nozzle(cv, PUMPKIN_X, PUMPKIN_BASE, rows, pose)
    return pose


def pumpkin_hook(cv: Canvas, t: float, b: Beat) -> None:
    pose = _pumpkin_world(cv, t, 0, nozzle=True)
    if (dy := pop_dy(t, b.cue("pumpkin"))) is not None:
        cv.text(b.label("pumpkin"), 54, 32 + max(dy, -1), color=P.AMBER, scale=2, kind="title")
    if (dy := pop_dy(t, b.cue("halloween"))) is not None:
        cv.text(b.label("halloween"), 54, 52 + max(dy, 0), color=P.YELLOW, kind="title")
        sparkle(cv, 14, 48, pose, P.YELLOW, size=1)
        sparkle(cv, 94, 58, pose + 2, P.CREAM, size=1)


def pumpkin_hook_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [Sfx(b.cue("pumpkin"), "whoosh", 0.8), Sfx(b.cue("halloween"), "bell", 0.9)], []


def pumpkin_layers(cv: Canvas, t: float, b: Beat) -> None:
    rows = _rows_since(t, b.cue("orange"), full=34, seconds=1.4)
    pose = _pumpkin_world(cv, t, rows, nozzle=True)
    cv.text(b.label("topic"), 54, 28, color=P.YELLOW) if pop_dy(t, b.cue("topic")) is not None else None
    for key, color in (("bed", P.SHINE), ("stack", P.YELLOW), ("orange", P.AMBER)):
        if pop_dy(t, b.cue(key)) is not None:
            label(cv, b, key, t, 54, 40, color=color, bounce=False)
            break
    if rows and pose % 4 == 0:
        sparkle(cv, PUMPKIN_X, PUMPKIN_BASE - rows - 2, pose, P.AMBER, size=1)


def pumpkin_layers_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("topic"), "whoosh", 0.6),
        Sfx(b.cue("orange"), "blip", 0.6),
        Sfx(b.cue("stack"), "blip_hi", 0.7),
        Sfx(b.cue("bed"), "clank", 0.7),
    ], [(b.cue("bed"), 1)]


def pumpkin_face(cv: Canvas, t: float, b: Beat) -> None:
    eyes = t >= b.cue("eyes") - 0.01
    grin = t >= b.cue("grin") - 0.01
    pose = _pumpkin_world(cv, t, 34, eyes=eyes, grin=grin, nozzle=not grin or poses_since(t, b.cue("grin")) < 6)
    cv.text(b.label("topic"), 54, 28, color=P.YELLOW) if pop_dy(t, b.cue("topic")) is not None else None
    label(cv, b, "eyes", t, 28, 40, color=P.YELLOW, bounce=False)
    label(cv, b, "grin", t, 80, 40, color=P.AMBER, bounce=False)
    if grin:
        sparkle(cv, PUMPKIN_X, PUMPKIN_BASE - 8, pose, P.YELLOW, size=1)


def pumpkin_face_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("topic"), "blip", 0.5),
        Sfx(b.cue("eyes"), "blip_hi", 0.8),
        Sfx(b.cue("grin"), "ting", 0.8),
    ], [(b.cue("grin"), 1)]


def pumpkin_stem(cv: Canvas, t: float, b: Beat) -> None:
    stem = t >= b.cue("stem") - 0.01
    pose = _pumpkin_world(cv, t, 34, eyes=True, grin=True, stem=stem)
    cv.text(b.label("topic"), 54, 28, color=P.GREEN) if pop_dy(t, b.cue("topic")) is not None else None
    label(cv, b, "green", t, 30, 40, color=P.GREEN, bounce=False)
    label(cv, b, "pops", t, 78, 40, color=P.YELLOW, bounce=False)
    if stem:
        particles(cv, t, b.cue("pops"), PUMPKIN_X, PUMPKIN_BASE - 40, 7, (P.GREEN, P.STAIN, P.YELLOW), count=8, speed=28, life=0.4)


def pumpkin_stem_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("stem"), "blip", 0.6),
        Sfx(b.cue("green"), "blip_hi", 0.6),
        Sfx(b.cue("pops"), "impact", 0.9),
    ], [(b.cue("pops"), 1)]


def pumpkin_glow(cv: Canvas, t: float, b: Beat) -> None:
    glow = t >= b.cue("glows") - 0.01
    pose = _pumpkin_world(cv, t, 34, eyes=True, grin=True, stem=True, glow=glow)
    cv.text(b.label("topic"), 54, 28, color=P.YELLOW) if pop_dy(t, b.cue("topic")) is not None else None
    label(cv, b, "glows", t, 54, 40, color=P.AMBER, bounce=False)
    if glow:
        sparkle(cv, 34, 96, pose, P.YELLOW)
        sparkle(cv, 74, 100, pose + 1, P.CREAM)
        particles(cv, t, b.cue("glows"), PUMPKIN_X, PUMPKIN_BASE - 16, 9, (P.YELLOW, P.AMBER, P.WHITE), count=10, speed=22, life=0.45)


def pumpkin_glow_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [Sfx(b.cue("topic"), "blip", 0.5), Sfx(b.cue("glows"), "ting", 1.0)], [(b.cue("glows"), 1)]


def pumpkin_end(cv: Canvas, t: float, b: Beat) -> None:
    pose = _pumpkin_world(cv, t, 34, eyes=True, grin=True, stem=True, glow=True)
    if t >= b.cue("done") - 0.01:
        cv.box(6, 24, 101, 76, fill=P.NAVY, outline=P.NAVY2)
        cv.rect(6, 24, 101, 24, fill=P.AMBER)
    if (dy := pop_dy(t, b.cue("done"))) is not None:
        cv.text(b.label("done"), 54, 28 + max(dy, 0), color=P.YELLOW)
    if pop_dy(t, b.cue("follow")) is not None:
        cv.text(b.label("follow1"), 54, 40, color=P.CREAM)
        cv.text(b.cfg["handle"], 54, 64, color=P.YELLOW, kind="handle")
        sparkle(cv, 16, 34, pose, P.YELLOW, size=1)
        sparkle(cv, 92, 34, pose + 2, P.CREAM, size=1)
    if pop_dy(t, b.cue("spooky")) is not None:
        cv.text(b.label("follow2"), 54, 52, color=P.AMBER)


def pumpkin_end_events(b: Beat) -> tuple[list[Sfx], list[Shake]]:
    return [
        Sfx(b.cue("done"), "bell", 1.0),
        Sfx(b.cue("follow"), "whoosh", 0.6),
        Sfx(b.cue("spooky"), "ting", 0.8),
        Sfx(b.cue("prints"), "impact", 0.7),
    ], [(b.cue("prints"), 1)]


SCENES = {
    "hook": (hook, hook_events),
    "look": (look, look_events),
    "printing": (printing, printing_events),
    "finishing": (finishing, finishing_events),
    "weight": (weight, weight_events),
    "verdict": (verdict, verdict_events),
    "feel": (feel, feel_events),
    "habits": (habits, habits_events),
    "surface": (surface, surface_events),
    "uses": (uses, uses_events),
    "pumpkin_hook": (pumpkin_hook, pumpkin_hook_events),
    "pumpkin_layers": (pumpkin_layers, pumpkin_layers_events),
    "pumpkin_face": (pumpkin_face, pumpkin_face_events),
    "pumpkin_stem": (pumpkin_stem, pumpkin_stem_events),
    "pumpkin_glow": (pumpkin_glow, pumpkin_glow_events),
    "pumpkin_end": (pumpkin_end, pumpkin_end_events),
}

VERSUS_SCENES = set(SCENES) - {
    "pumpkin_hook",
    "pumpkin_layers",
    "pumpkin_face",
    "pumpkin_stem",
    "pumpkin_glow",
    "pumpkin_end",
}


def small_badge(cv: Canvas, b: Beat, t: float) -> None:
    if b.scene not in VERSUS_SCENES:
        return
    if b.scene == "hook" and t < b.cue("vs"):
        S.vs_badge(cv, 54, 98, big=False)
    elif b.scene not in ("hook", "verdict"):
        S.vs_badge(cv, 54, BADGE_Y, big=False)


def entered(b: Beat, t: float) -> bool:
    """False while the previous scene should stay on screen under this beat's intro."""
    if b.index == 0:
        return True
    if "round" in b.cfg:
        return t >= b.start + CARD_SLIDE
    if b.scene == "verdict":
        return t >= b.cue("it") - 0.05
    return True
