"""
short_75s/render_char_short.py — Stage 2 (Python with resvg-py):
Drives `MekanikMudaCharacter` (unchanged 2.5D pipeline & style!) with natural, non-robotic
acting across all 5 Acts & 6 Locations of the 75-second YouTube Short:
  - Hook welding intensity -> natural walk cycle -> fender inspection -> grabbing steel plate ->
    workbench prep -> turning Argon gas valve -> checking jack stands & ground clamp ->
    pulling brass goggles down -> steady weaving welding pass -> pushing goggles up -> proud smile!
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict

import resvg_py

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from render_char_25d import project_ra_hand_uv  # noqa: E402
from tr.mekanik_muda_character import Easing, MekanikMudaCharacter, interpolate  # noqa: E402

from short_75s.config_short import (  # noqa: E402
    CAMERA_SYNC_PATH,
    CHAR_FRAMES_DIR,
    CHAR_HAND_SYNC_PATH,
    CLIMAX_ARC_END,
    CLIMAX_ARC_START,
    FPS,
    HOOK_ARC_END,
)


def build_75s_character_overrides(frame: int, action: str) -> Dict[str, Any]:
    """Natural, expressive non-robotic 2.5D acting synced to the 75-second narration."""
    ov: Dict[str, Any] = {
        "animation": "idle",
        "ground_shadow": False,
        "pose": "ready",
        "prop": "none",
    }

    # Subtle organic breathing / head bob so character NEVER feels stiff or robotic
    breath = math.sin(frame * 0.14)
    ov["head_tilt"] = round(breath * 0.025, 4)

    # 1) HOOK (Frames 1..48): Explosive welding flash-forward!
    if frame <= 48:
        ov["hat_lift_y"] = -92.0
        ov["hat_tilt"] = 0.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "grit_teeth"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.20
        u_h = min(1.0, frame / float(max(1, HOOK_ARC_END)))
        zig = math.sin(frame * 1.2) * 3.0
        ov["left_hand_target"] = (-66.0, 250.0, 32.0)
        ov["right_hand_target"] = (-26.0 + u_h * 10.0, 248.0 + zig, 51.0 - u_h * 3.0)
        return ov

    # 2) ACT 1: Walking in from courtyard -> inspecting broken red fender (49..336)
    if frame <= 220:
        ov["animation"] = "walk"
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.10
        ov["eye_gaze_x"] = -0.20
        ov["eye_gaze_y"] = 0.05
        return ov

    if frame <= 336:
        # Inspecting cracked fender naturally (hand reaches out, then confident smirk!)
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused" if frame < 290 else "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk" if frame < 300 else "confident_gap"
        ov["mouth_open"] = 0.0 if frame < 300 else 0.22
        ov["eye_gaze_x"] = -0.40
        ov["eye_gaze_y"] = 0.25 if frame < 290 else 0.0
        ov["head_tilt"] = -0.07 if frame < 290 else 0.03
        ov["right_hand_target"] = (-28.0, 255.0 + breath * 3.0, 48.0)
        ov["left_hand_target"] = (-54.0, 276.0, 26.0)
        return ov

    # 3) ACT 2: Parts Alcove (337..440) -> Workbench (441..544) -> MIG Welder & Argon Tank (545..696)
    if action == "walk":
        ov["animation"] = "walk"
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        return ov

    if frame <= 440:
        # Grabbing fresh steel repair plate from LOC 5 shelf
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -4.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["right_hand_target"] = (-22.0, 210.0 + breath * 4.0, 50.0)
        ov["left_hand_target"] = (-48.0, 222.0, 44.0)
        return ov

    if frame <= 544:
        # Selecting chrome wrench at Master Workbench (LOC 3)
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.14
        ov["right_hand_target"] = (-16.0, 205.0 + breath * 4.0, 46.0)
        ov["left_hand_target"] = (-52.0, 268.0, 28.0)
        return ov

    if frame <= 696:
        # Turning Argon gas valve & flipping MIG welder switch (LOC 4)
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        twist = math.sin(frame * 0.45) * 8.0
        ov["right_hand_target"] = (-18.0 + twist, 218.0, 48.0)
        ov["left_hand_target"] = (-50.0, 260.0, 32.0)
        return ov

    # 4) ACT 3: Checking Jack Stands & Ground Clamp -> Pulling Brass Goggles Down (697..1032)
    if frame <= 875:
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["head_tilt"] = -0.10
        ov["eye_gaze_y"] = 0.30
        ov["right_hand_target"] = (-20.0, 295.0, 44.0)
        ov["left_hand_target"] = (-56.0, 285.0, 30.0)
        return ov

    if frame <= 1032:
        # Iconic Goggles Pull-Down (Frames 910..960) + Torch Ready (961..1032)
        if frame < 910:
            ov["hat_lift_y"] = 0.0
            ov["hat_tilt"] = -6.0
        elif frame <= 960:
            ov["hat_lift_y"] = interpolate(frame, [910, 922, 950, 960], [0.0, 6.0, -88.0, -92.0], easing=Easing.in_out_cubic)
            ov["hat_tilt"] = interpolate(frame, [910, 948, 960], [-6.0, -1.0, 0.0], easing=Easing.in_out_quad)
        else:
            ov["hat_lift_y"] = -92.0
            ov["hat_tilt"] = 0.0

        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.20

        if 900 <= frame <= 968:
            lx = interpolate(frame, [900, 922, 952, 968], [-54.0, -34.0, -30.0, -58.0])
            ly = interpolate(frame, [900, 922, 952, 968], [285.0, 108.0, 142.0, 240.0])
            lz = interpolate(frame, [900, 922, 952, 968], [24.0, 42.0, 44.0, 32.0])
            ov["left_hand_target"] = (lx, ly, lz)
        else:
            ov["left_hand_target"] = (-66.0, 250.0, 32.0)

        rx = interpolate(frame, [876, 940, 1015, 1032], [30.0, -6.0, -34.0, -34.0], easing=Easing.in_out_quad)
        ry = interpolate(frame, [876, 940, 1015, 1032], [280.0, 260.0, 248.0, 248.0], easing=Easing.in_out_quad)
        rz = interpolate(frame, [876, 940, 1015, 1032], [32.0, 44.0, 54.0, 54.0], easing=Easing.in_out_quad)
        ov["right_hand_target"] = (rx, ry, rz)
        return ov

    # 5) ACT 4: High-Energy Welding Climax (1033..1435)
    if frame <= CLIMAX_ARC_END:
        ov["hat_lift_y"] = -92.0
        ov["hat_tilt"] = 0.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "grit_teeth"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.22
        if frame <= CLIMAX_ARC_START + 8:
            ov["head_tilt"] = 0.05
            ov["squash_x"] = 1.03
            ov["squash_y"] = 0.97
        else:
            ov["head_tilt"] = -0.05 + breath * 0.015

        u_w = (frame - CLIMAX_ARC_START) / float(max(1, CLIMAX_ARC_END - CLIMAX_ARC_START))
        zig = math.sin((frame - CLIMAX_ARC_START) * 1.15) * 3.0
        ov["left_hand_target"] = (-68.0, 252.0, 32.0)
        ov["right_hand_target"] = (-34.0 + u_w * 26.0, 248.0 + zig, 54.0 - u_w * 8.0)
        return ov

    # 6) ACT 5: Cooling Ember, Goggles Push-Up & Triumphant Sunset Smile (1436..1800)
    if frame < 1518:
        ov["hat_lift_y"] = -92.0
        ov["hat_tilt"] = 0.0
    elif frame <= 1565:
        ov["hat_lift_y"] = interpolate(frame, [1518, 1528, 1554, 1565], [-92.0, -86.0, 5.0, 0.0], easing=Easing.in_out_cubic)
        ov["hat_tilt"] = interpolate(frame, [1518, 1554, 1565], [0.0, -6.5, -6.0], easing=Easing.in_out_quad)
    else:
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0

    if frame <= 1535:
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.05
    else:
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "happy"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.36
        ov["eye_gaze_x"] = -0.08
        ov["eye_gaze_y"] = 0.0
        if 1575 <= frame <= 1645:
            ov["head_tilt"] = interpolate(frame, [1575, 1605, 1645], [0.02, -0.08, 0.01], easing=Easing.in_out_quad)

    if 1510 <= frame <= 1575:
        lx = interpolate(frame, [1510, 1528, 1556, 1575], [-56.0, -30.0, -34.0, -54.0])
        ly = interpolate(frame, [1510, 1528, 1556, 1575], [230.0, 142.0, 106.0, 286.0])
        lz = interpolate(frame, [1510, 1528, 1556, 1575], [32.0, 44.0, 42.0, 24.0])
        ov["left_hand_target"] = (lx, ly, lz)

    rx = interpolate(frame, [1436, 1485, 1555, 1800], [-8.0, 22.0, 44.0, 44.0], easing=Easing.out_cubic)
    ry = interpolate(frame, [1436, 1485, 1555, 1800], [248.0, 236.0, 284.0, 284.0], easing=Easing.out_cubic)
    rz = interpolate(frame, [1436, 1485, 1555, 1800], [46.0, 40.0, 30.0, 30.0], easing=Easing.out_cubic)
    ov["right_hand_target"] = (rx, ry, rz)
    return ov


def main() -> None:
    if not CAMERA_SYNC_PATH.exists():
        raise FileNotFoundError(f"Missing {CAMERA_SYNC_PATH} — run short_75s/export_sync_short.py first!")

    sync_data = json.loads(CAMERA_SYNC_PATH.read_text(encoding="utf-8"))
    frames_map: Dict[str, Dict[str, Any]] = sync_data["frames"]
    target_frames = [int(f) for f in sync_data["target_frames"]]

    CHAR_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    char = MekanikMudaCharacter(scale=2.0, fps=FPS)

    hand_sync: Dict[str, Dict[str, float]] = {}
    for idx, f in enumerate(target_frames):
        entry = frames_map[str(f)]
        angle_deg = float(entry["angle"])
        action = str(entry.get("action", "idle"))
        ov = build_75s_character_overrides(f, action)

        ctx, pose = char._render_ctx(frame=f, fps=FPS, angle=angle_deg, scale=2.0, **ov)
        png_bytes = resvg_py.svg_to_bytes(svg_string=ctx.to_svg(), skip_system_fonts=not ctx._has_text)

        out_png = CHAR_FRAMES_DIR / f"char_{f:04d}.png"
        out_png.write_bytes(png_bytes)

        u, v = project_ra_hand_uv(pose, angle_deg)
        hand_sync[str(f)] = {
            "u": u,
            "v": v,
            "angle": angle_deg,
            "hat_lift_y": round(float(ov.get("hat_lift_y", 0.0)), 2),
        }

        if idx % 30 == 0 or idx == len(target_frames) - 1 or len(target_frames) <= 12:
            print(f"[Short75s 2.5D] Frame {f:04d} ({action:14s}, ang={angle_deg:5.1f}°, raHnd=({u:.3f},{v:.3f}))", flush=True)

    CHAR_HAND_SYNC_PATH.write_text(json.dumps({"frames": hand_sync}, indent=2), encoding="utf-8")
    print(f"[Short75s 2.5D] Saved {len(target_frames)} sprites -> {CHAR_HAND_SYNC_PATH}")


if __name__ == "__main__":
    main()
