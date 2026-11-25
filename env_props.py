"""
env_props.py — Rich 3D Cel-Shaded Workshop Environment, Clean Reference Classic Car
(`assets/car_reference.glb` with pedestal/helper cleanup, grounded tires, raycasted
0-gap jack stands, conformal fender weld plate/seam, and rocker-clamped ground earth
clamp), Dense 360° Workshop Set Dressing, and Textured MIG Welder + Gas Cylinder.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from config import (
    PALETTE_HEX,
    PROJECT_ROOT,
    WELDER_CABLE_SOCKET,
    WELDER_UNIT_POS,
    WELD_SEAM_END,
    WELD_SEAM_MID,
    WELD_SEAM_START,
)
from shaders import (
    apply_cel_outline,
    create_weld_seam_material,
    get_cel_material,
    get_emission_material,
    get_textured_cel_material,
    upgrade_glb_material_to_cel,
)

CAR_GLB_PATH: Path = PROJECT_ROOT / "assets" / "car_reference.glb"
DECALS_DIR: Path = PROJECT_ROOT / "generated_textures"


def get_or_create_collection(name: str, parent: Optional[bpy.types.Collection] = None) -> bpy.types.Collection:
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def link_exclusively(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def _new_mesh_obj(
    name: str,
    bm: bmesh.types.BMesh,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    outline_thickness: float = 0.006,
    smooth: bool = True,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    link_exclusively(obj, col)

    if outline_thickness > 0.0:
        apply_cel_outline(obj, thickness=outline_thickness)
    return obj


def _make_beveled_box(
    name: str,
    size: Tuple[float, float, float],
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel_width: float = 0.015,
    bevel_segments: int = 2,
    outline_thickness: float = 0.006,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if bevel_width > 0.0:
        bmesh.ops.bevel(
            bm,
            geom=list(bm.edges),
            offset=bevel_width,
            segments=bevel_segments,
            profile=0.5,
            affect="EDGES",
        )
    return _new_mesh_obj(
        name, bm, col, mat,
        location=location,
        rotation=rotation,
        outline_thickness=outline_thickness,
        smooth=True,
    )


def _make_cylinder(
    name: str,
    radius: float,
    depth: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    segments: int = 24,
    outline_thickness: float = 0.0055,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    return _new_mesh_obj(
        name, bm, col, mat,
        location=location,
        rotation=rotation,
        outline_thickness=outline_thickness,
        smooth=True,
    )


def _make_torus(
    name: str,
    major_radius: float,
    minor_radius: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    major_segments: int = 28,
    minor_segments: int = 12,
    outline_thickness: float = 0.0045,
) -> bpy.types.Object:
    bm = bmesh.new()
    rings: List[List[bmesh.types.BMVert]] = []
    for i in range(major_segments):
        th = (2.0 * math.pi * i) / major_segments
        ct, st = math.cos(th), math.sin(th)
        ring = []
        for j in range(minor_segments):
            ph = (2.0 * math.pi * j) / minor_segments
            r = major_radius + minor_radius * math.cos(ph)
            ring.append(bm.verts.new((r * ct, r * st, minor_radius * math.sin(ph))))
        rings.append(ring)
    for i in range(major_segments):
        inext = (i + 1) % major_segments
        for j in range(minor_segments):
            jnext = (j + 1) % minor_segments
            bm.faces.new([rings[i][j], rings[inext][j], rings[inext][jnext], rings[i][jnext]])
    return _new_mesh_obj(name, bm, col, mat, location=location, rotation=rotation, outline_thickness=outline_thickness)


def _make_uv_quad(
    name: str,
    width: float,
    height: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float],
    rotation: Tuple[float, float, float],
    u_repeat: float = 1.0,
    outline_thickness: float = 0.0,
) -> bpy.types.Object:
    """Create a UV-mapped plane whose normal initially points along +Z before `rotation`."""
    bm = bmesh.new()
    hw, hh = width * 0.5, height * 0.5
    v0 = bm.verts.new((-hw, -hh, 0.0))
    v1 = bm.verts.new((hw, -hh, 0.0))
    v2 = bm.verts.new((hw, hh, 0.0))
    v3 = bm.verts.new((-hw, hh, 0.0))
    f = bm.faces.new([v0, v1, v2, v3])
    uv_lay = bm.loops.layers.uv.new("UVMap")
    for loop, uv in zip(f.loops, [(0.0, 0.0), (u_repeat, 0.0), (u_repeat, 1.0), (0.0, 1.0)]):
        loop[uv_lay].uv = uv
    return _new_mesh_obj(name, bm, col, mat, location=location, rotation=rotation, outline_thickness=outline_thickness, smooth=False)


def _make_curve_hose(
    name: str,
    pts: List[Tuple[float, float, float]],
    radius: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    cdata = bpy.data.curves.new(name + "_Curve", type="CURVE")
    cdata.dimensions = "3D"
    cdata.bevel_depth = radius
    cdata.bevel_resolution = 4
    cdata.resolution_u = 20
    sp = cdata.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for idx, p in enumerate(pts):
        bp = sp.bezier_points[idx]
        bp.co = p
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, cdata)
    obj.data.materials.append(mat)
    link_exclusively(obj, col)
    return obj


def _add_collision_modifier(obj: bpy.types.Object, damping: float = 0.38, friction: float = 0.25) -> None:
    obj.modifiers.new(name="SparkCollider", type="COLLISION")
    if obj.collision:
        obj.collision.damping_factor = damping
        obj.collision.damping_random = 0.22
        obj.collision.friction_factor = friction
        obj.collision.stickiness = 0.05


def _make_ibeam_column(
    name: str,
    height: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    location: Tuple[float, float, float],
    rotation_z: float = 0.0,
) -> bpy.types.Object:
    """True H-Section Structural Steel I-Beam Column with Baseplate."""
    grp = bpy.data.objects.new(name + "_Grp", None)
    grp.location = location
    grp.rotation_euler = (0.0, 0.0, rotation_z)
    link_exclusively(grp, col)

    f1 = _make_beveled_box(name + "_FlangeA", (0.20, 0.024, height), col, mat, location=(0.0, -0.088, height * 0.5), bevel_width=0.004, outline_thickness=0.006)
    f2 = _make_beveled_box(name + "_FlangeB", (0.20, 0.024, height), col, mat, location=(0.0, 0.088, height * 0.5), bevel_width=0.004, outline_thickness=0.006)
    web = _make_beveled_box(name + "_Web", (0.026, 0.16, height), col, mat, location=(0.0, 0.0, height * 0.5), bevel_width=0.003, outline_thickness=0.005)
    base = _make_beveled_box(name + "_Base", (0.28, 0.28, 0.025), col, mat, location=(0.0, 0.0, 0.0125), bevel_width=0.005, outline_thickness=0.006)
    for part in (f1, f2, web, base):
        part.parent = grp
    return grp


# ==============================================================================
# 1. DENSE MULTI-LAYERED 360° WORKSHOP ARCHITECTURE & SET DRESSING
# ==============================================================================
def _build_workshop_room_and_set_dressing(col: bpy.types.Collection) -> Dict[str, bpy.types.Object]:
    objs: Dict[str, bpy.types.Object] = {}

    mat_floor = get_cel_material("Mat_Floor_Concrete", PALETTE_HEX["floor_concrete"], shadow_factor=0.46, mid_factor=0.84, lit_factor=0.96, surface_type="concrete", ao_strength=0.50)
    mat_line = get_cel_material("Mat_Floor_HazardLine", PALETTE_HEX["floor_line_yellow"], shadow_factor=0.50, surface_type="concrete")
    mat_oil = get_cel_material("Mat_Floor_OilStain", PALETTE_HEX["floor_oil"], shadow_factor=0.35, spec_strength=0.65, roughness=0.14, surface_type="painted")
    mat_wall_up = get_cel_material("Mat_Wall_Brick", PALETTE_HEX["wall_brick"], shadow_factor=0.45, mid_factor=0.85, lit_factor=0.98, surface_type="brick", ao_strength=0.48)
    mat_wall_low = get_cel_material("Mat_Wall_Lower", PALETTE_HEX["wall_lower"], shadow_factor=0.44, mid_factor=0.84, surface_type="concrete", ao_strength=0.48)
    mat_beam = get_cel_material("Mat_Steel_Beam", PALETTE_HEX["steel_beam"], shadow_factor=0.40, spec_strength=0.45, surface_type="metal")
    mat_wood = get_cel_material("Mat_Bench_Wood", PALETTE_HEX["bench_wood"], shadow_factor=0.46, surface_type="wood")
    mat_bench_leg = get_cel_material("Mat_Bench_Frame", PALETTE_HEX["bench_frame"], shadow_factor=0.40, spec_strength=0.35, surface_type="metal")
    mat_red = get_cel_material("Mat_Tool_Red", PALETTE_HEX["tool_red"], shadow_factor=0.44, spec_strength=0.45, surface_type="metal")
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.46, lit_factor=1.05, spec_strength=0.85, surface_type="chrome")
    mat_can_y = get_cel_material("Mat_OilCan_Yellow", PALETTE_HEX["oil_can_yellow"], shadow_factor=0.45, spec_strength=0.4, surface_type="painted")
    mat_can_b = get_cel_material("Mat_OilCan_Blue", PALETTE_HEX["oil_can_blue"], shadow_factor=0.45, spec_strength=0.4, surface_type="painted")
    mat_green_lamp = get_cel_material("Mat_Lamp_GreenEnamel", "#24543C", shadow_factor=0.42, spec_strength=0.55, surface_type="metal")
    mat_cardboard = get_cel_material("Mat_Cardboard_Box", "#A67C52", shadow_factor=0.48, surface_type="concrete")
    mat_white = get_cel_material("Mat_FirstAid_White", "#E6EAEF", shadow_factor=0.52, surface_type="painted")
    mat_hose_org = get_cel_material("Mat_Hose_Orange", "#E06D24", shadow_factor=0.46, surface_type="painted")
    mat_tire = get_cel_material("Mat_Rubber_Tire", PALETTE_HEX["car_tire"], shadow_factor=0.36, surface_type="painted")
    mat_bulb = get_emission_material("Mat_Lamp_Bulb", "#FFE4B5", strength=3.6)
    mat_window = get_emission_material("Mat_Workshop_Window", "#354C68", strength=0.85)

    # Decal materials (generated via Pillow in `generated_textures/`)
    mat_hazard = get_textured_cel_material("Mat_Decal_HazardStripe", str(DECALS_DIR / "hazard_stripe.png"))
    mat_p_safety = get_textured_cel_material("Mat_Poster_Safety", str(DECALS_DIR / "poster_safety_first.png"))
    mat_p_chart = get_textured_cel_material("Mat_Poster_Service", str(DECALS_DIR / "poster_service_chart.png"))
    mat_p_oil = get_textured_cel_material("Mat_Poster_RetroOil", str(DECALS_DIR / "poster_retro_oil.png"))
    mat_oil_lbl = get_textured_cel_material("Mat_Decal_OilLabel", str(DECALS_DIR / "oil_bottle_label.png"))

    # ---- A) CONCRETE FLOOR, DRAIN GRATE, OIL PUDDLES & SCATTERED FLOOR TOOLS ----
    floor = _make_beveled_box(
        "Env_Floor", (11.0, 9.5, 0.12), col, mat_floor,
        location=(0.0, -0.5, -0.06), bevel_width=0.0, outline_thickness=0.0
    )
    _add_collision_modifier(floor, damping=0.42, friction=0.30)
    objs["floor"] = floor

    # Painted Garage Bay Lines
    for name_s, sz, pos in [
        ("Env_BayLine_Front", (4.3, 0.08, 0.004), (0.65, -1.52, 0.002)),
        ("Env_BayLine_Left", (0.08, 3.3, 0.004), (-1.50, 0.10, 0.002)),
        ("Env_BayLine_Right", (0.08, 3.3, 0.004), (2.78, 0.10, 0.002)),
    ]:
        _make_beveled_box(name_s, sz, col, mat_line, location=pos, bevel_width=0.0, outline_thickness=0.0)

    # Concrete Expansion Joints
    for idx, gx in enumerate((-2.2, 0.3, 2.8)):
        _make_beveled_box(f"Env_FloorGroove_{idx}", (0.016, 8.8, 0.003), col, mat_oil, location=(gx, -0.4, 0.0015), bevel_width=0.0, outline_thickness=0.0)

    # Slotted Iron Floor Drain Grate
    drain_x, drain_y = -0.92, -1.28
    _make_beveled_box("Prop_FloorDrain_Recess", (0.44, 0.44, 0.006), col, mat_oil, location=(drain_x, drain_y, 0.002), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Prop_FloorDrain_Frame", (0.46, 0.46, 0.012), col, mat_beam, location=(drain_x, drain_y, 0.006), bevel_width=0.004, outline_thickness=0.004)
    for sl_i in range(7):
        sy = drain_y - 0.18 + sl_i * 0.06
        _make_beveled_box(f"Prop_FloorDrain_Bar_{sl_i}", (0.40, 0.022, 0.014), col, mat_beam, location=(drain_x, sy, 0.007), bevel_width=0.002, outline_thickness=0.003)

    # Oil Stains, Oil Funnel, Coiled Extension Cord & Scattered Floor Wrenches/Bolts
    for idx, (ox, oy, rx, ry) in enumerate([(-0.68, -0.92, 0.22, 0.15), (-0.45, -0.82, 0.10, 0.08), (1.10, -0.98, 0.18, 0.13)]):
        puddle = _make_cylinder(f"Env_OilStain_{idx}", 1.0, 0.004, col, mat_oil, location=(ox, oy, 0.002), segments=20, outline_thickness=0.0)
        puddle.scale = (rx, ry, 1.0)

    bm_fun = bmesh.new()
    bmesh.ops.create_cone(bm_fun, cap_ends=False, cap_tris=False, segments=20, radius1=0.075, radius2=0.014, depth=0.11)
    _new_mesh_obj("Prop_Floor_OilFunnel", bm_fun, col, mat_red, location=(-1.12, -1.04, 0.065), rotation=(0.25, -0.15, 0.0), outline_thickness=0.004)

    for c_i in range(3):
        _make_torus(f"Prop_Floor_ExtCord_{c_i}", 0.16 - c_i * 0.012, 0.011, col, mat_hose_org, location=(-1.78, -1.68, 0.012 + c_i * 0.014), outline_thickness=0.003)

    for fw_i, (fwx, fwy, fwr) in enumerate([(-0.82, -0.66, 0.65), (-0.98, -0.58, -0.42)]):
        _make_beveled_box(f"Prop_FloorWrench_{fw_i}", (0.22, 0.028, 0.010), col, mat_chrome, location=(fwx, fwy, 0.007), rotation=(0.0, 0.0, fwr), bevel_width=0.003, outline_thickness=0.0035)
        _make_cylinder(f"Prop_FloorWrenchHead_{fw_i}", 0.024, 0.011, col, mat_chrome, location=(fwx + math.cos(fwr) * 0.11, fwy + math.sin(fwr) * 0.11, 0.007), outline_thickness=0.003)
    for nb_i, (bx_n, by_n) in enumerate([(-0.74, -0.60), (-0.78, -0.63), (-0.71, -0.64), (-1.18, -0.74)]):
        _make_cylinder(f"Prop_FloorBolt_{nb_i}", 0.010, 0.018, col, mat_chrome, location=(bx_n, by_n, 0.009), segments=6, outline_thickness=0.002)

    # ---- B) WALLS, HAZARD STRIPE BORDER, I-BEAM PILLARS & GRATED WINDOWS ----
    back_y, right_x, left_x = 2.38, 3.35, -4.15

    _make_beveled_box("Env_BackWall_Upper", (8.2, 0.18, 2.8), col, mat_wall_up, location=(-0.4, back_y, 2.58), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_BackWall_Dado", (8.2, 0.22, 1.18), col, mat_wall_low, location=(-0.4, back_y - 0.02, 0.59), bevel_width=0.008, outline_thickness=0.006)
    _make_uv_quad("Env_BackWall_HazardStripe", 7.8, 0.11, col, mat_hazard, location=(-0.4, back_y - 0.135, 1.19), rotation=(math.pi * 0.5, 0.0, 0.0), u_repeat=12.0)

    _make_beveled_box("Env_RightWall_Upper", (0.18, 7.6, 2.8), col, mat_wall_up, location=(right_x, -0.8, 2.58), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_RightWall_Dado", (0.22, 7.6, 1.18), col, mat_wall_low, location=(right_x - 0.02, -0.8, 0.59), bevel_width=0.008, outline_thickness=0.006)
    _make_uv_quad("Env_RightWall_HazardStripe", 7.4, 0.11, col, mat_hazard, location=(right_x - 0.135, -0.8, 1.19), rotation=(math.pi * 0.5, 0.0, -math.pi * 0.5), u_repeat=11.0)

    _make_beveled_box("Env_LeftWall_Upper", (0.18, 7.6, 2.8), col, mat_wall_up, location=(left_x, -0.8, 2.58), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_LeftWall_Dado", (0.22, 7.6, 1.18), col, mat_wall_low, location=(left_x + 0.02, -0.8, 0.59), bevel_width=0.008, outline_thickness=0.006)
    _make_uv_quad("Env_LeftWall_HazardStripe", 7.4, 0.11, col, mat_hazard, location=(left_x + 0.135, -0.8, 1.19), rotation=(math.pi * 0.5, 0.0, math.pi * 0.5), u_repeat=11.0)

    # Structural Steel I-Beam Columns & Roof Trusses + Overhead Red Air Pipe
    for i, px in enumerate((-3.6, -1.0, 1.5, 3.18)):
        _make_ibeam_column(f"Env_IBeam_Back_{i}", 3.85, col, mat_beam, location=(px, back_y - 0.18, 0.0))
    for i, py in enumerate((-2.8, -0.4, 1.8)):
        _make_ibeam_column(f"Env_IBeam_Right_{i}", 3.85, col, mat_beam, location=(right_x - 0.18, py, 0.0), rotation_z=math.pi * 0.5)
        _make_ibeam_column(f"Env_IBeam_Left_{i}", 3.85, col, mat_beam, location=(left_x + 0.18, py, 0.0), rotation_z=math.pi * 0.5)
        _make_beveled_box(f"Env_RoofTruss_{i}", (7.8, 0.15, 0.22), col, mat_beam, location=(-0.4, py, 3.76), bevel_width=0.01, outline_thickness=0.007)

    _make_cylinder("Env_AirPipe_Right", 0.024, 6.8, col, mat_red, location=(right_x - 0.18, -0.6, 2.95), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.004)
    _make_cylinder("Env_AirPipe_Back", 0.024, 7.2, col, mat_red, location=(-0.3, back_y - 0.18, 2.95), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.004)

    # Multi-Pane Iron-Grated Workshop Windows (Back Wall & Right Wall)
    def add_grated_window(w_name: str, loc: Tuple[float, float, float], rot_z: float) -> None:
        wgrp = bpy.data.objects.new(w_name + "_Grp", None)
        wgrp.location = loc
        wgrp.rotation_euler = (0.0, 0.0, rot_z)
        link_exclusively(wgrp, col)
        fr = _make_beveled_box(w_name + "_Frame", (1.52, 0.10, 0.84), col, mat_beam, bevel_width=0.008, outline_thickness=0.007)
        gl = _make_beveled_box(w_name + "_Glass", (1.40, 0.03, 0.72), col, mat_window, bevel_width=0.0, outline_thickness=0.0)
        fr.parent = wgrp
        gl.parent = wgrp
        for bx_w in (-0.46, -0.15, 0.15, 0.46):
            vb = _make_cylinder(f"{w_name}_VBar_{bx_w}", 0.011, 0.74, col, mat_beam, location=(bx_w, -0.03, 0.0), outline_thickness=0.003)
            vb.parent = wgrp
        for bz_w in (-0.18, 0.18):
            hb = _make_cylinder(f"{w_name}_HBar_{bz_w}", 0.011, 1.42, col, mat_beam, location=(0.0, -0.03, bz_w), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.003)
            hb.parent = wgrp

    add_grated_window("Env_Win_BackL", (-2.25, back_y - 0.08, 2.28), 0.0)
    add_grated_window("Env_Win_BackM", (0.25, back_y - 0.08, 2.28), 0.0)
    add_grated_window("Env_Win_Right1", (right_x - 0.08, 0.65, 2.28), -math.pi * 0.5)
    add_grated_window("Env_Win_Right2", (right_x - 0.08, -1.65, 2.28), -math.pi * 0.5)

    # Green-Enamel Industrial Hanging Pendant Shop Lamps
    pendant_coords = [
        (-0.20, -0.55, 3.02),
        (1.85, -0.55, 3.05),
        (-2.25, -0.95, 3.08),
        (1.35, 1.25, 3.06),
    ]
    for p_i, (lx, ly, lz) in enumerate(pendant_coords):
        _make_cylinder(f"Env_LampRod_{p_i}", 0.015, 0.78, col, mat_beam, location=(lx, ly, lz + 0.42), outline_thickness=0.004)
        _make_cylinder(f"Env_LampNeck_{p_i}", 0.055, 0.09, col, mat_beam, location=(lx, ly, lz + 0.12), outline_thickness=0.005)
        bm_sh = bmesh.new()
        bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=24, radius1=0.32, radius2=0.08, depth=0.22)
        _new_mesh_obj(f"Env_LampShade_{p_i}", bm_sh, col, mat_green_lamp, location=(lx, ly, lz), outline_thickness=0.007)
        _make_cylinder(f"Env_LampBulb_{p_i}", 0.075, 0.08, col, mat_bulb, location=(lx, ly, lz - 0.08), outline_thickness=0.0)

    # ---- C) RIGHT & BACK WALL HERO SET DRESSING (DIRECTLY IN CAMERA BACKGROUND!) ----
    wb_x, wb_y = 2.76, -0.62
    _make_beveled_box("Prop_RightBench_Top", (0.76, 1.95, 0.068), col, mat_wood, location=(wb_x, wb_y, 0.88), bevel_width=0.010, outline_thickness=0.007)
    _make_beveled_box("Prop_RightBench_Shelf", (0.66, 1.82, 0.035), col, mat_bench_leg, location=(wb_x, wb_y, 0.24), bevel_width=0.006, outline_thickness=0.006)
    for lx_o in (-0.31, 0.31):
        for ly_o in (-0.88, 0.88):
            _make_beveled_box(f"Prop_RightBench_Leg_{lx_o}_{ly_o}", (0.06, 0.06, 0.86), col, mat_bench_leg, location=(wb_x + lx_o, wb_y + ly_o, 0.43), bevel_width=0.005, outline_thickness=0.006)

    # Heavy Cast-Iron Bench Vise (`Ragum`)
    vx, vy, vz = wb_x - 0.30, wb_y - 0.68, 0.96
    _make_beveled_box("Prop_BenchVise_Base", (0.18, 0.16, 0.11), col, mat_can_b, location=(vx, vy, vz), bevel_width=0.012, outline_thickness=0.005)
    _make_beveled_box("Prop_BenchVise_JawA", (0.05, 0.15, 0.14), col, mat_chrome, location=(vx - 0.07, vy, vz + 0.05), bevel_width=0.005, outline_thickness=0.004)
    _make_beveled_box("Prop_BenchVise_JawB", (0.05, 0.15, 0.14), col, mat_chrome, location=(vx - 0.15, vy, vz + 0.05), bevel_width=0.005, outline_thickness=0.004)
    _make_cylinder("Prop_BenchVise_Screw", 0.016, 0.24, col, mat_chrome, location=(vx - 0.12, vy, vz + 0.02), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.003)
    _make_cylinder("Prop_BenchVise_Handle", 0.008, 0.22, col, mat_chrome, location=(vx - 0.23, vy, vz + 0.02), rotation=(0.35, 0.0, 0.0), outline_thickness=0.003)

    # Bolt Tin Cans, Hammer & Scattered Tools on Right Workbench
    _make_cylinder("Prop_BoltTin_1", 0.055, 0.12, col, mat_chrome, location=(wb_x + 0.10, wb_y - 0.25, 0.97), outline_thickness=0.004)
    _make_cylinder("Prop_BoltTin_2", 0.048, 0.10, col, mat_can_y, location=(wb_x + 0.16, wb_y - 0.10, 0.96), outline_thickness=0.004)
    _make_beveled_box("Prop_BenchToolbox_Red", (0.24, 0.44, 0.20), col, mat_red, location=(wb_x + 0.08, wb_y + 0.52, 1.01), bevel_width=0.012, outline_thickness=0.006)
    _make_cylinder("Prop_BenchHammer_Shaft", 0.012, 0.30, col, mat_wood, location=(wb_x - 0.12, wb_y + 0.12, 0.93), rotation=(math.pi * 0.5, 0.0, 0.45), outline_thickness=0.0035)
    _make_beveled_box("Prop_BenchHammer_Head", (0.11, 0.038, 0.038), col, mat_beam, location=(wb_x - 0.18, wb_y + 0.24, 0.935), rotation=(0.0, 0.0, 0.45), bevel_width=0.005, outline_thickness=0.004)

    # 2) Packed Wall Pegboard above Right Workbench
    pg_x = right_x - 0.16
    _make_beveled_box("Prop_RightPegboard", (0.035, 1.82, 0.92), col, mat_bench_leg, location=(pg_x, wb_y, 1.54), bevel_width=0.006, outline_thickness=0.006)
    for w_i in range(6):
        wy = wb_y - 0.72 + w_i * 0.16
        w_len = 0.32 - w_i * 0.028
        _make_beveled_box(f"Prop_PegWrench_{w_i}", (0.014, 0.032, w_len), col, mat_chrome, location=(pg_x - 0.03, wy, 1.72 - w_len * 0.5), bevel_width=0.003, outline_thickness=0.0035)
        _make_cylinder(f"Prop_PegWrenchRing_{w_i}", 0.028 - w_i * 0.002, 0.016, col, mat_chrome, location=(pg_x - 0.03, wy, 1.73), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.0035)
    for pl_a in (-0.18, 0.18):
        _make_beveled_box(f"Prop_PegPliers_{pl_a}", (0.014, 0.020, 0.22), col, mat_red, location=(pg_x - 0.03, wb_y + 0.32 + pl_a * 0.08, 1.62), rotation=(pl_a, 0.0, 0.0), bevel_width=0.003, outline_thickness=0.0035)
    _make_cylinder("Prop_PegHammer_Handle", 0.013, 0.32, col, mat_wood, location=(pg_x - 0.03, wb_y + 0.55, 1.58), outline_thickness=0.0035)
    _make_beveled_box("Prop_PegHammer_Head", (0.035, 0.13, 0.038), col, mat_chrome, location=(pg_x - 0.03, wb_y + 0.55, 1.74), bevel_width=0.005, outline_thickness=0.004)
    for sd_i, sd_col in enumerate((mat_red, mat_can_y, mat_can_b)):
        sdy = wb_y + 0.72 + sd_i * 0.08
        _make_cylinder(f"Prop_PegSD_Handle_{sd_i}", 0.016, 0.10, col, sd_col, location=(pg_x - 0.03, sdy, 1.68), outline_thickness=0.003)
        _make_cylinder(f"Prop_PegSD_Shaft_{sd_i}", 0.005, 0.13, col, mat_chrome, location=(pg_x - 0.03, sdy, 1.56), outline_thickness=0.002)

    # 3) Multi-Tier Steel Storage Rack
    rk_x, rk_y = 2.78, 1.18
    for rx_o in (-0.28, 0.28):
        for ry_o in (-0.62, 0.62):
            _make_beveled_box(f"Prop_RackPost_{rx_o}_{ry_o}", (0.045, 0.045, 1.92), col, mat_beam, location=(rk_x + rx_o, rk_y + ry_o, 0.96), bevel_width=0.004, outline_thickness=0.005)
    for sh_z in (0.18, 0.72, 1.26, 1.80):
        _make_beveled_box(f"Prop_RackShelf_{sh_z}", (0.60, 1.30, 0.035), col, mat_bench_leg, location=(rk_x, rk_y, sh_z), bevel_width=0.005, outline_thickness=0.005)

    for j_i, (jy, j_mat) in enumerate([(rk_y - 0.38, mat_red), (rk_y - 0.14, mat_can_y), (rk_y + 0.10, mat_can_b)]):
        _make_beveled_box(f"Prop_OilJug_{j_i}", (0.14, 0.18, 0.28), col, j_mat, location=(rk_x - 0.05, jy, 1.42), bevel_width=0.022, outline_thickness=0.005)
        _make_cylinder(f"Prop_OilJugCap_{j_i}", 0.024, 0.04, col, mat_white, location=(rk_x - 0.05, jy + 0.04, 1.58), outline_thickness=0.003)
        _make_uv_quad(f"Prop_OilJugLabel_{j_i}", 0.13, 0.15, col, mat_oil_lbl, location=(rk_x - 0.123, jy, 1.41), rotation=(math.pi * 0.5, 0.0, -math.pi * 0.5))

    for sp_i, sp_m in enumerate((mat_can_b, mat_can_y, mat_red, mat_can_b)):
        spy = rk_y + 0.22 + sp_i * 0.09
        _make_cylinder(f"Prop_SprayCan_{sp_i}", 0.034, 0.20, col, sp_m, location=(rk_x - 0.08, spy, 0.84), outline_thickness=0.004)
        _make_cylinder(f"Prop_SprayCap_{sp_i}", 0.033, 0.045, col, mat_red if sp_i % 2 == 0 else mat_can_y, location=(rk_x - 0.08, spy, 0.96), outline_thickness=0.003)

    _make_beveled_box("Prop_PartsBox_1", (0.38, 0.46, 0.28), col, mat_cardboard, location=(rk_x, rk_y - 0.25, 0.34), rotation=(0.0, 0.0, 0.08), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Prop_PartsBox_2", (0.34, 0.38, 0.24), col, mat_cardboard, location=(rk_x, rk_y + 0.28, 0.32), rotation=(0.0, 0.0, -0.06), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Prop_PartsBox_Top", (0.36, 0.44, 0.26), col, mat_cardboard, location=(rk_x, rk_y + 0.15, 1.95), bevel_width=0.008, outline_thickness=0.005)

    # Wall-Mounted First-Aid Kit (`Kotak P3K`)
    p3k_x, p3k_y, p3k_z = right_x - 0.16, 0.28, 1.48
    _make_beveled_box("Prop_FirstAid_Box", (0.12, 0.28, 0.32), col, mat_white, location=(p3k_x, p3k_y, p3k_z), bevel_width=0.012, outline_thickness=0.005)
    _make_beveled_box("Prop_FirstAid_CrossH", (0.015, 0.13, 0.042), col, mat_red, location=(p3k_x - 0.062, p3k_y, p3k_z), bevel_width=0.002, outline_thickness=0.0)
    _make_beveled_box("Prop_FirstAid_CrossV", (0.015, 0.042, 0.13), col, mat_red, location=(p3k_x - 0.062, p3k_y, p3k_z), bevel_width=0.002, outline_thickness=0.0)

    # Wall-Mounted Yellow/Orange Air Compressor Hose Reel
    reel_x, reel_y, reel_z = right_x - 0.22, 0.28, 2.02
    _make_beveled_box("Prop_HoseReel_Bracket", (0.22, 0.14, 0.26), col, mat_red, location=(reel_x + 0.06, reel_y, reel_z), bevel_width=0.008, outline_thickness=0.005)
    for d_off in (-0.065, 0.065):
        _make_cylinder(f"Prop_HoseReel_Disc_{d_off}", 0.19, 0.018, col, mat_can_y, location=(reel_x, reel_y + d_off, reel_z), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.005)
    for hc_i in range(4):
        _make_torus(f"Prop_AirHose_Coil_{hc_i}", 0.135, 0.014, col, mat_hose_org, location=(reel_x, reel_y - 0.045 + hc_i * 0.03, reel_z), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.003)

    # 4) Multi-Tier Red Rolling Tool Chests:
    # Right-rear chest rotated by 90° (`math.pi`) so drawers & chrome handles face `-X`
    # directly toward the work area and camera instead of showing a blank side panel!
    for tc_tag, tcx, tcy, tc_rot in [("Right", 2.82, -2.02, math.pi), ("LeftFG", -3.62, -2.35, 0.0)]:
        tc_grp = bpy.data.objects.new(f"Prop_ToolChest_{tc_tag}_Grp", None)
        tc_grp.location = (tcx, tcy, 0.0)
        tc_grp.rotation_euler = (0.0, 0.0, tc_rot)
        link_exclusively(tc_grp, col)

        low_cab = _make_beveled_box(f"Prop_TC_Lower_{tc_tag}", (0.58, 0.88, 0.82), col, mat_red, location=(0.0, 0.0, 0.49), bevel_width=0.016, outline_thickness=0.007)
        top_cab = _make_beveled_box(f"Prop_TC_Upper_{tc_tag}", (0.46, 0.80, 0.46), col, mat_red, location=(-0.03, 0.0, 1.13), bevel_width=0.014, outline_thickness=0.006)
        low_cab.parent = tc_grp
        top_cab.parent = tc_grp
        for d_i in range(4):
            dr = _make_beveled_box(f"Prop_TC_LowDrw_{tc_tag}_{d_i}", (0.025, 0.76, 0.14), col, mat_bench_leg, location=(0.295, 0.0, 0.22 + d_i * 0.175), bevel_width=0.004, outline_thickness=0.004)
            hl = _make_beveled_box(f"Prop_TC_LowHdl_{tc_tag}_{d_i}", (0.022, 0.68, 0.022), col, mat_chrome, location=(0.312, 0.0, 0.25 + d_i * 0.175), bevel_width=0.003, outline_thickness=0.003)
            dr.parent = tc_grp
            hl.parent = tc_grp
        for u_i in range(3):
            udr = _make_beveled_box(f"Prop_TC_UpDrw_{tc_tag}_{u_i}", (0.022, 0.70, 0.10), col, mat_bench_leg, location=(0.205, 0.0, 0.98 + u_i * 0.125), bevel_width=0.003, outline_thickness=0.0035)
            uhl = _make_beveled_box(f"Prop_TC_UpHdl_{tc_tag}_{u_i}", (0.020, 0.62, 0.018), col, mat_chrome, location=(0.220, 0.0, 1.00 + u_i * 0.125), bevel_width=0.002, outline_thickness=0.003)
            udr.parent = tc_grp
            uhl.parent = tc_grp
        for wx_o in (-0.21, 0.21):
            for wy_o in (-0.34, 0.34):
                cw = _make_cylinder(f"Prop_TC_Caster_{tc_tag}_{wx_o}_{wy_o}", 0.04, 0.03, col, mat_tire, location=(wx_o, wy_o, 0.04), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.003)
                cw.parent = tc_grp

    # Left Wall Secondary Workbench + Pegboard
    _make_beveled_box("Prop_LeftBench_Top", (0.72, 1.95, 0.065), col, mat_wood, location=(-3.65, -0.65, 0.88), bevel_width=0.010, outline_thickness=0.007)
    _make_beveled_box("Prop_LeftPegboard", (0.035, 1.75, 0.88), col, mat_bench_leg, location=(-4.02, -0.65, 1.54), bevel_width=0.006, outline_thickness=0.006)
    for lw_i in range(5):
        _make_beveled_box(f"Prop_LeftWrench_{lw_i}", (0.014, 0.032, 0.28 - lw_i * 0.03), col, mat_chrome, location=(-3.98, -1.25 + lw_i * 0.28, 1.62), bevel_width=0.003, outline_thickness=0.0035)

    # 5) Three Crisp Workshop Wall Posters / Signs (Right & Back Walls)
    posters = [
        ("Prop_Poster_SafetyFirst", mat_p_safety, (right_x - 0.12, -2.55, 1.82), (math.pi * 0.5, 0.0, -math.pi * 0.5)),
        ("Prop_Poster_ServiceChart", mat_p_chart, (1.85, back_y - 0.12, 1.86), (math.pi * 0.5, 0.0, 0.0)),
        ("Prop_Poster_RetroOil", mat_p_oil, (-0.95, back_y - 0.12, 1.86), (math.pi * 0.5, 0.0, 0.0)),
    ]
    for p_name, p_mat, p_loc, p_rot in posters:
        _make_beveled_box(p_name + "_Frame", (0.64, 0.022, 0.84), col, mat_beam, location=p_loc, rotation=(0.0, 0.0, p_rot[2]), bevel_width=0.005, outline_thickness=0.005)
        offset_n = Vector((0.0, -0.016, 0.0)) if abs(p_rot[2]) < 0.1 else Vector((-0.016, 0.0, 0.0))
        _make_uv_quad(p_name + "_Print", 0.58, 0.78, col, p_mat, location=tuple(Vector(p_loc) + offset_n), rotation=p_rot)

    # 6) Corner Metal Oil Drums & Spare Tire Stack
    drum_specs = [
        ("BackRight1", 2.15, 1.88, mat_can_b),
        ("BackRight2", 2.75, 1.96, mat_red),
        ("BackLeft1", -2.85, 1.88, mat_green_lamp),
    ]
    for d_tag, dx, dy, d_mat in drum_specs:
        _make_cylinder(f"Prop_OilDrum_{d_tag}", 0.28, 0.88, col, d_mat, location=(dx, dy, 0.44), outline_thickness=0.007)
        for rz_rib in (0.28, 0.60, 0.87):
            _make_torus(f"Prop_OilDrumRib_{d_tag}_{rz_rib}", 0.284, 0.012, col, mat_beam if rz_rib == 0.87 else d_mat, location=(dx, dy, rz_rib), outline_thickness=0.003)

    for t_i in range(3):
        _make_cylinder(f"Prop_SpareTire_{t_i}", 0.33, 0.21, col, mat_tire, location=(-1.95 + (t_i % 2) * 0.03, 1.92, 0.105 + t_i * 0.215), outline_thickness=0.006)

    return objs


# ==============================================================================
# 2. REALISTIC CLASSIC CAR IMPORT (`car_reference.glb`), CLEANUP & RAYCAST PROPS
# ==============================================================================
def _eval_world_bbox(objs: List[bpy.types.Object], deps: bpy.types.Depsgraph) -> Tuple[Vector, Vector]:
    min_v = Vector((1e9, 1e9, 1e9))
    max_v = Vector((-1e9, -1e9, -1e9))
    found = False
    for o in objs:
        if o.type != "MESH":
            continue
        oe = o.evaluated_get(deps)
        for corner in oe.bound_box:
            wc = oe.matrix_world @ Vector(corner)
            min_v.x = min(min_v.x, wc.x)
            min_v.y = min(min_v.y, wc.y)
            min_v.z = min(min_v.z, wc.z)
            max_v.x = max(max_v.x, wc.x)
            max_v.y = max(max_v.y, wc.y)
            max_v.z = max(max_v.z, wc.z)
            found = True
    if not found:
        return Vector((-1.0, -1.0, 0.0)), Vector((1.0, 1.0, 1.0))
    return min_v, max_v


def _is_ancestor_in_set(obj: bpy.types.Object, valid_roots: set) -> bool:
    cur = obj
    while cur is not None:
        if cur in valid_roots:
            return True
        cur = cur.parent
    return False


def _build_world_car_surface_proxy(
    body_meshes: List[bpy.types.Object],
    deps: bpy.types.Depsgraph,
    col: bpy.types.Collection,
) -> bpy.types.Object:
    """
    Combine evaluated world-space solid car body panels (excluding glass & wheels)
    into a temporary Identity-transform mesh so `ray_cast` & `closest_point_on_mesh`
    operate with 100% precision directly in world coordinates.
    """
    bm_merged = bmesh.new()
    for o in body_meshes:
        if o.type != "MESH" or o.hide_render:
            continue
        oe = o.evaluated_get(deps)
        tmp_m = bpy.data.meshes.new_from_object(oe, preserve_all_data_layers=False, depsgraph=deps)
        bm_part = bmesh.new()
        bm_part.from_mesh(tmp_m)
        bmesh.ops.transform(bm_part, matrix=oe.matrix_world, verts=bm_part.verts)
        tmp_part_mesh = bpy.data.meshes.new("_TmpPartMesh")
        bm_part.to_mesh(tmp_part_mesh)
        bm_part.free()
        bm_merged.from_mesh(tmp_part_mesh)
        bpy.data.meshes.remove(tmp_part_mesh)
        bpy.data.meshes.remove(tmp_m)

    bmesh.ops.triangulate(bm_merged, faces=list(bm_merged.faces))
    bm_merged.normal_update()
    proxy_mesh = bpy.data.meshes.new("_TmpCarSurfaceProxy_Mesh")
    bm_merged.to_mesh(proxy_mesh)
    bm_merged.free()

    proxy_obj = bpy.data.objects.new("_TmpCarSurfaceProxy", proxy_mesh)
    col.objects.link(proxy_obj)
    bpy.context.view_layer.update()
    return proxy_obj


def _project_onto_left_car_panel(
    proxy_obj: bpy.types.Object,
    x: float,
    z: float,
    fallback_y: float = -0.42,
) -> Tuple[Vector, Vector]:
    """
    Project `(x, z)` onto the car's front-left outer body surface using `ray_cast`
    from `-Y -> +Y` (with `closest_point_on_mesh` fallback), returning `(world_pt, outward_normal)`.
    """
    hit, loc, norm, _ = proxy_obj.ray_cast(Vector((x, -1.50, z)), Vector((0.0, 1.0, 0.0)))
    if not hit or loc.y > -0.15:
        ok, c_loc, c_norm, _ = proxy_obj.closest_point_on_mesh(Vector((x, fallback_y, z)))
        if ok:
            loc, norm = c_loc, c_norm
        else:
            loc, norm = Vector((x, fallback_y, z)), Vector((0.0, -1.0, 0.0))

    n = norm.normalized() if norm.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    if n.y > 0.0:
        n = -n
    return loc.copy(), n


def _import_and_setup_reference_car(col: bpy.types.Collection) -> Dict[str, Any]:
    """
    Import `assets/car_reference.glb`:
      1. Inspect all imported child meshes & helper objects; delete `Icosphere` /
         `glTF_not_exported` bone-shape helpers and any non-body pedestal/base meshes.
      2. Keep 100% pure car meshes (all 4 wheels, doors, glass, hood, body) with ZERO
         stray procedural brake rotors/calipers or duplicate license plates.
      3. Recompute clean world `bound_box`, orient front toward `-X`, pitch front axle
         gently (~16 cm lift), and rest rear tires cleanly on `Z = 0.000m`.
    """
    import addon_utils
    try:
        addon_utils.enable("io_scene_gltf2", default_set=True)
    except Exception:
        pass

    pre_objs = set(bpy.data.objects)
    pre_cols = set(bpy.data.collections)
    bpy.ops.import_scene.gltf(filepath=str(CAR_GLB_PATH))
    raw_imported = [o for o in bpy.data.objects if o not in pre_objs]
    new_cols = [c for c in bpy.data.collections if c not in pre_cols]

    # Strip custom bone shapes (`Icosphere`) from any imported Armature first
    for o in raw_imported:
        if o.type == "ARMATURE" and o.pose:
            for pb in o.pose.bones:
                pb.custom_shape = None

    # Identify valid car hierarchy roots (exclude `glTF_not_exported` & helper primitives)
    bad_name_tokens = (
        "icosphere", "bone_shape", "pedestal", "ground", "floor",
        "base", "stand", "shadow", "backdrop", "plinth", "rock",
    )
    valid_roots = set()
    for o in raw_imported:
        if o.parent is None:
            in_hidden_col = any("not_exported" in c.name.lower() for c in o.users_collection)
            bad_root_name = any(tok in o.name.lower() for tok in bad_name_tokens)
            if not in_hidden_col and not bad_root_name:
                valid_roots.add(o)

    imported: List[bpy.types.Object] = []
    removed_names: List[str] = []
    for o in list(raw_imported):
        low_n = o.name.lower()
        in_hidden_col = any("not_exported" in c.name.lower() for c in o.users_collection)
        has_bad_name = any(tok in low_n for tok in bad_name_tokens)
        in_car_tree = _is_ancestor_in_set(o, valid_roots)
        no_mat_mesh = (o.type == "MESH" and len(o.data.materials) == 0)

        if in_hidden_col or has_bad_name or (not in_car_tree) or no_mat_mesh:
            removed_names.append(f"{o.name}({o.type})")
            mesh_data = o.data if o.type == "MESH" else None
            bpy.data.objects.remove(o, do_unlink=True)
            if mesh_data is not None and mesh_data.users == 0:
                bpy.data.meshes.remove(mesh_data)
        else:
            imported.append(o)

    for c in new_cols:
        if c.name in bpy.data.collections and len(c.objects) == 0 and len(c.children) == 0:
            bpy.data.collections.remove(c)

    for o in imported:
        link_exclusively(o, col)

    roots = [o for o in imported if o.parent is None]
    master = bpy.data.objects.new("Car_Reference_Master", None)
    link_exclusively(master, col)
    for r in roots:
        w_m = r.matrix_world.copy()
        r.parent = master
        r.matrix_world = w_m

    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    # Identify wheel meshes accurately via active non-zero vertex-group weight (`FL_2`, `FR_0`, `RL_3`, `RR_1`)
    def _dominant_vg_name(mesh_obj: bpy.types.Object) -> str:
        if mesh_obj.type != "MESH" or not mesh_obj.vertex_groups or len(mesh_obj.data.vertices) == 0:
            return ""
        best_idx = -1
        best_w = 0.0
        for g in mesh_obj.data.vertices[0].groups:
            if g.weight > best_w:
                best_w = g.weight
                best_idx = g.group
        if best_idx >= 0 and best_idx < len(mesh_obj.vertex_groups):
            return mesh_obj.vertex_groups[best_idx].name
        return ""

    wheel_vg_map: Dict[str, bpy.types.Object] = {}
    for o in imported:
        if o.type != "MESH":
            continue
        dom_vg = _dominant_vg_name(o).upper()
        for tag, key in (("FL", "FL_2"), ("FR", "FR_0"), ("RL", "RL_3"), ("RR", "RR_1")):
            if dom_vg == key:
                wheel_vg_map[tag] = o

    if len(wheel_vg_map) == 4:
        w_bmin, _ = _eval_world_bbox(list(wheel_vg_map.values()), deps)
        for o in list(imported):
            if o.type != "MESH" or o in wheel_vg_map.values():
                continue
            omin, _ = _eval_world_bbox([o], deps)
            if omin.z < w_bmin.z - 0.05:
                removed_names.append(f"{o.name}(sub-wheel-base z={omin.z:.3f})")
                imported.remove(o)
                md = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if md and md.users == 0:
                    bpy.data.meshes.remove(md)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

    mesh_objs = [o for o in imported if o.type == "MESH"]
    print(f"[CarGLB Inspect] Kept {len(mesh_objs)} clean car meshes; Wheels={sorted(wheel_vg_map.keys())}; Removed helpers/pedestals: {removed_names}")
    for mo in mesh_objs:
        mats_s = [m.name for m in mo.data.materials if m]
        print(f"  [CarGLB Mesh] {mo.name}: verts={len(mo.data.vertices)}, mats={mats_s}, dom_vg={_dominant_vg_name(mo)}")

    # 1) Auto-orient Car so Front Headlights face `-X`
    front_meshes = [o for o in mesh_objs if any("lights_front" in (m.name.lower() if m else "") for m in o.data.materials)]
    rear_meshes = [o for o in mesh_objs if any("taillight" in (m.name.lower() if m else "") for m in o.data.materials)]
    if front_meshes and rear_meshes:
        f_min, f_max = _eval_world_bbox(front_meshes, deps)
        r_min, r_max = _eval_world_bbox(rear_meshes, deps)
        fwd_xy = ((f_min + f_max) * 0.5 - (r_min + r_max) * 0.5).xy
        cur_yaw = math.atan2(fwd_xy.y, fwd_xy.x)
        master.rotation_euler = (0.0, 0.0, math.pi - cur_yaw)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

    # 2) Normalize Scale to Realistic Classic Sedan Length = 3.96m using ONLY clean car meshes
    b_min, b_max = _eval_world_bbox(mesh_objs, deps)
    cur_len = max(0.1, b_max.x - b_min.x)
    scale_factor = 3.96 / cur_len
    master.scale = (scale_factor, scale_factor, scale_factor)

    # Service pitch (-0.072 rad around local +Y BEFORE R_z(pi)): lifts car FRONT (+X local -> -X world)
    # UP by ~16 cm while keeping rear tires flat on Z=0.0!
    master.rotation_euler = (master.rotation_euler.x, -0.072, master.rotation_euler.z)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    # 3) Recompute exact world bound_box of clean car meshes, wheels, and main body shell
    b_min, b_max = _eval_world_bbox(mesh_objs, deps)
    main_body_meshes = [o for o in mesh_objs if _dominant_vg_name(o) == "Root_10"] or mesh_objs
    body_min, _ = _eval_world_bbox(main_body_meshes, deps)

    fl_wheel = wheel_vg_map.get("FL")
    fr_wheel = wheel_vg_map.get("FR")
    rear_wheels = [w for k, w in wheel_vg_map.items() if k in ("RL", "RR")]

    # Auto-verify pitch direction: front wheels MUST be higher than rear wheels (never nose-down!)
    if fl_wheel is not None and rear_wheels:
        fl_chk_min, _ = _eval_world_bbox([fl_wheel], deps)
        rw_chk_min, _ = _eval_world_bbox(rear_wheels, deps)
        if fl_chk_min.z < rw_chk_min.z + 0.02:
            master.rotation_euler = (master.rotation_euler.x, -master.rotation_euler.y, master.rotation_euler.z)
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            b_min, b_max = _eval_world_bbox(mesh_objs, deps)
            body_min, _ = _eval_world_bbox(main_body_meshes, deps)

    if fl_wheel is not None:
        fl_min, fl_max = _eval_world_bbox([fl_wheel], deps)
        fl_center_x = 0.5 * (fl_min.x + fl_max.x)
    else:
        fl_center_x = b_min.x + 0.80

    if rear_wheels:
        rw_min, _ = _eval_world_bbox(rear_wheels, deps)
        rear_ground_z = rw_min.z
    else:
        rear_ground_z = b_min.z

    # Position car so:
    #   - Rear tires sit 100% flush on workshop floor (`Z = 0.000m`)
    #   - Front tires sit cleanly ~16cm ABOVE the floor (NEVER sinking underground!)
    #   - Front-left wheel hub X sits at `X = -0.32m`
    #   - Left body flank sits at `Y = -0.440m`
    dx = -0.32 - fl_center_x
    dy = -0.440 - body_min.y
    dz = 0.0 - rear_ground_z
    master.location = (master.location.x + dx, master.location.y + dy, master.location.z + dz)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    # Final hard safety clamp: guarantee NO tire ever drops below Z = 0.000m
    all_wheels = list(wheel_vg_map.values())
    if all_wheels:
        aw_min, _ = _eval_world_bbox(all_wheels, deps)
        if aw_min.z < 0.0:
            master.location.z += -aw_min.z
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()

    # Upgrade All GLB Materials to Rich Textured Cel-Shade + Clean Outlines & Collision
    upgraded_mats = set()
    solid_body_meshes: List[bpy.types.Object] = []
    wheel_set = set(wheel_vg_map.values())

    for o in mesh_objs:
        for m in o.data.materials:
            if m and m.name not in upgraded_mats:
                upgrade_glb_material_to_cel(m)
                upgraded_mats.add(m.name)
        is_glass_or_lamp = any(
            m and any(k in m.name.lower() for k in ("glass", "light", "blink", "fog", "reverse"))
            for m in o.data.materials
        )
        if not is_glass_or_lamp:
            apply_cel_outline(o, thickness=0.0042, use_even_offset=False)
            if o not in wheel_set:
                solid_body_meshes.append(o)

    b_min_f, b_max_f = _eval_world_bbox(mesh_objs, deps)
    fl_min_f, fl_max_f = _eval_world_bbox([fl_wheel], deps) if fl_wheel else (Vector((-0.58, -0.42, 0.16)), Vector((-0.05, -0.22, 0.69)))
    fr_min_f, fr_max_f = _eval_world_bbox([fr_wheel], deps) if fr_wheel else (Vector((-0.58, 0.84, 0.16)), Vector((-0.05, 1.04, 0.69)))
    rw_min_f, _ = _eval_world_bbox(rear_wheels, deps) if rear_wheels else (Vector((1.48, -0.40, 0.0)), Vector((2.01, -0.20, 0.53)))

    print(
        f"[CarGLB Bounds] Clean Car World BBox: min=({b_min_f.x:.3f},{b_min_f.y:.3f},{b_min_f.z:.3f}) "
        f"max=({b_max_f.x:.3f},{b_max_f.y:.3f},{b_max_f.z:.3f}) | "
        f"RearTire Z_min={rw_min_f.z:.4f}m | FrontTire Z_min={fl_min_f.z:.4f}m"
    )

    return {
        "car_master": master,
        "car_mid_y": 0.5 * (b_min_f.y + b_max_f.y),
        "solid_body_meshes": solid_body_meshes,
        "fl_wheel_bbox": (fl_min_f, fl_max_f),
        "fr_wheel_bbox": (fr_min_f, fr_max_f),
    }


def _build_conformal_fender_patch(
    proxy_obj: bpy.types.Object,
    col: bpy.types.Collection,
    mat_primer: bpy.types.Material,
    x_min: float = -0.43,
    x_max: float = -0.07,
    z_min: float = 0.708,
    z_max: float = 0.784,
    nx_steps: int = 15,
    nz_steps: int = 7,
    outer_offset: float = 0.0030,
    inner_offset: float = 0.0006,
) -> bpy.types.Object:
    """
    Build a thin contoured sheet-metal repair plate mapped directly onto the red car's
    front-left fender via `ray_cast` / `closest_point_on_mesh` (`outer_offset <= 0.004m`!).
    """
    bm = bmesh.new()
    outer_grid: List[List[bmesh.types.BMVert]] = []
    inner_grid: List[List[bmesh.types.BMVert]] = []

    for iz in range(nz_steps):
        vz = z_min + (z_max - z_min) * (iz / float(nz_steps - 1))
        o_row: List[bmesh.types.BMVert] = []
        i_row: List[bmesh.types.BMVert] = []
        for ix in range(nx_steps):
            vx = x_min + (x_max - x_min) * (ix / float(nx_steps - 1))
            hit_pt, hit_n = _project_onto_left_car_panel(proxy_obj, vx, vz)
            o_row.append(bm.verts.new(hit_pt + hit_n * outer_offset))
            i_row.append(bm.verts.new(hit_pt + hit_n * inner_offset))
        outer_grid.append(o_row)
        inner_grid.append(i_row)

    for iz in range(nz_steps - 1):
        for ix in range(nx_steps - 1):
            # Outer surface facing -Y (camera/workshop side)
            bm.faces.new([outer_grid[iz][ix], outer_grid[iz][ix + 1], outer_grid[iz + 1][ix + 1], outer_grid[iz + 1][ix]])
            # Inner backing surface
            bm.faces.new([inner_grid[iz][ix], inner_grid[iz + 1][ix], inner_grid[iz + 1][ix + 1], inner_grid[iz][ix + 1]])

    # Stitch thin sheet-metal perimeter edges
    for ix in range(nx_steps - 1):
        bm.faces.new([inner_grid[0][ix], inner_grid[0][ix + 1], outer_grid[0][ix + 1], outer_grid[0][ix]])
        t = nz_steps - 1
        bm.faces.new([outer_grid[t][ix], outer_grid[t][ix + 1], inner_grid[t][ix + 1], inner_grid[t][ix]])
    for iz in range(nz_steps - 1):
        bm.faces.new([outer_grid[iz][0], inner_grid[iz][0], inner_grid[iz + 1][0], outer_grid[iz + 1][0]])
        r = nx_steps - 1
        bm.faces.new([inner_grid[iz][r], outer_grid[iz][r], outer_grid[iz + 1][r], inner_grid[iz + 1][r]])

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    patch_obj = _new_mesh_obj(
        "Car_FenderRepairPatch", bm, col, mat_primer,
        outline_thickness=0.0022, smooth=True,
    )
    _add_collision_modifier(patch_obj, damping=0.32, friction=0.20)
    return patch_obj


def _build_car_jacks_weld_seam_and_ground_clamp(col: bpy.types.Collection) -> Dict[str, Any]:
    """
    Import clean reference car + raycasted 0-gap Jack Stands + surface-snapped Weld Plate &
    Weld Seam + rocker-panel-clamped Orange Ground Clamp.
    """
    result: Dict[str, Any] = {}
    car_info = _import_and_setup_reference_car(col)
    result.update(car_info)

    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    proxy_obj = _build_world_car_surface_proxy(car_info["solid_body_meshes"], deps, col)

    mat_primer = get_cel_material("Mat_Car_PrimerPatch", PALETTE_HEX["car_primer_grey"], shadow_factor=0.45, roughness=0.62, surface_type="metal")
    mat_jack = get_cel_material("Mat_Jack_Orange", PALETTE_HEX["jack_orange"], shadow_factor=0.42, spec_strength=0.45, surface_type="metal")
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], spec_strength=0.85, surface_type="chrome")
    mat_dark = get_cel_material("Mat_Car_Chassis", PALETTE_HEX["car_interior"], surface_type="metal")
    mat_copper = get_cel_material("Mat_Torch_Copper", PALETTE_HEX["torch_copper"], shadow_factor=0.45, spec_strength=0.80, surface_type="chrome")
    mat_seam_groove = get_cel_material("Mat_Seam_DarkGroove", "#181A22", shadow_factor=0.3, surface_type="metal")

    # ---- 1) TWO HEAVY-DUTY ORANGE JACK STANDS (0.0mm GAP VIA UPWARD RAYCAST!) ----
    fl_min, fl_max = car_info["fl_wheel_bbox"]
    fr_min, fr_max = car_info["fr_wheel_bbox"]
    # Strictly behind front tires (`fl_max.x + 0.15m` = `+0.10m`), under solid front frame rails!
    jack_x = fl_max.x + 0.155
    jack_y_fl = fl_min.y + 0.165
    jack_y_fr = fr_max.y - 0.165

    jack_contacts: Dict[str, Dict[str, float]] = {}
    for j_tag, jy in (("FL", jack_y_fl), ("FR", jack_y_fr)):
        hit_zs: List[float] = []
        for ox in (-0.025, 0.0, 0.025):
            for oy in (-0.025, 0.0, 0.025):
                hit, h_loc, _, _ = proxy_obj.ray_cast(Vector((jack_x + ox, jy + oy, 0.0)), Vector((0.0, 0.0, 1.0)))
                if hit and 0.12 < h_loc.z < 0.65:
                    hit_zs.append(h_loc.z)
        z_chassis = min(hit_zs) if hit_zs else 0.305

        h_saddle = 0.026
        h_base = min(0.195, z_chassis * 0.62)
        saddle_center_z = z_chassis - h_saddle * 0.5  # Top of saddle == z_chassis (0.000m gap!)
        post_bottom_z = h_base - 0.025
        post_top_z = z_chassis - h_saddle + 0.003
        h_post = max(0.05, post_top_z - post_bottom_z)
        post_center_z = 0.5 * (post_bottom_z + post_top_z)

        bm_j = bmesh.new()
        bmesh.ops.create_cone(bm_j, cap_ends=True, cap_tris=False, segments=4, radius1=0.145, radius2=0.058, depth=h_base)
        _new_mesh_obj(
            f"Prop_JackStand_Base_{j_tag}", bm_j, col, mat_jack,
            location=(jack_x, jy, h_base * 0.5),
            rotation=(0.0, 0.0, math.pi * 0.25),
            outline_thickness=0.0055,
        )
        _make_beveled_box(
            f"Prop_JackStand_Post_{j_tag}", (0.046, 0.046, h_post), col, mat_chrome,
            location=(jack_x, jy, post_center_z),
            bevel_width=0.004, outline_thickness=0.004,
        )
        _make_beveled_box(
            f"Prop_JackStand_Saddle_{j_tag}", (0.088, 0.105, h_saddle), col, mat_dark,
            location=(jack_x, jy, saddle_center_z),
            bevel_width=0.004, outline_thickness=0.004,
        )
        jack_contacts[j_tag] = {
            "x": round(jack_x, 4),
            "y": round(jy, 4),
            "chassis_z": round(z_chassis, 4),
            "saddle_top_z": round(saddle_center_z + h_saddle * 0.5, 4),
            "gap_mm": 0.0,
        }
        print(f"[JackStand {j_tag}] Raycast chassis Z={z_chassis:.4f}m at ({jack_x:.3f}, {jy:.3f}) -> Saddle top={z_chassis:.4f}m (0.0mm gap)")

    result["jack_contacts"] = jack_contacts

    # Hydraulic Floor Jack parked cleanly to front-left of car bumper
    _make_beveled_box("Prop_FloorJack_Body", (0.54, 0.22, 0.11), col, mat_jack, location=(-1.42, -0.58, 0.065), rotation=(0.0, 0.0, 0.38), bevel_width=0.015, outline_thickness=0.006)
    _make_cylinder("Prop_FloorJack_Cup", 0.055, 0.04, col, mat_dark, location=(-1.24, -0.50, 0.13), outline_thickness=0.004)
    for jw_x, jw_y in [(-1.24, -0.43), (-1.24, -0.59), (-1.58, -0.56), (-1.58, -0.72)]:
        _make_cylinder(f"Prop_FloorJack_Wheel_{jw_x}_{jw_y}", 0.032, 0.025, col, mat_chrome, location=(jw_x, jw_y, 0.032), rotation=(math.pi * 0.5, 0.0, 0.38), outline_thickness=0.003)
    _make_cylinder("Prop_FloorJack_Handle", 0.014, 0.86, col, mat_chrome, location=(-1.72, -0.70, 0.40), rotation=(0.30, -0.68, 0.38), outline_thickness=0.004)

    # ---- 2) SURFACE-CONFORMING FENDER REPAIR PLATE & RAYCASTED WELD SEAM ----
    patch = _build_conformal_fender_patch(proxy_obj, col, mat_primer)
    result["fender_patch"] = patch

    num_seam_pts = 9
    seam_points: List[Vector] = []
    seam_normals: List[Vector] = []
    groove_points: List[Vector] = []

    for i in range(num_seam_pts):
        u = i / float(num_seam_pts - 1)
        sx = -0.40 + 0.30 * u
        sz = 0.740 + 0.008 * math.sin(math.pi * u)
        hit_pt, hit_n = _project_onto_left_car_panel(proxy_obj, sx, sz)
        # Offset strictly <= 0.004m outward along surface normal!
        seam_points.append(hit_pt + hit_n * 0.0036)
        groove_points.append(hit_pt + hit_n * 0.0031)
        seam_normals.append(hit_n)

    seam_bg_curve = bpy.data.curves.new("Car_WeldGroove_Curve", type="CURVE")
    seam_bg_curve.dimensions = "3D"
    seam_bg_curve.bevel_depth = 0.0032
    seam_bg_curve.bevel_resolution = 3
    sp_bg = seam_bg_curve.splines.new("BEZIER")
    sp_bg.bezier_points.add(len(groove_points) - 1)
    for idx, gp in enumerate(groove_points):
        bp = sp_bg.bezier_points[idx]
        bp.co = gp
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    seam_groove_obj = bpy.data.objects.new("Car_WeldGroove", seam_bg_curve)
    seam_groove_obj.data.materials.append(mat_seam_groove)
    link_exclusively(seam_groove_obj, col)

    seam_curve = bpy.data.curves.new("VFX_WeldSeam_Curve", type="CURVE")
    seam_curve.dimensions = "3D"
    seam_curve.bevel_depth = 0.0045
    seam_curve.bevel_resolution = 4
    if hasattr(seam_curve, "use_uv_as_generated"):
        seam_curve.use_uv_as_generated = True
    sp = seam_curve.splines.new("BEZIER")
    sp.bezier_points.add(len(seam_points) - 1)
    for idx, spt in enumerate(seam_points):
        bp = sp.bezier_points[idx]
        bp.co = spt
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    seam_mat, seam_prog_node, seam_heat_node = create_weld_seam_material()
    seam_obj = bpy.data.objects.new("VFX_WeldSeam", seam_curve)
    seam_obj.data.materials.append(seam_mat)
    link_exclusively(seam_obj, col)

    result["weld_seam_obj"] = seam_obj
    result["seam_prog_node"] = seam_prog_node
    result["seam_heat_node"] = seam_heat_node
    result["seam_points"] = seam_points
    result["seam_normals"] = seam_normals
    print(f"[WeldSeam] Snapped {len(seam_points)} pts flush to car fender: start={tuple(round(v, 4) for v in seam_points[0])} -> end={tuple(round(v, 4) for v in seam_points[-1])}")

    # ---- 3) ORANGE GROUND CLAMP CLIPPED DIRECTLY ONTO LOWER ROCKER / CHASSIS EDGE ----
    clamp_target_x, clamp_target_z = 0.05, 0.348
    c_hit, c_loc, c_norm, _ = proxy_obj.ray_cast(Vector((clamp_target_x, -1.20, clamp_target_z)), Vector((0.0, 1.0, 0.0)))
    if not c_hit or c_loc.y > -0.15:
        _, c_loc, c_norm, _ = proxy_obj.closest_point_on_mesh(Vector((clamp_target_x, -0.37, clamp_target_z)))

    clamp_grp = bpy.data.objects.new("Prop_GroundClamp_Grp", None)
    clamp_grp.location = c_loc
    # Orient local +Y into the rocker edge (`+Y` world, slightly `+Z`) so jaws bite directly onto the metal lip!
    bite_dir = Vector((0.0, 0.94, 0.34)).normalized()
    clamp_grp.rotation_euler = bite_dir.to_track_quat("Y", "Z").to_euler()
    link_exclusively(clamp_grp, col)

    # Copper contact pads gripping right at (0, 0, 0) (`c_loc` metal surface, 0mm gap!)
    pad_up = _make_beveled_box("Prop_GroundClamp_PadA", (0.026, 0.036, 0.008), col, mat_copper, location=(0.0, 0.004, 0.006), bevel_width=0.002, outline_thickness=0.002)
    pad_lo = _make_beveled_box("Prop_GroundClamp_PadB", (0.026, 0.036, 0.008), col, mat_copper, location=(0.0, 0.004, -0.006), bevel_width=0.002, outline_thickness=0.002)
    # Bright Orange Insulated Spring Clamp Handles (`jack_orange`)
    jaw_up = _make_beveled_box("Prop_GroundClamp_JawA", (0.032, 0.105, 0.018), col, mat_jack, location=(0.0, -0.038, 0.018), rotation=(-0.22, 0.0, 0.0), bevel_width=0.004, outline_thickness=0.0035)
    jaw_lo = _make_beveled_box("Prop_GroundClamp_JawB", (0.032, 0.105, 0.018), col, mat_jack, location=(0.0, -0.038, -0.018), rotation=(0.22, 0.0, 0.0), bevel_width=0.004, outline_thickness=0.0035)
    piv = _make_cylinder("Prop_GroundClamp_Pivot", 0.011, 0.038, col, mat_chrome, location=(0.0, -0.032, 0.0), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.0025)
    for part in (pad_up, pad_lo, jaw_up, jaw_lo, piv):
        part.parent = clamp_grp

    bpy.context.view_layer.update()
    clamp_tail_world = clamp_grp.matrix_world @ Vector((0.0, -0.092, -0.028))
    result["ground_clamp_tail"] = clamp_tail_world
    result["ground_clamp_contact"] = c_loc.copy()
    print(f"[GroundClamp] Clipped directly onto car rocker metal at {tuple(round(v, 4) for v in c_loc)}")

    # Clean up temporary world-space raycast proxy mesh
    proxy_data = proxy_obj.data
    bpy.data.objects.remove(proxy_obj, do_unlink=True)
    if proxy_data and proxy_data.users == 0:
        bpy.data.meshes.remove(proxy_data)

    return result


# ==============================================================================
# 3. HIGH-DETAIL MIG WELDER, TEXTURED CONTROL PANEL & ARGON CYLINDER + GAUGES
# ==============================================================================
def _build_welder_torch_and_cable(
    col: bpy.types.Collection,
    ground_clamp_tail: Vector,
) -> Dict[str, bpy.types.Object]:
    """
    Build detailed MIG Welder Cart + Argon Cylinder + smooth Ground Earth Cable connected
    directly to the rocker-clamped Orange Ground Clamp + Articulated 3D Welding Torch.
    """
    mat_welder = get_cel_material("Mat_Welder_Red", PALETTE_HEX["welder_red"], shadow_factor=0.42, spec_strength=0.45, surface_type="metal")
    mat_panel_dark = get_cel_material("Mat_Welder_Dark", "#20232C", shadow_factor=0.36, surface_type="painted")
    mat_tank = get_cel_material("Mat_GasTank_Green", PALETTE_HEX["gas_tank_green"], shadow_factor=0.40, spec_strength=0.55, surface_type="metal")
    mat_brass = get_cel_material("Mat_Brass", PALETTE_HEX["brass_goggles"], shadow_factor=0.44, spec_strength=0.78, surface_type="chrome")
    mat_torch_y = get_cel_material("Mat_Torch_Yellow", PALETTE_HEX["torch_yellow"], shadow_factor=0.45, spec_strength=0.4, surface_type="painted")
    mat_copper = get_cel_material("Mat_Torch_Copper", PALETTE_HEX["torch_copper"], shadow_factor=0.45, spec_strength=0.80, surface_type="chrome")
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], spec_strength=0.85, surface_type="chrome")
    mat_cable = get_cel_material("Mat_Welding_Cable", "#181A20", shadow_factor=0.36, spec_strength=0.30, surface_type="painted")

    mat_panel_tex = get_textured_cel_material("Mat_Decal_WelderPanel", str(DECALS_DIR / "welder_panel.png"), emissive_boost=1.22)
    mat_gauge_tex = get_textured_cel_material("Mat_Decal_PressureGauge", str(DECALS_DIR / "pressure_gauge.png"), alpha_cutout=True, emissive_boost=1.08)
    mat_tank_lbl = get_textured_cel_material("Mat_Decal_GasTankLabel", str(DECALS_DIR / "gas_tank_label.png"))

    wx, wy, wz = WELDER_UNIT_POS
    welder_yaw = 2.45

    welder_grp = bpy.data.objects.new("Prop_WelderCart_Grp", None)
    welder_grp.location = (wx, wy, wz)
    welder_grp.rotation_euler = (0.0, 0.0, welder_yaw)
    link_exclusively(welder_grp, col)

    cart_base = _make_beveled_box("Prop_Welder_CartTray", (0.76, 0.44, 0.05), col, mat_panel_dark, location=(0.0, 0.0, 0.11), bevel_width=0.008, outline_thickness=0.006)
    cart_base.parent = welder_grp
    for cy_u in (-0.18, 0.18):
        up = _make_cylinder(f"Prop_Welder_CartPost_{cy_u}", 0.015, 0.78, col, mat_panel_dark, location=(-0.08, cy_u, 0.50), outline_thickness=0.004)
        up.parent = welder_grp
    for cx_o in (-0.30, 0.30):
        for cy_o in (-0.18, 0.18):
            wh = _make_cylinder(f"Prop_Welder_Wheel_{cx_o}_{cy_o}", 0.055, 0.036, col, mat_cable, location=(cx_o, cy_o, 0.055), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.004)
            wh.parent = welder_grp

    w_box = _make_beveled_box("Prop_Welder_Box", (0.48, 0.35, 0.48), col, mat_welder, location=(0.09, 0.0, 0.38), bevel_width=0.018, outline_thickness=0.007)
    w_box.parent = welder_grp

    for bx_c in (-0.145, 0.325):
        for by_c in (-0.172, 0.172):
            for bz_c in (0.145, 0.615):
                cb = _make_beveled_box(f"Prop_Welder_Bumper_{bx_c}_{by_c}_{bz_c}", (0.048, 0.048, 0.048), col, mat_panel_dark, location=(bx_c, by_c, bz_c), bevel_width=0.010, outline_thickness=0.003)
                cb.parent = welder_grp

    hdl = _make_beveled_box("Prop_Welder_TopHandle", (0.28, 0.032, 0.055), col, mat_panel_dark, location=(0.09, 0.0, 0.65), bevel_width=0.010, outline_thickness=0.004)
    hdl.parent = welder_grp

    for sy_side in (-0.178, 0.178):
        for lv_i in range(7):
            lv = _make_beveled_box(f"Prop_Welder_Louver_{sy_side}_{lv_i}", (0.22, 0.014, 0.022), col, mat_panel_dark, location=(0.04, sy_side, 0.24 + lv_i * 0.042), rotation=(0.35 if sy_side > 0 else -0.35, 0.0, 0.0), bevel_width=0.002, outline_thickness=0.0025)
            lv.parent = welder_grp

    p_quad = _make_uv_quad("Prop_Welder_FrontDecal", 0.31, 0.25, col, mat_panel_tex, location=(0.334, 0.0, 0.45), rotation=(math.pi * 0.5, 0.0, math.pi * 0.5))
    p_quad.parent = welder_grp
    for ky_d in (0.072, -0.038):
        kn = _make_cylinder(f"Prop_Welder_Knob_{ky_d}", 0.022, 0.026, col, mat_panel_dark, location=(0.345, ky_d, 0.39), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.003)
        kn.parent = welder_grp

    tx_loc, ty_loc = -0.23, 0.0
    tank = _make_cylinder("Prop_GasCylinder_Body", 0.118, 0.96, col, mat_tank, location=(tx_loc, ty_loc, 0.61), outline_thickness=0.007)
    tank.parent = welder_grp
    bm_dome = bmesh.new()
    bmesh.ops.create_uvsphere(bm_dome, u_segments=22, v_segments=14, radius=0.118)
    tank_dome = _new_mesh_obj("Prop_GasCylinder_Dome", bm_dome, col, mat_tank, location=(tx_loc, ty_loc, 1.09), outline_thickness=0.007)
    tank_dome.parent = welder_grp

    bm_lbl = bmesh.new()
    lbl_segs = 14
    lbl_verts_b, lbl_verts_t = [], []
    for li in range(lbl_segs + 1):
        ang = -0.85 + (1.70 * li / lbl_segs)
        r_l = 0.121
        lbl_verts_b.append(bm_lbl.verts.new((math.cos(ang) * r_l, math.sin(ang) * r_l, -0.065)))
        lbl_verts_t.append(bm_lbl.verts.new((math.cos(ang) * r_l, math.sin(ang) * r_l, 0.065)))
    uv_l = bm_lbl.loops.layers.uv.new("UVMap")
    for li in range(lbl_segs):
        u0, u1 = li / lbl_segs, (li + 1) / lbl_segs
        f_l = bm_lbl.faces.new([lbl_verts_b[li], lbl_verts_b[li + 1], lbl_verts_t[li + 1], lbl_verts_t[li]])
        for loop, uv in zip(f_l.loops, [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]):
            loop[uv_l].uv = uv
    lbl_obj = _new_mesh_obj("Prop_GasCylinder_Label", bm_lbl, col, mat_tank_lbl, location=(tx_loc, ty_loc, 0.84), rotation=(0.0, 0.0, 0.65), outline_thickness=0.0)
    lbl_obj.parent = welder_grp

    for th_i in range(3):
        tr = _make_torus(f"Prop_GasNeck_Thread_{th_i}", 0.036, 0.006, col, mat_brass, location=(tx_loc, ty_loc, 1.20 + th_i * 0.015), outline_thickness=0.002)
        tr.parent = welder_grp
    valve = _make_cylinder("Prop_GasCylinder_Valve", 0.024, 0.11, col, mat_brass, location=(tx_loc, ty_loc, 1.26), outline_thickness=0.004)
    valve.parent = welder_grp
    vwheel = _make_torus("Prop_GasValve_Wheel", 0.042, 0.008, col, mat_panel_dark, location=(tx_loc, ty_loc, 1.33), outline_thickness=0.003)
    vwheel.parent = welder_grp

    for g_idx, g_off in enumerate((-0.068, 0.068)):
        g_body = _make_cylinder(f"Prop_GasGauge_Body_{g_idx}", 0.044, 0.028, col, mat_brass, location=(-0.17, g_off, 1.28), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.004)
        g_dial = _make_uv_quad(f"Prop_GasGauge_Dial_{g_idx}", 0.078, 0.078, col, mat_gauge_tex, location=(-0.153, g_off, 1.28), rotation=(math.pi * 0.5, 0.0, math.pi * 0.5))
        g_stem = _make_cylinder(f"Prop_GasGauge_Stem_{g_idx}", 0.009, 0.06, col, mat_brass, location=(-0.20, g_off * 0.5, 1.26), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.003)
        for gp in (g_body, g_dial, g_stem):
            gp.parent = welder_grp

    for ch_i in range(14):
        ang = -math.pi * 0.65 + (math.pi * 1.30 * ch_i / 13.0)
        cx_l = tx_loc + math.cos(ang) * 0.128
        cy_l = ty_loc + math.sin(ang) * 0.128
        clink = _make_torus(f"Prop_SafetyChain_{ch_i}", 0.018, 0.0045, col, mat_chrome, location=(cx_l, cy_l, 0.72), rotation=(math.pi * 0.5 if ch_i % 2 == 0 else 0.2, 0.0, ang), outline_thickness=0.002)
        clink.parent = welder_grp

    gas_hose = _make_curve_hose(
        "Prop_Regulator_GasHose",
        [(-0.20, -0.04, 1.24), (-0.34, -0.14, 0.96), (-0.26, -0.12, 0.58), (-0.14, -0.06, 0.44)],
        radius=0.011, col=col, mat=mat_cable,
    )
    gas_hose.parent = welder_grp

    # Smooth Black Ground Return Cable from MIG Welder Earth Socket right into the Clamped Orange Ground Clamp!
    bpy.context.view_layer.update()
    earth_socket_world = welder_grp.matrix_world @ Vector((0.34, -0.09, 0.26))
    gt = ground_clamp_tail
    _make_curve_hose(
        "Prop_Welder_GroundCable",
        [
            tuple(earth_socket_world),
            (0.48, -0.96, 0.014),
            (0.24, -0.66, 0.014),
            (gt.x + 0.03, gt.y - 0.07, max(0.05, gt.z - 0.12)),
            tuple(gt),
        ],
        radius=0.010, col=col, mat=mat_cable,
    )

    # Welder Cable Socket Empty (World Anchor for Main Torch Cable)
    socket_empty = bpy.data.objects.new("Empty_WelderSocket", None)
    socket_empty.empty_display_size = 0.06
    socket_empty.location = WELDER_CABLE_SOCKET
    link_exclusively(socket_empty, col)

    # Articulated Welding Torch (`Prop_WeldingTorch`) + Flexible Hooked Bezier Cable
    torch_root = _make_cylinder(
        "Prop_WeldingTorch", 0.022, 0.165, col, mat_panel_dark,
        location=(0.0, -0.005, 0.0),
        rotation=(math.pi * 0.5, 0.0, 0.0),
        segments=20, outline_thickness=0.005
    )
    grip_sleeve = _make_beveled_box("Prop_Torch_YellowGrip", (0.046, 0.105, 0.052), col, mat_torch_y, location=(0.0, 0.005, 0.002), bevel_width=0.014, outline_thickness=0.004)
    grip_sleeve.parent = torch_root

    trigger = _make_beveled_box("Prop_Torch_Trigger", (0.016, 0.042, 0.022), col, mat_welder, location=(0.0, 0.032, -0.028), rotation=(0.22, 0.0, 0.0), bevel_width=0.004, outline_thickness=0.003)
    trigger.parent = torch_root

    neck1 = _make_cylinder("Prop_Torch_SwanNeck1", 0.0095, 0.085, col, mat_chrome, location=(0.0, 0.112, -0.008), rotation=(math.pi * 0.5 + 0.24, 0.0, 0.0), segments=16, outline_thickness=0.0035)
    neck1.parent = torch_root

    bm_noz = bmesh.new()
    bmesh.ops.create_cone(bm_noz, cap_ends=True, cap_tris=False, segments=18, radius1=0.016, radius2=0.0095, depth=0.056)
    nozzle = _new_mesh_obj("Prop_Torch_CopperNozzle", bm_noz, col, mat_copper, location=(0.0, 0.172, -0.028), rotation=(math.pi * 0.5 + 0.42, 0.0, 0.0), outline_thickness=0.004)
    nozzle.parent = torch_root

    wire_tip = _make_cylinder("Prop_Torch_ElectrodeTip", 0.0028, 0.022, col, mat_brass, location=(0.0, 0.200, -0.041), rotation=(math.pi * 0.5 + 0.42, 0.0, 0.0), segments=10, outline_thickness=0.002)
    wire_tip.parent = torch_root

    torch_tip = bpy.data.objects.new("Empty_TorchTip", None)
    torch_tip.empty_display_type = "SPHERE"
    torch_tip.empty_display_size = 0.025
    torch_tip.location = (0.0, 0.208, -0.045)
    torch_tip.parent = torch_root
    link_exclusively(torch_tip, col)

    boot = _make_cylinder("Prop_Torch_RearBoot", 0.016, 0.05, col, mat_cable, location=(0.0, -0.095, -0.004), rotation=(math.pi * 0.5 - 0.18, 0.0, 0.0), segments=14, outline_thickness=0.0035)
    boot.parent = torch_root

    cable_end_empty = bpy.data.objects.new("Empty_TorchCableBase", None)
    cable_end_empty.empty_display_size = 0.03
    cable_end_empty.location = (0.0, -0.115, -0.008)
    cable_end_empty.parent = torch_root
    link_exclusively(cable_end_empty, col)

    cable_mid_sag = bpy.data.objects.new("Empty_CableFloorLoop", None)
    cable_mid_sag.empty_display_size = 0.05
    cable_mid_sag.location = (0.34, -0.96, 0.16)
    link_exclusively(cable_mid_sag, col)

    cable_curve = bpy.data.curves.new("Prop_WeldingCable_Curve", type="CURVE")
    cable_curve.dimensions = "3D"
    cable_curve.bevel_depth = 0.014
    cable_curve.bevel_resolution = 4
    cable_curve.resolution_u = 24

    spline = cable_curve.splines.new("BEZIER")
    spline.bezier_points.add(2)

    torch_root.location = Vector((-0.24, -0.62, 0.70))
    bpy.context.view_layer.update()

    p0 = cable_end_empty.matrix_world.translation.copy()
    p1 = cable_mid_sag.location.copy()
    p2 = Vector(WELDER_CABLE_SOCKET)

    pts = [p0, p1, p2]
    for idx, co in enumerate(pts):
        bp = spline.bezier_points[idx]
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    cable_obj = bpy.data.objects.new("Prop_WeldingCable", cable_curve)
    cable_obj.data.materials.append(mat_cable)
    link_exclusively(cable_obj, col)

    bpy.context.view_layer.update()

    for idx, target_empty, h_name in [
        (0, cable_end_empty, "Hook_Cable_Torch"),
        (1, cable_mid_sag, "Hook_Cable_Sag"),
        (2, socket_empty, "Hook_Cable_Welder"),
    ]:
        hm = cable_obj.modifiers.new(name=h_name, type="HOOK")
        hm.object = target_empty
        bp = spline.bezier_points[idx]
        bp.handle_left_type = "ALIGNED"
        bp.handle_right_type = "ALIGNED"
        hm.center = tuple(pts[idx])
        hm.vertex_indices_set([idx * 3, idx * 3 + 1, idx * 3 + 2])
        hm.matrix_inverse = target_empty.matrix_world.inverted()

    return {
        "welder_grp": welder_grp,
        "torch_root": torch_root,
        "torch_tip": torch_tip,
        "cable_end_empty": cable_end_empty,
        "cable_mid_sag": cable_mid_sag,
        "socket_empty": socket_empty,
        "cable_obj": cable_obj,
    }


def build_environment_and_props() -> Dict[str, Any]:
    """Build the dense 3D cel-shaded workshop, cleaned reference classic car, and detailed MIG welder."""
    env_col = get_or_create_collection("Col_Workshop_Env")
    props_col = get_or_create_collection("Col_Props_Car_Welder")

    room_objs = _build_workshop_room_and_set_dressing(env_col)
    car_data = _build_car_jacks_weld_seam_and_ground_clamp(props_col)
    welder_data = _build_welder_torch_and_cable(
        props_col,
        ground_clamp_tail=car_data["ground_clamp_tail"],
    )

    return {
        "env_collection": env_col,
        "props_collection": props_col,
        **room_objs,
        **car_data,
        **welder_data,
    }
