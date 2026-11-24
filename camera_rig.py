"""
camera_rig.py — Fast-Paced Cinematic Single-Take / Whip-Zoom Camera System
Combines:
  1) 3D Bezier Travel Path (`Cam_Rig_Path`) + `Follow Path` constraint on `Cam_Dolly`
  2) Dynamic `Cam_FocusTarget` Empty + `Track To` constraint on `Camera_Main`
  3) Aggressive Bezier `Focal Length` whip-zoom transitions (24mm -> 55mm -> 85mm -> 35mm)
  4) Restricted F-Curve `NOISE` micro-camera shake strictly during Welding Beat 3 (113..203)
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import bpy
from mathutils import Vector

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
      - Beat 1 (1-60):   Wide Workshop Establishing Travel -> Whip-Zoom In (24mm -> 55mm)
      - Beat 2 (61-110): Overshoot Settle & 3/4 Front-Side Medium Close-Up Orbit
      - Beat 3 (111-205): Punch-In Zoom (55mm -> 85mm) + Dynamic Spark Orbit + Micro Shake
      - Beat 4 (206-264): Whip-Zoom Pull-Back (85mm -> 35mm) + Heroic Two-Shot Payoff
    """
    cam_col = get_or_create_collection("Col_Camera_Rig")

    # 1) 3D Bezier Travel Curve (`Cam_Rig_Path`)
    # Carefully routed through the obstacle-free workshop corridor X in [-3.1..-1.05], Y in [-3.2..-0.55]
    # so zero props block the lens while showcasing workbench/wrenches, car/engine, sparks & mechanic!
    curve_data = bpy.data.curves.new("Cam_Rig_Path_Data", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 36
    curve_data.use_path = True
    curve_data.path_duration = 100

    spline = curve_data.splines.new("BEZIER")
    # Control points along u in [0.0 .. 1.0]:
    path_pts: List[Tuple[float, float, float]] = [
        (-3.05, -3.15, 1.56),  # [0] u=0.00: Wide back-left workshop bay start (Frame 1)
        (-2.35, -1.95, 1.40),  # [1] u=0.20: Gliding past tool chest & wrench rack (Frame 20)
        (-1.54, -0.96, 1.26),  # [2] u=0.40: Whip-zoom arrival beside front bumper (Frame 60)
        (-1.44, -0.58, 1.23),  # [3] u=0.55: 3/4 Front Medium Close-Up on Mechanic & Goggles (Frame 85)
        (-1.24, -0.92, 1.13),  # [4] u=0.78: Dynamic low-angle Spark & Welding Arc Orbit (Frame 155)
        (-1.72, -1.32, 1.24),  # [5] u=1.00: Heroic Pull-Back Two-Shot of Mechanic + Welded Car (Frame 240..264)
    ]
    spline.bezier_points.add(len(path_pts) - 1)
    for idx, pt in enumerate(path_pts):
        bp = spline.bezier_points[idx]
        bp.co = pt
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    path_obj = bpy.data.objects.new("Cam_Rig_Path", curve_data)
    link_exclusively(path_obj, cam_col)

    # 2) Camera Dolly Empty with `Follow Path` Constraint (`offset_factor` 0.0 -> 1.0)
    dolly = bpy.data.objects.new("Cam_Dolly", None)
    dolly.empty_display_type = "SPHERE"
    dolly.empty_display_size = 0.08
    link_exclusively(dolly, cam_col)

    fp_con = dolly.constraints.new(type="FOLLOW_PATH")
    fp_con.name = "Follow_CameraCurve"
    fp_con.target = path_obj
    fp_con.use_fixed_location = True

    # Animate `offset_factor` with fast glide, slight Beat-2 overshoot, smooth Beat-3 orbit, fast Beat-4 pullback!
    dolly_offset_keys = [
        (1,   0.000),
        (20,  0.205),  # Diagnostic Frame 20: Wide travel past tools & car!
        (58,  0.415),  # Fast arrival
        (66,  0.448),  # Subtle overshoot settle
        (85,  0.545),  # Diagnostic Frame 85: 3/4 Medium Close-Up on Goggle Pull!
        (108, 0.585),
        (120, 0.650),  # Punch-in orbit start
        (155, 0.775),  # Diagnostic Frame 155: Sweeping past flying sparks & blue-white arc!
        (203, 0.855),
        (226, 0.985),  # Snappy whip-pullback as torch lifts!
        (240, 0.995),  # Diagnostic Frame 240: Heroic Payoff Two-Shot!
        (264, 1.000),
    ]
    for f, u_val in dolly_offset_keys:
        fp_con.offset_factor = u_val
        dolly.keyframe_insert(data_path='constraints["Follow_CameraCurve"].offset_factor', frame=f)

    # 3) Dynamic Camera Look-At Target (`Cam_FocusTarget`)
    target = bpy.data.objects.new("Cam_FocusTarget", None)
    target.empty_display_type = "CROSS"
    target.empty_display_size = 0.12
    link_exclusively(target, cam_col)

    target_keys = [
        # Beat 1: Wide bay framing -> converging onto mechanic & front fender
        (1,   (-0.35, -0.35, 1.02)),
        (20,  (-0.22, -0.52, 1.02)),
        (58,  (-0.18, -0.82, 1.12)),
        # Beat 2: Centered cleanly between mechanic's head/goggles & fender
        (85,  (-0.18, -0.88, 1.18)),
        (106, (-0.24, -0.68, 1.04)),
        # Beat 3: Tight hero framing capturing BOTH blazing torch/sparks AND goggle-clad face!
        (116, (-0.26, -0.62, 1.04)),
        (155, (-0.20, -0.66, 1.05)),
        (203, (-0.12, -0.66, 1.03)),
        # Beat 4: Slight upward tilt & wider center framing both smiling mechanic & glowing weld seam!
        (226, (-0.16, -0.78, 1.08)),
        (240, (-0.16, -0.78, 1.10)),
        (264, (-0.15, -0.76, 1.10)),
    ]
    for f, t_pos in target_keys:
        target.location = t_pos
        target.keyframe_insert(data_path="location", frame=f)

    # 4) Main Camera (`Camera_Main`) -> Child of ShakeRig -> Tracked to `Cam_FocusTarget`
    # Putting Track To on `Cam_Tracker` and making `Camera_Main` its child allows clean
    # Dutch tilt + restricted F-Curve NOISE micro-shake during welding!
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

    # Focal Length Whip-Zoom Choreography (24mm -> 55mm -> 85mm -> 35mm)
    lens_keys = [
        (1,   24.0),
        (20,  26.0),
        (42,  29.0),
        (60,  55.0),  # Beat 1 -> 2 Whip-Zoom In!
        (68,  57.0),  # Slight zoom settle
        (85,  55.0),  # Beat 2 Medium Close-Up
        (107, 56.0),
        (119, 85.0),  # Beat 3 Punch-In Zoom onto Torch & Sparks!
        (155, 82.0),  # Crisp close action framing
        (204, 84.0),
        (224, 35.0),  # Beat 4 Fast Whip-Zoom Pull-Back!
        (240, 35.0),  # Payoff Two-Shot
        (264, 36.0),
    ]
    for f, fl in lens_keys:
        cam_data.lens = fl
        cam_data.keyframe_insert(data_path="lens", frame=f)

    # Subtle Dynamic Camera Roll / Tilt Accent + Restricted Welding Micro-Shake!
    roll_keys = [
        (1,   (0.000, 0.0, -0.025)),
        (60,  (0.000, 0.0,  0.015)),
        (85,  (0.000, 0.0,  0.000)),
        (113, (0.000, 0.0,  0.020)),
        (203, (0.000, 0.0, -0.018)),
        (226, (0.022, 0.0,  0.022)),  # Slight heroic tilt on Beat 4 pull-back!
        (240, (0.018, 0.0,  0.015)),
        (264, (0.015, 0.0,  0.010)),
    ]
    for f, r_eul in roll_keys:
        cam_obj.rotation_euler = r_eul
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)

    _smooth_fcurves(dolly)
    _smooth_fcurves(target)
    _smooth_fcurves(cam_data)
    _smooth_fcurves(cam_obj)

    # Micro Handheld Camera Shake ONLY while Welding Arc is Active (113..203)!
    add_restricted_noise_modifier(
        cam_obj, data_path="rotation_euler",
        frame_start=float(WELD_ARC_START), frame_end=float(WELD_ARC_END),
        scale=1.6, strength=0.0065, phase=3.1, index=0
    )
    add_restricted_noise_modifier(
        cam_obj, data_path="rotation_euler",
        frame_start=float(WELD_ARC_START), frame_end=float(WELD_ARC_END),
        scale=1.9, strength=0.0055, phase=14.8, index=2
    )

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()

    return {
        "camera": cam_obj,
        "dolly": dolly,
        "target": target,
        "path": path_obj,
    }
