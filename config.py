"""
config.py — Global Configuration, Frame Timing, Coordinates & Cel-Shade Palette
Project: Young Mechanic Welding 3D Cel-Shaded Short Animation
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

# ==============================================================================
# PATHS
# ==============================================================================
PROJECT_ROOT: Path = Path(__file__).resolve().parent
CHARACTER_SCRIPT_PATH: Path = PROJECT_ROOT / "tr" / "mekanik_muda_character.py"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
DEBUG_FRAMES_DIR: Path = OUTPUT_DIR / "debug_frames"
GENERATED_TEX_DIR: Path = OUTPUT_DIR / "generated_textures"
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
# Car sits near origin, angled slightly for dynamic 3/4 workshop composition.
# Mechanic stands on the negative-Y side of the front-left fender facing +Y.
MECHANIC_ROOT_POS: Tuple[float, float, float] = (-0.18, -1.02, 0.0)

# Exact 3D weld seam along the car's front-left fender arch/panel
# Mechanic reaches comfortably forward (+Y) at chest/upper-waist height (Z ~ 0.96m)
WELD_SEAM_START: Tuple[float, float, float] = (-0.34, -0.43, 0.955)
WELD_SEAM_MID: Tuple[float, float, float] = (-0.17, -0.445, 0.975)
WELD_SEAM_END: Tuple[float, float, float] = (0.01, -0.43, 0.945)

# Safe hand rest point on upper intact fender lip for Mechanic's Left Hand during Beat 3
# Carefully placed on the outer/upper surface so fingers rest cleanly without clipping
FENDER_LEFT_HAND_REST: Tuple[float, float, float] = (-0.46, -0.47, 1.035)

# MIG Welder unit & Gas Cylinder position (to Mechanic's right-rear, +X / -Y)
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
    # Ink Outlines (matches mekanik_muda_character.py #201720)
    "ink_outline": "#201720",
    # Character exact colors from CHARACTER_CONFIG
    "skin": "#FBE1CA",
    "skin_blush": "#DEAE96",
    "iris_honey": "#B86B22",
    "hair_dark": "#332018",
    "vest_mustard": "#D89E28",
    "tee_ivory": "#F4EFE1",
    "belt_leather": "#4E2E1D",
    "buckle_metal": "#7D8088",
    "brass_goggles": "#9E7A38",
    "strap_black": "#232026",
    "goggle_lens": "#2F5E4E",
    "loupe_glass": "#9FE0F2",
    "noodle_limb": "#1F161E",
    "pencil_yellow": "#F2BE26",
    "pencil_eraser": "#DE8F96",
    "bandage_cream": "#F0DEC4",
    "copper_wire": "#C86D3B",
    "screwdriver_red": "#D82E29",
    # Stylized Car & Welding Props
    "car_body_teal": "#2B7A9B",
    "car_body_accent": "#E8ECF2",
    "car_primer_grey": "#6E7682",
    "car_interior": "#272A34",
    "car_tire": "#1E2026",
    "car_rim_alloy": "#C9D3E0",
    "jack_orange": "#E05A2B",
    "welder_red": "#C8372D",
    "gas_tank_green": "#2D5A4C",
    "torch_yellow": "#E5A92E",
    "torch_copper": "#D47A42",
    # Workshop Environment
    "floor_concrete": "#464B57",
    "floor_line_yellow": "#D9A432",
    "floor_oil": "#22252E",
    "wall_brick": "#5C4948",
    "wall_lower": "#383E4C",
    "steel_beam": "#2F3542",
    "bench_wood": "#8C6239",
    "bench_frame": "#2E3642",
    "tool_red": "#C9382E",
    "oil_can_yellow": "#E0A82E",
    "oil_can_blue": "#346FA8",
    "lamp_shade": "#303A48",
    # VFX
    "weld_arc_core": "#E8FAFF",
    "weld_arc_blue": "#52C8FF",
    "spark_gold": "#FFC44D",
    "seam_molten": "#FF6E1A",
}
