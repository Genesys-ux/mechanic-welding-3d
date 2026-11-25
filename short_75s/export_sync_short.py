"""
short_75s/export_sync_short.py — Stage 1 (Blender Headless):
Builds the 30-move continuous camera rig and 6-location `Empty_Mechanic`, computes exact
360° camera-to-mechanic relative angles, and exports `output_short_75s/camera_sync.json`.
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from env_props import get_or_create_collection, link_exclusively  # noqa: E402
from export_camera_sync import compute_character_turnaround_angle  # noqa: E402

from short_75s.camera_continuous_30moves import build_30move_continuous_camera_rig  # noqa: E402
from short_75s.config_short import (  # noqa: E402
    CAMERA_SYNC_PATH,
    DEBUG_FRAMES,
    FPS,
    FRAME_END,
    FRAME_START,
    OUTPUT_DIR,
)
from short_75s.story_beats import eval_character_blocking  # noqa: E402


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Export 75s Short 360° Camera-to-Mechanic Sync JSON")
    parser.add_argument("--mode", choices=["debug", "final"], default="debug")
    parser.add_argument("--frames", type=str, default="", help="Optional comma-separated frame list")
    parser.add_argument("--start", type=int, default=FRAME_START)
    parser.add_argument("--end", type=int, default=FRAME_END)
    return parser.parse_args(extra)


def create_6loc_mechanic_empty(target_frames: List[int]) -> bpy.types.Object:
    col = get_or_create_collection("Col_Mechanic_Character")
    emp = bpy.data.objects.new("Empty_Mechanic", None)
    emp.empty_display_type = "SINGLE_ARROW"
    emp.empty_display_size = 0.35
    link_exclusively(emp, col)

    for f in target_frames:
        pos, yaw_deg, _ = eval_character_blocking(f)
        emp.location = pos
        emp.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
        emp.keyframe_insert(data_path="location", frame=f)
        emp.keyframe_insert(data_path="rotation_euler", frame=f)
    return emp


def main() -> None:
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END

    if args.frames.strip():
        target_frames: List[int] = [int(x.strip()) for x in args.frames.split(",") if x.strip()]
    elif args.mode == "debug":
        target_frames = list(DEBUG_FRAMES)
    else:
        # Include 1 padding frame on both ends so motion-blur subframes NEVER miss a sprite PNG!
        pad_start = max(FRAME_START, args.start - 1)
        pad_end = min(FRAME_END, args.end + 1)
        target_frames = list(range(pad_start, pad_end + 1))

    mech_empty = create_6loc_mechanic_empty(target_frames)
    cam_data = build_30move_continuous_camera_rig(scene, sample_step=3, extra_frames=target_frames)
    cam_obj = cam_data["camera"]

    frames_payload: Dict[str, Dict[str, object]] = {}
    for f in target_frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        cam_eval = cam_obj.evaluated_get(deps)
        mech_eval = mech_empty.evaluated_get(deps)
        _, yaw_deg, act_tag = eval_character_blocking(f)
        ang = compute_character_turnaround_angle(cam_eval.matrix_world.translation, mech_eval.matrix_world)
        frames_payload[str(f)] = {
            "angle": ang,
            "action": act_tag,
            "mech_yaw_deg": round(yaw_deg, 2),
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sync_doc = {
        "mode": args.mode,
        "fps": FPS,
        "target_frames": target_frames,
        "frames": frames_payload,
    }
    CAMERA_SYNC_PATH.write_text(json.dumps(sync_doc, indent=2), encoding="utf-8")
    print(f"[Short75s Sync] Exported {len(target_frames)} frames -> {CAMERA_SYNC_PATH}")


if __name__ == "__main__":
    main()
