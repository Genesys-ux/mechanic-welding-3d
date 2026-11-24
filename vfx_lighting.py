"""
vfx_lighting.py — Dramatic Workshop Lighting, Flickering Welding Arc Point Light,
Plasma Core Starburst, Particle + Deterministic Bouncing Sparks & Cooling Weld Seam.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

import bmesh
import bpy
from mathutils import Euler, Vector

from config import (
    FRAME_END,
    PALETTE_HEX,
    RANDOM_SEED,
    WELD_ARC_END,
    WELD_ARC_START,
    WELD_SEAM_END,
    WELD_SEAM_MID,
    WELD_SEAM_START,
    hex_to_rgb,
    hex_to_rgba,
)
from env_props import get_or_create_collection, link_exclusively
from shaders import get_emission_material

_ACTIVE_SEAM_PTS: List[Vector] = []
_ACTIVE_SEAM_NORMS: List[Vector] = []


def set_active_weld_seam(
    points: Sequence[Vector],
    normals: Optional[Sequence[Vector]] = None,
) -> None:
    """Register the exact raycasted surface weld seam points & normals from `env_props.py`."""
    global _ACTIVE_SEAM_PTS, _ACTIVE_SEAM_NORMS
    _ACTIVE_SEAM_PTS = [Vector(p) for p in points]
    if normals and len(normals) == len(points):
        _ACTIVE_SEAM_NORMS = [Vector(n).normalized() for n in normals]
    else:
        _ACTIVE_SEAM_NORMS = [Vector((0.0, -0.90, 0.43)).normalized() for _ in _ACTIVE_SEAM_PTS]


def _get_action_fcurves(id_data: bpy.types.ID):
    """Retrieve F-Curves compatibly across Blender 3.6, 4.2 LTS, and 4.4+ slotted actions."""
    ad = getattr(id_data, "animation_data", None)
    if ad is None or ad.action is None:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return act.fcurves
    if hasattr(act, "layers"):
        for layer in act.layers:
            for strip in getattr(layer, "strips", []):
                for cb in getattr(strip, "channelbags", []):
                    if hasattr(cb, "fcurves"):
                        return cb.fcurves
    return []


def add_restricted_noise_modifier(
    id_data: bpy.types.ID,
    data_path: str,
    frame_start: float,
    frame_end: float,
    scale: float = 1.5,
    strength: float = 100.0,
    phase: float = 0.0,
    index: int = -1,
) -> None:
    """Attach an F-Curve NOISE modifier active strictly between [frame_start, frame_end]."""
    for fc in _get_action_fcurves(id_data):
        if fc.data_path == data_path and (index < 0 or fc.array_index == index):
            mod = fc.modifiers.new(type="NOISE")
            mod.scale = scale
            mod.strength = strength
            mod.phase = phase
            mod.depth = 2
            mod.use_restricted_range = True
            mod.frame_start = frame_start
            mod.frame_end = frame_end
            mod.blend_in = 2.0
            mod.blend_out = 2.0


def eval_weld_seam_point(u: float) -> Vector:
    """Piecewise-linear / Bezier interpolation along the raycasted car fender weld seam."""
    u = max(0.0, min(1.0, u))
    if len(_ACTIVE_SEAM_PTS) >= 2:
        scaled = u * (len(_ACTIVE_SEAM_PTS) - 1)
        idx = min(len(_ACTIVE_SEAM_PTS) - 2, int(math.floor(scaled)))
        frac = scaled - idx
        return _ACTIVE_SEAM_PTS[idx].lerp(_ACTIVE_SEAM_PTS[idx + 1], frac)

    p0 = Vector(WELD_SEAM_START)
    p1 = Vector(WELD_SEAM_MID)
    p2 = Vector(WELD_SEAM_END)
    ctrl = p1 * 2.0 - (p0 + p2) * 0.5
    omt = 1.0 - u
    return (omt * omt) * p0 + (2.0 * omt * u) * ctrl + (u * u) * p2


def eval_weld_seam_normal(u: float) -> Vector:
    """Outward surface normal along the raycasted car fender weld seam."""
    u = max(0.0, min(1.0, u))
    if len(_ACTIVE_SEAM_NORMS) >= 2:
        scaled = u * (len(_ACTIVE_SEAM_NORMS) - 1)
        idx = min(len(_ACTIVE_SEAM_NORMS) - 2, int(math.floor(scaled)))
        frac = scaled - idx
        n = _ACTIVE_SEAM_NORMS[idx].lerp(_ACTIVE_SEAM_NORMS[idx + 1], frac)
        return n.normalized() if n.length > 1e-6 else Vector((0.0, -0.90, 0.43)).normalized()
    return Vector((0.0, -0.90, 0.43)).normalized()


def _setup_world_background(scene: bpy.types.Scene) -> None:
    if scene.world is None:
        scene.world = bpy.data.worlds.new("WorkshopWorld")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (300, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (0, 0)
    bg.inputs["Color"].default_value = hex_to_rgba("#141923")
    bg.inputs["Strength"].default_value = 0.18
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def _create_area_light(
    name: str,
    col: bpy.types.Collection,
    location: Tuple[float, float, float],
    target_pt: Tuple[float, float, float],
    energy: float,
    hex_color: str,
    size: float = 1.2,
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


def build_lighting_and_vfx(
    scene: bpy.types.Scene,
    torch_tip_empty: bpy.types.Object,
    seam_prog_node: bpy.types.Node,
    seam_heat_node: bpy.types.Node,
) -> Dict[str, Any]:
    """
    Create dramatic workshop 3-point cel lighting + dynamic Welding_Arc_Light,
    arc plasma core, particle emitter + deterministic bouncing spark streaks right at
    the nozzle-to-car-fender contact point, and molten cooling weld seam animation.
    """
    _setup_world_background(scene)
    vfx_col = get_or_create_collection("Col_VFX_Lighting")

    # ==========================================================================
    # 1. WORKSHOP DRAMATIC KEY, BAY & COOL RIM LIGHTS (Calibrated for Standard View)
    # ==========================================================================
    key_light = _create_area_light(
        "Light_Workshop_Key", vfx_col,
        location=(-0.35, -0.85, 2.86),
        target_pt=(-0.22, -0.52, 0.75),
        energy=36.0,
        hex_color="#FFD7A6",
        size=1.40,
        cast_shadow=True,
    )

    rim_light = _create_area_light(
        "Light_Workshop_CoolRim", vfx_col,
        location=(1.25, 0.85, 2.25),
        target_pt=(-0.18, -0.60, 0.85),
        energy=24.0,
        hex_color="#6EC8FF",
        size=1.20,
        cast_shadow=True,
    )

    bay_left = _create_area_light(
        "Light_Workshop_BayLeft", vfx_col,
        location=(-2.35, -0.95, 2.92),
        target_pt=(-3.25, -1.10, 1.00),
        energy=26.0,
        hex_color="#FFE2B8",
        size=1.25,
        cast_shadow=False,
    )

    bay_back = _create_area_light(
        "Light_Workshop_BayBack", vfx_col,
        location=(1.85, 0.55, 2.92),
        target_pt=(0.65, 0.35, 0.80),
        energy=22.0,
        hex_color="#CFE2FF",
        size=1.40,
        cast_shadow=False,
    )

    front_fill = _create_area_light(
        "Light_Mechanic_FrontFill", vfx_col,
        location=(-2.25, -1.65, 1.35),
        target_pt=(-0.20, -0.65, 0.85),
        energy=9.0,
        hex_color="#FFF6EC",
        size=1.60,
        cast_shadow=False,
    )

    # ==========================================================================
    # 2. WELDING ARC FLICKERING POINT LIGHT (`Welding_Arc_Light`) AT CAR CONTACT
    # ==========================================================================
    arc_ldata = bpy.data.lights.new("Welding_Arc_Light_Data", type="POINT")
    arc_ldata.color = hex_to_rgb("#1EB2FF")
    arc_ldata.shadow_soft_size = 0.030
    if hasattr(arc_ldata, "use_shadow"):
        arc_ldata.use_shadow = True

    arc_light = bpy.data.objects.new("Welding_Arc_Light", arc_ldata)
    arc_light.parent = torch_tip_empty
    # Placed right at the nozzle contact point (8mm outside the metal panel to avoid self-shadow clipping)
    arc_light.location = (0.0, -0.008, 0.004)
    link_exclusively(arc_light, vfx_col)

    for f, val in [
        (1, 0.0),
        (WELD_ARC_START - 1, 0.0),
        (WELD_ARC_START, 72.0),
        (WELD_ARC_END, 72.0),
        (WELD_ARC_END + 1, 0.0),
        (FRAME_END, 0.0),
    ]:
        arc_ldata.energy = val
        arc_ldata.keyframe_insert(data_path="energy", frame=f)

    for fc in _get_action_fcurves(arc_ldata):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT" if kp.co.x in (1, WELD_ARC_START - 1, WELD_ARC_END + 1) else "LINEAR"

    add_restricted_noise_modifier(
        arc_ldata,
        data_path="energy",
        frame_start=float(WELD_ARC_START),
        frame_end=float(WELD_ARC_END),
        scale=1.25,
        strength=52.0,
        phase=7.3,
    )

    # Warm Orange Seam Ember Light right on the freshly welded car fender seam
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
        (1, 0.0),
        (WELD_ARC_START, 0.0),
        (WELD_ARC_START + 12, 16.0),
        (WELD_ARC_END, 22.0),
        (225, 11.0),
        (245, 5.5),
        (FRAME_END, 2.2),
    ]:
        ember_ldata.energy = val
        ember_ldata.keyframe_insert(data_path="energy", frame=f)

    # ==========================================================================
    # 3. ARC PLASMA SPHERE & STARBURST FLARE AT TORCH TIP (`VFX_ArcCore`)
    # ==========================================================================
    mat_arc_core = get_emission_material("Mat_VFX_ArcCore", PALETTE_HEX["weld_arc_core"], strength=42.0)

    bm_core = bmesh.new()
    bmesh.ops.create_icosphere(bm_core, subdivisions=2, radius=0.018)
    for rot_ax in ((0.0, 0.0, 0.0), (0.0, math.pi / 3.0, 0.4), (math.pi / 2.0, 0.3, -0.5)):
        verts_f = [
            bm_core.verts.new(Euler(rot_ax).to_matrix() @ Vector(co))
            for co in ((-0.048, 0.0, 0.0), (0.0, 0.0, 0.009), (0.048, 0.0, 0.0), (0.0, 0.0, -0.009))
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
        (1, (0.0, 0.0, 0.0)),
        (WELD_ARC_START - 1, (0.0, 0.0, 0.0)),
        (WELD_ARC_START, (1.0, 1.0, 1.0)),
        (WELD_ARC_END, (1.0, 1.0, 1.0)),
        (WELD_ARC_END + 1, (0.0, 0.0, 0.0)),
        (FRAME_END, (0.0, 0.0, 0.0)),
    ]:
        arc_core_obj.scale = sc
        arc_core_obj.keyframe_insert(data_path="scale", frame=f)

    for ax_i in range(3):
        add_restricted_noise_modifier(
            arc_core_obj,
            data_path="scale",
            frame_start=float(WELD_ARC_START),
            frame_end=float(WELD_ARC_END),
            scale=1.4,
            strength=0.55,
            phase=ax_i * 11.7,
            index=ax_i,
        )

    # ==========================================================================
    # 4. WELDING SPARKS AT CAR FENDER CONTACT (`Sparks` Emitter + Streaks)
    # ==========================================================================
    mat_spark_hot = get_emission_material("Mat_VFX_SparkHot", "#FFF2A6", strength=28.0)
    mat_spark_org = get_emission_material("Mat_VFX_SparkOrange", "#FF8E26", strength=22.0)

    bm_sp = bmesh.new()
    bmesh.ops.create_icosphere(bm_sp, subdivisions=1, radius=1.0)
    bmesh.ops.scale(bm_sp, vec=(0.005, 0.032, 0.005), verts=bm_sp.verts)
    sp_proto_mesh = bpy.data.meshes.new("VFX_SparkProto_Mesh")
    bm_sp.to_mesh(sp_proto_mesh)
    bm_sp.free()
    sp_proto_obj = bpy.data.objects.new("VFX_SparkProto", sp_proto_mesh)
    sp_proto_obj.data.materials.append(mat_spark_hot)
    sp_proto_obj.location = (0.0, 0.0, -5.0)
    link_exclusively(sp_proto_obj, vfx_col)

    # Emitter mesh right at Torch Tip contact point on the car body
    bm_em = bmesh.new()
    bmesh.ops.create_icosphere(bm_em, subdivisions=1, radius=0.006)
    em_mesh = bpy.data.meshes.new("Sparks_Emitter_Mesh")
    bm_em.to_mesh(em_mesh)
    bm_em.free()
    em_obj = bpy.data.objects.new("Sparks", em_mesh)
    em_obj.parent = torch_tip_empty
    em_obj.location = (0.0, -0.003, 0.0)
    link_exclusively(em_obj, vfx_col)

    ps_mod = em_obj.modifiers.new(name="WeldSparksPSys", type="PARTICLE_SYSTEM")
    psys = ps_mod.particle_system
    pset = psys.settings
    pset.count = 340
    pset.frame_start = float(WELD_ARC_START)
    pset.frame_end = float(WELD_ARC_END)
    pset.lifetime = 22.0
    pset.lifetime_random = 0.35
    pset.emit_from = "FACE"
    pset.normal_factor = 2.5
    pset.factor_random = 1.7
    pset.render_type = "OBJECT"
    pset.instance_object = sp_proto_obj
    pset.particle_size = 0.85
    pset.size_random = 0.45
    pset.use_rotations = True
    pset.rotation_mode = "VEL"
    em_obj.show_instancer_for_render = False
    em_obj.show_instancer_for_viewport = False

    # Deterministic Keyframed Ballistic Spark Streaks originating right at the raycasted
    # fender weld seam contact point and bouncing off the fender normal & workshop floor!
    rng = random.Random(RANDOM_SEED + 155)
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

        st_obj.scale = (0.0, 0.0, 0.0)
        st_obj.keyframe_insert(data_path="scale", frame=1)
        st_obj.keyframe_insert(data_path="scale", frame=WELD_ARC_START - 1)

        life_frames = rng.randint(10, 17)
        first_birth = WELD_ARC_START + (s_idx % 12)
        f_cur = first_birth
        while f_cur <= WELD_ARC_END:
            u_seam = (f_cur - WELD_ARC_START) / max(1.0, float(WELD_ARC_END - WELD_ARC_START))
            s_origin = eval_weld_seam_point(u_seam)
            s_norm = eval_weld_seam_normal(u_seam)
            pos = s_origin + s_norm * 0.003

            # Spray outward along car surface normal + tangential scatter
            vx = rng.uniform(-2.1, 2.1)
            vy = rng.uniform(-2.5, -0.35)
            vz = rng.uniform(0.30, 2.35)
            vel = Vector((vx, vy, vz))

            for age in range(life_frames + 1):
                frame_k = f_cur + age
                if frame_k > WELD_ARC_END + 14:
                    break

                if age == 0:
                    sc_val = rng.uniform(0.85, 1.40)
                elif age >= life_frames:
                    sc_val = 0.0
                else:
                    sc_val = (1.0 - (age / float(life_frames)) ** 1.6) * 1.22

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

                # Bounce off Car Fender plane near weld zone
                if -0.85 <= pos.x <= 0.35 and 0.30 <= pos.z <= 0.90:
                    pen = (pos - s_origin).dot(s_norm)
                    if pen < 0.004 and pos.y > s_origin.y - 0.02:
                        pos = pos + s_norm * (0.005 - pen)
                        vn = vel.dot(s_norm)
                        if vn < 0.0:
                            vel = (vel - 1.65 * vn * s_norm) * 0.78

                # Bounce off Workshop Concrete Floor (Z = 0.008)
                if pos.z < 0.008:
                    pos.z = 0.008
                    vel.z = abs(vel.z) * 0.46
                    vel.x *= 0.72
                    vel.y *= 0.72

            f_cur += life_frames + rng.randint(1, 4)

        st_obj.scale = (0.0, 0.0, 0.0)
        st_obj.keyframe_insert(data_path="scale", frame=WELD_ARC_END + 15)
        st_obj.keyframe_insert(data_path="scale", frame=FRAME_END)

    # ==========================================================================
    # 5. ANIMATE MOLTEN WELD SEAM REVEAL & COOLING EMBER GLOW
    # ==========================================================================
    p_sock = seam_prog_node.outputs[0]
    for f, pv in [
        (1, 0.0),
        (WELD_ARC_START - 1, 0.0),
        (WELD_ARC_START, 0.03),
        (WELD_ARC_END, 1.0),
        (FRAME_END, 1.0),
    ]:
        p_sock.default_value = pv
        p_sock.keyframe_insert(data_path="default_value", frame=f)

    h_sock = seam_heat_node.outputs[0]
    for f, hv in [
        (1, 0.0),
        (WELD_ARC_START - 1, 0.0),
        (WELD_ARC_START, 1.0),
        (WELD_ARC_END, 1.0),
        (215, 0.78),
        (240, 0.52),
        (FRAME_END, 0.28),
    ]:
        h_sock.default_value = hv
        h_sock.keyframe_insert(data_path="default_value", frame=f)

    return {
        "vfx_collection": vfx_col,
        "key_light": key_light,
        "rim_light": rim_light,
        "bay_left": bay_left,
        "bay_back": bay_back,
        "front_fill": front_fill,
        "arc_light": arc_light,
        "ember_light": ember_light,
        "arc_core_obj": arc_core_obj,
        "spark_emitter": em_obj,
        "spark_streaks": streak_objs,
    }
