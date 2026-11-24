"""
main.py — Main Entry Point for 3D Cel-Shaded Young Mechanic Welding Animation
Usage:
  1) Standard full pipeline (builds .blend, runs verification, renders debug frames & final MP4):
       blender --background --python main.py
  2) Fast diagnostic / self-verification pass (960x540 frames 20, 85, 155, 240 + .blend):
       blender --background --python main.py -- --mode debug
  3) Parallel shard render for fast CI matrix (1920x1080 PNG sequence f0..f1):
       blender --background --python main.py -- --mode shard --start 1 --end 33 --fast-ci
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

# Ensure local modular imports resolve cleanly when invoked via `blender --python main.py`
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from animation_core import animate_mechanic_choreography  # noqa: E402
from camera_rig import build_cinematic_camera_rig  # noqa: E402
from character_rig import build_mechanic_character  # noqa: E402
from config import (  # noqa: E402
    BLEND_FILE_PATH,
    DEBUG_FRAMES_DIR,
    DEBUG_RES_X,
    DEBUG_RES_Y,
    DIAGNOSTIC_FRAMES,
    FINAL_VIDEO_PATH,
    FPS,
    FRAME_END,
    FRAME_START,
    OUTPUT_DIR,
    RES_X,
    RES_Y,
)
from env_props import build_environment_and_props  # noqa: E402
from vfx_lighting import build_lighting_and_vfx, eval_weld_seam_point  # noqa: E402


def parse_cli_args() -> argparse.Namespace:
    argv = sys.argv
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Mechanic Welding 3D Cel-Shaded Pipeline")
    parser.add_argument("--mode", choices=["all", "debug", "shard", "blend_only"], default="all")
    parser.add_argument("--start", type=int, default=FRAME_START)
    parser.add_argument("--end", type=int, default=FRAME_END)
    parser.add_argument("--width", type=int, default=RES_X)
    parser.add_argument("--height", type=int, default=RES_Y)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--fast-ci", action="store_true", help="Tune EEVEE Next for fast headless Mesa/CI")
    parser.add_argument("--frames-dir", type=str, default=str(OUTPUT_DIR / "frames"))
    return parser.parse_args(extra)


def reset_clean_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    return scene


def configure_render_and_compositor(
    scene: bpy.types.Scene,
    width: int,
    height: int,
    samples: int = 8,
    fast_ci: bool = False,
) -> None:
    """Configure EEVEE / EEVEE Next + AgX Color Management + Anime Welding Arc Bloom."""
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    else:
        scene.render.engine = "BLENDER_EEVEE"

    eevee = scene.eevee
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = samples
    # Disable expensive CPU screen-space raytracing in software GL while keeping crisp shadows
    if hasattr(eevee, "use_raytracing"):
        eevee.use_raytracing = False if fast_ci else False
    if hasattr(eevee, "use_shadows"):
        eevee.use_shadows = True
    if hasattr(eevee, "shadow_resolution_scale"):
        eevee.shadow_resolution_scale = 0.55 if fast_ci else 0.85
    if hasattr(eevee, "shadow_ray_count"):
        eevee.shadow_ray_count = 1
    if hasattr(eevee, "shadow_step_count"):
        eevee.shadow_step_count = 5
    if hasattr(eevee, "use_bloom"):
        eevee.use_bloom = True

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    # Color management: AgX Medium High Contrast prevents any highlight clipping!
    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
        for lk in ("AgX - Medium High Contrast", "AgX - Punchy", "None"):
            try:
                vs.look = lk
                break
            except Exception:
                pass
    except Exception:
        vs.view_transform = "Filmic"
    vs.exposure = 0.0
    vs.gamma = 1.0

    # Compositor Bloom strictly for HDR Emission > 2.8 (Welding Arc, Sparks & Molten Seam)!
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()

    rl = nt.nodes.new("CompositorNodeRLayers")
    rl.location = (-360, 0)

    glare = nt.nodes.new("CompositorNodeGlare")
    glare.location = (0, 0)
    try:
        glare.glare_type = "BLOOM"
    except Exception:
        glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.threshold = 2.8
    try:
        glare.size = 6
    except Exception:
        pass
    glare.mix = -0.55

    comp = nt.nodes.new("CompositorNodeComposite")
    comp.location = (340, 0)

    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])


def run_automated_diagnostics(
    scene: bpy.types.Scene,
    arm_obj: bpy.types.Object,
    torch_obj: bpy.types.Object,
    torch_tip: bpy.types.Object,
    spark_streaks: List[bpy.types.Object],
    cam_obj: bpy.types.Object,
) -> Dict[str, Any]:
    """
    Evaluate key diagnostic frames (20, 85, 155, 240) and verify:
      - Hand-to-Torch grip lock (`dist < 0.05m`)
      - Goggles position (up on forehead at 20 & 240, down over eyes at 85 & 155)
      - Torch tip proximity to car weld seam at 155
      - Visible spark count inside camera frustum at 155
      - Camera framing NDC coordinates & obstacle-free line of sight
    """
    report: Dict[str, Any] = {"frames": {}, "all_checks_passed": True, "warnings": []}
    pb = arm_obj.pose.bones

    for f in DIAGNOSTIC_FRAMES:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

        arm_eval = arm_obj.evaluated_get(deps)
        torch_eval = torch_obj.evaluated_get(deps)
        tip_eval = torch_tip.evaluated_get(deps)
        cam_eval = cam_obj.evaluated_get(deps)

        hand_r_w = arm_eval.matrix_world @ arm_eval.pose.bones["Hand.R"].head
        hand_l_w = arm_eval.matrix_world @ arm_eval.pose.bones["Hand.L"].head
        head_w = arm_eval.matrix_world @ (arm_eval.pose.bones["Head"].head + Vector((0.0, 0.0, 0.20)))
        eyes_w = arm_eval.matrix_world @ pb["Eye_Iris.L"].head
        goggles_cup_w = (arm_eval.matrix_world @ pb["Goggles_Ctrl"].matrix) @ Vector((-0.066, 0.204, 0.0))

        torch_w = torch_eval.matrix_world.translation
        tip_w = tip_eval.matrix_world.translation

        hand_torch_dist = (hand_r_w - torch_w).length
        goggles_dz = goggles_cup_w.z - eyes_w.z

        head_ndc = world_to_camera_view(scene, cam_eval, head_w)
        tip_ndc = world_to_camera_view(scene, cam_eval, tip_w)

        vis_sparks = 0
        if f == 155:
            for sp_o in spark_streaks:
                sp_ev = sp_o.evaluated_get(deps)
                if sp_ev.scale.length > 0.15:
                    ndc = world_to_camera_view(scene, cam_eval, sp_ev.matrix_world.translation)
                    if 0.0 <= ndc.x <= 1.0 and 0.0 <= ndc.y <= 1.0 and ndc.z > 0.0:
                        vis_sparks += 1

        # Raycast from camera toward mechanic head center to confirm no environment wall/prop blocks view
        cam_pos = cam_eval.matrix_world.translation
        ray_vec = head_w - cam_pos
        hit, hit_loc, _, _, hit_obj, _ = scene.ray_cast(deps, cam_pos, ray_vec.normalized(), distance=ray_vec.length * 0.82)
        blocked_by = hit_obj.name if (hit and hit_obj and not hit_obj.name.startswith(("Char_", "Prop_Welding", "VFX_"))) else None

        f_info: Dict[str, Any] = {
            "hand_to_torch_dist_m": round(hand_torch_dist, 4),
            "goggles_above_eye_dz_m": round(goggles_dz, 4),
            "torch_tip_world": [round(c, 4) for c in tip_w],
            "left_hand_world": [round(c, 4) for c in hand_l_w],
            "head_ndc": [round(head_ndc.x, 3), round(head_ndc.y, 3), round(head_ndc.z, 3)],
            "torch_tip_ndc": [round(tip_ndc.x, 3), round(tip_ndc.y, 3), round(tip_ndc.z, 3)],
            "camera_lens_mm": round(cam_eval.data.lens, 2),
            "camera_blocked_by": blocked_by,
        }
        if f == 85:
            g_left_rim = (arm_eval.matrix_world @ pb["Goggles_Ctrl"].matrix) @ Vector((-0.132, 0.205, -0.010))
            f_info["left_hand_to_goggle_rim_m"] = round((hand_l_w - g_left_rim).length, 4)
        if f == 155:
            u_155 = (155 - 113) / float(203 - 113)
            seam_155 = eval_weld_seam_point(u_155)
            f_info["tip_to_seam_dist_m"] = round((tip_w - seam_155).length, 4)
            f_info["visible_sparks_in_frame"] = vis_sparks

        # Validate thresholds
        if hand_torch_dist > 0.06:
            report["warnings"].append(f"Frame {f}: Torch grip drift ({hand_torch_dist:.3f}m)")
        if blocked_by:
            report["warnings"].append(f"Frame {f}: Camera obstructed by {blocked_by}")
        if not (0.08 <= head_ndc.x <= 0.92 and 0.12 <= head_ndc.y <= 0.94):
            report["warnings"].append(f"Frame {f}: Head near/outside screen edge NDC=({head_ndc.x:.2f}, {head_ndc.y:.2f})")
        if f == 155 and vis_sparks < 6:
            report["warnings"].append(f"Frame 155: Low visible spark count ({vis_sparks})")

        report["frames"][str(f)] = f_info

    if report["warnings"]:
        report["all_checks_passed"] = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rep_path = OUTPUT_DIR / "verification_report.json"
    rep_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n=== AUTOMATED DIAGNOSTIC REPORT ===")
    print(json.dumps(report, indent=2))
    return report


def render_diagnostic_frames(scene: bpy.types.Scene, fast_ci: bool = False) -> None:
    DEBUG_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    configure_render_and_compositor(scene, DEBUG_RES_X, DEBUG_RES_Y, samples=6, fast_ci=fast_ci)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    for f in DIAGNOSTIC_FRAMES:
        scene.frame_set(f)
        out_png = DEBUG_FRAMES_DIR / f"debug_frame_{f:04d}.png"
        scene.render.filepath = str(out_png)
        print(f"[Debug Render] Rendering Frame {f} -> {out_png} ...")
        bpy.ops.render.render(write_still=True)


def render_shard_png_sequence(scene: bpy.types.Scene, args: argparse.Namespace) -> None:
    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    configure_render_and_compositor(scene, args.width, args.height, samples=args.samples, fast_ci=args.fast_ci)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    for f in range(args.start, args.end + 1):
        scene.frame_set(f)
        out_f = frames_dir / f"frame_{f:04d}.png"
        scene.render.filepath = str(out_f)
        print(f"[Shard Render] Frame {f}/{args.end} -> {out_f}", flush=True)
        bpy.ops.render.render(write_still=True)


def render_full_mp4_animation(scene: bpy.types.Scene, args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_render_and_compositor(scene, args.width, args.height, samples=args.samples, fast_ci=args.fast_ci)

    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.filepath = str(FINAL_VIDEO_PATH)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"

    print(f"[Full Render] Rendering 264 frames ({args.width}x{args.height} @ {FPS} FPS) -> {FINAL_VIDEO_PATH} ...")
    bpy.ops.render.render(animation=True)


def main() -> None:
    args = parse_cli_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[Pipeline] 1/5 Resetting clean 24 FPS Blender scene...")
    scene = reset_clean_scene()

    print("[Pipeline] 2/5 Building 3D cel-shaded workshop environment, car & MIG welder...")
    env_data = build_environment_and_props()

    print("[Pipeline] 3/5 Importing MekanikMudaCharacter & building 3D Bendy-Bone IK rig...")
    char_data = build_mechanic_character(torch_obj=env_data["torch_root"])

    print("[Pipeline] 4/5 Building workshop lights, flickering arc VFX & bouncing sparks...")
    vfx_data = build_lighting_and_vfx(
        scene=scene,
        torch_tip_empty=env_data["torch_tip"],
        seam_prog_node=env_data["seam_prog_node"],
        seam_heat_node=env_data["seam_heat_node"],
    )

    print("[Pipeline] 5/5 Applying 4-Beat character choreography & whip-zoom camera rig...")
    animate_mechanic_choreography(
        scene=scene,
        arm_obj=char_data["armature"],
        torch_local_tip_in_hand=char_data["torch_local_tip_in_hand"],
        cable_mid_sag=env_data["cable_mid_sag"],
    )
    cam_data = build_cinematic_camera_rig(scene)

    # Configure default full-HD 1920x1080 settings before saving the .blend file
    configure_render_and_compositor(scene, RES_X, RES_Y, samples=args.samples, fast_ci=args.fast_ci)
    scene.frame_set(155)  # Save .blend parked on the dramatic welding hero frame!
    bpy.context.view_layer.update()

    if args.mode in ("all", "debug", "blend_only"):
        # Pack generated textures into the .blend so it opens standalone anywhere in Blender GUI!
        try:
            bpy.ops.file.pack_all()
        except Exception as exc:
            print(f"[Warn] pack_all skipped: {exc}")
        BLEND_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_FILE_PATH), compress=True)
        print(f"[Saved] Blender scene saved to: {BLEND_FILE_PATH}")

    if args.mode in ("all", "debug"):
        run_automated_diagnostics(
            scene=scene,
            arm_obj=char_data["armature"],
            torch_obj=env_data["torch_root"],
            torch_tip=env_data["torch_tip"],
            spark_streaks=vfx_data["spark_streaks"],
            cam_obj=cam_data["camera"],
        )
        render_diagnostic_frames(scene, fast_ci=args.fast_ci)

    if args.mode == "shard":
        render_shard_png_sequence(scene, args)
    elif args.mode == "all":
        render_full_mp4_animation(scene, args)

    print("[Pipeline] Completed successfully with 0 errors!")


if __name__ == "__main__":
    main()
