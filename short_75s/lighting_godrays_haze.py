"""
short_75s/lighting_godrays_haze.py — Dynamic Story-Driven Lighting & Welding VFX:
  - Low Grazing Sun (`Light_LowSun`) casting Long Dramatic Shadows across the workshop
  - Cool Blue Shade (`Light_BlueShade_*`) deepening dramatically during the Act 3 Twilight Turn
  - Volumetric God Rays & Atmospheric Haze animated smoothly across all 5 Acts
  - Dual-Window Welding Arc (`Welding_Arc_Light`) & Bouncing Sparks during BOTH the 2s Hook
    (Frames 1..38) AND the High-Energy Climax (Frames 1033..1435)!
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import bmesh
import bpy
from mathutils import Euler, Vector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import PALETTE_HEX, hex_to_rgb, hex_to_rgba  # noqa: E402
from env_props import get_or_create_collection, link_exclusively  # noqa: E402
from shaders import get_emission_material  # noqa: E402
from vfx_lighting import (  # noqa: E402
    _get_action_fcurves,
    add_restricted_noise_modifier,
    eval_weld_seam_normal,
    eval_weld_seam_point,
)

from short_75s.config_short import (  # noqa: E402
    CLIMAX_ARC_END,
    CLIMAX_ARC_START,
    FRAME_END,
    HOOK_ARC_END,
    HOOK_ARC_START,
    RANDOM_SEED,
)
from short_75s.story_beats import LIGHTING_MOOD_KEYS  # noqa: E402


def _setup_haze_world(scene: bpy.types.Scene) -> bpy.types.Node:
    """Configure clean deep-blue atmospheric world background (no global washout haze!)."""
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Short75s_World")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (360, 0)

    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (80, 0)
    bg.inputs["Color"].default_value = hex_to_rgba("#182848")
    bg.inputs["Strength"].default_value = 0.24
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return bg


def _create_area_light(
    name: str,
    col: bpy.types.Collection,
    location: Tuple[float, float, float],
    target_pt: Tuple[float, float, float],
    energy: float,
    hex_color: str,
    size: float = 1.4,
    cast_shadow: bool = True,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name + "_Data", type="AREA")
    ldata.energy = energy
    ldata.color = hex_to_rgb(hex_color)
    ldata.size = size
    if hasattr(ldata, "use_shadow"):
        ldata.use_shadow = cast_shadow

    lobj = bpy.data.objects.new(name, ldata)
    lobj.location = location
    direction = (Vector(target_pt) - Vector(location)).normalized()
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    link_exclusively(lobj, col)
    return lobj


def build_75s_lighting_and_vfx(
    scene: bpy.types.Scene,
    torch_tip_empty: bpy.types.Object,
    seam_prog_node: bpy.types.Node,
    seam_heat_node: bpy.types.Node,
    hero_window_loc: Tuple[float, float, float],
    haze_col_sock: bpy.types.NodeSocket,
    haze_dens_sock: bpy.types.NodeSocket,
) -> Dict[str, Any]:
    """Build dynamic Low-Sun + Long-Shadow + Blue-Shade + Single Real Window God Ray + Dual-Arc VFX."""
    vfx_col = get_or_create_collection("Col_VFX_Lighting")
    _setup_haze_world(scene)

    # Enable real EEVEE Next Volumetric Shadows so the Window God Ray is PHYSICALLY BLOCKED
    # by the window mullions, car, workbench, and character (NEVER penetrates props/char!)
    eevee = scene.eevee
    if hasattr(eevee, "use_volumetric_shadows"):
        eevee.use_volumetric_shadows = True
    if hasattr(eevee, "volumetric_tile_size"):
        eevee.volumetric_tile_size = "4"
    if hasattr(eevee, "volumetric_samples"):
        eevee.volumetric_samples = 32
    if hasattr(eevee, "volumetric_start"):
        eevee.volumetric_start = 0.25
    if hasattr(eevee, "volumetric_end"):
        eevee.volumetric_end = 18.0

    # ==========================================================================
    # 1. LOW GRAZING SUN (`Light_LowSun`) -> LONG DRAMATIC SHADOWS
    # ==========================================================================
    sun_data = bpy.data.lights.new("Light_LowSun_Data", type="SUN")
    sun_data.energy = 6.2
    sun_data.angle = math.radians(1.2)
    if hasattr(sun_data, "use_shadow"):
        sun_data.use_shadow = True
    sun_obj = bpy.data.objects.new("Light_LowSun", sun_data)
    sun_obj.location = (-8.0, -3.0, 2.5)
    link_exclusively(sun_obj, vfx_col)

    # ==========================================================================
    # 1B. SINGLE PHYSICAL WINDOW GOD-RAY SPOT LIGHT (`Light_Window_GodRay`)
    # Positioned OUTSIDE the Hero Window aiming cleanly through its 3D steel mullions!
    # ==========================================================================
    spot_data = bpy.data.lights.new("Light_Window_GodRay_Data", type="SPOT")
    spot_data.energy = 2600.0
    spot_data.color = hex_to_rgb("#FFC470")
    spot_data.spot_size = math.radians(42.0)
    spot_data.spot_blend = 0.28
    spot_data.shadow_soft_size = 0.03
    if hasattr(spot_data, "use_shadow"):
        spot_data.use_shadow = True

    spot_obj = bpy.data.objects.new("Light_Window_GodRay", spot_data)
    wx, wy, wz = hero_window_loc
    spot_origin = Vector((wx - 2.20, wy + 0.65, wz + 0.95))
    spot_target = Vector((wx + 3.60, wy - 1.95, 0.35))
    spot_obj.location = tuple(spot_origin)
    spot_obj.rotation_euler = (spot_target - spot_origin).normalized().to_track_quat("-Z", "Y").to_euler()
    link_exclusively(spot_obj, vfx_col)

    # ==========================================================================
    # 2. BLUE SHADE & WORKSHOP PRACTICAL PENDANT LIGHTS
    # ==========================================================================
    blue_sky = _create_area_light(
        "Light_BlueShade_Sky", vfx_col,
        location=(1.8, 1.4, 3.2), target_pt=(-0.4, -0.6, 0.8),
        energy=26.0, hex_color="#3D74C8", size=2.8, cast_shadow=False,
    )
    blue_courtyard = _create_area_light(
        "Light_BlueShade_Courtyard", vfx_col,
        location=(-6.2, 1.5, 3.1), target_pt=(-5.5, -1.2, 0.7),
        energy=22.0, hex_color="#4882D6", size=3.2, cast_shadow=False,
    )
    pendant_bay = _create_area_light(
        "Light_Pendant_Bay", vfx_col,
        location=(-0.20, -0.55, 2.86), target_pt=(-0.20, -0.55, 0.70),
        energy=28.0, hex_color="#FFD49A", size=1.35, cast_shadow=True,
    )
    pendant_bench = _create_area_light(
        "Light_Pendant_Workbench", vfx_col,
        location=(2.10, -0.65, 2.85), target_pt=(2.75, -0.65, 1.00),
        energy=26.0, hex_color="#FFE0B0", size=1.40, cast_shadow=False,
    )
    pendant_alcove = _create_area_light(
        "Light_Pendant_PartsAlcove", vfx_col,
        location=(-1.05, 3.35, 2.85), target_pt=(-1.05, 3.95, 1.05),
        energy=24.0, hex_color="#D4E4FF", size=1.50, cast_shadow=False,
    )

    # Animate Low Sun elevation/color, Blue Shade intensity, God-Ray shafts & Haze as the story turns!
    for mk in LIGHTING_MOOD_KEYS:
        f = mk["f"]
        sun_data.energy = mk["sun_e"]
        sun_data.color = hex_to_rgb(mk["sun_col"])
        sun_data.keyframe_insert(data_path="energy", frame=f)
        sun_data.keyframe_insert(data_path="color", frame=f)

        # Grazing elevation angle streaming from -X/-Y open courtyard gate into the bay!
        elev_rad = math.radians(mk["sun_elev"])
        azim_rad = math.radians(-18.0)
        # Sun direction vector pointing FROM sun INTO workshop (+X, +Y, -Z)
        sun_dir = Vector((math.cos(elev_rad) * math.cos(azim_rad), math.cos(elev_rad) * math.sin(azim_rad), -math.sin(elev_rad))).normalized()
        sun_obj.rotation_euler = sun_dir.to_track_quat("-Z", "Y").to_euler()
        sun_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        blue_sky.data.energy = mk["blue_e"]
        blue_sky.data.keyframe_insert(data_path="energy", frame=f)
        blue_courtyard.data.energy = mk["blue_e"] * 0.85
        blue_courtyard.data.keyframe_insert(data_path="energy", frame=f)

        # Single physical Window God-Ray Spot Light + localized Volume Scatter haze!
        spot_data.energy = 7500.0 * mk["ray_alpha"]
        spot_data.color = hex_to_rgb(mk["ray_col"])
        spot_data.keyframe_insert(data_path="energy", frame=f)
        spot_data.keyframe_insert(data_path="color", frame=f)

        haze_col_sock.default_value = hex_to_rgba(mk["ray_col"])
        haze_col_sock.keyframe_insert(data_path="default_value", frame=f)
        haze_dens_sock.default_value = mk["haze"]
        haze_dens_sock.keyframe_insert(data_path="default_value", frame=f)

    # ==========================================================================
    # 3. DUAL-WINDOW WELDING ARC POINT LIGHT (`Welding_Arc_Light`) AT CAR CONTACT
    # Active during BOTH 2s Hook (1..38) AND Welding Climax (1033..1435)!
    # ==========================================================================
    arc_ldata = bpy.data.lights.new("Welding_Arc_Light_Data", type="POINT")
    arc_ldata.color = hex_to_rgb("#1EB2FF")
    arc_ldata.shadow_soft_size = 0.030
    if hasattr(arc_ldata, "use_shadow"):
        arc_ldata.use_shadow = True

    arc_light = bpy.data.objects.new("Welding_Arc_Light", arc_ldata)
    arc_light.parent = torch_tip_empty
    arc_light.location = (0.0, -0.008, 0.004)
    link_exclusively(arc_light, vfx_col)

    arc_keys = [
        (HOOK_ARC_START, 78.0),
        (HOOK_ARC_END, 78.0),
        (HOOK_ARC_END + 1, 0.0),
        (CLIMAX_ARC_START - 1, 0.0),
        (CLIMAX_ARC_START, 84.0),
        (CLIMAX_ARC_END, 84.0),
        (CLIMAX_ARC_END + 1, 0.0),
        (FRAME_END, 0.0),
    ]
    for f, val in arc_keys:
        arc_ldata.energy = val
        arc_ldata.keyframe_insert(data_path="energy", frame=f)

    for fc in _get_action_fcurves(arc_ldata):
        for kp in fc.keyframe_points:
            if kp.co.x in (HOOK_ARC_END + 1, CLIMAX_ARC_START - 1, CLIMAX_ARC_END + 1):
                kp.interpolation = "CONSTANT"
            else:
                kp.interpolation = "LINEAR"

    add_restricted_noise_modifier(arc_ldata, "energy", float(HOOK_ARC_START), float(HOOK_ARC_END), scale=1.2, strength=54.0, phase=3.1)
    add_restricted_noise_modifier(arc_ldata, "energy", float(CLIMAX_ARC_START), float(CLIMAX_ARC_END), scale=1.2, strength=56.0, phase=7.3)

    # Warm Orange Seam Ember Light right on the freshly welded car fender
    seam_mid_pt = eval_weld_seam_point(0.5)
    seam_mid_n = eval_weld_seam_normal(0.5)
    ember_ldata = bpy.data.lights.new("Light_SeamEmber_Data", type="POINT")
    ember_ldata.color = hex_to_rgb(PALETTE_HEX["seam_molten"])
    ember_ldata.shadow_soft_size = 0.05
    if hasattr(ember_ldata, "use_shadow"):
        ember_ldata.use_shadow = False
    ember_light = bpy.data.objects.new("Light_SeamEmber", ember_ldata)
    ember_light.location = tuple(seam_mid_pt + seam_mid_n * 0.025)
    link_exclusively(ember_light, vfx_col)

    for f, val in [
        (1, 18.0), (HOOK_ARC_END, 18.0), (HOOK_ARC_END + 2, 0.0),
        (CLIMAX_ARC_START, 0.0), (CLIMAX_ARC_START + 24, 18.0),
        (CLIMAX_ARC_END, 26.0), (1510, 14.0), (1620, 6.0), (FRAME_END, 2.0),
    ]:
        ember_ldata.energy = val
        ember_ldata.keyframe_insert(data_path="energy", frame=f)

    # ==========================================================================
    # 4. ARC PLASMA CORE & STARBURST AT NOZZLE CONTACT (`VFX_ArcCore`)
    # ==========================================================================
    mat_arc_core = get_emission_material("Mat_VFX_ArcCore", PALETTE_HEX["weld_arc_core"], strength=42.0)
    bm_core = bmesh.new()
    bmesh.ops.create_icosphere(bm_core, subdivisions=2, radius=0.018)
    for rot_ax in ((0.0, 0.0, 0.0), (0.0, math.pi / 3.0, 0.4), (math.pi / 2.0, 0.3, -0.5)):
        verts_f = [
            bm_core.verts.new(Euler(rot_ax).to_matrix() @ Vector(co))
            for co in ((-0.052, 0.0, 0.0), (0.0, 0.0, 0.009), (0.052, 0.0, 0.0), (0.0, 0.0, -0.009))
        ]
        bm_core.faces.new(verts_f)
    arc_mesh = bpy.data.meshes.new("VFX_ArcCore_Mesh")
    bm_core.to_mesh(arc_mesh)
    bm_core.free()

    arc_core_obj = bpy.data.objects.new("VFX_ArcCore", arc_mesh)
    arc_core_obj.data.materials.append(mat_arc_core)
    arc_core_obj.parent = torch_tip_empty
    arc_core_obj.location = (0.0, 0.0, 0.0)
    link_exclusively(arc_core_obj, vfx_col)

    for f, sc in [
        (HOOK_ARC_START, (1.0, 1.0, 1.0)),
        (HOOK_ARC_END, (1.0, 1.0, 1.0)),
        (HOOK_ARC_END + 1, (0.0, 0.0, 0.0)),
        (CLIMAX_ARC_START - 1, (0.0, 0.0, 0.0)),
        (CLIMAX_ARC_START, (1.0, 1.0, 1.0)),
        (CLIMAX_ARC_END, (1.0, 1.0, 1.0)),
        (CLIMAX_ARC_END + 1, (0.0, 0.0, 0.0)),
        (FRAME_END, (0.0, 0.0, 0.0)),
    ]:
        arc_core_obj.scale = sc
        arc_core_obj.keyframe_insert(data_path="scale", frame=f)

    for ax_i in range(3):
        add_restricted_noise_modifier(arc_core_obj, "scale", float(HOOK_ARC_START), float(HOOK_ARC_END), scale=1.4, strength=0.55, phase=ax_i * 7.1, index=ax_i)
        add_restricted_noise_modifier(arc_core_obj, "scale", float(CLIMAX_ARC_START), float(CLIMAX_ARC_END), scale=1.4, strength=0.55, phase=ax_i * 11.7, index=ax_i)

    # ==========================================================================
    # 5. DETERMINISTIC BOUNCING SPARK STREAKS (Hook + Climax Windows!)
    # ==========================================================================
    mat_spark_hot = get_emission_material("Mat_VFX_SparkHot", "#FFF2A6", strength=28.0)
    mat_spark_org = get_emission_material("Mat_VFX_SparkOrange", "#FF8E26", strength=22.0)

    rng = random.Random(RANDOM_SEED + 1033)
    num_streaks = 44
    dt = 1.0 / 24.0
    gravity = Vector((0.0, 0.0, -9.2))
    windows = [(HOOK_ARC_START, HOOK_ARC_END), (CLIMAX_ARC_START, CLIMAX_ARC_END)]

    streak_objs: List[bpy.types.Object] = []
    for s_idx in range(num_streaks):
        bm_st = bmesh.new()
        bmesh.ops.create_icosphere(bm_st, subdivisions=1, radius=1.0)
        bmesh.ops.scale(bm_st, vec=(0.0080, 0.058, 0.0080), verts=bm_st.verts)
        st_mesh = bpy.data.meshes.new(f"VFX_SparkStreak_{s_idx:02d}_Mesh")
        bm_st.to_mesh(st_mesh)
        bm_st.free()
        st_obj = bpy.data.objects.new(f"VFX_SparkStreak_{s_idx:02d}", st_mesh)
        st_obj.data.materials.append(mat_spark_hot if s_idx % 2 == 0 else mat_spark_org)
        link_exclusively(st_obj, vfx_col)
        streak_objs.append(st_obj)

        for w_start, w_end in windows:
            if w_start > 1:
                st_obj.scale = (0.0, 0.0, 0.0)
                st_obj.keyframe_insert(data_path="scale", frame=w_start - 1)

            life_frames = rng.randint(10, 16)
            f_cur = w_start + (s_idx % 10)
            while f_cur <= w_end:
                if w_start == HOOK_ARC_START:
                    u_seam = 0.42 + 0.18 * ((f_cur - w_start) / max(1.0, float(w_end - w_start)))
                else:
                    u_seam = (f_cur - w_start) / max(1.0, float(w_end - w_start))
                s_origin = eval_weld_seam_point(u_seam)
                s_norm = eval_weld_seam_normal(u_seam)
                pos = s_origin + s_norm * 0.003

                vel = Vector((rng.uniform(-2.2, 2.2), rng.uniform(-2.6, -0.35), rng.uniform(0.35, 2.40)))
                for age in range(life_frames + 1):
                    frame_k = f_cur + age
                    if frame_k > w_end + 12:
                        break
                    sc_val = 0.0 if age >= life_frames else (1.0 - (age / float(life_frames)) ** 1.6) * 1.25
                    speed = vel.length
                    stretch = min(2.2, max(0.5, speed * 0.42))
                    st_obj.location = pos
                    if speed > 1e-4:
                        st_obj.rotation_euler = vel.normalized().to_track_quat("Y", "Z").to_euler()
                    st_obj.scale = (sc_val, sc_val * stretch, sc_val)
                    st_obj.keyframe_insert(data_path="location", frame=frame_k)
                    st_obj.keyframe_insert(data_path="rotation_euler", frame=frame_k)
                    st_obj.keyframe_insert(data_path="scale", frame=frame_k)

                    vel = vel + gravity * dt
                    pos = pos + vel * dt
                    if -0.85 <= pos.x <= 0.35 and 0.30 <= pos.z <= 0.90:
                        pen = (pos - s_origin).dot(s_norm)
                        if pen < 0.004 and pos.y > s_origin.y - 0.02:
                            pos = pos + s_norm * (0.005 - pen)
                            vn = vel.dot(s_norm)
                            if vn < 0.0:
                                vel = (vel - 1.65 * vn * s_norm) * 0.78
                    if pos.z < 0.008:
                        pos.z = 0.008
                        vel.z = abs(vel.z) * 0.46
                        vel.x *= 0.72
                        vel.y *= 0.72
                f_cur += life_frames + rng.randint(1, 4)

            st_obj.scale = (0.0, 0.0, 0.0)
            st_obj.keyframe_insert(data_path="scale", frame=w_end + 13)

        st_obj.scale = (0.0, 0.0, 0.0)
        st_obj.keyframe_insert(data_path="scale", frame=FRAME_END)

    # ==========================================================================
    # 6. ANIMATE MOLTEN WELD SEAM REVEAL & COOLING EMBER GLOW
    # ==========================================================================
    p_sock = seam_prog_node.outputs[0]
    for f, pv in [
        (1, 0.55), (HOOK_ARC_END, 0.65), (HOOK_ARC_END + 2, 0.0),
        (CLIMAX_ARC_START - 1, 0.0), (CLIMAX_ARC_START, 0.03),
        (CLIMAX_ARC_END, 1.0), (FRAME_END, 1.0),
    ]:
        p_sock.default_value = pv
        p_sock.keyframe_insert(data_path="default_value", frame=f)

    h_sock = seam_heat_node.outputs[0]
    for f, hv in [
        (1, 1.0), (HOOK_ARC_END, 1.0), (HOOK_ARC_END + 2, 0.0),
        (CLIMAX_ARC_START - 1, 0.0), (CLIMAX_ARC_START, 1.0),
        (CLIMAX_ARC_END, 1.0), (1475, 0.76), (1580, 0.48), (FRAME_END, 0.22),
    ]:
        h_sock.default_value = hv
        h_sock.keyframe_insert(data_path="default_value", frame=f)

    return {
        "vfx_collection": vfx_col,
        "sun_obj": sun_obj,
        "blue_sky": blue_sky,
        "arc_light": arc_light,
        "ember_light": ember_light,
        "arc_core_obj": arc_core_obj,
        "spark_streaks": streak_objs,
    }
