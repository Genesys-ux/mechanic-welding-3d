"""
animation_core.py — 12 Principles Character Choreography (24 FPS, 264 Frames / 11s)
Implements all 4 Beats with natural Bezier F-Curves:
  - Beat 1 (1-60):   Relaxed Mechanic Stance, Idle Breathing, Scanning Car Fender
  - Beat 2 (61-110): Shoulder Anticipation, Left Hand Pulls Brass Goggles Over Eyes,
                     Weight Shift Forward, Left Hand Braces on Fender, Torch Approaches Seam
  - Beat 3 (111-205): Arc Ignition Micro-Recoil, Precision Zig-Zag Welding Pass Along Seam,
                      Secondary Follow-Through on Lightning Hair Tufts & Right-Ear Pencil
  - Beat 4 (206-264): Torch Lift-Off, Left Hand Pushes Goggles Back to Forehead,
                      Proud Gap-Tooth Grin & Satisfied Head Nod Payoff
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import bpy
from mathutils import Euler, Matrix, Vector

from config import (
    FENDER_LEFT_HAND_REST,
    FRAME_END,
    FRAME_START,
    WELD_ARC_END,
    WELD_ARC_START,
)
from vfx_lighting import _get_action_fcurves, eval_weld_seam_point


def _set_world_pose_target(
    arm_obj: bpy.types.Object,
    pb: bpy.types.PoseBone,
    world_pos: Vector,
    world_euler: Tuple[float, float, float],
) -> None:
    """Set a PoseBone's transform to an exact World-Space location & Euler orientation."""
    m_world = Matrix.Translation(world_pos) @ Euler(world_euler, "XYZ").to_matrix().to_4x4()
    pb.matrix = arm_obj.matrix_world.inverted() @ m_world


def _key_pb(pb: bpy.types.PoseBone, frame: int, loc: bool = True, rot: bool = True, scale: bool = False) -> None:
    if loc:
        pb.keyframe_insert(data_path="location", frame=frame)
    if rot:
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale:
        pb.keyframe_insert(data_path="scale", frame=frame)


def _polish_bezier_fcurves(arm_obj: bpy.types.Object) -> None:
    """Ensure every character animation F-Curve uses smooth organic AUTO_CLAMPED Bezier handles."""
    for fc in _get_action_fcurves(arm_obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


def animate_mechanic_choreography(
    scene: bpy.types.Scene,
    arm_obj: bpy.types.Object,
    torch_local_tip_in_hand: Vector,
    cable_mid_sag: Optional[bpy.types.Object] = None,
) -> None:
    """
    Build the complete 264-frame character animation across Beats 1..4.
    """
    # Angle the mechanic +22 degrees around Z so he naturally faces the front-left fender
    # AND opens a dramatic 3/4 front-face angle toward the camera!
    arm_obj.location = (-0.12, -1.00, 0.0)
    arm_obj.rotation_euler = (0.0, 0.0, math.radians(22.0))
    bpy.context.view_layer.update()

    pb = arm_obj.pose.bones
    for b in pb:
        b.rotation_mode = "XYZ"

    # Keep feet rock-solid planted on the workshop floor via Root-space IK targets
    for foot_b in ("IK_Foot.L", "IK_Foot.R"):
        pb[foot_b].location = (0.0, 0.0, 0.0)
        pb[foot_b].rotation_euler = (0.0, 0.0, 0.0)
        _key_pb(pb[foot_b], 1)
        _key_pb(pb[foot_b], FRAME_END)

    # Position Elbow Pole Targets cleanly behind/outward so elbows never flip!
    pb["Pole_Arm.L"].location = (-0.12, -0.25, 0.05)
    pb["Pole_Arm.R"].location = (0.18, -0.28, 0.05)
    _key_pb(pb["Pole_Arm.L"], 1, rot=False)
    _key_pb(pb["Pole_Arm.R"], 1, rot=False)

    # ==========================================================================
    # PASS 1: TORSO, SPINE SQUASH/STRETCH, HEAD, GOGGLES, FACIAL & SECONDARY RIG
    # ==========================================================================
    # Keyframes for Pelvis (weight shift & breathing), Spine (lean & squash/stretch),
    # Chest, Head, Goggles_Ctrl, Brows, Mouth, Blink, Eye_Target, Hair Tufts & Ear Pencil

    torso_head_keys = [
        # (frame, pelvis_loc, pelvis_rotZ, spine_rotX, spine_scaleZ, head_rotXYZ, eye_world)
        # Beat 1 (1..60): Idle breathing & observing car fender damage
        (1,   (0.000, 0.000,  0.000),  0.00, -0.03, 1.000, (-0.06,  0.02, -0.08), (-0.28, -0.44, 0.96)),
        (20,  (0.004, 0.006, -0.012), -0.02, -0.05, 0.985, (-0.09, -0.01, -0.14), (-0.18, -0.44, 0.97)),
        (40,  (0.000, 0.000,  0.010),  0.01, -0.02, 1.015, (-0.05,  0.03, -0.05), (-0.06, -0.44, 0.95)),
        (58,  (0.002, 0.004, -0.008),  0.00, -0.04, 0.992, (-0.07,  0.01, -0.10), (-0.24, -0.44, 0.96)),

        # Beat 2 (61..110): Anticipation dip -> Pull Goggles Down (nod at 85!) -> Weight Shift Forward!
        (65,  (-0.010, -0.018, -0.026), 0.04, -0.08, 0.968, (0.04, -0.03, 0.04),  (-0.26, -0.44, 1.02)),  # Anticipation!
        (76,  (-0.005,  0.005,  0.008), 0.02, -0.03, 1.012, (-0.04, 0.02, -0.02), (-0.26, -0.44, 1.00)),  # Reach forehead
        (85,  (-0.012,  0.022, -0.014), 0.00, -0.09, 0.988, (-0.16, 0.04, -0.04), (-0.28, -0.44, 0.96)),  # Pull goggles + nod!
        (93,  (-0.018,  0.045, -0.018),-0.02, -0.13, 0.992, (-0.12, 0.01, -0.08), (-0.33, -0.44, 0.96)),
        (108, (-0.035,  0.105, -0.032),-0.06, -0.22, 0.985, (-0.14,-0.02, -0.12), (-0.34, -0.43, 0.955)), # Braced & ready!

        # Beat 3 (111..205): Arc Ignition Micro-Recoil (115) + Focused Steady Welding Tracking
        (113, (-0.035,  0.105, -0.032),-0.06, -0.22, 0.985, (-0.14,-0.02, -0.12), (-0.34, -0.43, 0.955)),
        (116, (-0.025,  0.082, -0.044),-0.04, -0.18, 0.965, (-0.06, 0.04, -0.08), (-0.32, -0.43, 0.96)),  # Spark ignition flinch!
        (124, (-0.034,  0.104, -0.030),-0.06, -0.22, 0.990, (-0.15,-0.01, -0.13), (-0.28, -0.44, 0.965)),
        (155, (-0.020,  0.108, -0.034),-0.09, -0.23, 0.986, (-0.16,-0.02, -0.20), (-0.17, -0.445,0.975)), # Mid-seam Hero Frame 155!
        (185, (-0.008,  0.106, -0.030),-0.12, -0.22, 0.990, (-0.15,-0.03, -0.26), (-0.06, -0.435,0.955)),
        (203, (-0.004,  0.102, -0.032),-0.13, -0.21, 0.988, (-0.14,-0.02, -0.28), ( 0.01, -0.43, 0.945)),

        # Beat 4 (206..264): Pull Back, Push Goggles Up to Forehead, Proud Smile & Nod!
        (214, (-0.006,  0.035,  0.006),-0.04, -0.07, 1.012, (-0.04, 0.02, -0.12), (-0.15, -0.44, 0.97)),
        (223, (-0.004,  0.010,  0.000),-0.01, -0.03, 1.004, ( 0.05,-0.02, -0.06), (-0.17, -0.44, 1.02)),  # Hand touches goggles
        (233, ( 0.000,  0.000,  0.012), 0.01,  0.01, 1.018, ( 0.08,-0.03, -0.05), (-0.17, -0.44, 1.00)),  # Pushed goggles up!
        (240, ( 0.002,  0.000,  0.002), 0.02, -0.02, 1.002, (-0.03, 0.03,  0.06), (-0.55, -0.70, 1.08)),  # Proud Smile Hero Frame 240!
        (248, ( 0.002,  0.004, -0.012), 0.02, -0.04, 0.988, (-0.13, 0.04,  0.04), (-0.20, -0.45, 0.97)),  # Satisfied nod down
        (256, ( 0.000,  0.000,  0.006), 0.01, -0.02, 1.008, (-0.04, 0.02,  0.05), (-0.35, -0.55, 1.02)),  # Nod up
        (264, ( 0.000,  0.000,  0.000), 0.01, -0.02, 1.000, (-0.05, 0.02,  0.04), (-0.30, -0.52, 1.00)),
    ]

    for (f, p_loc, p_rz, sp_rx, sp_sz, h_rot, eye_w) in torso_head_keys:
        pb["Pelvis"].location = p_loc
        pb["Pelvis"].rotation_euler = (0.0, 0.0, p_rz)
        _key_pb(pb["Pelvis"], f)

        pb["Spine"].rotation_euler = (sp_rx, 0.0, 0.0)
        pb["Spine"].scale = (1.0, 1.0, sp_sz)
        _key_pb(pb["Spine"], f, loc=False, rot=True, scale=True)

        pb["Chest"].rotation_euler = (sp_rx * 0.35, 0.0, p_rz * 0.4)
        _key_pb(pb["Chest"], f, loc=False, rot=True)

        pb["Head"].rotation_euler = h_rot
        _key_pb(pb["Head"], f, loc=False, rot=True)

        _set_world_pose_target(arm_obj, pb["Eye_Target"], Vector(eye_w), (0.0, 0.0, 0.0))
        _key_pb(pb["Eye_Target"], f, loc=True, rot=False)

    # ==========================================================================
    # GOGGLES RIG ANIMATION (`Goggles_Ctrl` & `Goggles_Loupe`)
    # ==========================================================================
    # Forehead Rest:  loc=(0, 0, 0), rot=(0, -0.10, 0)  (-6 deg classic tilt)
    # Over-Eyes Weld: loc=(0.0, 0.018, -0.122), rot=(0.08, 0.0, 0.0)
    goggles_keys = [
        (1,   (0.0, 0.000,  0.000), (0.00, -0.10, 0.0), (0.0, 0.0, 0.0)),
        (75,  (0.0, 0.000,  0.000), (0.00, -0.10, 0.0), (0.0, 0.0, 0.0)),
        (78,  (0.0, 0.006,  0.010), (-0.03,-0.06, 0.0), (0.0, 0.0, 0.12)),   # Slight lift off hair
        (85,  (0.0, 0.020, -0.112), (0.07, -0.01, 0.0), (0.0, 0.0, -0.35)),  # Pulled right onto eyes at Frame 85!
        (89,  (0.0, 0.018, -0.124), (0.08,  0.00, 0.0), (0.0, 0.0, -0.55)),  # Snug fit + loupe swings in!
        (219, (0.0, 0.018, -0.124), (0.08,  0.00, 0.0), (0.0, 0.0, -0.55)),  # Held firmly all through Beat 3 (incl. 155)!
        (223, (0.0, 0.022, -0.116), (0.06, -0.02, 0.0), (0.0, 0.0, -0.30)),  # Hand grabs goggles
        (232, (0.0, 0.004,  0.008), (-0.02,-0.11, 0.0), (0.0, 0.0,  0.08)),  # Pushed back up with tiny overshoot
        (236, (0.0, 0.000,  0.000), (0.00, -0.10, 0.0), (0.0, 0.0,  0.00)),  # Settled on forehead before Frame 240!
        (264, (0.0, 0.000,  0.000), (0.00, -0.10, 0.0), (0.0, 0.0,  0.00)),
    ]
    for f, g_loc, g_rot, l_rot in goggles_keys:
        pb["Goggles_Ctrl"].location = g_loc
        pb["Goggles_Ctrl"].rotation_euler = g_rot
        _key_pb(pb["Goggles_Ctrl"], f)
        pb["Goggles_Loupe"].rotation_euler = l_rot
        _key_pb(pb["Goggles_Loupe"], f, loc=False, rot=True)

    # ==========================================================================
    # FACIAL EXPRESSIONS: BLINKS, EYEBROWS & MOUTH SWITCH (SMILE <-> FOCUSED)
    # ==========================================================================
    # Natural Eyelid Blinks (frames ~28, ~68, ~214, ~244)
    blink_frames = [
        (1, 0.05), (25, 0.05), (28, 1.02), (32, 0.05),
        (64, 0.05), (67, 0.98), (71, 0.05),
        (110, 0.22), (204, 0.22),  # Slight focused squint behind goggles
        (211, 0.05), (214, 1.02), (218, 0.05),
        (242, 0.05), (245, 0.96), (249, 0.05), (264, 0.05),
    ]
    for f, bz in blink_frames:
        for side_s in ("L", "R"):
            pb[f"Blink.{side_s}"].scale = (1.0, 1.0, bz)
            _key_pb(pb[f"Blink.{side_s}"], f, loc=False, rot=False, scale=True)

    # Eyebrows: Curious/Relaxed -> Furrowed Focus -> Proud Happy Arch!
    brow_keys = [
        (1,   0.000,  0.00),
        (60,  0.000,  0.00),
        (95, -0.010,  0.20),  # Furrowed determination
        (205,-0.010,  0.20),
        (232, 0.014, -0.12),  # Proud raised eyebrows!
        (264, 0.010, -0.08),
    ]
    for f, dz_b, tilt_b in brow_keys:
        pb["Brow.L"].location = (0.0, 0.0, dz_b)
        pb["Brow.L"].rotation_euler = (0.0, -tilt_b, 0.0)
        pb["Brow.R"].location = (0.0, 0.0, dz_b)
        pb["Brow.R"].rotation_euler = (0.0,  tilt_b, 0.0)
        _key_pb(pb["Brow.L"], f)
        _key_pb(pb["Brow.R"], f)

    # Mouth State Switch:
    # Beat 1 (1..70): Relaxed Confident Gap-Smile (1.0)
    # Beat 2 & 3 (78..224): Focused Determined Welding Mouth
    # Beat 4 (230..264): Big Proud Gap-Tooth Grin (1.16x)!
    mouth_keys = [
        (1,   (0.95, 1.0, 0.90), (0.001, 0.001, 0.001)),
        (70,  (0.95, 1.0, 0.90), (0.001, 0.001, 0.001)),
        (76,  (0.001, 0.001, 0.001), (1.0, 1.0, 1.0)),
        (224, (0.001, 0.001, 0.001), (1.0, 1.0, 1.0)),
        (231, (1.16, 1.0, 1.22), (0.001, 0.001, 0.001)),  # Big proud smile!
        (264, (1.12, 1.0, 1.15), (0.001, 0.001, 0.001)),
    ]
    for f, sm_sc, fc_sc in mouth_keys:
        pb["Mouth_Smile_Bone"].scale = sm_sc
        pb["Mouth_Focus_Bone"].scale = fc_sc
        _key_pb(pb["Mouth_Smile_Bone"], f, loc=False, rot=False, scale=True)
        _key_pb(pb["Mouth_Focus_Bone"], f, loc=False, rot=False, scale=True)

    # ==========================================================================
    # SECONDARY MOTION / FOLLOW-THROUGH (Lightning Hair Tufts, Nape & Ear Pencil!)
    # ==========================================================================
    # Lagged overlapping oscillations triggered by breathing, goggle nod (85),
    # arc ignition flinch (116), and proud payoff nod (248)
    for f in range(1, FRAME_END + 1, 4):
        t = f / 24.0
        idle_sway = math.sin(t * 3.2 - 0.6) * 0.045
        # Extra damped spring impulses at key action beats (85, 116, 232, 248)
        imp = 0.0
        for f0, amp in ((84, 0.16), (115, -0.22), (231, 0.18), (247, 0.14)):
            if f >= f0:
                dt_s = (f - f0) / 24.0
                imp += amp * math.exp(-5.5 * dt_s) * math.sin(18.0 * dt_s)

        pb["Hair_Bolt_1"].rotation_euler = (imp * 0.8, idle_sway + imp, 0.0)
        pb["Hair_Bolt_2"].rotation_euler = (imp * 0.9, idle_sway * 1.2 + imp * 1.15, 0.0)
        pb["Hair_Nape"].rotation_euler = (-imp * 0.6 + idle_sway * 0.5, 0.0, 0.0)
        pb["Ear_Pencil.R"].rotation_euler = (imp * 0.85 + idle_sway * 0.6, imp * 0.4, 0.0)

        _key_pb(pb["Hair_Bolt_1"], f, loc=False, rot=True)
        _key_pb(pb["Hair_Bolt_2"], f, loc=False, rot=True)
        _key_pb(pb["Hair_Nape"], f, loc=False, rot=True)
        _key_pb(pb["Ear_Pencil.R"], f, loc=False, rot=True)

    # ==========================================================================
    # PASS 2: EXACT WORLD-SPACE HAND IK (`IK_Hand.L` & `IK_Hand.R` + TORCH!)
    # ==========================================================================
    # Helper to compute exact Right Hand world pos so `Empty_TorchTip` lands on `tip_world`!
    def solve_right_hand_for_tip(tip_world: Vector, hand_euler: Tuple[float, float, float]) -> Vector:
        r_mat = Euler(hand_euler, "XYZ").to_matrix()
        return tip_world - (r_mat @ torch_local_tip_in_hand)

    # 1) LEFT HAND (`IK_Hand.L`) CHOREOGRAPHY:
    # We evaluate `Goggles_Ctrl` in world space at frames 76..88 and 223..233 so Left Hand
    # locks onto the outer-left brass goggle cup with 0.00mm gap and zero head clipping!
    def goggle_left_grip_world(frame_eval: int) -> Vector:
        scene.frame_set(frame_eval)
        bpy.context.view_layer.update()
        g_wmat = arm_obj.matrix_world @ pb["Goggles_Ctrl"].matrix
        # Outer-left brass goggle frame in Goggles_Ctrl local space: X=-0.132, Y=+0.205, Z=-0.010
        return g_wmat @ Vector((-0.132, 0.205, -0.010))

    lh_idle = Vector((-0.34, -0.86, 0.58))
    lh_fender = Vector(FENDER_LEFT_HAND_REST) + Vector((0.0, -0.01, 0.018))  # Cleanly resting on fender crest!

    left_hand_plan: List[Tuple[int, Vector, Tuple[float, float, float]]] = [
        (1,   lh_idle, (-0.15, 0.0, 0.25)),
        (20,  lh_idle + Vector((0.0, 0.01, -0.01)), (-0.15, 0.0, 0.25)),
        (62,  lh_idle, (-0.15, 0.0, 0.25)),
        (66,  lh_idle + Vector((-0.02, -0.02, -0.03)), (-0.25, 0.0, 0.25)),  # Anticipation
        (72,  Vector((-0.36, -0.78, 1.02)), (0.55, 0.15, 0.20)),             # Rising arc
    ]
    # Exact lockstep goggle pull-down frames (76..88, including Diagnostic Frame 85!)
    for fg in (76, 80, 85, 88):
        left_hand_plan.append((fg, goggle_left_grip_world(fg), (0.65, 0.25, -0.15)))

    left_hand_plan.extend([
        (95,  Vector((-0.44, -0.62, 1.12)), (0.20, 0.10, 0.10)),             # Arcing from goggles to fender
        (106, lh_fender, (-0.22, 0.08, 0.15)),                               # Planted firmly on fender!
        (155, lh_fender, (-0.22, 0.08, 0.15)),                               # Rock-steady brace at Frame 155!
        (206, lh_fender, (-0.22, 0.08, 0.15)),
        (215, Vector((-0.40, -0.68, 1.08)), (0.35, 0.15, 0.05)),             # Lifting toward goggles
    ])
    # Exact lockstep goggle push-up frames (222..233)
    for fg in (222, 227, 233):
        left_hand_plan.append((fg, goggle_left_grip_world(fg), (0.65, 0.22, -0.15)))

    left_hand_plan.extend([
        (238, Vector((-0.36, -0.84, 0.72)), (-0.05, 0.05, 0.20)),
        (244, lh_idle + Vector((-0.01, 0.02, 0.03)), (-0.12, 0.0, 0.25)),    # Relaxed on hip!
        (264, lh_idle + Vector((-0.01, 0.02, 0.02)), (-0.12, 0.0, 0.25)),
    ])

    for f, l_pos, l_rot in left_hand_plan:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        _set_world_pose_target(arm_obj, pb["IK_Hand.L"], l_pos, l_rot)
        _key_pb(pb["IK_Hand.L"], f)

    # 2) RIGHT HAND (`IK_Hand.R`) + WELDING TORCH CHOREOGRAPHY:
    # Beat 1 (1..60): Holding welding torch comfortably at side-front
    rh_idle = Vector((0.12, -0.92, 0.62))
    rh_idle_rot = (-0.28, 0.10, 0.22)  # Nozzle angled safely forward-down

    # Welding wrist orientation: aims torch forward (+Y) & slightly left (+Z yaw = +0.28) toward fender
    weld_base_rot = (0.12, -0.08, 0.26)

    right_hand_plan: List[Tuple[int, Vector, Tuple[float, float, float]]] = [
        (1,   rh_idle, rh_idle_rot),
        (25,  rh_idle + Vector((0.0, 0.01, -0.012)), rh_idle_rot),
        (60,  rh_idle, rh_idle_rot),
        (68,  rh_idle + Vector((0.02, -0.03, -0.02)), (-0.35, 0.12, 0.18)),  # Anticipation
        (85,  Vector((0.04, -0.78, 0.78)), (-0.05, 0.05, 0.24)),             # Raising torch as goggles come down
        (102, solve_right_hand_for_tip(eval_weld_seam_point(0.0) + Vector((0.0, -0.06, 0.03)), weld_base_rot), weld_base_rot),
        (111, solve_right_hand_for_tip(eval_weld_seam_point(0.0) + Vector((0.0, -0.004, 0.0)), weld_base_rot), weld_base_rot),
    ]

    # High-Frequency Micro-Zig-Zag Welding Pass (Frames 113 .. 203, every 3 frames!)
    for fw in range(WELD_ARC_START, WELD_ARC_END + 1, 3):
        u_w = (fw - WELD_ARC_START) / float(WELD_ARC_END - WELD_ARC_START)
        seam_pt = eval_weld_seam_point(u_w)
        # Authentic MIG weave oscillation (~4mm vertical/lateral zig-zag)
        zig = math.sin((fw - WELD_ARC_START) * 1.15) * 0.0045
        tip_target = seam_pt + Vector((0.0, -0.003, zig))
        rot_w = (
            weld_base_rot[0] + zig * 2.5,
            weld_base_rot[1],
            weld_base_rot[2] - u_w * 0.34,  # Smooth wrist pan as torch travels -X -> +X!
        )
        right_hand_plan.append((fw, solve_right_hand_for_tip(tip_target, rot_w), rot_w))

    # Ensure exact end-of-seam & Beat 4 pull-back payoff keyframes
    payoff_rh = Vector((0.13, -0.88, 0.68))
    payoff_rot = (-0.18, 0.12, 0.25)
    right_hand_plan.extend([
        (204, solve_right_hand_for_tip(eval_weld_seam_point(1.0) + Vector((0.0, -0.01, 0.005)), (0.12, -0.08, -0.08)), (0.12, -0.08, -0.08)),
        (214, Vector((0.08, -0.74, 0.86)), (0.22, 0.05, 0.12)),   # Clean torch lift-off away from glowing seam!
        (230, payoff_rh + Vector((0.0, 0.03, 0.04)), payoff_rot),
        (240, payoff_rh, payoff_rot),                             # Relaxed confident hold at Frame 240!
        (264, payoff_rh + Vector((0.0, 0.0, -0.01)), payoff_rot),
    ])

    for f, r_pos, r_rot in right_hand_plan:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        _set_world_pose_target(arm_obj, pb["IK_Hand.R"], r_pos, r_rot)
        _key_pb(pb["IK_Hand.R"], f)

        # Subtle follow-through on the flexible welding cable's mid-loop Empty!
        if cable_mid_sag is not None and f in (1, 60, 85, 113, 155, 203, 240, 264):
            cable_mid_sag.location = (
                0.38 + (r_pos.x - 0.12) * 0.30,
                -1.14 + (r_pos.y + 0.92) * 0.28,
                0.18 + max(0.0, (r_pos.z - 0.62) * 0.22),
            )
            cable_mid_sag.keyframe_insert(data_path="location", frame=f)

    _polish_bezier_fcurves(arm_obj)
    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()
