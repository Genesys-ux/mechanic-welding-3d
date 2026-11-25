"""
short_75s/story_beats.py — Master Storyboard, Narration Script, 30 Continuous Camera Moves,
6-Location Character Blocking & Dynamic Lighting Mood Progression (75 Seconds = 1,800 Frames).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


# ==============================================================================
# 1. EASING & OVERSHOOT MATH (Exponential Ease-In-Out & Smooth Decel Overshoot)
# ==============================================================================
def ease_in_out_expo(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t == 0.0 or t == 1.0:
        return t
    if t < 0.5:
        return 0.5 * (2.0 ** (20.0 * t - 10.0))
    return 1.0 - 0.5 * (2.0 ** (-20.0 * t + 10.0))


def ease_out_back(t: float, overshoot: float = 0.85) -> float:
    """Smooth deceleration with subtle cinematic overshoot (`overshoot` ~ 0.6..1.1)."""
    t = max(0.0, min(1.0, t))
    c3 = overshoot + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + overshoot * ((t - 1.0) ** 2)


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4.0 * t * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def apply_curve(t: float, mode: str) -> float:
    if mode == "expo":
        return ease_in_out_expo(t)
    if mode == "overshoot":
        return ease_out_back(t, overshoot=0.72)
    if mode == "whip":
        # Snappy speed-ramped whip curve (rapid middle sweep, smooth ends)
        return ease_in_out_expo(t)
    if mode == "linear":
        return max(0.0, min(1.0, t))
    return ease_in_out_cubic(t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp3(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


# ==============================================================================
# 2. FAST-PACED INDONESIAN NARRATION BEATS (EXACT SYNC TO 75.0s = 1,800 FRAMES)
# ==============================================================================
NARRATION_BEATS: List[Dict[str, Any]] = [
    # 2-SECOND OPENING HOOK (0.0s - 2.0s)
    {
        "id": "HOOK",
        "start_f": 1, "end_f": 48,
        "location": "LOC6_FenderMacro",
        "text": "Mobil tua ini hampir masuk rongsokan, sampai satu percikan api mengubah segalanya!",
        "caption": "HAMPIR JADI RONGSOKAN... SAMPAI SATU PERCIKAN API!",
    },
    # ACT 1: GOLDEN AFTERNOON & BROKEN CLASSIC (2.0s - 14.0s)
    {
        "id": "ACT1_A",
        "start_f": 50, "end_f": 168,
        "location": "LOC1_CourtyardGate",
        "text": "Sore itu matahari mulai rendah. Di bengkel tua ujung jalan, masuk sedan merah klasik peninggalan kakek.",
        "caption": "SORE HARI DI BENGKEL TUA — SEDAN MERAH KLASIK",
    },
    {
        "id": "ACT1_B",
        "start_f": 170, "end_f": 336,
        "location": "LOC2_ServiceBay",
        "text": "Fender kirinya robek parah, karat di mana-mana. Bengkel lain sudah menyerah, tapi mekanik muda ini justru tersenyum.",
        "caption": "FENDER ROBEK & KARAT — BENGKEL LAIN MENYERAH!",
    },
    # ACT 2: PARTS, WORKBENCH & WELDER PREP (14.0s - 29.0s)
    {
        "id": "ACT2_A",
        "start_f": 338, "end_f": 440,
        "location": "LOC5_PartsAlcove",
        "text": "Ia langsung melangkah ke rak suku cadang belakang, memilih plat baja baru yang pas untuk tambalan.",
        "caption": "PILIH PLAT BAJA BARU DI RAK SUKU CADANG",
    },
    {
        "id": "ACT2_B",
        "start_f": 442, "end_f": 544,
        "location": "LOC3_MasterWorkbench",
        "text": "Dari meja kerja dan papan perkakas, kunci pas krom dan ragum besi disiapkan dengan cekatan.",
        "caption": "SIAPKAN PERKAKAS KROM DI MEJA KERJA",
    },
    {
        "id": "ACT2_C",
        "start_f": 546, "end_f": 696,
        "location": "LOC4_WeldingStation",
        "text": "Lalu katup gas argon dibuka, jarum tekanan naik stabil, dan mesin las MIG merah menyala penuh tenaga!",
        "caption": "GAS ARGON DIBUKA — MESIN LAS MIG MENYALA!",
    },
    # ACT 3: JACK STANDS, GROUND CLAMP & BLUE SHADE TURN (29.0s - 43.0s)
    {
        "id": "ACT3_A",
        "start_f": 698, "end_f": 860,
        "location": "LOC2_ServiceBay",
        "text": "Mobil ditopang kokoh di atas dongkrak oranye tanpa celah, dan klem ground dijepit rapat ke sasis logam.",
        "caption": "DONGKRAK PRESISI & KLEM GROUND DIJEPIT RAPAT",
    },
    {
        "id": "ACT3_B",
        "start_f": 862, "end_f": 1032,
        "location": "LOC6_FenderMacro",
        "text": "Cahaya sore berubah dingin kebiruan. Kacamata las kuningan diturunkan—fokus penuh ke titik sambungan!",
        "caption": "CAHAYA BERUBAH BIRU — KACAMATA LAS TURUN!",
    },
    # ACT 4: HIGH-ENERGY WELDING CLIMAX (43.0s - 60.0s)
    {
        "id": "ACT4_A",
        "start_f": 1034, "end_f": 1232,
        "location": "LOC6_FenderMacro",
        "text": "ZAP! Busur listrik menyala menyilaukan! Ujung nozzle menempel presisi, menyusuri setiap milimeter garis las!",
        "caption": "ZAP! BUSUR LISTRIK & PERCIKAN API MEMBARA!",
    },
    {
        "id": "ACT4_B",
        "start_f": 1234, "end_f": 1440,
        "location": "LOC2_ServiceBay",
        "text": "Percikan api emas memantul di lantai beton, sementara panas membara menyatukan kembali plat baja dengan bodi merah!",
        "caption": "PERCIKAN EMAS MEMANTUL — BAJA MENYATU SEMPURNA!",
    },
    # ACT 5: COOLING EMBER & GOLDEN SUNSET PAYOFF (60.0s - 75.0s)
    {
        "id": "ACT5_A",
        "start_f": 1442, "end_f": 1584,
        "location": "LOC6_FenderMacro",
        "text": "Api padam, bara oranye perlahan mendingin—hasil las rata sempurna! Kacamata dinaikkan dengan senyum puas.",
        "caption": "HASIL LAS RATA SEMPURNA! SENYUM PUAS!",
    },
    {
        "id": "ACT5_B",
        "start_f": 1586, "end_f": 1796,
        "location": "LOC1_CourtyardGate",
        "text": "Di bawah sinar senja keemasan, sedan klasik ini siap kembali mengaspal! Subscribe untuk kisah restorasi selanjutnya!",
        "caption": "SANG LEGENDA SIAP MENGASPAL! SUBSCRIBE!",
    },
]


# ==============================================================================
# 3. 30 CONTINUOUS 3D CAMERA MOVES (CM01 .. CM30)
# Each entry defines the destination keyframe of a camera move segment:
#   (move_id, start_f, end_f, cam_pos, target_pos, lens_mm, roll_deg, ease_mode, blur_shutter)
# Continuous virtual camera interpolates smoothly from move[i-1] -> move[i] with
# exponential ease-in-out, overshoot deceleration, snappy zoom transitions & motion blur!
# ==============================================================================
CAMERA_MOVES: List[Dict[str, Any]] = [
    # --- ACT 0: 2-SECOND HOOK (Frames 1..48) ---
    {"id": "CM01", "f0": 1,    "f1": 20,   "pos": (-1.35, -1.25, 0.92), "tgt": (-0.25, -0.45, 0.78), "lens": 52.0, "roll":  3.5, "ease": "expo",      "blur": 0.15},
    {"id": "CM02", "f0": 20,   "f1": 48,   "pos": (-7.40, -3.60, 1.45), "tgt": (-1.20, -0.60, 0.95), "lens": 18.0, "roll": -4.0, "ease": "whip",      "blur": 0.55},

    # --- ACT 1: LOC 1 COURTYARD GATE -> LOC 2 SERVICE BAY (Frames 49..336) ---
    {"id": "CM03", "f0": 48,   "f1": 110,  "pos": (-5.80, -2.80, 1.18), "tgt": (-2.40, -1.20, 0.92), "lens": 20.0, "roll": -1.5, "ease": "cubic",     "blur": 0.18},
    {"id": "CM04", "f0": 110,  "f1": 168,  "pos": (-3.65, -2.05, 1.12), "tgt": (-1.15, -0.85, 0.95), "lens": 28.0, "roll":  1.0, "ease": "overshoot", "blur": 0.20},
    {"id": "CM05", "f0": 168,  "f1": 228,  "pos": (-2.45, -1.55, 1.06), "tgt": (-0.25, -0.50, 0.85), "lens": 26.0, "roll":  0.5, "ease": "cubic",     "blur": 0.12},
    {"id": "CM06", "f0": 228,  "f1": 276,  "pos": (-1.55, -1.25, 0.86), "tgt": (-0.26, -0.42, 0.74), "lens": 56.0, "roll":  2.0, "ease": "expo",      "blur": 0.30},
    {"id": "CM07", "f0": 276,  "f1": 336,  "pos": (-1.95, -1.55, 1.14), "tgt": (-0.30, -0.82, 1.08), "lens": 38.0, "roll":  0.0, "ease": "overshoot", "blur": 0.14},

    # --- ACT 2: LOC 5 PARTS ALCOVE -> LOC 3 WORKBENCH -> LOC 4 WELDER (Frames 337..696) ---
    {"id": "CM08", "f0": 336,  "f1": 385,  "pos": (-2.10,  1.25, 1.38), "tgt": (-1.05,  3.10, 1.10), "lens": 21.0, "roll": -3.0, "ease": "whip",      "blur": 0.55},
    {"id": "CM09", "f0": 385,  "f1": 440,  "pos": (-1.65,  1.95, 1.18), "tgt": (-0.95,  3.20, 1.05), "lens": 46.0, "roll":  1.2, "ease": "overshoot", "blur": 0.18},
    {"id": "CM10", "f0": 440,  "f1": 496,  "pos": ( 0.85, -0.40, 1.24), "tgt": ( 2.55, -0.65, 1.12), "lens": 22.0, "roll": -2.5, "ease": "whip",      "blur": 0.48},
    {"id": "CM11", "f0": 496,  "f1": 544,  "pos": ( 1.20, -1.20, 1.18), "tgt": ( 2.75, -0.80, 1.15), "lens": 48.0, "roll":  1.5, "ease": "expo",      "blur": 0.25},
    {"id": "CM12", "f0": 544,  "f1": 600,  "pos": (-0.45, -2.65, 1.08), "tgt": ( 0.90, -1.35, 0.88), "lens": 24.0, "roll": -2.0, "ease": "whip",      "blur": 0.45},
    {"id": "CM13", "f0": 600,  "f1": 648,  "pos": (-0.10, -2.15, 0.96), "tgt": ( 0.92, -1.32, 0.86), "lens": 58.0, "roll":  1.0, "ease": "overshoot", "blur": 0.22},
    {"id": "CM14", "f0": 648,  "f1": 696,  "pos": (-1.70, -2.25, 0.82), "tgt": ( 0.10, -0.85, 0.65), "lens": 24.0, "roll": -1.5, "ease": "expo",      "blur": 0.30},

    # --- ACT 3: LOC 2 JACK STANDS -> GROUND CLAMP -> TWILIGHT BLUE TURN (Frames 697..1032) ---
    {"id": "CM15", "f0": 696,  "f1": 752,  "pos": (-1.65, -1.45, 0.34), "tgt": ( 0.08, -0.28, 0.26), "lens": 24.0, "roll":  0.5, "ease": "cubic",     "blur": 0.16},
    {"id": "CM16", "f0": 752,  "f1": 804,  "pos": (-1.05, -1.12, 0.30), "tgt": ( 0.10, -0.26, 0.25), "lens": 56.0, "roll":  1.5, "ease": "overshoot", "blur": 0.24},
    {"id": "CM17", "f0": 804,  "f1": 860,  "pos": (-0.85, -1.18, 0.42), "tgt": ( 0.05, -0.37, 0.35), "lens": 48.0, "roll": -2.0, "ease": "whip",      "blur": 0.42},
    {"id": "CM18", "f0": 860,  "f1": 920,  "pos": (-2.15, -1.35, 1.15), "tgt": (-0.24, -0.78, 0.96), "lens": 28.0, "roll":  1.0, "ease": "cubic",     "blur": 0.15},
    {"id": "CM19", "f0": 920,  "f1": 980,  "pos": (-1.85, -1.15, 1.16), "tgt": (-0.28, -0.78, 1.10), "lens": 54.0, "roll":  2.0, "ease": "overshoot", "blur": 0.22},
    {"id": "CM20", "f0": 980,  "f1": 1032, "pos": (-1.55, -1.08, 0.92), "tgt": (-0.36, -0.45, 0.74), "lens": 64.0, "roll":  2.5, "ease": "expo",      "blur": 0.12},

    # --- ACT 4: HIGH-ENERGY WELDING CLIMAX (Frames 1033..1440) ---
    {"id": "CM21", "f0": 1032, "f1": 1092, "pos": (-2.05, -1.25, 1.00), "tgt": (-0.28, -0.58, 0.86), "lens": 40.0, "roll": -2.5, "ease": "expo",      "blur": 0.32},
    {"id": "CM22", "f0": 1092, "f1": 1168, "pos": (-1.75, -1.68, 1.05), "tgt": (-0.22, -0.58, 0.86), "lens": 38.0, "roll":  2.0, "ease": "cubic",     "blur": 0.18},
    {"id": "CM23", "f0": 1168, "f1": 1232, "pos": (-1.30, -1.18, 0.85), "tgt": (-0.22, -0.42, 0.75), "lens": 64.0, "roll":  3.0, "ease": "overshoot", "blur": 0.28},
    {"id": "CM24", "f0": 1232, "f1": 1304, "pos": (-2.15, -1.45, 0.42), "tgt": (-0.18, -0.55, 0.58), "lens": 24.0, "roll": -3.5, "ease": "whip",      "blur": 0.45},
    {"id": "CM25", "f0": 1304, "f1": 1376, "pos": (-1.85, -1.85, 1.78), "tgt": (-0.15, -0.55, 0.82), "lens": 26.0, "roll":  4.0, "ease": "cubic",     "blur": 0.20},
    {"id": "CM26", "f0": 1376, "f1": 1440, "pos": (-1.68, -1.22, 0.94), "tgt": (-0.14, -0.48, 0.78), "lens": 52.0, "roll":  1.0, "ease": "overshoot", "blur": 0.22},

    # --- ACT 5: COOLING EMBER & GOLDEN SUNSET PAYOFF (Frames 1441..1800) ---
    {"id": "CM27", "f0": 1440, "f1": 1508, "pos": (-1.32, -1.15, 0.86), "tgt": (-0.22, -0.42, 0.75), "lens": 58.0, "roll":  0.5, "ease": "expo",      "blur": 0.12},
    {"id": "CM28", "f0": 1508, "f1": 1584, "pos": (-2.28, -1.52, 1.12), "tgt": (-0.20, -0.74, 0.98), "lens": 34.0, "roll": -1.0, "ease": "overshoot", "blur": 0.28},
    {"id": "CM29", "f0": 1584, "f1": 1680, "pos": (-2.85, -2.05, 1.08), "tgt": (-0.10, -0.55, 0.88), "lens": 26.0, "roll":  1.2, "ease": "cubic",     "blur": 0.14},
    {"id": "CM30", "f0": 1680, "f1": 1800, "pos": (-6.60, -3.45, 1.48), "tgt": (-0.50, -0.50, 0.92), "lens": 19.0, "roll":  0.0, "ease": "expo",      "blur": 0.25},
]

# Initial camera state at Frame 1 (before CM01 snaps in)
CAM_INITIAL: Dict[str, Any] = {
    "pos": (-2.10, -1.50, 1.04),
    "tgt": (-0.25, -0.50, 0.82),
    "lens": 24.0,
    "roll": 0.0,
}


def eval_camera_state(frame: int) -> Dict[str, Any]:
    """Evaluate continuous 3D camera `(pos, tgt, lens, roll_deg, blur, move_id)` at `frame`."""
    f = max(1, min(1800, frame))
    prev_pos = CAM_INITIAL["pos"]
    prev_tgt = CAM_INITIAL["tgt"]
    prev_lens = CAM_INITIAL["lens"]
    prev_roll = CAM_INITIAL["roll"]

    for mv in CAMERA_MOVES:
        f0, f1 = mv["f0"], mv["f1"]
        if f <= f1:
            t_raw = (f - f0) / max(1.0, float(f1 - f0))
            t = apply_curve(t_raw, mv["ease"])
            # For overshoot, clamp lens cleanly so focal length never goes negative
            lens_val = max(16.0, lerp(prev_lens, mv["lens"], t))
            return {
                "pos": lerp3(prev_pos, mv["pos"], t),
                "tgt": lerp3(prev_tgt, mv["tgt"], t),
                "lens": lens_val,
                "roll_deg": lerp(prev_roll, mv["roll"], t),
                "blur": mv["blur"] * math.sin(math.pi * max(0.0, min(1.0, t_raw))),
                "move_id": mv["id"],
            }
        prev_pos = mv["pos"]
        prev_tgt = mv["tgt"]
        prev_lens = mv["lens"]
        prev_roll = mv["roll"]

    last = CAMERA_MOVES[-1]
    return {
        "pos": last["pos"],
        "tgt": last["tgt"],
        "lens": last["lens"],
        "roll_deg": last["roll"],
        "blur": 0.0,
        "move_id": last["id"],
    }


# ==============================================================================
# 4. NATURAL CHARACTER BLOCKING ACROSS ALL 6 LOCATIONS (1,800 FRAMES)
# (frame, (x, y, z), yaw_deg, action_tag)
# ==============================================================================
CHAR_BLOCKING_KEYS: List[Tuple[int, Tuple[float, float, float], float, str]] = [
    # HOOK (1..46): Welding intensely at the front-left fender!
    (1,    (-0.24, -0.790, 0.0),  28.0, "hook_weld"),
    (44,   (-0.18, -0.785, 0.0),  26.0, "hook_weld"),
    # ACT 1 (48..336): Walks in from sunlit courtyard gate (LOC 1) to car fender (LOC 2)!
    (49,   (-4.60, -1.650, 0.0), -82.0, "walk"),
    (135,  (-2.55, -1.250, 0.0), -72.0, "walk"),
    (210,  (-0.65, -0.920, 0.0),  24.0, "walk"),
    (245,  (-0.32, -0.820, 0.0),  34.0, "inspect_fender"),
    (335,  (-0.32, -0.820, 0.0),  44.0, "inspect_fender"),
    # ACT 2A (336..440): Walks to Spare-Parts Alcove (LOC 5) & grabs steel repair plate
    (365,  (-1.05,  2.450, 0.0),   5.0, "walk"),
    (405,  (-1.00,  2.650, 0.0),  10.0, "grab_plate"),
    (440,  (-0.95,  2.550, 0.0), -45.0, "grab_plate"),
    # ACT 2B (441..544): Walks to Master Workbench (LOC 3) & picks up chrome wrench
    (480,  ( 1.95, -0.720, 0.0), -85.0, "walk"),
    (515,  ( 2.10, -0.720, 0.0), -90.0, "workbench_prep"),
    (544,  ( 2.05, -0.820, 0.0), -125.0, "workbench_prep"),
    # ACT 2C (545..696): Walks to Welding Station (LOC 4), opens Argon valve & turns on MIG
    (585,  ( 0.35, -1.550, 0.0), -42.0, "walk"),
    (625,  ( 0.42, -1.480, 0.0), -35.0, "welder_prep"),
    (660,  ( 0.32, -1.350, 0.0),  15.0, "walk"),
    # ACT 3 (697..1032): Checks jack stands, clips ground clamp, pulls goggles down!
    (730,  (-0.18, -0.920, 0.0),  28.0, "check_jack"),
    (815,  ( 0.02, -0.880, 0.0),  24.0, "clip_clamp"),
    (890,  (-0.30, -0.800, 0.0),  38.0, "goggles_prep"),
    (965,  (-0.33, -0.805, 0.0),  34.0, "goggles_pull"),
    (1032, (-0.34, -0.805, 0.0),  30.0, "weld_ready"),
    # ACT 4 (1033..1440): High-energy welding pass along red car fender seam!
    (1033, (-0.34, -0.805, 0.0),  30.0, "welding"),
    (1235, (-0.20, -0.788, 0.0),  26.0, "welding"),
    (1435, (-0.06, -0.772, 0.0),  22.0, "welding"),
    # ACT 5 (1441..1800): Cooling ember admiration, pushes goggles up, proud golden-sunset smile!
    (1505, (-0.12, -0.785, 0.0),  36.0, "admire_seam"),
    (1560, (-0.18, -0.790, 0.0),  54.0, "goggles_push"),
    (1640, (-0.20, -0.795, 0.0),  58.0, "hero_payoff"),
    (1800, (-0.22, -0.800, 0.0),  56.0, "hero_payoff"),
]


def eval_character_blocking(frame: int) -> Tuple[Tuple[float, float, float], float, str]:
    """Return `(world_pos, yaw_deg, action_tag)` with smooth natural ease-in-out between keys."""
    f = max(1, min(1800, frame))
    for i in range(len(CHAR_BLOCKING_KEYS) - 1):
        f0, p0, y0, act0 = CHAR_BLOCKING_KEYS[i]
        f1, p1, y1, act1 = CHAR_BLOCKING_KEYS[i + 1]
        if f0 <= f <= f1:
            # Instant cut between Hook (44) and Story Start (49)
            if f0 == 44 and f1 == 49:
                return (p0, y0, act0) if f <= 47 else (p1, y1, act1)
            t = ease_in_out_cubic((f - f0) / max(1.0, float(f1 - f0)))
            pos = lerp3(p0, p1, t)
            # Shortest angular interpolation
            dy = ((y1 - y0 + 180.0) % 360.0) - 180.0
            yaw = y0 + dy * t
            return pos, yaw, act0 if t < 0.75 else act1
    _, pos, yaw, act = CHAR_BLOCKING_KEYS[-1]
    return pos, yaw, act


# ==============================================================================
# 5. DYNAMIC LIGHTING MOOD PROGRESSION (LOW SUN, LONG SHADOW, BLUE SHADE, GOD RAYS)
# Shifts dramatically as the story turns!
# ==============================================================================
LIGHTING_MOOD_KEYS: List[Dict[str, Any]] = [
    # Hook: High-contrast blue shade + arc flash
    {"f": 1,    "sun_e": 0.8, "sun_elev":  6.0, "sun_col": "#8AB8FF", "blue_e": 34.0, "ray_alpha": 0.14, "ray_col": "#5EB2FF", "haze": 0.018},
    {"f": 46,   "sun_e": 0.8, "sun_elev":  6.0, "sun_col": "#8AB8FF", "blue_e": 34.0, "ray_alpha": 0.14, "ray_col": "#5EB2FF", "haze": 0.018},
    # Act 1: Low Golden Afternoon Sun, Long Shadows, Warm God Rays + Cool Blue Shade
    {"f": 50,   "sun_e": 7.5, "sun_elev": 12.5, "sun_col": "#FFB463", "blue_e": 24.0, "ray_alpha": 0.34, "ray_col": "#FFD28E", "haze": 0.014},
    {"f": 336,  "sun_e": 6.8, "sun_elev": 10.5, "sun_col": "#FFA552", "blue_e": 26.0, "ray_alpha": 0.32, "ray_col": "#FFC778", "haze": 0.015},
    # Act 2: Late Afternoon Dipping Lower (Longer Shadows)
    {"f": 696,  "sun_e": 5.2, "sun_elev":  8.0, "sun_col": "#FF8F40", "blue_e": 30.0, "ray_alpha": 0.28, "ray_col": "#FFB062", "haze": 0.016},
    # Act 3: STORY TURN — Twilight Blue Shade takes over as goggles drop!
    {"f": 880,  "sun_e": 1.6, "sun_elev":  4.0, "sun_col": "#6E9EE8", "blue_e": 42.0, "ray_alpha": 0.20, "ray_col": "#5EA6FF", "haze": 0.020},
    {"f": 1032, "sun_e": 0.7, "sun_elev":  3.0, "sun_col": "#4C82D8", "blue_e": 46.0, "ray_alpha": 0.16, "ray_col": "#4898FF", "haze": 0.022},
    # Act 4: Welding Climax — Deep Blue Shade + Electric Cyan Arc + Haze
    {"f": 1435, "sun_e": 0.7, "sun_elev":  3.0, "sun_col": "#4C82D8", "blue_e": 44.0, "ray_alpha": 0.18, "ray_col": "#4CAEFF", "haze": 0.022},
    # Act 5: STORY PAYOFF — Epic Golden Sunset God Rays break back through!
    {"f": 1540, "sun_e": 6.5, "sun_elev":  9.5, "sun_col": "#FFA048", "blue_e": 28.0, "ray_alpha": 0.36, "ray_col": "#FFC470", "haze": 0.016},
    {"f": 1800, "sun_e": 8.2, "sun_elev":  8.5, "sun_col": "#FF983E", "blue_e": 24.0, "ray_alpha": 0.40, "ray_col": "#FFBE66", "haze": 0.015},
]
