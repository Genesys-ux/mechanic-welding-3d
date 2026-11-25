"""
short_75s/main_short.py — Stage 3 Main Entry Point for the 75-Second YouTube Short
("Mesin Tua, Nyawa Baru" — 1,800 Frames @ 24 FPS, 9:16 Vertical, 6 Locations, 30 Camera Moves,
Low Sun + Long Shadows + Blue Shade + Volumetric God Rays + Haze + Synced 2.5D/3D Action).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from animation_core import _aim_torch_tip_quat, _smooth_obj_fcurves, billboard_uv_to_world  # noqa: E402
from character_rig import _create_shadeless_25d_sequence_material  # noqa: E402
from env_props import get_or_create_collection, link_exclusively  # noqa: E402
from main import configure_render_and_compositor  # noqa: E402
from vfx_lighting import eval_weld_seam_point, set_active_weld_seam  # noqa: E402

from short_75s.camera_continuous_30moves import build_30move_continuous_camera_rig  # noqa: E402
from short_75s.config_short import (  # noqa: E402
    BLEND_FILE_PATH,
    CHAR_BILLBOARD_HEIGHT,
    CHAR_BILLBOARD_WIDTH,
    CHAR_FRAMES_DIR,
    CHAR_HAND_SYNC_PATH,
    CHAR_Z_BOTTOM_OFFSET,
    CLIMAX_ARC_END,
    CLIMAX_ARC_START,
    DEBUG_FRAMES,
    DEBUG_FRAMES_DIR,
    DEBUG_RES_X,
    DEBUG_RES_Y,
    FPS,
    FRAME_END,
    FRAME_START,
    HOOK_ARC_END,
    HOOK_ARC_START,
    OUTPUT_DIR,
    RES_X,
    RES_Y,
)
from short_75s.env_world_6loc import build_6location_workshop_world  # noqa: E402
from short_75s.lighting_godrays_haze import build_75s_lighting_and_vfx  # noqa: E402
from short_75s.story_beats import eval_character_blocking  # noqa: E402


def parse_cli_args() -> argparse.Namespace:
    argv = sys.argv
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="75s YouTube Short 2.5D+3D Pipeline")
    parser.add_argument("--mode", choices=["debug", "shard"], default="debug")
    parser.add_argument("--frames", type=str, default="", help="Optional comma-separated debug frame list")
    parser.add_argument("--start", type=int, default=FRAME_START)
    parser.add_argument("--end", type=int, default=FRAME_END)
    parser.add_argument("--width", type=int, default=RES_X)
    parser.add_argument("--height", type=int, default=RES_Y)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--fast-ci", action="store_true")
    parser.add_argument("--save-blend", action="store_true")
    parser.add_argument("--frames-dir", type=str, default=str(OUTPUT_DIR / "frames"))
    return parser.parse_args(extra)


def build_75s_mechanic_billboard(camera_obj: bpy.types.Object, target_frames: List[int]) -> Dict[str, Any]:
    char_col = get_or_create_collection("Col_Mechanic_Character")
    mech_empty = bpy.data.objects.new("Empty_Mechanic", None)
    mech_empty.empty_display_type = "SINGLE_ARROW"
    mech_empty.empty_display_size = 0.35
    link_exclusively(mech_empty, char_col)

    bake_frames = sorted(set(target_frames) | set(range(FRAME_START, FRAME_END + 1, 3)) | {FRAME_START, FRAME_END})
    for f in bake_frames:
        pos, yaw_deg, _ = eval_character_blocking(f)
        mech_empty.location = pos
        mech_empty.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
        mech_empty.keyframe_insert(data_path="location", frame=f)
        mech_empty.keyframe_insert(data_path="rotation_euler", frame=f)

    half_w = CHAR_BILLBOARD_WIDTH * 0.5
    z_bot = CHAR_Z_BOTTOM_OFFSET
    z_top = z_bot + CHAR_BILLBOARD_HEIGHT

    bm = bmesh.new()
    v0 = bm.verts.new((-half_w, 0.0, z_bot))
    v1 = bm.verts.new((half_w, 0.0, z_bot))
    v2 = bm.verts.new((half_w, 0.0, z_top))
    v3 = bm.verts.new((-half_w, 0.0, z_top))
    face = bm.faces.new([v0, v1, v2, v3])
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for loop, uv in zip(face.loops, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]):
        loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new("Char_Billboard_Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    mat_25d = _create_shadeless_25d_sequence_material(CHAR_FRAMES_DIR, name="Mat_Char25D_Short75s")
    # Extend sequence duration to cover all 1,800 frames (75s)!
    for nd in mat_25d.node_tree.nodes:
        if nd.type == "TEX_IMAGE":
            nd.image_user.frame_duration = FRAME_END
            nd.image_user.frame_start = FRAME_START
            nd.image_user.frame_offset = 0
            nd.image_user.use_auto_refresh = True

    billboard = bpy.data.objects.new("Char_Billboard", mesh)
    billboard.data.materials.append(mat_25d)
    billboard.parent = mech_empty
    link_exclusively(billboard, char_col)

    lt = billboard.constraints.new(type="LOCKED_TRACK")
    lt.name = "Billboard_FaceCamera"
    lt.target = camera_obj
    lt.track_axis = "TRACK_NEGATIVE_Y"
    lt.lock_axis = "LOCK_Z"

    return {"empty_mechanic": mech_empty, "billboard": billboard, "material": mat_25d}


def animate_75s_torch_and_cable(
    scene: bpy.types.Scene,
    billboard_obj: bpy.types.Object,
    torch_obj: bpy.types.Object,
    cable_mid_sag: Optional[bpy.types.Object],
) -> None:
    """
    Sync 3D Welding Torch across the 75s story:
      - Hook (1..42) & Climax (1033..1435): nozzle locked 0.0mm to car fender seam, grip in hand!
      - Acts 1–2 (49..860): torch parked neatly on MIG welder cart holster while mechanic moves around!
      - Act 3 Prep (861..1032) & Act 5 Payoff (1436..1800): torch gripped cleanly in mechanic's hand!
    """
    hand_doc = json.loads(CHAR_HAND_SYNC_PATH.read_text(encoding="utf-8"))
    hand_frames: Dict[str, Dict[str, float]] = hand_doc["frames"]
    sorted_frames = sorted(int(k) for k in hand_frames.keys())

    torch_tip_local = Vector((0.0, 0.208, -0.045))
    q_swan_fix = torch_tip_local.normalized().rotation_difference(Vector((0.0, 1.0, 0.0)))
    torch_obj.rotation_mode = "XYZ"
    prev_euler: Optional[Euler] = None
    holster_pos = Vector((0.84, -1.24, 0.68))
    holster_rot = Euler((0.25, 0.0, 2.35), "XYZ")

    for f in sorted_frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        bb_eval = billboard_obj.evaluated_get(deps)

        h_entry = hand_frames[str(f)]
        hand_w = billboard_uv_to_world(bb_eval, float(h_entry["u"]), float(h_entry["v"]), depth_offset=-0.025)

        if HOOK_ARC_START <= f <= HOOK_ARC_END + 4:
            u_h = 0.42 + 0.18 * min(1.0, (f - HOOK_ARC_START) / float(max(1, HOOK_ARC_END - HOOK_ARC_START)))
            seam_pt = eval_weld_seam_point(u_h)
            rot_quat = _aim_torch_tip_quat(seam_pt - hand_w, q_swan_fix)
            torch_pos = seam_pt - (rot_quat.to_matrix() @ torch_tip_local)
            cur_euler = rot_quat.to_euler("XYZ", prev_euler) if prev_euler else rot_quat.to_euler("XYZ")
        elif 48 <= f <= 860:
            # Torch rests cleanly on the MIG welder cart while mechanic walks across LOC 1, 5, 3, 4!
            torch_pos = holster_pos
            cur_euler = holster_rot.copy()
        elif CLIMAX_ARC_START <= f <= CLIMAX_ARC_END:
            u_w = (f - CLIMAX_ARC_START) / float(max(1, CLIMAX_ARC_END - CLIMAX_ARC_START))
            seam_pt = eval_weld_seam_point(u_w)
            rot_quat = _aim_torch_tip_quat(seam_pt - hand_w, q_swan_fix)
            torch_pos = seam_pt - (rot_quat.to_matrix() @ torch_tip_local)
            cur_euler = rot_quat.to_euler("XYZ", prev_euler) if prev_euler else rot_quat.to_euler("XYZ")
        elif 980 <= f < CLIMAX_ARC_START:
            alpha = (f - 980.0) / float(CLIMAX_ARC_START - 980)
            seam_pt = eval_weld_seam_point(0.0)
            rot_quat = _aim_torch_tip_quat(seam_pt - hand_w, q_swan_fix)
            weld_pos = seam_pt - (rot_quat.to_matrix() @ torch_tip_local)
            torch_pos = hand_w.lerp(weld_pos, alpha)
            cur_euler = rot_quat.to_euler("XYZ", prev_euler) if prev_euler else rot_quat.to_euler("XYZ")
        else:
            fender_aim = (eval_weld_seam_point(0.3) + Vector((-0.08, -0.06, -0.10))) - hand_w
            rot_quat = _aim_torch_tip_quat(fender_aim, q_swan_fix)
            torch_pos = hand_w
            cur_euler = rot_quat.to_euler("XYZ", prev_euler) if prev_euler else rot_quat.to_euler("XYZ")

        prev_euler = cur_euler.copy()
        torch_obj.location = torch_pos
        torch_obj.rotation_euler = cur_euler
        torch_obj.keyframe_insert(data_path="location", frame=f)
        torch_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        if cable_mid_sag is not None:
            cable_mid_sag.location = (
                0.36 + (torch_pos.x + 0.20) * 0.25,
                -0.96 + (torch_pos.y + 0.65) * 0.25,
                0.14 + max(0.0, (torch_pos.z - 0.55) * 0.16),
            )
            cable_mid_sag.keyframe_insert(data_path="location", frame=f)

    _smooth_obj_fcurves(torch_obj)
    if cable_mid_sag is not None:
        _smooth_obj_fcurves(cable_mid_sag)


def main() -> None:
    args = parse_cli_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END

    if args.frames.strip():
        target_frames = [int(x.strip()) for x in args.frames.split(",") if x.strip()]
    elif args.mode == "debug":
        target_frames = list(DEBUG_FRAMES)
    else:
        target_frames = list(range(args.start, args.end + 1))

    print("[Short75s 1/5] Building 6-Location Cel-Shaded Workshop Compound & Cleaned Car...")
    env_data = build_6location_workshop_world()
    if "seam_points" in env_data:
        set_active_weld_seam(env_data["seam_points"], env_data.get("seam_normals"))

    print("[Short75s 2/5] Building 30-Move Continuous 3D Virtual Camera Rig...")
    cam_data = build_30move_continuous_camera_rig(scene, sample_step=2, extra_frames=target_frames)

    print("[Short75s 3/5] Building 6-Location 2.5D Dynamic Billboard Character...")
    char_data = build_75s_mechanic_billboard(cam_data["camera"], target_frames)

    print("[Short75s 4/5] Building Low-Sun, Long-Shadow, Blue-Shade, God-Rays, Haze & Dual-Arc VFX...")
    build_75s_lighting_and_vfx(
        scene=scene,
        torch_tip_empty=env_data["torch_tip"],
        seam_prog_node=env_data["seam_prog_node"],
        seam_heat_node=env_data["seam_heat_node"],
        godray_col_node=env_data["godray_col_node"],
        godray_alpha_node=env_data["godray_alpha_node"],
    )

    print("[Short75s 5/5] Synchronizing 3D Welding Torch & Cable Across 75s Story...")
    animate_75s_torch_and_cable(
        scene=scene,
        billboard_obj=char_data["billboard"],
        torch_obj=env_data["torch_root"],
        cable_mid_sag=env_data["cable_mid_sag"],
    )

    if args.mode == "debug":
        DEBUG_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        configure_render_and_compositor(scene, DEBUG_RES_X, DEBUG_RES_Y, samples=3 if args.fast_ci else 5, fast_ci=args.fast_ci)
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        if hasattr(scene.render, "use_persistent_data"):
            scene.render.use_persistent_data = True

        report: Dict[str, Any] = {"frames": {}, "jack_contacts": env_data.get("jack_contacts", {})}
        for idx, f in enumerate(target_frames, start=1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            cam_ev = cam_data["camera"].evaluated_get(deps)
            bb_ev = char_data["billboard"].evaluated_get(deps)
            head_ndc = world_to_camera_view(scene, cam_ev, bb_ev.matrix_world @ Vector((0.0, 0.0, CHAR_BILLBOARD_HEIGHT * 0.72)))
            report["frames"][str(f)] = {
                "head_ndc": [round(head_ndc.x, 3), round(head_ndc.y, 3), round(head_ndc.z, 3)],
                "lens_mm": round(cam_ev.data.lens, 2),
            }
            out_png = DEBUG_FRAMES_DIR / f"short_debug_{f:04d}.png"
            scene.render.filepath = str(out_png)
            print(f"[Short75s Debug {idx}/{len(target_frames)}] Frame {f} -> {out_png}", flush=True)
            bpy.ops.render.render(write_still=True)

        (OUTPUT_DIR / "verification_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        frames_dir = Path(args.frames_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)
        configure_render_and_compositor(scene, args.width, args.height, samples=args.samples, fast_ci=args.fast_ci)
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.use_file_extension = True
        if hasattr(scene.render, "use_persistent_data"):
            scene.render.use_persistent_data = True
        scene.frame_start = args.start
        scene.frame_end = args.end
        scene.frame_step = 1
        scene.render.filepath = str(frames_dir / "frame_")
        print(f"[Short75s Shard] Persistent animation {args.start}..{args.end} ({args.width}x{args.height})", flush=True)
        bpy.ops.render.render(animation=True)

    if args.save_blend:
        BLEND_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_FILE_PATH), compress=True)
        print(f"[Short75s Saved] {BLEND_FILE_PATH}")

    print("[Short75s] Completed with 0 errors!")


if __name__ == "__main__":
    main()
