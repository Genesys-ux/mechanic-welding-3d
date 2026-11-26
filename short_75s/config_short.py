"""
short_75s/config_short.py — Configuration for 75-Second 9:16 YouTube Short
("Mesin Tua, Nyawa Baru" — 1,800 Frames @ 24 FPS, 6 Locations, 30 Camera Moves).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

SHORT_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = SHORT_DIR.parent
OUTPUT_DIR: Path = PROJECT_ROOT / "output_short_75s"
DEBUG_FRAMES_DIR: Path = OUTPUT_DIR / "debug_frames"
CHAR_FRAMES_DIR: Path = OUTPUT_DIR / "char_frames"
CAMERA_SYNC_PATH: Path = OUTPUT_DIR / "camera_sync.json"
CHAR_HAND_SYNC_PATH: Path = OUTPUT_DIR / "char_hand_sync.json"
BLEND_FILE_PATH: Path = OUTPUT_DIR / "short_75s_scene.blend"
FINAL_MP4_PATH: Path = OUTPUT_DIR / "mechanic_short_75s_final.mp4"
AUDIO_WAV_PATH: Path = OUTPUT_DIR / "narration_mix.wav"
CAPTIONS_SRT_PATH: Path = OUTPUT_DIR / "captions.srt"

# ==============================================================================
# TIMELINE & 9:16 YOUTUBE SHORTS RESOLUTION (75 Seconds @ 24 FPS = 1,800 Frames)
# ==============================================================================
FPS: int = 24
DURATION_SEC: float = 75.0
FRAME_START: int = 1
FRAME_END: int = 1800
TOTAL_FRAMES: int = 1800

# 9:16 Vertical YouTube Shorts
RES_X: int = 1080
RES_Y: int = 1920
DEBUG_RES_X: int = 540
DEBUG_RES_Y: int = 960

# 12 representative debug preview frames spanning Hook + all 6 Locations + Lighting Turns + Payoff
DEBUG_FRAMES: List[int] = [
    12,    # 0.5s  — HOOK: Explosive welding arc & sparks flash-forward (LOC 6)
    95,    # 4.0s  — LOC 1: Golden low-sun courtyard gate, long shadows & god rays
    250,   # 10.4s — LOC 2/6: Zoom-in on cracked red sedan fender in golden haze
    415,   # 17.3s — LOC 5: Spare-parts storage alcove & grabbing steel plate
    520,   # 21.7s — LOC 3: Master workbench, chrome pegboard & red tool chest
    625,   # 26.0s — LOC 4: Zoom-in on MIG welder panel & Argon pressure gauges
    780,   # 32.5s — LOC 2/6: Low floor push onto 0-gap orange jack stands
    950,   # 39.6s — LOC 2: Twilight BLUE SHADE turn + pulling brass goggles down
    1120,  # 46.7s — LOC 6: Climax dynamic welding orbit & electric cyan arc
    1205,  # 50.2s — LOC 6: Macro zoom-in on molten weld bead & nozzle contact
    1475,  # 61.5s — LOC 6: Cooling orange ember seam flush on red fender
    1650,  # 68.8s — LOC 2->1: Golden sunset god-rays heroic payoff & pull-out
]

# Active welding arc windows (Hook + 30s Finale: Front -> Side -> Rear!)
HOOK_ARC_START: int = 1
HOOK_ARC_END: int = 38
FRONT_ARC_START: int = 1081
FRONT_ARC_END: int = 1296
SIDE_ARC_START: int = 1337
SIDE_ARC_END: int = 1536
REAR_ARC_START: int = 1589
REAR_ARC_END: int = 1748
CLIMAX_ARC_START: int = FRONT_ARC_START
CLIMAX_ARC_END: int = REAR_ARC_END

RANDOM_SEED: int = 75

# 2.5D Character Billboard Proportions (matches 240x520 MekanikMudaCharacter)
CHAR_BASE_WIDTH_PX: int = 240
CHAR_BASE_HEIGHT_PX: int = 520
CHAR_FEET_Y_PX: float = 476.0
CHAR_BILLBOARD_HEIGHT: float = 1.58
CHAR_BILLBOARD_WIDTH: float = CHAR_BILLBOARD_HEIGHT * (CHAR_BASE_WIDTH_PX / CHAR_BASE_HEIGHT_PX)
CHAR_Z_BOTTOM_OFFSET: float = -((CHAR_BASE_HEIGHT_PX - CHAR_FEET_Y_PX) / CHAR_BASE_HEIGHT_PX) * CHAR_BILLBOARD_HEIGHT

# Fallback weld seam anchors (overridden at runtime by exact ray_cast onto car fender!)
WELD_SEAM_START: Tuple[float, float, float] = (-0.40, -0.416, 0.742)
WELD_SEAM_MID: Tuple[float, float, float] = (-0.25, -0.420, 0.750)
WELD_SEAM_END: Tuple[float, float, float] = (-0.10, -0.423, 0.742)
WELDER_UNIT_POS: Tuple[float, float, float] = (0.92, -1.32, 0.0)
WELDER_CABLE_SOCKET: Tuple[float, float, float] = (0.72, -1.12, 0.56)
