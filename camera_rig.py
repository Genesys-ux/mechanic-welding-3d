"""
camera_rig.py — Fast-Paced Cinematic Single-Take / Whip-Zoom Camera System
Combines:
  1) 3D Bezier Travel Path (`Cam_Rig_Path`) + `Follow Path` constraint on `Cam_Dolly`
  2) Dynamic `Cam_FocusTarget` Empty + `Track To` constraint on `Camera_Main`
  3) Aggressive Bezier `Focal Length` whip-zoom transitions (24mm -> 50mm -> 65mm -> 35mm)
  4) Restricted F-Curve `NOISE` micro-camera shake strictly during Welding Beat 3 (113..203)
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import bpy

from config import FRAME_END, FRAME_START, WELD_ARC_END, WELD_ARC_START
from env_props import get_or_create_collection, link_exclusively
from vfx_lighting import _get_action_fcurves, add_restricted_noise_modifier


def _smooth_fcurves(id_data: bpy.types.ID) -> None:
    for fc in _get_action_fcurves(id_data):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


def build_cinematic_camera_rig(scene: bpy.types.Scene) -> Dict[str, bpy.types.Object]:
    """
    Construct the obstacle-free 3D Bezier camera path & focus rig across all 4 Beats:
      - Beat 1 (1-60):   Wide Workshop Establishing Travel -> Whip-Zoom In (24mm -> 50mm)
      - Beat 2 (61-110): Overshoot Settle & 3/4 Front Medium Close-Up Orbit (Frame 85)
      - Beat 3 (111-205): Punch-In Zoom + Dynamic Spark Orbit + Micro Shake (Frame 155)
      - Beat 4 (206-264): Whip-Zoom Pull-Back (64mm -> 35mm) + Heroic Two-Shot Payoff (Frame 240)
    """
    cam_col = get_or_create_collection("Col_Camera_Rig")

    curve_data = bpy.data.curves.new("Cam_Rig_Path_Data", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 36
    curve_data.use_path = True
    curve_data.path_duration = 100

    spline = curve_data.splines.new("BEZIER")
    path_pts: List[Tuple[float, float, float]] = [
        (-3.25, -2.95, 1.54),  # [0] u=0.00: Wide back-left workshop bay start (Frame 1)
        (-2.72, -1.85, 1.40),  # [1] u=0.20: Gliding past tool chest & wrench rack (Frame 20)
        (-2.06, -0.68, 1.24),  # [2] u=0.42: Whip-zoom arrival in 3/4 front corridor (Frame 60)
        (-2.04, -0.38, 1.23),  # [3] u=0.55: 3/4 Front Medium Close-Up on Mechanic & Goggles (Frame 85)
        (-1.98, -0.76, 1.15),  # [4] u=0.78: Dynamic Spark & Welding Arc Action Orbit (Frame 155)
        (-2.35, -1.02, 1.20),  # [5] u=1.00: Heroic Pull-Back Two-Shot of Mechanic + Welded Car (Frame 240..264)
    ]
    spline.bezier_points.add(len(path_pts) - 1)
    for idx, pt in enumerate(path_pts):
        bp = spline.bezier_points[idx]
        bp.co = pt
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    path_obj = bpy.data.objects.new("Cam_Rig_Path", curve_data)
    link_exclusively(path_obj, cam_col)

    dolly = bpy.data.objects.new("Cam_Dolly", None)
    dolly.empty_display_type = "SPHERE"
    dolly.empty_display_size = 0.08
    link_exclusively(dolly, cam_col)

    fp_con = dolly.constraints.new(type="FOLLOW_PATH")
    fp_con.name = "Follow_CameraCurve"
    fp_con.target = path_obj
    fp_con.use_fixed_location = True

    dolly_offset_keys = [
        (1,   0.000),
        (20,  0.205),  # Diagnostic Frame 20: Wide travel past tools & car!
        (58,  0.420),  # Fast arrival
        (66,  0.455),  # Subtle overshoot settle
        (85,  0.548),  # Diagnostic Frame 85: 3/4 Medium Shot on Goggle Pull + Torch!
        (108, 0.590),
        (120, 0.655),  # Punch-in orbit start
        (155, 0.778),  # Diagnostic Frame 155: Sweeping past flying sparks & blue-white arc!
        (203, 0.858),
        (226, 0.985),  # Snappy whip-pullback as torch lifts!
        (240, 0.995),  # Diagnostic Frame 240: Heroic Payoff Two-Shot!
        (264, 1.000),
    ]
    for f, u_val in dolly_offset_keys:
        fp_con.offset_factor = u_val
        dolly.keyframe_insert(data_path='constraints["Follow_CameraCurve"].offset_factor', frame=f)

    target = bpy.data.objects.new("Cam_FocusTarget", None)
    target.empty_display_type = "PLAIN_AXES"
    target.empty_display_size = 0.12
    link_exclusively(target, cam_col)

    target_keys = [
        # Beat 1: Wide bay framing -> converging onto mechanic & front fender
        (1,   (-0.32, -0.45, 0.92)),
        (20,  (-0.26, -0.56, 0.90)),
        (58,  (-0.18, -0.78, 1.06)),
        # Beat 2: Balanced 3/4 framing of Mechanic's upper body, goggles, torch & car fender
        (85,  (-0.16, -0.78, 1.08)),
        (106, (-0.22, -0.68, 1.06)),
        # Beat 3: Hero action framing capturing BOTH blazing torch/sparks AND goggle-clad face!
        (116, (-0.24, -0.66, 1.08)),
        (155, (-0.18, -0.68, 1.09)),
        (203, (-0.12, -0.68, 1.07)),
        # Beat 4: Heroic two-shot framing both smiling mechanic & glowing freshly welded seam!
        (226, (-0.18, -0.70, 1.02)),
        (240, (-0.18, -0.70, 1.02)),
        (264, (-0.16, -0.70, 1.02)),
    ]
    for f, t_pos in target_keys:
        target.location = t_pos
        target.keyframe_insert(data_path="location", frame=f)

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
    cam_data.clip_end = 50.0
    cam_data.sensor_width = 36.0

    cam_obj = bpy.data.objects.new("Camera_Main", cam_data)
    cam_obj.parent = tracker
    cam_obj.location = (0.0, 0.0, 0.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    link_exclusively(cam_obj, cam_col)
    scene.camera = cam_obj

    # Focal Length Whip-Zoom Choreography (24mm -> 50mm -> 62mm -> 35mm)
    lens_keys = [
        (1,   24.0),
        (20,  25.0),
        (42,  28.0),
        (60,  50.0),  # Beat 1 -> 2 Whip-Zoom In!
        (68,  52.0),  # Slight zoom overshoot settle
        (85,  48.0),  # Beat 2 Crisp 3/4 Medium Close-Up
        (107, 49.0),
        (119, 62.0),  # Beat 3 Punch-In Zoom onto Torch, Sparks & Goggles!
        (155, 58.0),  # Balanced close action framing (both head & sparks inside frame!)
        (204, 60.0),
        (224, 35.0),  # Beat 4 Fast Whip-Zoom Pull-Back!
        (240, 35.0),  # Payoff Two-Shot
        (264, 36.0),
    ]
    for f, fl in lens_keys:
        cam_data.lens = fl
        cam_data.keyframe_insert(data_path="lens", frame=f)

    roll_keys = [
        (1,   (0.000, 0.0, -0.025)),
        (60,  (0.000, 0.0,  0.015)),
        (85,  (0.000, 0.0,  0.000)),
        (113, (0.000, 0.0,  0.018)),
        (203, (0.000, 0.0, -0.015)),
        (226, (0.018, 0.0,  0.018)),
        (240, (0.015, 0.0,  0.012)),
        (264, (0.012, 0.0,  0.008)),
    ]
    for f, r_eul in roll_keys:
        cam_obj.rotation_euler = r_eul
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)

    _smooth_fcurves(dolly)
    _smooth_fcurves(target)
    _smooth_fcurves(cam_data)
    _smooth_fcurves(cam_obj)

    add_restricted_noise_modifier(
        cam_obj, data_path="rotation_euler",
        frame_start=float(WELD_ARC_START), frame_end=float(WELD_ARC_END),
        scale=1.6, strength=0.0055, phase=3.1, index=0
    )
    add_restricted_noise_modifier(
        cam_obj, data_path="rotation_euler",
        frame_start=float(WELD_ARC_START), frame_end=float(WELD_ARC_END),
        scale=1.9, strength=0.0045, phase=14.8, index=2
    )

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()

    return {
        "camera": cam_obj,
        "dolly": dolly,
        "target": target,
        "path": path_obj,
    }
