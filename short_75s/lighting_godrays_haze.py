"""
short_75s/lighting_godrays_haze.py — Dynamic Story-Driven Lighting & 3-Zone Welding VFX:
  - Low Grazing Sun (`Light_LowSun`) -> Long Shadows
  - Single Physical Window God-Ray Spot Light (`Light_Window_GodRay`) + Volumetric Shadows
    so the god ray NEVER penetrates props or character!
  - Cool Blue Shade deepening during Twilight Turn & 30s Welding Marathon
  - Multi-Zone Welding Arcs & Bouncing Sparks across Hook + Front + Side + Rear zones!
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import bmesh
import bpy
from mathutils import Euler, Vector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import PALETTE_HEX, hex_to_rgb, hex_to_rgba  # noqa: E402
from env_props import get_or_create_collection, link_exclusively  # noqa: E402
from shaders import get_emission_material  # noqa: E402
from vfx_lighting import _get_action_fcurves, add_restricted_noise_modifier  # noqa: E402

from short_75s.config_short import (  # noqa: E402
    FRAME_END,
    FRONT_ARC_END,
    FRONT_ARC_START,
    HOOK_ARC_END,
    HOOK_ARC_START,
    RANDOM_SEED,
    REAR_ARC_END,
    REAR_ARC_START,
    SIDE_ARC_END,
    SIDE_ARC_START,
)
from short_75s.story_beats import LIGHTING_MOOD_KEYS  # noqa: E402


def eval_zone_curve(pts: Sequence[Vector], u: float) -> Vector:
    u = max(0.0, min(1.0, u))
    if len(pts) < 2:
        return Vector(pts[0]) if pts else Vector((0.0, -0.42, 0.72))
    sc = u * (len(pts) - 1)
    idx = min(len(pts) - 2, int(math.floor(sc)))
    return Vector(pts[idx]).lerp(Vector(pts[idx + 1]), sc - idx)


def _setup_haze_world(scene: bpy.types.Scene) -> bpy.types.Node:
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
    weld_zones: Dict[str, Dict[str, Any]],
    hero_window_loc: Tuple[float, float, float],
    haze_col_sock: bpy.types.NodeSocket,
    haze_dens_sock: bpy.types.NodeSocket,
) -> Dict[str, Any]:
    vfx_col = get_or_create_collection("Col_VFX_Lighting")
    _setup_haze_world(scene)

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

    # 1. LOW GRAZING SUN -> LONG SHADOWS
    sun_data = bpy.data.lights.new("Light_LowSun_Data", type="SUN")
    sun_data.energy = 6.2
    sun_data.angle = math.radians(1.2)
    if hasattr(sun_data, "use_shadow"):
        sun_data.use_shadow = True
    sun_obj = bpy.data.objects.new("Light_LowSun", sun_data)
    sun_obj.location = (-8.0, -3.0, 2.5)
    link_exclusively(sun_obj, vfx_col)

    # 2. SINGLE PHYSICAL WINDOW GOD-RAY SPOT LIGHT
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

    # 3. BLUE SHADE & PRACTICAL PENDANTS
    blue_sky = _create_area_light("Light_BlueShade_Sky", vfx_col, (1.8, 1.4, 3.2), (-0.4, -0.6, 0.8), 26.0, "#3D74C8", 2.8, False)
    blue_courtyard = _create_area_light("Light_BlueShade_Courtyard", vfx_col, (-6.2, 1.5, 3.1), (-5.5, -1.2, 0.7), 22.0, "#4882D6", 3.2, False)
    _create_area_light("Light_Pendant_Bay", vfx_col, (-0.20, -0.55, 2.86), (-0.20, -0.55, 0.70), 28.0, "#FFD49A", 1.35, True)
    _create_area_light("Light_Pendant_Workbench", vfx_col, (3.00, -0.65, 2.85), (3.55, -0.65, 1.00), 26.0, "#FFE0B0", 1.40, False)
    _create_area_light("Light_Pendant_PartsAlcove", vfx_col, (-1.05, 3.35, 2.85), (-1.05, 3.95, 1.05), 24.0, "#D4E4FF", 1.50, False)

    for mk in LIGHTING_MOOD_KEYS:
        f = mk["f"]
        sun_data.energy = mk["sun_e"]
        sun_data.color = hex_to_rgb(mk["sun_col"])
        sun_data.keyframe_insert(data_path="energy", frame=f)
        sun_data.keyframe_insert(data_path="color", frame=f)

        elev_rad = math.radians(mk["sun_elev"])
        azim_rad = math.radians(-18.0)
        sun_dir = Vector((math.cos(elev_rad) * math.cos(azim_rad), math.cos(elev_rad) * math.sin(azim_rad), -math.sin(elev_rad))).normalized()
        sun_obj.rotation_euler = sun_dir.to_track_quat("-Z", "Y").to_euler()
        sun_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        blue_sky.data.energy = mk["blue_e"]
        blue_sky.data.keyframe_insert(data_path="energy", frame=f)
        blue_courtyard.data.energy = mk["blue_e"] * 0.85
        blue_courtyard.data.keyframe_insert(data_path="energy", frame=f)

        spot_data.energy = 7500.0 * mk["ray_alpha"]
        spot_data.color = hex_to_rgb(mk["ray_col"])
        spot_data.keyframe_insert(data_path="energy", frame=f)
        spot_data.keyframe_insert(data_path="color", frame=f)

        haze_col_sock.default_value = hex_to_rgba(mk["ray_col"])
        haze_col_sock.keyframe_insert(data_path="default_value", frame=f)
        haze_dens_sock.default_value = mk["haze"]
        haze_dens_sock.keyframe_insert(data_path="default_value", frame=f)

    # 4. MULTI-WINDOW WELDING ARC POINT LIGHT & PLASMA CORE (Hook + Front + Side + Rear!)
    arc_windows = [
        ("FRONT", HOOK_ARC_START,  HOOK_ARC_END),
        ("FRONT", FRONT_ARC_START, FRONT_ARC_END),
        ("SIDE",  SIDE_ARC_START,  SIDE_ARC_END),
        ("REAR",  REAR_ARC_START,  REAR_ARC_END),
    ]

    arc_ldata = bpy.data.lights.new("Welding_Arc_Light_Data", type="POINT")
    arc_ldata.color = hex_to_rgb("#1EB2FF")
    arc_ldata.shadow_soft_size = 0.030
    if hasattr(arc_ldata, "use_shadow"):
        arc_ldata.use_shadow = True
    arc_light = bpy.data.objects.new("Welding_Arc_Light", arc_ldata)
    arc_light.parent = torch_tip_empty
    arc_light.location = (0.0, -0.008, 0.004)
    link_exclusively(arc_light, vfx_col)

    mat_arc_core = get_emission_material("Mat_VFX_ArcCore", PALETTE_HEX["weld_arc_core"], strength=42.0)
    bm_core = bmesh.new()
    bmesh.ops.create_icosphere(bm_core, subdivisions=2, radius=0.018)
    for rot_ax in ((0.0, 0.0, 0.0), (0.0, math.pi / 3.0, 0.4), (math.pi / 2.0, 0.3, -0.5)):
        verts_f = [bm_core.verts.new(Euler(rot_ax).to_matrix() @ Vector(co)) for co in ((-0.052, 0.0, 0.0), (0.0, 0.0, 0.009), (0.052, 0.0, 0.0), (0.0, 0.0, -0.009))]
        bm_core.faces.new(verts_f)
    arc_mesh = bpy.data.meshes.new("VFX_ArcCore_Mesh")
    bm_core.to_mesh(arc_mesh)
    bm_core.free()
    arc_core_obj = bpy.data.objects.new("VFX_ArcCore", arc_mesh)
    arc_core_obj.data.materials.append(mat_arc_core)
    arc_core_obj.parent = torch_tip_empty
    arc_core_obj.location = (0.0, 0.0, 0.0)
    link_exclusively(arc_core_obj, vfx_col)

    for idx_w, (_, w0, w1) in enumerate(arc_windows):
        if w0 > 1:
            arc_ldata.energy = 0.0
            arc_ldata.keyframe_insert(data_path="energy", frame=w0 - 1)
            arc_core_obj.scale = (0.0, 0.0, 0.0)
            arc_core_obj.keyframe_insert(data_path="scale", frame=w0 - 1)
        arc_ldata.energy = 82.0
        arc_ldata.keyframe_insert(data_path="energy", frame=w0)
        arc_ldata.keyframe_insert(data_path="energy", frame=w1)
        arc_ldata.energy = 0.0
        arc_ldata.keyframe_insert(data_path="energy", frame=w1 + 1)

        arc_core_obj.scale = (1.0, 1.0, 1.0)
        arc_core_obj.keyframe_insert(data_path="scale", frame=w0)
        arc_core_obj.keyframe_insert(data_path="scale", frame=w1)
        arc_core_obj.scale = (0.0, 0.0, 0.0)
        arc_core_obj.keyframe_insert(data_path="scale", frame=w1 + 1)

    arc_ldata.energy = 0.0
    arc_ldata.keyframe_insert(data_path="energy", frame=FRAME_END)
    arc_core_obj.scale = (0.0, 0.0, 0.0)
    arc_core_obj.keyframe_insert(data_path="scale", frame=FRAME_END)

    for idx_w, (_, w0, w1) in enumerate(arc_windows):
        add_restricted_noise_modifier(arc_ldata, "energy", float(w0), float(w1), scale=1.2, strength=54.0, phase=3.1 + idx_w * 5.2)
        for ax_i in range(3):
            add_restricted_noise_modifier(arc_core_obj, "scale", float(w0), float(w1), scale=1.4, strength=0.55, phase=ax_i * 9.3 + idx_w * 4.1, index=ax_i)

    # 5. DETERMINISTIC BOUNCING SPARK STREAKS ACROSS ALL 4 WELDING WINDOWS!
    mat_spark_hot = get_emission_material("Mat_VFX_SparkHot", "#FFF2A6", strength=28.0)
    mat_spark_org = get_emission_material("Mat_VFX_SparkOrange", "#FF8E26", strength=22.0)

    rng = random.Random(RANDOM_SEED + 1081)
    num_streaks = 44
    dt = 1.0 / 24.0
    gravity = Vector((0.0, 0.0, -9.2))
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

        for z_name, w0, w1 in arc_windows:
            z_pts = weld_zones[z_name]["points"]
            z_nrm = weld_zones[z_name]["normals"]
            if w0 > 1:
                st_obj.scale = (0.0, 0.0, 0.0)
                st_obj.keyframe_insert(data_path="scale", frame=w0 - 1)

            life_frames = rng.randint(10, 15)
            f_cur = w0 + (s_idx % 10)
            while f_cur <= w1:
                u_s = (f_cur - w0) / max(1.0, float(w1 - w0))
                if w0 == HOOK_ARC_START:
                    u_s = 0.35 + 0.25 * u_s
                s_origin = eval_zone_curve(z_pts, u_s)
                s_norm = eval_zone_curve(z_nrm, u_s).normalized()
                pos = s_origin + s_norm * 0.003

                vel = Vector((rng.uniform(-2.2, 2.2), rng.uniform(-2.6, -0.35), rng.uniform(0.35, 2.40)))
                for age in range(life_frames + 1):
                    frame_k = f_cur + age
                    if frame_k > w1 + 10:
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
                    if pos.z < 0.008:
                        pos.z = 0.008
                        vel.z = abs(vel.z) * 0.46
                        vel.x *= 0.72
                        vel.y *= 0.72
                f_cur += life_frames + rng.randint(1, 4)

            st_obj.scale = (0.0, 0.0, 0.0)
            st_obj.keyframe_insert(data_path="scale", frame=min(FRAME_END, w1 + 11))

        st_obj.scale = (0.0, 0.0, 0.0)
        st_obj.keyframe_insert(data_path="scale", frame=FRAME_END)

    # 6. ANIMATE MOLTEN SEAM REVEAL & COOLING EMBER FOR ALL 3 ZONES (FRONT, SIDE, REAR!)
    zone_timings = {
        "FRONT": (FRONT_ARC_START, FRONT_ARC_END, True),
        "SIDE":  (SIDE_ARC_START,  SIDE_ARC_END,  False),
        "REAR":  (REAR_ARC_START,  REAR_ARC_END,  False),
    }
    for z_name, (zs, ze, in_hook) in zone_timings.items():
        p_sock = weld_zones[z_name]["prog_node"].outputs[0]
        h_sock = weld_zones[z_name]["heat_node"].outputs[0]

        p_keys = [(1, 0.55), (HOOK_ARC_END, 0.65), (HOOK_ARC_END + 2, 0.0)] if in_hook else [(1, 0.0)]
        p_keys.extend([(zs - 1, 0.0), (zs, 0.03), (ze, 1.0), (FRAME_END, 1.0)])
        for f, pv in p_keys:
            p_sock.default_value = pv
            p_sock.keyframe_insert(data_path="default_value", frame=f)

        h_keys = [(1, 1.0), (HOOK_ARC_END, 1.0), (HOOK_ARC_END + 2, 0.0)] if in_hook else [(1, 0.0)]
        h_keys.extend([(zs - 1, 0.0), (zs, 1.0), (ze, 1.0), (min(FRAME_END, ze + 90), 0.55), (FRAME_END, 0.35)])
        for f, hv in h_keys:
            h_sock.default_value = hv
            h_sock.keyframe_insert(data_path="default_value", frame=f)

    return {"vfx_collection": vfx_col, "sun_obj": sun_obj, "arc_light": arc_light, "arc_core_obj": arc_core_obj, "spark_streaks": streak_objs}
