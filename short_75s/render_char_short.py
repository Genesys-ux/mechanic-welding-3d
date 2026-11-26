"""
short_75s/render_char_short.py — Stage 2 (Python with resvg-py):
Drives `MekanikMudaCharacter` (unchanged 2.5D pipeline & style!) with:
  - Smooth natural `walk` cycle whenever moving (`action == "walk"`, NEVER dragged/sliding!)
  - Natural held-prop poses (`grab_plate` for Steel Plate, `workbench_prep` for Chrome Wrench)
  - Full 30-second multi-zone welding pass (Front -> Side -> Rear!) + goggles pull/push & proud smile!
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
    FPS,
    FRONT_ARC_END,
    FRONT_ARC_START,
    HOOK_ARC_END,
    REAR_ARC_END,
    REAR_ARC_START,
    SIDE_ARC_END,
    SIDE_ARC_START,
)


def build_75s_character_overrides(frame: int, action: str) -> Dict[str, Any]:
    ov: Dict[str, Any] = {
        "animation": "idle",
        "ground_shadow": False,
        "pose": "ready",
        "prop": "none",
    }
    breath = math.sin(frame * 0.14)
    ov["head_tilt"] = round(breath * 0.022, 4)

    # 0) PRIORITY: Whenever character is walking between locations/zones, ALWAYS play natural walk!
    if action == "walk":
        ov["animation"] = "walk"
        # Keep goggles down if walking between welding zones (1297..1588)!
        goggles_down = frame >= 1035 and frame <= 1750
        ov["hat_lift_y"] = -92.0 if goggles_down else 0.0
        ov["hat_tilt"] = 0.0 if goggles_down else -6.0
        ov["eyes"] = "focused" if goggles_down else "honey_oval"
        ov["eyebrows"] = "angry" if goggles_down else "thick_arch"
        ov["mouth"] = "smirk" if goggles_down else "confident_gap"
        ov["mouth_open"] = 0.0 if goggles_down else 0.08
        return ov

    # 1) HOOK (Frames 1..47): Explosive welding flash-forward!
    if action == "hook_weld" or frame <= 47:
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
        ov["right_hand_target"] = (-26.0 + u_h * 12.0, 248.0 + zig, 51.0 - u_h * 3.0)
        return ov

    # 2) ACT 1: Inspecting cracked front fender (245..330)
    if action == "inspect_fender":
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused" if frame < 300 else "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk" if frame < 305 else "confident_gap"
        ov["mouth_open"] = 0.0 if frame < 305 else 0.22
        ov["eye_gaze_x"] = -0.40
        ov["eye_gaze_y"] = 0.24 if frame < 300 else 0.0
        ov["head_tilt"] = -0.06 if frame < 300 else 0.02
        ov["right_hand_target"] = (-24.0, 252.0 + breath * 3.0, 48.0)
        ov["left_hand_target"] = (-54.0, 276.0, 26.0)
        return ov

    # 3) ACT 2A: Holding real 3D Steel Repair Plate at LOC 5 (442..478)
    if action == "grab_plate":
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -4.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["right_hand_target"] = (-16.0, 238.0 + breath * 4.0, 48.0)
        ov["left_hand_target"] = (-44.0, 240.0 + breath * 4.0, 44.0)
        return ov

    # 4) ACT 2B: Holding real 3D Chrome Wrench at LOC 3 Workbench (628..660)
    if action == "workbench_prep":
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.14
        ov["right_hand_target"] = (-14.0, 232.0 + breath * 4.0, 48.0)
        ov["left_hand_target"] = (-52.0, 268.0, 28.0)
        return ov

    # 5) ACT 2C: Opening Argon valve & activating MIG welder at LOC 4 (728..778)
    if action == "welder_prep":
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        twist = math.sin(frame * 0.42) * 7.0
        ov["right_hand_target"] = (-16.0 + twist, 224.0, 48.0)
        ov["left_hand_target"] = (-50.0, 260.0, 32.0)
        return ov

    # 6) ACT 3: Checking Jack Stands & Ground Clamp (820..950)
    if action in ("check_jack", "clip_clamp"):
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -5.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["head_tilt"] = -0.10
        ov["eye_gaze_y"] = 0.28
        ov["right_hand_target"] = (-20.0, 290.0, 44.0)
        ov["left_hand_target"] = (-56.0, 284.0, 30.0)
        return ov

    # 7) ACT 3B: Pulling Brass Goggles Down (985..1080)
    if action in ("goggles_pull", "weld_ready"):
        if frame < 995:
            ov["hat_lift_y"] = 0.0
            ov["hat_tilt"] = -6.0
        elif frame <= 1045:
            ov["hat_lift_y"] = interpolate(frame, [995, 1006, 1034, 1045], [0.0, 6.0, -88.0, -92.0], easing=Easing.in_out_cubic)
            ov["hat_tilt"] = interpolate(frame, [995, 1034, 1045], [-6.0, -1.0, 0.0], easing=Easing.in_out_quad)
        else:
            ov["hat_lift_y"] = -92.0
            ov["hat_tilt"] = 0.0

        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "smirk"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.20

        if 988 <= frame <= 1052:
            lx = interpolate(frame, [988, 1008, 1036, 1052], [-54.0, -34.0, -30.0, -58.0])
            ly = interpolate(frame, [988, 1008, 1036, 1052], [285.0, 108.0, 142.0, 240.0])
            lz = interpolate(frame, [988, 1008, 1036, 1052], [24.0, 42.0, 44.0, 32.0])
            ov["left_hand_target"] = (lx, ly, lz)
        else:
            ov["left_hand_target"] = (-66.0, 250.0, 32.0)

        rx = interpolate(frame, [985, 1035, 1080], [20.0, -16.0, -34.0], easing=Easing.in_out_quad)
        ry = interpolate(frame, [985, 1035, 1080], [275.0, 256.0, 248.0], easing=Easing.in_out_quad)
        rz = interpolate(frame, [985, 1035, 1080], [36.0, 48.0, 54.0], easing=Easing.in_out_quad)
        ov["right_hand_target"] = (rx, ry, rz)
        return ov

    # 8) ACT 4 (LAST 30 SECONDS): FRONT -> SIDE -> REAR WELDING!
    if action in ("weld_front", "weld_side", "weld_rear"):
        ov["hat_lift_y"] = -92.0
        ov["hat_tilt"] = 0.0
        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "grit_teeth"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.22
        ov["head_tilt"] = -0.05 + breath * 0.015

        if action == "weld_front":
            u_w = max(0.0, min(1.0, (frame - FRONT_ARC_START) / float(max(1, FRONT_ARC_END - FRONT_ARC_START))))
        elif action == "weld_side":
            u_w = max(0.0, min(1.0, (frame - SIDE_ARC_START) / float(max(1, SIDE_ARC_END - SIDE_ARC_START))))
        else:
            u_w = max(0.0, min(1.0, (frame - REAR_ARC_START) / float(max(1, REAR_ARC_END - REAR_ARC_START))))

        zig = math.sin(frame * 1.15) * 3.0
        ov["left_hand_target"] = (-68.0, 252.0, 32.0)
        ov["right_hand_target"] = (-34.0 + u_w * 26.0, 248.0 + zig, 54.0 - u_w * 8.0)
        return ov

    # 9) FINAL PAYOFF (1749..1800): Goggles Push-Up & Proud Sunset Smile!
    if frame <= 1775:
        ov["hat_lift_y"] = interpolate(frame, [1749, 1756, 1768, 1775], [-92.0, -86.0, 5.0, 0.0], easing=Easing.in_out_cubic)
        ov["hat_tilt"] = interpolate(frame, [1749, 1768, 1775], [0.0, -6.5, -6.0], easing=Easing.in_out_quad)
    else:
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0

    ov["eyes"] = "honey_oval"
    ov["eyebrows"] = "happy"
    ov["mouth"] = "confident_gap"
    ov["mouth_open"] = 0.36
    ov["eye_gaze_x"] = -0.08
    ov["eye_gaze_y"] = 0.0
    ov["right_hand_target"] = (40.0, 282.0, 30.0)
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
