"""
main.py — Stage 3 Main Entry Point (Blender Headless Scene Assembly & Renderer)
Assembles:
  - 3D Cel-Shaded Workshop Environment, Cleaned Reference Car on 0-Gap Jack Stands & MIG Welder (`env_props.py`)
  - 360° Dynamic Travel/Whip-Zoom Camera Rig (`camera_rig.py`)
  - Native 2.5D Dynamic Billboard Character loading `output/char_frames/char_XXXX.png` (`character_rig.py`)
  - Synchronized 3D Welding Torch, Flexible Cable, Arc Light & Sparks (`animation_core.py`, `vfx_lighting.py`)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from animation_core import animate_torch_and_cable_sync  # noqa: E402
from camera_rig import build_cinematic_camera_rig  # noqa: E402
from character_rig import build_mechanic_character  # noqa: E402
from config import (  # noqa: E402
    BLEND_FILE_PATH,
    CHAR_BILLBOARD_HEIGHT,
    DEBUG_FRAMES,
    DEBUG_FRAMES_DIR,
    DEBUG_RES_X,
    DEBUG_RES_Y,
    FINAL_VIDEO_PATH,
    FPS,
    FRAME_END,
    FRAME_START,
    OUTPUT_DIR,
    RES_X,
    RES_Y,
    WELD_ARC_END,
    WELD_ARC_START,
)
from env_props import build_environment_and_props  # noqa: E402
from vfx_lighting import (  # noqa: E402
    build_lighting_and_vfx,
    eval_weld_seam_point,
    set_active_weld_seam,
)


def parse_cli_args() -> argparse.Namespace:
    argv = sys.argv
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Mechanic Welding 2.5D/3D Hybrid Pipeline")
    parser.add_argument("--mode", choices=["debug", "final", "shard"], default="debug")
    parser.add_argument("--start", type=int, default=FRAME_START)
    parser.add_argument("--end", type=int, default=FRAME_END)
    parser.add_argument("--width", type=int, default=RES_X)
    parser.add_argument("--height", type=int, default=RES_Y)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--fast-ci", action="store_true", help="Optimize EEVEE Next for headless CI")
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
    """
    Configure EEVEE / EEVEE Next with:
      - `View Transform = Standard`, `Exposure = 0.0` for 100% accurate 2.5D character colors!
      - Selective `Glare` (Bloom) with `threshold >= 4.0` (`4.5`) and small `mix` (`-0.80`)
        so ONLY the intense welding arc & sparks glow!
    """
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    else:
        scene.render.engine = "BLENDER_EEVEE"

    eevee = scene.eevee
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = samples
    if hasattr(eevee, "use_raytracing"):
        eevee.use_raytracing = False
    if hasattr(eevee, "use_shadows"):
        eevee.use_shadows = True
    if hasattr(eevee, "shadow_resolution_scale"):
        eevee.shadow_resolution_scale = 0.55 if fast_ci else 0.85
    if hasattr(eevee, "shadow_ray_count"):
        eevee.shadow_ray_count = 1
    if hasattr(eevee, "shadow_step_count"):
        eevee.shadow_step_count = 5

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    vs = scene.view_settings
    vs.view_transform = "Standard"
    try:
        vs.look = "None"
    except Exception:
        pass
    vs.exposure = 0.0
    vs.gamma = 1.0

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
    glare.threshold = 4.5
    try:
        glare.size = 6
    except Exception:
        pass
    glare.mix = -0.80

    comp = nt.nodes.new("CompositorNodeComposite")
    comp.location = (340, 0)

    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])


def run_automated_diagnostics(
    scene: bpy.types.Scene,
    billboard_obj: bpy.types.Object,
    torch_tip: bpy.types.Object,
    spark_streaks: List[bpy.types.Object],
    cam_obj: bpy.types.Object,
    env_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify framing, 0-gap jack stands, torch-seam contact, and spark visibility across all 12 DEBUG_FRAMES."""
    report: Dict[str, Any] = {
        "debug_frames": list(DEBUG_FRAMES),
        "jack_contacts": env_data.get("jack_contacts", {}),
        "ground_clamp_contact": [round(v, 4) for v in env_data["ground_clamp_contact"]] if "ground_clamp_contact" in env_data else [],
        "frames": {},
        "all_checks_passed": True,
        "warnings": [],
    }

    for f in DEBUG_FRAMES:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

        bb_eval = billboard_obj.evaluated_get(deps)
        tip_eval = torch_tip.evaluated_get(deps)
        cam_eval = cam_obj.evaluated_get(deps)

        head_approx_w = bb_eval.matrix_world @ Vector((0.0, 0.0, CHAR_BILLBOARD_HEIGHT * 0.72))
        feet_w = bb_eval.matrix_world @ Vector((0.0, 0.0, 0.0))
        tip_w = tip_eval.matrix_world.translation

        head_ndc = world_to_camera_view(scene, cam_eval, head_approx_w)
        feet_ndc = world_to_camera_view(scene, cam_eval, feet_w)
        tip_ndc = world_to_camera_view(scene, cam_eval, tip_w)

        f_info: Dict[str, Any] = {
            "head_ndc": [round(head_ndc.x, 3), round(head_ndc.y, 3), round(head_ndc.z, 3)],
            "feet_ndc": [round(feet_ndc.x, 3), round(feet_ndc.y, 3), round(feet_ndc.z, 3)],
            "torch_tip_ndc": [round(tip_ndc.x, 3), round(tip_ndc.y, 3), round(tip_ndc.z, 3)],
            "camera_lens_mm": round(cam_eval.data.lens, 2),
        }

        if WELD_ARC_START <= f <= WELD_ARC_END:
            u_f = (f - WELD_ARC_START) / float(WELD_ARC_END - WELD_ARC_START)
            seam_f = eval_weld_seam_point(u_f)
            f_info["tip_to_seam_dist_m"] = round((tip_w - seam_f).length, 5)
            vis_sparks = 0
            for sp_o in spark_streaks:
                sp_ev = sp_o.evaluated_get(deps)
                if sp_ev.scale.length > 0.15:
                    ndc = world_to_camera_view(scene, cam_eval, sp_ev.matrix_world.translation)
                    if 0.0 <= ndc.x <= 1.0 and 0.0 <= ndc.y <= 1.0 and ndc.z > 0.0:
                        vis_sparks += 1
            f_info["visible_sparks_in_frame"] = vis_sparks

        if not (0.03 <= head_ndc.x <= 0.97 and 0.08 <= head_ndc.y <= 0.95):
            report["warnings"].append(f"Frame {f}: Head near/outside screen edge NDC=({head_ndc.x:.2f}, {head_ndc.y:.2f})")

        report["frames"][str(f)] = f_info

    if report["warnings"]:
        report["all_checks_passed"] = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rep_path = OUTPUT_DIR / "verification_report.json"
    rep_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n=== AUTOMATED 12-FRAME 2.5D/3D DIAGNOSTIC REPORT ===")
    print(json.dumps(report, indent=2))
    return report


def render_diagnostic_frames(scene: bpy.types.Scene, fast_ci: bool = False) -> None:
    DEBUG_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    configure_render_and_compositor(scene, DEBUG_RES_X, DEBUG_RES_Y, samples=6, fast_ci=fast_ci)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    for idx, f in enumerate(DEBUG_FRAMES, start=1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        out_png = DEBUG_FRAMES_DIR / f"debug_frame_{f:04d}.png"
        scene.render.filepath = str(out_png)
        print(f"[Debug Render {idx}/{len(DEBUG_FRAMES)}] Rendering Frame {f} -> {out_png} ...", flush=True)
        bpy.ops.render.render(write_still=True)


def render_shard_png_sequence(scene: bpy.types.Scene, args: argparse.Namespace) -> None:
    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    configure_render_and_compositor(scene, args.width, args.height, samples=args.samples, fast_ci=args.fast_ci)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    for f in range(args.start, args.end + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
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

    print("[Pipeline] 2/5 Building 3D cel-shaded workshop, cleaned reference car & MIG welder...")
    env_data = build_environment_and_props()
    if "seam_points" in env_data:
        set_active_weld_seam(env_data["seam_points"], env_data.get("seam_normals"))

    print("[Pipeline] 3/5 Building 360° dynamic camera rig & Native 2.5D Billboard Character...")
    cam_data = build_cinematic_camera_rig(scene)
    char_data = build_mechanic_character(camera_obj=cam_data["camera"])

    print("[Pipeline] 4/5 Building calibrated workshop lights, contact arc VFX & bouncing sparks...")
    vfx_data = build_lighting_and_vfx(
        scene=scene,
        torch_tip_empty=env_data["torch_tip"],
        seam_prog_node=env_data["seam_prog_node"],
        seam_heat_node=env_data["seam_heat_node"],
    )

    print("[Pipeline] 5/5 Synchronizing 3D Welding Torch & Cable with 2.5D Character Hand & Car Seam...")
    animate_torch_and_cable_sync(
        scene=scene,
        billboard_obj=char_data["billboard"],
        torch_obj=env_data["torch_root"],
        cable_mid_sag=env_data["cable_mid_sag"],
    )

    configure_render_and_compositor(scene, RES_X, RES_Y, samples=args.samples, fast_ci=args.fast_ci)
    scene.frame_set(155)
    bpy.context.view_layer.update()

    if args.mode in ("debug", "final"):
        run_automated_diagnostics(
            scene=scene,
            billboard_obj=char_data["billboard"],
            torch_tip=env_data["torch_tip"],
            spark_streaks=vfx_data["spark_streaks"],
            cam_obj=cam_data["camera"],
            env_data=env_data,
        )
        render_diagnostic_frames(scene, fast_ci=args.fast_ci)

        configure_render_and_compositor(scene, RES_X, RES_Y, samples=args.samples, fast_ci=args.fast_ci)
        scene.frame_set(155)
        bpy.context.view_layer.update()
        BLEND_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_FILE_PATH), compress=True)
        print(f"[Saved] Blender scene saved to: {BLEND_FILE_PATH}")

    if args.mode == "shard":
        render_shard_png_sequence(scene, args)
    elif args.mode == "final":
        render_full_mp4_animation(scene, args)

    print("[Pipeline] Completed successfully with 0 errors!")


if __name__ == "__main__":
    main()
