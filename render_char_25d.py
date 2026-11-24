"""
render_char_25d.py — Stage 2 (System Python Runner with resvg-py & Pillow):
Reads `output/camera_sync.json`, renders 100% authentic 2.5D transparent PNG sprites
directly from `tr/mekanik_muda_character.py` (`MekanikMudaCharacter`) at `scale=2.0`,
saves `output/char_frames/char_XXXX.png`, and exports normalized right-hand (`raHnd`)
billboard coordinates `(u, v)` to `output/char_hand_sync.json`.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import resvg_py

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    CAMERA_SYNC_PATH,
    CHAR_BASE_HEIGHT_PX,
    CHAR_BASE_WIDTH_PX,
    CHAR_FRAMES_DIR,
    CHAR_HAND_SYNC_PATH,
    FPS,
    WELD_ARC_END,
    WELD_ARC_START,
)
from tr.mekanik_muda_character import Easing, MekanikMudaCharacter, interpolate  # noqa: E402


def build_character_beat_overrides(frame: int) -> Dict[str, Any]:
    """
    Choreograph natural 4-Beat 2.5D pose, goggles pull/push, hand IK & facial expressions:
      - Beat 1 (1-60):   Idle breathing, confident gap-smile, goggles up on forehead
      - Beat 2 (61-110): Left hand pulls goggles down over eyes (hat_lift_y: 0 -> -92),
                         focused eyes/mouth, hands move forward to car fender & weld seam
      - Beat 3 (111-205): Focused welding pass with micro zig-zag weave on right hand
      - Beat 4 (206-264): Torch pulls back, left hand pushes goggles up to forehead,
                         wide proud confident gap-tooth smile & satisfied nod!
    """
    ov: Dict[str, Any] = {
        "animation": "idle",
        "ground_shadow": False,
        "pose": "ready",
        "prop": "none",
    }

    # 1) Goggles Position (`hat_lift_y`: 0.0 = forehead, -92.0 = pulled down over eyes!)
    if frame < 72:
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0
    elif frame <= 89:
        ov["hat_lift_y"] = interpolate(frame, [72, 76, 85, 89], [0.0, 6.0, -88.0, -92.0], easing=Easing.in_out_cubic)
        ov["hat_tilt"] = interpolate(frame, [72, 85, 89], [-6.0, -0.5, 0.0], easing=Easing.in_out_quad)
    elif frame <= 219:
        ov["hat_lift_y"] = -92.0
        ov["hat_tilt"] = 0.0
    elif frame <= 235:
        ov["hat_lift_y"] = interpolate(frame, [219, 223, 232, 235], [-92.0, -86.0, 5.0, 0.0], easing=Easing.in_out_cubic)
        ov["hat_tilt"] = interpolate(frame, [219, 232, 235], [0.0, -6.5, -6.0], easing=Easing.in_out_quad)
    else:
        ov["hat_lift_y"] = 0.0
        ov["hat_tilt"] = -6.0

    # 2) Facial Expressions, Gaze & Head Tilt
    if frame <= 70:
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "thick_arch"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.08
        ov["eye_gaze_x"] = -0.35
        ov["eye_gaze_y"] = 0.12
    elif frame <= 224:
        ov["eyes"] = "focused"
        ov["eyebrows"] = "angry"
        ov["mouth"] = "grit_teeth" if WELD_ARC_START <= frame <= WELD_ARC_END else "smirk"
        ov["mouth_open"] = 0.0
        ov["eye_gaze_x"] = -0.45
        ov["eye_gaze_y"] = 0.22
        if 76 <= frame <= 92:
            ov["head_tilt"] = interpolate(frame, [76, 85, 92], [0.0, -0.09, -0.04], easing=Easing.in_out_quad)
        elif WELD_ARC_START <= frame <= WELD_ARC_START + 6:
            # Subtle spark-ignition flinch!
            ov["head_tilt"] = 0.05
            ov["squash_x"] = 1.03
            ov["squash_y"] = 0.97
        else:
            ov["head_tilt"] = -0.05
    else:
        ov["eyes"] = "honey_oval"
        ov["eyebrows"] = "happy"
        ov["mouth"] = "confident_gap"
        ov["mouth_open"] = 0.36
        ov["eye_gaze_x"] = -0.10
        ov["eye_gaze_y"] = 0.0
        if 238 <= frame <= 256:
            ov["head_tilt"] = interpolate(frame, [238, 246, 256], [0.02, -0.08, 0.01], easing=Easing.in_out_quad)

    # 3) Left Hand (`laHnd`): Idle -> Pull Goggles Down (72-90) -> Brace on Fender -> Push Goggles Up (218-235)
    if 68 <= frame <= 92:
        lx = interpolate(frame, [68, 76, 85, 92], [-54.0, -34.0, -30.0, -58.0])
        ly = interpolate(frame, [68, 76, 85, 92], [290.0, 108.0, 142.0, 235.0])
        lz = interpolate(frame, [68, 76, 85, 92], [24.0, 42.0, 44.0, 34.0])
        ov["left_hand_target"] = (lx, ly, lz)
    elif 93 <= frame <= 216:
        lx = interpolate(frame, [93, 106, 206, 216], [-58.0, -68.0, -68.0, -52.0])
        ly = interpolate(frame, [93, 106, 206, 216], [235.0, 252.0, 252.0, 220.0])
        ov["left_hand_target"] = (lx, ly, 32.0)
    elif 217 <= frame <= 238:
        lx = interpolate(frame, [217, 223, 232, 238], [-52.0, -30.0, -34.0, -54.0])
        ly = interpolate(frame, [217, 223, 232, 238], [220.0, 142.0, 106.0, 288.0])
        lz = interpolate(frame, [217, 223, 232, 238], [32.0, 44.0, 42.0, 24.0])
        ov["left_hand_target"] = (lx, ly, lz)

    # 4) Right Hand (`raHnd`, Foreground Torch Hand!):
    # At angle ~315° (3/4 Left), negative X + positive Z reaches forward-left toward the 3D car fender!
    if frame <= 65:
        ov["right_hand_target"] = (42.0, 288.0, 30.0)
    elif frame < WELD_ARC_START:
        rx = interpolate(frame, [65, 85, 108, WELD_ARC_START], [42.0, 8.0, -32.0, -34.0], easing=Easing.in_out_quad)
        ry = interpolate(frame, [65, 85, 108, WELD_ARC_START], [288.0, 266.0, 250.0, 248.0], easing=Easing.in_out_quad)
        rz = interpolate(frame, [65, 85, 108, WELD_ARC_START], [30.0, 40.0, 52.0, 54.0], easing=Easing.in_out_quad)
        ov["right_hand_target"] = (rx, ry, rz)
    elif frame <= WELD_ARC_END:
        u_w = (frame - WELD_ARC_START) / float(WELD_ARC_END - WELD_ARC_START)
        zig = math.sin((frame - WELD_ARC_START) * 1.2) * 3.2
        rx = -34.0 + u_w * 26.0
        ry = 248.0 + zig
        rz = 54.0 - u_w * 8.0
        ov["right_hand_target"] = (rx, ry, rz)
    else:
        rx = interpolate(frame, [WELD_ARC_END + 1, 216, 236, 264], [-8.0, 18.0, 44.0, 44.0], easing=Easing.out_cubic)
        ry = interpolate(frame, [WELD_ARC_END + 1, 216, 236, 264], [246.0, 232.0, 282.0, 284.0], easing=Easing.out_cubic)
        rz = interpolate(frame, [WELD_ARC_END + 1, 216, 236, 264], [46.0, 42.0, 30.0, 30.0], easing=Easing.out_cubic)
        ov["right_hand_target"] = (rx, ry, rz)

    return ov


def project_ra_hand_uv(pose: Any, angle_deg: float) -> Tuple[float, float]:
    """
    Exact 2D projection of `pose.raHnd` onto the `240 x 520` character canvas,
    returning normalized `(u, v)` (`u` in [0..1] left->right, `v` in [0..1] bottom->top).
    """
    rad = math.radians(angle_deg % 360.0)
    s, c = math.sin(rad), math.cos(rad)
    lean = float(pose.torsoLeanZ or 0.0)
    sh_dx = 110.0 * math.sin(lean)
    sh_dy = 110.0 * (1.0 - math.cos(lean))

    px = 120.0 + float(pose.raHnd.x) * c + float(pose.raHnd.z) * s + sh_dx * 0.35
    py = float(pose.raHnd.y) + sh_dy * 0.35

    sq_x = float(pose.squashX or 1.0)
    sq_y = float(pose.squashY or 1.0)
    px = 120.0 + (px - 120.0) * sq_x
    py = 476.0 + (py - 476.0) * sq_y

    u = max(0.0, min(1.0, px / float(CHAR_BASE_WIDTH_PX)))
    v = max(0.0, min(1.0, 1.0 - (py / float(CHAR_BASE_HEIGHT_PX))))
    return (round(u, 5), round(v, 5))


def main() -> None:
    if not CAMERA_SYNC_PATH.exists():
        raise FileNotFoundError(f"Missing {CAMERA_SYNC_PATH} — run export_camera_sync.py first!")

    sync_data = json.loads(CAMERA_SYNC_PATH.read_text(encoding="utf-8"))
    frames_map: Dict[str, Dict[str, float]] = sync_data["frames"]
    target_frames = [int(f) for f in sync_data["target_frames"]]

    CHAR_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    char = MekanikMudaCharacter(scale=2.0, fps=FPS)

    hand_sync: Dict[str, Dict[str, float]] = {}
    for idx, f in enumerate(target_frames):
        angle_deg = float(frames_map[str(f)]["angle"])
        ov = build_character_beat_overrides(f)

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

        if idx % 24 == 0 or idx == len(target_frames) - 1 or len(target_frames) <= 8:
            print(f"[2.5D Render] Frame {f:04d} (angle={angle_deg:6.2f}°, raHnd=({u:.3f},{v:.3f})) -> {out_png.name}", flush=True)

    CHAR_HAND_SYNC_PATH.write_text(json.dumps({"frames": hand_sync}, indent=2), encoding="utf-8")
    print(f"[2.5D Render] Saved {len(target_frames)} sprites & hand sync -> {CHAR_HAND_SYNC_PATH}")


if __name__ == "__main__":
    main()
