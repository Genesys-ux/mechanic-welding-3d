"""
export_camera_sync.py — Stage 1 (Blender Headless):
Builds the camera rig and `Empty_Mechanic`, computes the exact relative 360° view angle
between the active camera and `Empty_Mechanic`'s facing direction on each target frame,
and exports `output/camera_sync.json` for Stage 2 (`render_char_25d.py`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from camera_rig import build_cinematic_camera_rig  # noqa: E402
from config import (  # noqa: E402
    CAMERA_SYNC_PATH,
    DIAGNOSTIC_FRAMES,
    FPS,
    FRAME_END,
    FRAME_START,
    MECHANIC_BASE_YAW_DEG,
    MECHANIC_ROOT_POS,
    OUTPUT_DIR,
)
from env_props import get_or_create_collection, link_exclusively  # noqa: E402


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Export 360° Camera-to-Mechanic Sync JSON")
    parser.add_argument("--mode", choices=["debug", "final"], default="debug")
    parser.add_argument("--start", type=int, default=FRAME_START)
    parser.add_argument("--end", type=int, default=FRAME_END)
    return parser.parse_args(extra)


def create_animated_mechanic_empty() -> bpy.types.Object:
    """
    Create `Empty_Mechanic` at MECHANIC_ROOT_POS with subtle natural torso yaw across beats:
      - Beats 1 & 2: angled toward front-left fender (+36 deg)
      - Beat 3: follows weld pass along fender (+32 -> +22 deg)
      - Beat 4: turns proudly toward the 3/4 camera (+58 deg) for a clear confident smile!
    """
    col = get_or_create_collection("Col_Mechanic_Character")
    emp = bpy.data.objects.new("Empty_Mechanic", None)
    emp.empty_display_type = "SINGLE_ARROW"
    emp.empty_display_size = 0.35
    emp.location = MECHANIC_ROOT_POS
    link_exclusively(emp, col)

    yaw_keys = [
        (1,   math.radians(MECHANIC_BASE_YAW_DEG)),
        (85,  math.radians(MECHANIC_BASE_YAW_DEG + 4.0)),
        (113, math.radians(32.0)),
        (155, math.radians(28.0)),
        (203, math.radians(22.0)),
        (232, math.radians(56.0)),
        (240, math.radians(58.0)),
        (264, math.radians(56.0)),
    ]
    for f, rz in yaw_keys:
        emp.rotation_euler = (0.0, 0.0, rz)
        emp.keyframe_insert(data_path="rotation_euler", frame=f)

    return emp


def compute_character_turnaround_angle(cam_pos: Vector, mech_mat) -> float:
    """
    Compute 0..360° angle matching `MekanikMudaCharacter` convention:
      0°   = Front (Camera directly in front of Empty_Mechanic's +Y forward axis)
      90°  = Right Side (Mechanic faces screen-right)
      180° = Back (Camera behind Mechanic)
      270° = Left Side (Mechanic faces screen-left)
      315° = 3/4 Left (Mechanic faces screen-left toward car fender, 3/4 front visible!)
    """
    mech_pos = mech_mat.translation
    fwd_3d = mech_mat.to_3x3() @ Vector((0.0, 1.0, 0.0))
    fwd_xy = Vector((fwd_3d.x, fwd_3d.y))
    if fwd_xy.length < 1e-6:
        fwd_xy = Vector((0.0, 1.0))
    else:
        fwd_xy.normalize()

    to_cam = Vector((cam_pos.x - mech_pos.x, cam_pos.y - mech_pos.y))
    if to_cam.length < 1e-6:
        to_cam = fwd_xy.copy()
    else:
        to_cam.normalize()

    dot = max(-1.0, min(1.0, fwd_xy.x * to_cam.x + fwd_xy.y * to_cam.y))
    cross = fwd_xy.x * to_cam.y - fwd_xy.y * to_cam.x
    deg = (-math.degrees(math.atan2(cross, dot))) % 360.0
    return round(deg, 3)


def main() -> None:
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END

    mech_empty = create_animated_mechanic_empty()
    cam_data = build_cinematic_camera_rig(scene)
    cam_obj = cam_data["camera"]

    if args.mode == "debug":
        target_frames: List[int] = list(DIAGNOSTIC_FRAMES)
    else:
        target_frames = list(range(args.start, args.end + 1))

    frames_payload: Dict[str, Dict[str, float]] = {}
    for f in target_frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        cam_eval = cam_obj.evaluated_get(deps)
        mech_eval = mech_empty.evaluated_get(deps)

        ang = compute_character_turnaround_angle(cam_eval.matrix_world.translation, mech_eval.matrix_world)
        frames_payload[str(f)] = {
            "angle": ang,
            "cam_x": round(cam_eval.matrix_world.translation.x, 4),
            "cam_y": round(cam_eval.matrix_world.translation.y, 4),
            "cam_z": round(cam_eval.matrix_world.translation.z, 4),
            "mech_yaw_deg": round(math.degrees(mech_eval.matrix_world.to_euler().z), 3),
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sync_doc = {
        "mode": args.mode,
        "fps": FPS,
        "target_frames": target_frames,
        "frames": frames_payload,
    }
    CAMERA_SYNC_PATH.write_text(json.dumps(sync_doc, indent=2), encoding="utf-8")
    print(f"[CameraSync] Exported {len(target_frames)} frame angles -> {CAMERA_SYNC_PATH}")
    for fk in list(frames_payload.keys())[:6]:
        print(f"  Frame {fk}: angle={frames_payload[fk]['angle']}°")


if __name__ == "__main__":
    main()
