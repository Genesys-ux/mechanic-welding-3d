"""
short_75s/camera_continuous_30moves.py — Continuous 3D Virtual Camera Rig (30 Moves,
Exponential Ease-In-Out, Subtle Overshoot Deceleration, Whip-Pan Motion Blur & Zoom Transitions).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

import bpy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from env_props import get_or_create_collection, link_exclusively  # noqa: E402
from vfx_lighting import add_restricted_noise_modifier  # noqa: E402

from short_75s.config_short import (  # noqa: E402
    CLIMAX_ARC_END,
    CLIMAX_ARC_START,
    FRAME_END,
    FRAME_START,
    HOOK_ARC_END,
    HOOK_ARC_START,
)
from short_75s.story_beats import eval_camera_state  # noqa: E402


def build_30move_continuous_camera_rig(
    scene: bpy.types.Scene,
    sample_step: int = 2,
    extra_frames: Optional[Iterable[int]] = None,
) -> Dict[str, bpy.types.Object]:
    """
    Build the continuous 3D virtual camera (`Camera_Main`) across all 1,800 frames (75s)
    implementing all 30 choreographed moves (`CM01`..`CM30`) with:
      - Wide-angle travel lens (`18-26mm`) & snappy Zoom-In/Zoom-Out transitions (`48-64mm`)
      - Exponential ease-in-out & smooth deceleration with subtle overshoot
      - Keyframed motion blur (`motion_blur_shutter`) active during fast whip-pan sweeps
      - Subtle handheld micro-shake during Hook & Climax welding bursts
    """
    cam_col = get_or_create_collection("Col_Camera_Rig")

    dolly = bpy.data.objects.new("Cam_Dolly", None)
    dolly.empty_display_type = "SPHERE"
    dolly.empty_display_size = 0.08
    link_exclusively(dolly, cam_col)

    target = bpy.data.objects.new("Cam_FocusTarget", None)
    target.empty_display_type = "PLAIN_AXES"
    target.empty_display_size = 0.12
    link_exclusively(target, cam_col)

    tracker = bpy.data.objects.new("Cam_Tracker", None)
    tracker.parent = dolly
    tracker.location = (0.0, 0.0, 0.0)
    link_exclusively(tracker, cam_col)

    tt = tracker.constraints.new(type="TRACK_TO")
    tt.target = target
    tt.track_axis = "TRACK_NEGATIVE_Z"
    tt.up_axis = "UP_Y"

    cam_data = bpy.data.cameras.new("Camera_Main_Data")
    cam_data.clip_start = 0.08
    cam_data.clip_end = 80.0
    # Vertical 9:16 sensor fit so focal lengths (`18-64mm`) feel genuinely wide-angle & snappy!
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_width = 36.0
    cam_data.sensor_height = 36.0

    cam_obj = bpy.data.objects.new("Camera_Main", cam_data)
    cam_obj.parent = tracker
    cam_obj.location = (0.0, 0.0, 0.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    link_exclusively(cam_obj, cam_col)
    scene.camera = cam_obj

    # Enable clean EEVEE Next motion blur (shutter animated to 0.0 on still shots, 0.45 on whip-pans!)
    scene.render.use_motion_blur = True
    if hasattr(scene.eevee, "motion_blur_steps"):
        scene.eevee.motion_blur_steps = 2

    frames_to_bake = set(range(FRAME_START, FRAME_END + 1, max(1, sample_step)))
    frames_to_bake.add(FRAME_START)
    frames_to_bake.add(FRAME_END)
    if extra_frames:
        frames_to_bake.update(int(f) for f in extra_frames)

    for f in sorted(frames_to_bake):
        st = eval_camera_state(f)
        dolly.location = st["pos"]
        dolly.keyframe_insert(data_path="location", frame=f)

        target.location = st["tgt"]
        target.keyframe_insert(data_path="location", frame=f)

        cam_data.lens = st["lens"]
        cam_data.keyframe_insert(data_path="lens", frame=f)

        cam_obj.rotation_euler = (0.0, 0.0, math.radians(st["roll_deg"]))
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        # Clean motion blur during fast sweeps & whip-pans
        scene.render.motion_blur_shutter = round(st["blur"], 3)
        scene.render.keyframe_insert(data_path="motion_blur_shutter", frame=f)

    # Subtle energetic micro-shake strictly during Hook & Climax welding arcs
    for w0, w1 in ((HOOK_ARC_START, HOOK_ARC_END), (CLIMAX_ARC_START, CLIMAX_ARC_END)):
        add_restricted_noise_modifier(cam_obj, "rotation_euler", float(w0), float(w1), scale=1.5, strength=0.0045, phase=3.1, index=0)
        add_restricted_noise_modifier(cam_obj, "rotation_euler", float(w0), float(w1), scale=1.8, strength=0.0038, phase=14.8, index=2)

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()

    return {
        "camera": cam_obj,
        "dolly": dolly,
        "target": target,
    }
