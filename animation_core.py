"""
animation_core.py — Stage 3 3D Prop & Welding Torch Synchronization:
Reads normalized 2.5D hand coordinates (`raHnd`) from `output/char_hand_sync.json`,
projects them onto the live camera-facing `Char_Billboard` plane in 3D space, and
synchronizes the 3D Welding Torch, flexible Bezier welding cable, flickering arc light,
and sparks so:
  - `Empty_TorchTip` (copper nozzle & electrode tip) touches the exact raycasted weld
    seam on the red car fender (`0.0mm` gap!) across Frames 111–205
  - `Prop_WeldingTorch` yellow grip handle sits naturally inside Mekanik Muda's right hand!
"""

from __future__ import annotations

import json
import math
from typing import Dict, Optional

import bpy
from mathutils import Euler, Quaternion, Vector

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


def _aim_torch_tip_quat(aim_dir: Vector, q_swan_fix: Quaternion) -> Quaternion:
    """
    Compute world quaternion for `Prop_WeldingTorch` so `torch_tip_local` `(0, 0.208, -0.045)`
    points strictly along `aim_dir` (`rot_quat @ torch_tip_local == aim_dir.normalized() * L`).
    """
    d = aim_dir.normalized() if aim_dir.length > 1e-5 else Vector((-0.2, 0.96, 0.18)).normalized()
    return d.to_track_quat("Y", "Z") @ q_swan_fix


def animate_torch_and_cable_sync(
    scene: bpy.types.Scene,
    billboard_obj: bpy.types.Object,
    torch_obj: bpy.types.Object,
    cable_mid_sag: Optional[bpy.types.Object] = None,
) -> None:
    """
    Synchronize `Prop_WeldingTorch` (`Empty_TorchTip` at local `(0, 0.208, -0.045)`) with:
      - `raHnd` exported by `render_char_25d.py` (`output/char_hand_sync.json`)
      - Raycasted Car Fender 3D Weld Seam (`eval_weld_seam_point(u)`) during Frames 111..205!
    """
    if not CHAR_HAND_SYNC_PATH.exists():
        raise FileNotFoundError(f"Missing {CHAR_HAND_SYNC_PATH} — run render_char_25d.py first!")

    hand_doc = json.loads(CHAR_HAND_SYNC_PATH.read_text(encoding="utf-8"))
    hand_frames: Dict[str, Dict[str, float]] = hand_doc["frames"]
    sorted_frames = sorted(int(k) for k in hand_frames.keys())

    torch_tip_local = Vector((0.0, 0.208, -0.045))
    q_swan_fix = torch_tip_local.normalized().rotation_difference(Vector((0.0, 1.0, 0.0)))
    torch_obj.rotation_mode = "XYZ"
    prev_euler: Optional[Euler] = None

    for f in sorted_frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        bb_eval = billboard_obj.evaluated_get(deps)

        h_entry = hand_frames[str(f)]
        hand_w = billboard_uv_to_world(bb_eval, float(h_entry["u"]), float(h_entry["v"]), depth_offset=-0.025)

        if 111 <= f <= 205:
            # Active Welding Pass: lock `Empty_TorchTip` 100% flush onto the raycasted car fender seam
            # while aligning the yellow torch handle directly back into Mekanik Muda's 2.5D hand!
            u_seam = max(0.0, min(1.0, (f - WELD_ARC_START) / float(WELD_ARC_END - WELD_ARC_START)))
            seam_pt = eval_weld_seam_point(u_seam)

            aim_dir = seam_pt - hand_w
            rot_quat = _aim_torch_tip_quat(aim_dir, q_swan_fix)
            rot_mat = rot_quat.to_matrix()

            torch_pos = seam_pt - (rot_mat @ torch_tip_local)
        elif 96 <= f < 111:
            alpha = (f - 96.0) / 15.0
            seam_start = eval_weld_seam_point(0.0)
            aim_dir = seam_start - hand_w
            rot_quat = _aim_torch_tip_quat(aim_dir, q_swan_fix)
            rot_mat = rot_quat.to_matrix()
            weld_grip_pos = seam_start - (rot_mat @ torch_tip_local)
            torch_pos = hand_w.lerp(weld_grip_pos, alpha)
        elif 205 < f <= 220:
            alpha = (f - 205.0) / 15.0
            seam_end = eval_weld_seam_point(1.0)
            aim_dir = seam_end - hand_w
            rot_quat = _aim_torch_tip_quat(aim_dir, q_swan_fix)
            rot_mat = rot_quat.to_matrix()
            weld_grip_pos = seam_end - (rot_mat @ torch_tip_local)
            torch_pos = weld_grip_pos.lerp(hand_w, alpha)
        else:
            fender_aim = (eval_weld_seam_point(0.2) + Vector((-0.08, -0.06, -0.10))) - hand_w
            rot_quat = _aim_torch_tip_quat(fender_aim, q_swan_fix)
            torch_pos = hand_w

        cur_euler = rot_quat.to_euler("XYZ", prev_euler) if prev_euler is not None else rot_quat.to_euler("XYZ")
        prev_euler = cur_euler.copy()

        torch_obj.location = torch_pos
        torch_obj.rotation_euler = cur_euler
        torch_obj.keyframe_insert(data_path="location", frame=f)
        torch_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        if cable_mid_sag is not None:
            t_loc = torch_obj.location
            cable_mid_sag.location = (
                0.32 + (t_loc.x + 0.24) * 0.25,
                -0.96 + (t_loc.y + 0.65) * 0.25,
                0.15 + max(0.0, (t_loc.z - 0.58) * 0.18),
            )
            cable_mid_sag.keyframe_insert(data_path="location", frame=f)

    _smooth_obj_fcurves(torch_obj)
    if cable_mid_sag is not None:
        _smooth_obj_fcurves(cable_mid_sag)

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()
