"""
animation_core.py — Stage 3 3D Prop & Welding Torch Synchronization:
Reads normalized 2.5D hand coordinates (`raHnd`) from `output/char_hand_sync.json`,
projects them onto the live camera-facing `Char_Billboard` plane in 3D space, and
synchronizes the 3D Welding Torch, flexible Bezier welding cable, flickering arc light,
and sparks with both Mekanik Muda's right hand and the 3D car fender seam (Frames 111-205)!
"""

from __future__ import annotations

import json
import math
from typing import Dict, Optional

import bpy
from mathutils import Matrix, Vector

from config import (
    CHAR_BILLBOARD_HEIGHT,
    CHAR_BILLBOARD_WIDTH,
    CHAR_HAND_SYNC_PATH,
    CHAR_Z_BOTTOM_OFFSET,
    FRAME_START,
    WELD_ARC_END,
    WELD_ARC_START,
)
from vfx_lighting import _get_action_fcurves, eval_weld_seam_point


def _smooth_obj_fcurves(obj: bpy.types.Object) -> None:
    for fc in _get_action_fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


def billboard_uv_to_world(billboard_eval: bpy.types.Object, u: float, v: float, depth_offset: float = -0.025) -> Vector:
    """
    Convert normalized `(u, v)` sprite coordinates (`[0..1] x [0..1]`) into 3D world space
    on `Char_Billboard` (with a slight `-Y` camera-side offset so the 3D torch stays cleanly
    in front of the sprite card).
    """
    lx = (u - 0.5) * CHAR_BILLBOARD_WIDTH
    lz = CHAR_Z_BOTTOM_OFFSET + v * CHAR_BILLBOARD_HEIGHT
    return billboard_eval.matrix_world @ Vector((lx, depth_offset, lz))


def animate_torch_and_cable_sync(
    scene: bpy.types.Scene,
    billboard_obj: bpy.types.Object,
    torch_obj: bpy.types.Object,
    cable_mid_sag: Optional[bpy.types.Object] = None,
) -> None:
    """
    Synchronize `Prop_WeldingTorch` (`Empty_TorchTip` at local `(0, 0.208, -0.045)`) with:
      - `raHnd` exported by `render_char_25d.py` (`output/char_hand_sync.json`)
      - Car Fender 3D Weld Seam (`WELD_SEAM_START -> MID -> END`) during Frames 111..205!
    """
    if not CHAR_HAND_SYNC_PATH.exists():
        raise FileNotFoundError(f"Missing {CHAR_HAND_SYNC_PATH} — run render_char_25d.py first!")

    hand_doc = json.loads(CHAR_HAND_SYNC_PATH.read_text(encoding="utf-8"))
    hand_frames: Dict[str, Dict[str, float]] = hand_doc["frames"]
    sorted_frames = sorted(int(k) for k in hand_frames.keys())

    torch_tip_local = Vector((0.0, 0.208, -0.045))
    torch_obj.rotation_mode = "XYZ"

    for f in sorted_frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        bb_eval = billboard_obj.evaluated_get(deps)

        h_entry = hand_frames[str(f)]
        hand_w = billboard_uv_to_world(bb_eval, float(h_entry["u"]), float(h_entry["v"]), depth_offset=-0.025)

        if 111 <= f <= 205:
            # Active Welding Pass: lock `Empty_TorchTip` directly onto the 3D car fender seam
            # while orienting the torch handle right back toward Mekanik Muda's 2.5D hand!
            u_seam = max(0.0, min(1.0, (f - WELD_ARC_START) / float(WELD_ARC_END - WELD_ARC_START)))
            zig = math.sin((f - WELD_ARC_START) * 1.15) * 0.004
            seam_pt = eval_weld_seam_point(u_seam) + Vector((0.0, -0.003, zig))

            aim_dir = seam_pt - hand_w
            if aim_dir.length < 1e-4:
                aim_dir = Vector((-0.3, 0.9, 0.1))
            rot_quat = aim_dir.normalized().to_track_quat("Y", "Z")
            rot_mat = rot_quat.to_matrix()

            torch_pos = seam_pt - (rot_mat @ torch_tip_local)
            torch_obj.location = torch_pos
            torch_obj.rotation_euler = rot_quat.to_euler("XYZ")
        elif 96 <= f < 111:
            # Smooth approach transition from 2.5D hand toward weld seam start
            alpha = (f - 96.0) / 15.0
            seam_start = eval_weld_seam_point(0.0) + Vector((0.0, -0.02, 0.01))
            aim_dir = (seam_start - hand_w).normalized()
            rot_quat = aim_dir.to_track_quat("Y", "Z")
            rot_mat = rot_quat.to_matrix()
            weld_grip_pos = seam_start - (rot_mat @ torch_tip_local)

            torch_obj.location = hand_w.lerp(weld_grip_pos, alpha)
            torch_obj.rotation_euler = rot_quat.to_euler("XYZ")
        elif 205 < f <= 220:
            # Smooth pullback transition from weld seam end back to 2.5D hand hold
            alpha = (f - 205.0) / 15.0
            seam_end = eval_weld_seam_point(1.0) + Vector((0.0, -0.03, 0.02))
            aim_dir = (seam_end - hand_w).normalized()
            rot_quat = aim_dir.to_track_quat("Y", "Z")
            rot_mat = rot_quat.to_matrix()
            weld_grip_pos = seam_end - (rot_mat @ torch_tip_local)

            torch_obj.location = weld_grip_pos.lerp(hand_w, alpha)
            torch_obj.rotation_euler = rot_quat.to_euler("XYZ")
        else:
            # Idle / Goggle Prep / Payoff: Torch handle locked cleanly on Mekanik Muda's 2.5D hand!
            fender_aim = (eval_weld_seam_point(0.2) + Vector((-0.10, -0.08, -0.18))) - hand_w
            rot_quat = fender_aim.normalized().to_track_quat("Y", "Z")
            torch_obj.location = hand_w
            torch_obj.rotation_euler = rot_quat.to_euler("XYZ")

        torch_obj.keyframe_insert(data_path="location", frame=f)
        torch_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        if cable_mid_sag is not None:
            t_loc = torch_obj.location
            cable_mid_sag.location = (
                0.34 + (t_loc.x + 0.14) * 0.25,
                -0.96 + (t_loc.y + 0.65) * 0.25,
                0.16 + max(0.0, (t_loc.z - 0.60) * 0.18),
            )
            cable_mid_sag.keyframe_insert(data_path="location", frame=f)

    _smooth_obj_fcurves(torch_obj)
    if cable_mid_sag is not None:
        _smooth_obj_fcurves(cable_mid_sag)

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()
