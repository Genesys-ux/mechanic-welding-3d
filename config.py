"""
config.py — Global Configuration, Frame Timing, Coordinates & Cel-Shade Palette
Project: Young Mechanic Welding 3D Cel-Shaded Short Animation (2.5D Dynamic Billboard)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

# ==============================================================================
# PATHS
# ==============================================================================
PROJECT_ROOT: Path = Path(__file__).resolve().parent
CHARACTER_SCRIPT_PATH: Path = PROJECT_ROOT / "tr" / "mekanik_muda_character.py"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
DEBUG_FRAMES_DIR: Path = OUTPUT_DIR / "debug_frames"
CHAR_FRAMES_DIR: Path = OUTPUT_DIR / "char_frames"
CAMERA_SYNC_PATH: Path = OUTPUT_DIR / "camera_sync.json"
CHAR_HAND_SYNC_PATH: Path = OUTPUT_DIR / "char_hand_sync.json"
BLEND_FILE_PATH: Path = OUTPUT_DIR / "mechanic_scene.blend"
FINAL_VIDEO_PATH: Path = OUTPUT_DIR / "mechanic_welding_final.mp4"

# ==============================================================================
# RENDER & TIMELINE SETTINGS (11 Seconds @ 24 FPS = 264 Frames)
# ==============================================================================
FPS: int = 24
FRAME_START: int = 1
FRAME_END: int = 264
TOTAL_FRAMES: int = 264

RES_X: int = 1920
RES_Y: int = 1080
DEBUG_RES_X: int = 960
DEBUG_RES_Y: int = 540

DIAGNOSTIC_FRAMES: Tuple[int, ...] = (20, 85, 155, 240)
RANDOM_SEED: int = 42

# ==============================================================================
# 2.5D CHARACTER BILLBOARD PROPORTIONS (Matches 240x520 MekanikMudaCharacter)
# ==============================================================================
CHAR_BASE_WIDTH_PX: int = 240
CHAR_BASE_HEIGHT_PX: int = 520
CHAR_FEET_Y_PX: float = 476.0  # Soles of feet in 240x520 canvas

CHAR_BILLBOARD_HEIGHT: float = 1.58
CHAR_BILLBOARD_WIDTH: float = CHAR_BILLBOARD_HEIGHT * (CHAR_BASE_WIDTH_PX / CHAR_BASE_HEIGHT_PX)
# Vertical offset so y=476px sits right on Z=0.0 workshop floor:
CHAR_Z_BOTTOM_OFFSET: float = -((CHAR_BASE_HEIGHT_PX - CHAR_FEET_Y_PX) / CHAR_BASE_HEIGHT_PX) * CHAR_BILLBOARD_HEIGHT

# ==============================================================================
# BEAT SHEET TIMING
# ==============================================================================
BEAT1_START, BEAT1_END = 1, 60     # Fast Travel Establishing & Zoom-In
BEAT2_START, BEAT2_END = 61, 110   # Natural Preparation & Prop Interaction
BEAT3_START, BEAT3_END = 111, 205  # High-Energy Welding Action & Dynamic Orbit
BEAT4_START, BEAT4_END = 206, 264  # Whip-Zoom Pull-Back & Payoff

WELD_ARC_START: int = 113
WELD_ARC_END: int = 203

# ==============================================================================
# SPATIAL ANCHORS (World Coordinates in Meters, Blender Z-Up)
# ==============================================================================
# Empty_Mechanic sits beside the front-left fender (27cm from seam so 21cm torch bridges hand->fender!)
MECHANIC_ROOT_POS: Tuple[float, float, float] = (-0.14, -0.72, 0.0)
MECHANIC_BASE_YAW_DEG: float = 36.0

# Exact 3D weld seam along the car's front-left fender arch/panel
WELD_SEAM_START: Tuple[float, float, float] = (-0.34, -0.43, 0.955)
WELD_SEAM_MID: Tuple[float, float, float] = (-0.17, -0.445, 0.975)
WELD_SEAM_END: Tuple[float, float, float] = (0.01, -0.43, 0.945)

FENDER_LEFT_HAND_REST: Tuple[float, float, float] = (-0.46, -0.47, 1.035)

# MIG Welder unit & Gas Cylinder position
WELDER_UNIT_POS: Tuple[float, float, float] = (0.92, -1.32, 0.0)
WELDER_CABLE_SOCKET: Tuple[float, float, float] = (0.72, -1.12, 0.56)


# ==============================================================================
# COLOR UTILITIES & CEL-SHADE PALETTE (sRGB -> Linear RGB for Blender Nodes)
# ==============================================================================
def srgb_to_linear_channel(c: float) -> float:
    c = max(0.0, min(1.0, c))
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r = srgb_to_linear_channel(int(h[0:2], 16) / 255.0)
    g = srgb_to_linear_channel(int(h[2:4], 16) / 255.0)
    b = srgb_to_linear_channel(int(h[4:6], 16) / 255.0)
    return (r, g, b, alpha)


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    r, g, b, _ = hex_to_rgba(hex_color, 1.0)
    return (r, g, b)


PALETTE_HEX: Dict[str, str] = {
    "ink_outline": "#201720",
    "brass_goggles": "#9E7A38",
    # Stylized Car & Welding Props
    "car_body_teal": "#2B7A9B",
    "car_body_accent": "#DDE4EE",
    "car_primer_grey": "#68707C",
    "car_interior": "#232630",
    "car_tire": "#1C1E24",
    "car_rim_alloy": "#BCC7D6",
    "jack_orange": "#D95628",
    "welder_red": "#C2342A",
    "gas_tank_green": "#2B5648",
    "torch_yellow": "#DFA228",
    "torch_copper": "#CE743C",
    # Workshop Environment (darkened slightly for rich contrast under Standard View Transform)
    "floor_concrete": "#3A3F4B",
    "floor_line_yellow": "#CF9A2C",
    "floor_oil": "#1C1F28",
    "wall_brick": "#4B3B3B",
    "wall_lower": "#2E3442",
    "steel_beam": "#262C38",
    "bench_wood": "#7D5632",
    "bench_frame": "#28303C",
    "tool_red": "#BD342A",
    "oil_can_yellow": "#D69E28",
    "oil_can_blue": "#2F669C",
    "lamp_shade": "#2A3340",
    # VFX
    "weld_arc_core": "#E8FAFF",
    "weld_arc_blue": "#38BEFF",
    "spark_gold": "#FFC44D",
    "seam_molten": "#FF6E1A",
}
