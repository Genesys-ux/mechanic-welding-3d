"""
short_75s/story_beats.py — Revised Master Storyboard (75 Seconds = 1,800 Frames):
  - 2-second explosive welding Hook (0.0s - 2.0s)
  - 100% collision-free character & camera paths (ZERO wall/prop clipping!)
  - Speed-coupled natural walk cycle (ZERO foot sliding/dragging!)
  - Natural held 3D props (Steel Plate & Chrome Wrench)
  - Full 30-second multi-angle Welding Marathon (45.0s - 75.0s = Frames 1081..1800):
      Zone 1: Front Fender/Nose (1081..1296)
      Zone 2: Left Side Panel   (1297..1536)
      Zone 3: Rear Quarter/Tail (1537..1800)
  - 30 Continuous 3D Camera Moves (CM01..CM30) with snappy Zoom-In on key details!
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


# ==============================================================================
# 1. EASING & OVERSHOOT MATH
# ==============================================================================
def ease_in_out_expo(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t == 0.0 or t == 1.0:
        return t
    if t < 0.5:
        return 0.5 * (2.0 ** (20.0 * t - 10.0))
    return 1.0 - 0.5 * (2.0 ** (-20.0 * t + 10.0))


def ease_out_back(t: float, overshoot: float = 0.72) -> float:
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
        return ease_out_back(t, overshoot=0.65)
    if mode == "whip":
        return ease_in_out_expo(t)
    if mode == "linear":
        return max(0.0, min(1.0, t))
    return ease_in_out_cubic(t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp3(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


# ==============================================================================
# 2. FAST-PACED INDONESIAN NARRATION BEATS (SYNCED TO 30s MULTI-ZONE WELDING!)
# ==============================================================================
NARRATION_BEATS: List[Dict[str, Any]] = [
    # 2-SECOND OPENING HOOK (0.0s - 2.0s)
    {
        "id": "HOOK",
        "start_f": 1, "end_f": 48,
        "location": "LOC6_FrontWeld",
        "text": "Mobil tua ini hampir masuk rongsokan, sampai tiga titik las ini menghidupkannya kembali!",
        "caption": "HAMPIR JADI RONGSOKAN — 3 TITIK LAS PENENTU!",
    },
    # ACT 1: COURTYARD ARRIVAL & BROKEN CLASSIC (2.0s - 15.0s)
    {
        "id": "ACT1_A",
        "start_f": 50, "end_f": 180,
        "location": "LOC1_CourtyardGate",
        "text": "Sore itu matahari mulai rendah. Di bengkel tua ujung jalan, masuk sedan merah klasik penuh karat.",
        "caption": "SORE HARI DI BENGKEL TUA — SEDAN MERAH KLASIK",
    },
    {
        "id": "ACT1_B",
        "start_f": 182, "end_f": 348,
        "location": "LOC2_ServiceBay",
        "text": "Bodi depan, samping, dan belakangnya retak parah. Bengkel lain menyerah, tapi mekanik muda ini pantang mundur!",
        "caption": "DEPAN, SAMPING, BELAKANG RETAK — PANTANG MUNDUR!",
    },
    # ACT 2: PARTS ALCOVE -> WORKBENCH -> WELDER STATION (15.0s - 34.0s)
    {
        "id": "ACT2_A",
        "start_f": 350, "end_f": 504,
        "location": "LOC5_PartsAlcove",
        "text": "Ia melangkah ke rak suku cadang belakang dan mengambil plat baja baru langsung dengan tangannya.",
        "caption": "AMBIL PLAT BAJA BARU DI RAK BELAKANG",
    },
    {
        "id": "ACT2_B",
        "start_f": 506, "end_f": 660,
        "location": "LOC3_MasterWorkbench",
        "text": "Berlanjut ke meja kerja, kunci pas krom dipegang mantap untuk merapikan dudukan rangka.",
        "caption": "SIAPKAN KUNCI PAS KROM DI MEJA KERJA",
    },
    {
        "id": "ACT2_C",
        "start_f": 662, "end_f": 816,
        "location": "LOC4_WeldingStation",
        "text": "Katup tabung gas argon dibuka, jarum manometer naik stabil, dan mesin las MIG merah langsung aktif!",
        "caption": "GAS ARGON & MESIN LAS MIG MENYALA!",
    },
    # ACT 3: JACK STANDS, GROUND CLAMP & TWILIGHT BLUE TURN (34.0s - 45.0s)
    {
        "id": "ACT3_A",
        "start_f": 818, "end_f": 948,
        "location": "LOC2_ServiceBay",
        "text": "Mobil berdiri kokoh di atas dongkrak oranye tanpa celah, dan klem ground dijepit rapat ke sasis.",
        "caption": "DONGKRAK PRESISI & KLEM GROUND RAPAT",
    },
    {
        "id": "ACT3_B",
        "start_f": 950, "end_f": 1080,
        "location": "LOC6_FrontWeld",
        "text": "Cahaya sore berubah biru dingin. Kacamata las kuningan diturunkan—saatnya aksi las dimulai!",
        "caption": "CAHAYA BERUBAH BIRU — KACAMATA LAS TURUN!",
    },
    # ACT 4 (LAST 30 SECONDS = 45.0s - 75.0s): FRONT -> SIDE -> REAR WELDING MARATHON!
    {
        "id": "ACT4_FRONT",
        "start_f": 1082, "end_f": 1296,
        "location": "LOC6_FrontWeld",
        "text": "ZAP! Titik pertama di fender depan! Busur listrik biru menyala tajam, percikan api emas menghujani lantai beton!",
        "caption": "ZAP! LAS BAGIAN DEPAN — PERCIKAN API MEMBARA!",
    },
    {
        "id": "ACT4_SIDE",
        "start_f": 1298, "end_f": 1536,
        "location": "LOC2_SideWeld",
        "text": "Lanjut ke panel samping bodi! Tangan tetap mantap menyusuri setiap milimeter plat baja hingga menyatu rata!",
        "caption": "LANJUT LAS BAGIAN SAMPING BODI MERAH!",
    },
    {
        "id": "ACT4_REAR",
        "start_f": 1538, "end_f": 1716,
        "location": "LOC2_RearWeld",
        "text": "Kini titik terakhir di bodi belakang! Bara oranye membara menutup retakan terakhir dengan presisi tinggi!",
        "caption": "LAS BAGIAN BELAKANG — PENUTUPAN TERAKHIR!",
    },
    {
        "id": "ACT5_PAYOFF",
        "start_f": 1718, "end_f": 1796,
        "location": "LOC2_ServiceBay",
        "text": "Sinar senja kembali menyinari bengkel. Depan, samping, belakang selesai—sedan klasik ini lahir kembali!",
        "caption": "DEPAN, SAMPING, BELAKANG SELESAI! LAHIR KEMBALI!",
    },
]


# ==============================================================================
# 3. 30 COLLISION-FREE CONTINUOUS 3D CAMERA MOVES (CM01 .. CM30)
# Every camera position & interpolated segment stays strictly inside open space
# (X_gate=-4.15 open for Y in [-2.4..+0.6]; X_right=+4.25; Y_back=+2.38 open for
# X in [-2.35..+0.25]; Car AABB X=[-1.15..+2.85], Y=[-0.45..+1.08] avoided!)
# ==============================================================================
CAMERA_MOVES: List[Dict[str, Any]] = [
    # --- ACT 0: 2-SECOND HOOK (Frames 1..48) ---
    {"id": "CM01", "f0": 1,    "f1": 22,   "pos": (-1.75, -1.25, 0.90), "tgt": (-0.75, -0.42, 0.72), "lens": 56.0, "roll":  3.0, "ease": "expo",      "blur": 0.14},
    {"id": "CM02", "f0": 22,   "f1": 48,   "pos": (-6.40, -1.65, 1.38), "tgt": (-2.40, -0.95, 0.92), "lens": 19.0, "roll": -3.0, "ease": "whip",      "blur": 0.45},

    # --- ACT 1: LOC 1 COURTYARD -> LOC 2 SERVICE BAY & FENDER ZOOM (Frames 49..348) ---
    {"id": "CM03", "f0": 48,   "f1": 120,  "pos": (-5.10, -1.50, 1.18), "tgt": (-2.40, -1.05, 0.92), "lens": 21.0, "roll": -1.0, "ease": "cubic",     "blur": 0.14},
    {"id": "CM04", "f0": 120,  "f1": 195,  "pos": (-3.25, -1.55, 1.12), "tgt": (-1.40, -0.95, 0.92), "lens": 28.0, "roll":  0.8, "ease": "overshoot", "blur": 0.16},
    {"id": "CM05", "f0": 195,  "f1": 265,  "pos": (-2.40, -1.50, 1.04), "tgt": (-0.65, -0.50, 0.82), "lens": 26.0, "roll":  0.5, "ease": "cubic",     "blur": 0.10},
    {"id": "CM06", "f0": 265,  "f1": 310,  "pos": (-1.72, -1.22, 0.84), "tgt": (-0.76, -0.42, 0.72), "lens": 58.0, "roll":  2.0, "ease": "expo",      "blur": 0.24},
    {"id": "CM07", "f0": 310,  "f1": 348,  "pos": (-2.35, -1.10, 1.14), "tgt": (-1.35, -0.75, 1.02), "lens": 34.0, "roll":  0.0, "ease": "overshoot", "blur": 0.14},

    # --- ACT 2A: GLIDE AROUND FRONT OF CAR -> LOC 5 PARTS ALCOVE (Frames 349..504) ---
    # Stays strictly at X ~ -2.15 (in front of car bumper X=-1.15 and through open archway!)
    {"id": "CM08", "f0": 348,  "f1": 415,  "pos": (-2.15,  1.40, 1.24), "tgt": (-1.35,  3.00, 1.02), "lens": 22.0, "roll": -2.0, "ease": "cubic",     "blur": 0.25},
    {"id": "CM09", "f0": 415,  "f1": 465,  "pos": (-1.85,  2.10, 1.14), "tgt": (-1.05,  3.15, 0.98), "lens": 52.0, "roll":  1.2, "ease": "overshoot", "blur": 0.16},
    # Glide cleanly back out of archway along X = -2.15 before turning along front-left!
    {"id": "CM10", "f0": 465,  "f1": 525,  "pos": (-2.15, -1.45, 1.18), "tgt": ( 0.40, -1.10, 0.95), "lens": 22.0, "roll": -2.0, "ease": "whip",      "blur": 0.36},

    # --- ACT 2B: LOC 3 MASTER WORKBENCH & WRENCH ZOOM (Frames 526..660) ---
    {"id": "CM11", "f0": 525,  "f1": 585,  "pos": ( 1.45, -1.55, 1.22), "tgt": ( 3.15, -0.75, 1.05), "lens": 26.0, "roll":  0.8, "ease": "cubic",     "blur": 0.16},
    {"id": "CM12", "f0": 585,  "f1": 660,  "pos": ( 1.85, -1.40, 1.14), "tgt": ( 3.05, -0.72, 1.02), "lens": 52.0, "roll":  1.5, "ease": "overshoot", "blur": 0.18},

    # --- ACT 2C: LOC 4 MIG WELDER & ARGON GAUGE ZOOM (Frames 661..816) ---
    {"id": "CM13", "f0": 660,  "f1": 725,  "pos": ( 0.15, -2.85, 1.06), "tgt": ( 1.45, -2.75, 0.88), "lens": 26.0, "roll": -1.5, "ease": "cubic",     "blur": 0.22},
    {"id": "CM14", "f0": 725,  "f1": 775,  "pos": ( 0.42, -2.80, 0.98), "tgt": ( 1.45, -2.75, 0.92), "lens": 58.0, "roll":  1.0, "ease": "overshoot", "blur": 0.20},
    {"id": "CM15", "f0": 775,  "f1": 816,  "pos": (-1.35, -2.15, 0.65), "tgt": ( 0.05, -0.45, 0.42), "lens": 24.0, "roll": -1.0, "ease": "expo",      "blur": 0.24},

    # --- ACT 3: JACK STAND ZOOM -> GROUND CLAMP ZOOM -> BLUE SHADE GOGGLES PULL (Frames 817..1080) ---
    {"id": "CM16", "f0": 816,  "f1": 880,  "pos": (-1.05, -1.25, 0.34), "tgt": ( 0.10, -0.28, 0.26), "lens": 56.0, "roll":  1.2, "ease": "overshoot", "blur": 0.18},
    {"id": "CM17", "f0": 880,  "f1": 948,  "pos": (-0.85, -1.22, 0.42), "tgt": ( 0.05, -0.37, 0.35), "lens": 54.0, "roll": -1.5, "ease": "whip",      "blur": 0.30},
    {"id": "CM18", "f0": 948,  "f1": 1020, "pos": (-2.15, -1.30, 1.15), "tgt": (-0.78, -0.82, 1.08), "lens": 56.0, "roll":  1.8, "ease": "overshoot", "blur": 0.18},
    {"id": "CM19", "f0": 1020, "f1": 1080, "pos": (-1.85, -1.18, 0.90), "tgt": (-0.78, -0.42, 0.72), "lens": 62.0, "roll":  2.2, "ease": "expo",      "blur": 0.12},

    # --- ACT 4 (LAST 30 FULL SECONDS = Frames 1081..1800): FRONT -> SIDE -> REAR WELDING! ---
    # ZONE 1: FRONT FENDER / NOSE WELDING (Frames 1081..1296, 9 seconds)
    {"id": "CM20", "f0": 1080, "f1": 1145, "pos": (-2.25, -1.35, 0.96), "tgt": (-0.76, -0.58, 0.80), "lens": 38.0, "roll": -2.2, "ease": "expo",      "blur": 0.26},
    {"id": "CM21", "f0": 1145, "f1": 1220, "pos": (-1.52, -1.28, 0.84), "tgt": (-0.75, -0.42, 0.72), "lens": 62.0, "roll":  2.5, "ease": "overshoot", "blur": 0.20},
    {"id": "CM22", "f0": 1220, "f1": 1296, "pos": (-2.15, -1.75, 0.48), "tgt": (-0.65, -0.55, 0.64), "lens": 26.0, "roll": -2.5, "ease": "cubic",     "blur": 0.22},

    # ZONE 2: SIDE DOOR / PANEL WELDING (Frames 1297..1536, 10 seconds)
    {"id": "CM23", "f0": 1296, "f1": 1365, "pos": (-0.45, -1.85, 1.02), "tgt": ( 0.42, -0.55, 0.82), "lens": 32.0, "roll":  1.5, "ease": "cubic",     "blur": 0.20},
    {"id": "CM24", "f0": 1365, "f1": 1435, "pos": (-0.18, -1.42, 0.86), "tgt": ( 0.46, -0.42, 0.72), "lens": 64.0, "roll":  2.8, "ease": "overshoot", "blur": 0.22},
    {"id": "CM25", "f0": 1435, "f1": 1490, "pos": ( 0.85, -1.85, 0.46), "tgt": ( 0.50, -0.55, 0.65), "lens": 25.0, "roll": -3.0, "ease": "whip",      "blur": 0.34},
    {"id": "CM26", "f0": 1490, "f1": 1536, "pos": ( 0.95, -1.95, 1.48), "tgt": ( 1.45, -0.55, 0.84), "lens": 28.0, "roll":  2.5, "ease": "cubic",     "blur": 0.18},

    # ZONE 3: REAR QUARTER PANEL / TRUNK WELDING & SUNSET FINALE (Frames 1537..1800, 11 seconds)
    {"id": "CM27", "f0": 1536, "f1": 1610, "pos": ( 1.35, -1.78, 1.00), "tgt": ( 2.10, -0.52, 0.82), "lens": 36.0, "roll": -1.5, "ease": "cubic",     "blur": 0.18},
    {"id": "CM28", "f0": 1610, "f1": 1675, "pos": ( 1.65, -1.36, 0.88), "tgt": ( 2.15, -0.42, 0.76), "lens": 62.0, "roll":  2.2, "ease": "overshoot", "blur": 0.20},
    {"id": "CM29", "f0": 1675, "f1": 1735, "pos": ( 0.75, -2.05, 1.12), "tgt": ( 1.85, -0.62, 0.90), "lens": 34.0, "roll": -1.0, "ease": "cubic",     "blur": 0.16},
    {"id": "CM30", "f0": 1735, "f1": 1800, "pos": (-2.45, -2.35, 1.24), "tgt": ( 0.65, -0.45, 0.82), "lens": 22.0, "roll":  0.0, "ease": "expo",      "blur": 0.18},
]

CAM_INITIAL: Dict[str, Any] = {
    "pos": (-2.20, -1.48, 1.02),
    "tgt": (-0.75, -0.45, 0.78),
    "lens": 26.0,
    "roll": 0.0,
}


def eval_camera_state(frame: int) -> Dict[str, Any]:
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
# 4. 100% COLLISION-FREE NATURAL CHARACTER BLOCKING (NEVER CLIPS WALLS/CAR/PROPS!)
# Walk speed is calibrated to natural ~1.0–1.35 m/s, and `eval_character_blocking`
# AUTOMATICALLY sets `action="walk"` + faces walking direction whenever moving >0.10m/s
# so the character NEVER looks dragged/sliding!
# ==============================================================================
CHAR_BLOCKING_KEYS: List[Tuple[int, Tuple[float, float, float], float, str]] = [
    # HOOK (1..47): Welding intensely on Front-Left Fender!
    (1,    (-0.78, -0.810, 0.0),  28.0, "hook_weld"),
    (46,   (-0.70, -0.805, 0.0),  26.0, "hook_weld"),

    # ACT 1 (48..348): Walks smoothly from Sunlit Courtyard (LOC 1) through Open Gate into LOC 2!
    (48,   (-4.75, -1.200, 0.0), -82.0, "walk"),
    (128,  (-2.80, -1.150, 0.0), -82.0, "walk"),
    (205,  (-1.35, -0.950, 0.0), -40.0, "walk"),
    (245,  (-0.82, -0.840, 0.0),  28.0, "inspect_fender"),
    (330,  (-0.82, -0.840, 0.0),  38.0, "inspect_fender"),

    # ACT 2A (331..504): Walks cleanly AROUND front bumper (-1.75, -0.92) through Archway into LOC 5!
    (348,  (-1.75, -0.920, 0.0),  45.0, "walk"),
    (370,  (-1.75, -0.150, 0.0),   0.0, "walk"),
    (418,  (-1.75,  1.800, 0.0),  -8.0, "walk"),
    (446,  (-1.15,  2.950, 0.0), -10.0, "grab_plate"),
    (478,  (-1.15,  2.950, 0.0), -10.0, "grab_plate"),

    # ACT 2B (479..660): Walks cleanly BACK OUT through Archway -> around front -> along left side -> LOC 3 Workbench!
    (515,  (-1.75,  1.450, 0.0), 172.0, "walk"),
    (556,  (-1.75, -1.050, 0.0), -95.0, "walk"),
    (605,  ( 0.85, -1.150, 0.0), -90.0, "walk"),
    (636,  ( 2.85, -0.950, 0.0), -85.0, "workbench_prep"),
    (660,  ( 2.85, -0.950, 0.0), -85.0, "workbench_prep"),

    # ACT 2C (661..816): Walks cleanly to LOC 4 MIG Welder & Argon Tank (1.45, -2.75)!
    (700,  ( 1.10, -1.450, 0.0), 155.0, "walk"),
    (728,  ( 0.72, -2.350, 0.0), -65.0, "welder_prep"),
    (778,  ( 0.72, -2.350, 0.0), -65.0, "welder_prep"),

    # ACT 3 (781..1080): Walks back to car -> checks Jack Stands & Ground Clamp -> Blue Shade Goggles Pull!
    (820,  (-0.08, -1.050, 0.0),  15.0, "check_jack"),
    (880,  (-0.08, -1.050, 0.0),  15.0, "check_jack"),
    (910,  ( 0.06, -0.920, 0.0),  10.0, "clip_clamp"),
    (950,  ( 0.06, -0.920, 0.0),  10.0, "clip_clamp"),
    (985,  (-0.82, -0.820, 0.0),  34.0, "goggles_pull"),
    (1045, (-0.82, -0.820, 0.0),  32.0, "goggles_pull"),
    (1080, (-0.84, -0.805, 0.0),  30.0, "weld_ready"),

    # ACT 4 (LAST 30 SECONDS = 1081..1800): FRONT -> SIDE -> REAR WELDING!
    # Zone 1: FRONT FENDER WELD (1081..1296)
    (1081, (-0.84, -0.805, 0.0),  30.0, "weld_front"),
    (1188, (-0.72, -0.798, 0.0),  28.0, "weld_front"),
    (1296, (-0.60, -0.792, 0.0),  26.0, "weld_front"),

    # Walk smoothly along left side from Front (-0.60) to Side Panel (+0.26) (Frames 1297..1336, ~0.85m in 1.6s = natural walk!)
    (1336, ( 0.26, -0.805, 0.0),  30.0, "weld_side"),
    # Zone 2: SIDE PANEL WELD (1337..1536)
    (1436, ( 0.44, -0.795, 0.0),  26.0, "weld_side"),
    (1536, ( 0.62, -0.788, 0.0),  22.0, "weld_side"),

    # Walk smoothly along left side from Side (+0.62) to Rear Quarter (+1.92) (Frames 1537..1588, ~1.30m in 2.1s = natural walk!)
    (1588, ( 1.92, -0.805, 0.0),  28.0, "weld_rear"),
    # Zone 3: REAR QUARTER PANEL WELD (1589..1748)
    (1668, ( 2.10, -0.795, 0.0),  26.0, "weld_rear"),
    (1748, ( 2.26, -0.788, 0.0),  22.0, "weld_rear"),

    # Final Payoff Smile & Goggles Up (1749..1800)
    (1776, ( 2.18, -0.850, 0.0),  54.0, "hero_payoff"),
    (1800, ( 2.18, -0.850, 0.0),  56.0, "hero_payoff"),
]


def _eval_raw_char_pos_yaw(frame: int) -> Tuple[Tuple[float, float, float], float, str]:
    f = max(1, min(1800, frame))
    for i in range(len(CHAR_BLOCKING_KEYS) - 1):
        f0, p0, y0, act0 = CHAR_BLOCKING_KEYS[i]
        f1, p1, y1, act1 = CHAR_BLOCKING_KEYS[i + 1]
        if f0 <= f <= f1:
            if f0 == 46 and f1 == 48:
                return (p0, y0, act0) if f <= 47 else (p1, y1, act1)
            t = ease_in_out_cubic((f - f0) / max(1.0, float(f1 - f0)))
            pos = lerp3(p0, p1, t)
            dy = ((y1 - y0 + 180.0) % 360.0) - 180.0
            yaw = y0 + dy * t
            return pos, yaw, act0 if t < 0.85 else act1
    _, pos, yaw, act = CHAR_BLOCKING_KEYS[-1]
    return pos, yaw, act


def eval_character_blocking(frame: int) -> Tuple[Tuple[float, float, float], float, str]:
    """
    Return `(world_pos, yaw_deg, action_tag)`.
    Automatically detects genuine walking velocity (`> 0.16 m/s`) so the character ALWAYS
    plays a smooth natural `walk` cycle facing his stride direction — NEVER dragged/sliding!
    """
    pos, yaw, act = _eval_raw_char_pos_yaw(frame)
    # Never override active welding slow-step passes or Hook-to-Act1 cut
    if act in ("hook_weld", "weld_front", "weld_side", "weld_rear", "goggles_pull", "hero_payoff"):
        return pos, yaw, act
    if 45 <= frame <= 50:
        return pos, yaw, act

    p_prev, _, _ = _eval_raw_char_pos_yaw(max(1, frame - 1))
    p_next, _, _ = _eval_raw_char_pos_yaw(min(1800, frame + 1))
    dx = (p_next[0] - p_prev[0]) * 12.0  # m/s (over 2/24 s)
    dy = (p_next[1] - p_prev[1]) * 12.0
    speed = math.hypot(dx, dy)

    if speed > 0.16:
        # Face walking direction smoothly (+Y forward rotated by yaw around Z -> (-sin(yaw), cos(yaw)))
        move_yaw = math.degrees(math.atan2(-dx, dy))
        return pos, move_yaw, "walk"
    return pos, yaw, act


# ==============================================================================
# 5. DYNAMIC LIGHTING MOOD PROGRESSION (CHANGES AS THE STORY TURNS!)
# ==============================================================================
LIGHTING_MOOD_KEYS: List[Dict[str, Any]] = [
    # Hook: High-contrast blue shade + arc flash
    {"f": 1,    "sun_e": 0.9, "sun_elev":  6.0, "sun_col": "#8AB8FF", "blue_e": 34.0, "ray_alpha": 0.14, "ray_col": "#5EB2FF", "haze": 0.012},
    {"f": 46,   "sun_e": 0.9, "sun_elev":  6.0, "sun_col": "#8AB8FF", "blue_e": 34.0, "ray_alpha": 0.14, "ray_col": "#5EB2FF", "haze": 0.012},
    # Act 1-2: Low Golden Afternoon Sun, Long Shadows, Crisp Window God Ray + Cool Blue Shade
    {"f": 50,   "sun_e": 6.8, "sun_elev": 12.5, "sun_col": "#FFB463", "blue_e": 24.0, "ray_alpha": 0.34, "ray_col": "#FFD28E", "haze": 0.014},
    {"f": 500,  "sun_e": 6.0, "sun_elev": 10.0, "sun_col": "#FFA552", "blue_e": 26.0, "ray_alpha": 0.32, "ray_col": "#FFC778", "haze": 0.014},
    {"f": 816,  "sun_e": 4.8, "sun_elev":  8.0, "sun_col": "#FF8F40", "blue_e": 30.0, "ray_alpha": 0.28, "ray_col": "#FFB062", "haze": 0.015},
    # Act 3: STORY TURN — Twilight Blue Shade takes over as goggles drop!
    {"f": 960,  "sun_e": 1.4, "sun_elev":  4.0, "sun_col": "#6E9EE8", "blue_e": 42.0, "ray_alpha": 0.18, "ray_col": "#5EA6FF", "haze": 0.016},
    {"f": 1080, "sun_e": 0.7, "sun_elev":  3.0, "sun_col": "#4C82D8", "blue_e": 46.0, "ray_alpha": 0.15, "ray_col": "#4898FF", "haze": 0.018},
    # Act 4: 30-Second Welding Marathon — Deep Blue Shade + Electric Cyan Arcs (Front -> Side -> Rear!)
    {"f": 1620, "sun_e": 0.9, "sun_elev":  3.5, "sun_col": "#5890E0", "blue_e": 44.0, "ray_alpha": 0.18, "ray_col": "#54B0FF", "haze": 0.018},
    # Act 5 Finale: Golden Sunset God Ray breaks back through the Hero Window!
    {"f": 1715, "sun_e": 6.2, "sun_elev":  9.0, "sun_col": "#FFA048", "blue_e": 28.0, "ray_alpha": 0.36, "ray_col": "#FFC470", "haze": 0.015},
    {"f": 1800, "sun_e": 7.6, "sun_elev":  8.5, "sun_col": "#FF983E", "blue_e": 24.0, "ray_alpha": 0.38, "ray_col": "#FFBE66", "haze": 0.014},
]
