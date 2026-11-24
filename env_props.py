"""
env_props.py — 3D Cel-Shaded Workshop Environment, Stylized Car on Jack Stands,
MIG Welder + Argon Tank, Flexible Hooked Bezier Welding Cable & Welding Torch.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from config import (
    FENDER_LEFT_HAND_REST,
    PALETTE_HEX,
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
    get_ink_outline_material,
)


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
    outline_thickness: float = 0.008,
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
    bevel_width: float = 0.02,
    bevel_segments: int = 2,
    outline_thickness: float = 0.008,
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
    outline_thickness: float = 0.007,
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


def _add_collision_modifier(obj: bpy.types.Object, damping: float = 0.38, friction: float = 0.25) -> None:
    mod = obj.modifiers.new(name="SparkCollider", type="COLLISION")
    if obj.collision:
        obj.collision.damping_factor = damping
        obj.collision.damping_random = 0.22
        obj.collision.friction_factor = friction
        obj.collision.stickiness = 0.05


def _build_workshop_room_and_bg_props(col: bpy.types.Collection) -> Dict[str, bpy.types.Object]:
    objs: Dict[str, bpy.types.Object] = {}

    mat_floor = get_cel_material("Mat_Floor_Concrete", PALETTE_HEX["floor_concrete"], shadow_factor=0.52, mid_factor=0.88, lit_factor=1.06, rim_strength=0.0)
    mat_line = get_cel_material("Mat_Floor_HazardLine", PALETTE_HEX["floor_line_yellow"], shadow_factor=0.55, rim_strength=0.0)
    mat_oil = get_cel_material("Mat_Floor_OilStain", PALETTE_HEX["floor_oil"], shadow_factor=0.45, spec_strength=0.5, roughness=0.2, rim_strength=0.0)
    mat_wall_up = get_cel_material("Mat_Wall_Brick", PALETTE_HEX["wall_brick"], shadow_factor=0.48, rim_strength=0.0)
    mat_wall_low = get_cel_material("Mat_Wall_Lower", PALETTE_HEX["wall_lower"], shadow_factor=0.46, rim_strength=0.0)
    mat_beam = get_cel_material("Mat_Steel_Beam", PALETTE_HEX["steel_beam"], shadow_factor=0.42, spec_strength=0.35, rim_strength=0.12)
    mat_wood = get_cel_material("Mat_Bench_Wood", PALETTE_HEX["bench_wood"], shadow_factor=0.48, rim_strength=0.10)
    mat_bench_leg = get_cel_material("Mat_Bench_Frame", PALETTE_HEX["bench_frame"], shadow_factor=0.42, rim_strength=0.12)
    mat_red = get_cel_material("Mat_Tool_Red", PALETTE_HEX["tool_red"], shadow_factor=0.45, spec_strength=0.4, rim_strength=0.18)
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.48, lit_factor=1.22, spec_strength=0.75, rim_strength=0.25)
    mat_can_y = get_cel_material("Mat_OilCan_Yellow", PALETTE_HEX["oil_can_yellow"], shadow_factor=0.46, spec_strength=0.4, rim_strength=0.15)
    mat_can_b = get_cel_material("Mat_OilCan_Blue", PALETTE_HEX["oil_can_blue"], shadow_factor=0.46, spec_strength=0.4, rim_strength=0.15)
    mat_tire = get_cel_material("Mat_Rubber_Tire", PALETTE_HEX["car_tire"], shadow_factor=0.38, rim_strength=0.10)
    mat_lamp = get_cel_material("Mat_Lamp_Shade", PALETTE_HEX["lamp_shade"], shadow_factor=0.40, spec_strength=0.35, rim_strength=0.16)
    mat_bulb = get_emission_material("Mat_Lamp_Bulb", "#FFE3B3", strength=5.5)
    mat_window = get_emission_material("Mat_Workshop_Window", "#4A6688", strength=1.25)

    # 1) Concrete Floor (with collision for bouncing sparks)
    floor = _make_beveled_box(
        "Env_Floor", (12.0, 10.5, 0.12), col, mat_floor,
        location=(0.0, -0.5, -0.06), bevel_width=0.0, outline_thickness=0.0
    )
    _add_collision_modifier(floor, damping=0.42, friction=0.30)
    objs["floor"] = floor

    # Stylized Garage Bay Yellow Safety Lines
    for name_s, sz, pos in [
        ("Env_BayLine_Front", (4.2, 0.09, 0.004), (0.45, -1.55, 0.002)),
        ("Env_BayLine_Left", (0.09, 3.3, 0.004), (-1.60, 0.05, 0.002)),
        ("Env_BayLine_Right", (0.09, 3.3, 0.004), (2.50, 0.05, 0.002)),
    ]:
        _make_beveled_box(name_s, sz, col, mat_line, location=pos, bevel_width=0.0, outline_thickness=0.0)

    # Stylized Concrete Expansion Grooves & Oil Puddles
    for idx, gx in enumerate((-2.4, 0.0, 2.4)):
        _make_beveled_box(
            f"Env_FloorGroove_{idx}", (0.018, 9.5, 0.003), col, mat_oil,
            location=(gx, -0.5, 0.0015), bevel_width=0.0, outline_thickness=0.0
        )
    for idx, (ox, oy, rx, ry) in enumerate([
        (-0.85, -0.85, 0.24, 0.16),
        (-0.55, -0.68, 0.11, 0.09),
        (1.15, -0.95, 0.19, 0.14),
    ]):
        puddle = _make_cylinder(
            f"Env_OilStain_{idx}", 1.0, 0.004, col, mat_oil,
            location=(ox, oy, 0.002), segments=20, outline_thickness=0.0
        )
        puddle.scale = (rx, ry, 1.0)

    # 2) Workshop Walls & Industrial Pillars
    _make_beveled_box("Env_BackWall_Upper", (12.0, 0.18, 2.8), col, mat_wall_up, location=(0.0, 2.75, 2.6), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_BackWall_Dado", (12.0, 0.22, 1.25), col, mat_wall_low, location=(0.0, 2.72, 0.625), bevel_width=0.01, outline_thickness=0.008)
    _make_beveled_box("Env_LeftWall_Upper", (0.18, 10.5, 2.8), col, mat_wall_up, location=(-4.35, -0.5, 2.6), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_LeftWall_Dado", (0.22, 10.5, 1.25), col, mat_wall_low, location=(-4.32, -0.5, 0.625), bevel_width=0.01, outline_thickness=0.008)
    _make_beveled_box("Env_RightWall_Upper", (0.18, 10.5, 2.8), col, mat_wall_up, location=(4.45, -0.5, 2.6), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Env_RightWall_Dado", (0.22, 10.5, 1.25), col, mat_wall_low, location=(4.42, -0.5, 0.625), bevel_width=0.01, outline_thickness=0.008)

    # Steel I-Beam Columns & Roof Trusses
    for i, px in enumerate((-3.8, -1.2, 1.4, 3.8)):
        _make_beveled_box(f"Env_Pillar_Back_{i}", (0.18, 0.18, 4.0), col, mat_beam, location=(px, 2.58, 2.0), bevel_width=0.01, outline_thickness=0.009)
    for i, py in enumerate((-3.2, -0.8, 1.6)):
        _make_beveled_box(f"Env_Pillar_Left_{i}", (0.18, 0.18, 4.0), col, mat_beam, location=(-4.18, py, 2.0), bevel_width=0.01, outline_thickness=0.009)
        _make_beveled_box(f"Env_RoofBeam_{i}", (8.8, 0.16, 0.22), col, mat_beam, location=(0.0, py, 3.82), bevel_width=0.01, outline_thickness=0.008)

    # Frosted Industrial Windows on Back Wall
    for i, wx in enumerate((-2.5, 0.1, 2.6)):
        _make_beveled_box(f"Env_WindowFrame_{i}", (1.65, 0.08, 0.88), col, mat_beam, location=(wx, 2.64, 2.45), bevel_width=0.01, outline_thickness=0.008)
        _make_beveled_box(f"Env_WindowGlass_{i}", (1.52, 0.04, 0.76), col, mat_window, location=(wx, 2.65, 2.45), bevel_width=0.0, outline_thickness=0.0)

    # 3) Left-Side Workbench, Pegboard Wrench Rack, Vise, Oil Cans & Tool Chest
    # Positioned at X = -3.45..-4.15 so camera travelling at X = -2.6..-0.8 gets rich parallax!
    bx, by = -3.55, -0.65
    _make_beveled_box("Prop_Workbench_Top", (0.78, 2.15, 0.07), col, mat_wood, location=(bx, by, 0.88), bevel_width=0.012, outline_thickness=0.009)
    _make_beveled_box("Prop_Workbench_Shelf", (0.68, 2.02, 0.04), col, mat_bench_leg, location=(bx, by, 0.26), bevel_width=0.008, outline_thickness=0.007)
    for lx_off in (-0.32, 0.32):
        for ly_off in (-0.96, 0.96):
            _make_beveled_box(
                f"Prop_Workbench_Leg_{lx_off}_{ly_off}", (0.065, 0.065, 0.86), col, mat_bench_leg,
                location=(bx + lx_off, by + ly_off, 0.43), bevel_width=0.006, outline_thickness=0.007
            )

    # Pegboard + Hanging Wrenches on Left Wall
    _make_beveled_box("Prop_Pegboard", (0.04, 1.85, 0.95), col, mat_bench_leg, location=(-4.18, by, 1.58), bevel_width=0.008, outline_thickness=0.008)
    for w_i in range(6):
        wy = by - 0.68 + w_i * 0.27
        w_len = 0.34 - w_i * 0.032
        _make_beveled_box(
            f"Prop_RackWrench_Shaft_{w_i}", (0.016, 0.036, w_len), col, mat_chrome,
            location=(-4.13, wy, 1.66 - w_len * 0.5 + 0.12), bevel_width=0.004, outline_thickness=0.005
        )
        _make_cylinder(
            f"Prop_RackWrench_Head_{w_i}", 0.034 - w_i * 0.002, 0.018, col, mat_chrome,
            location=(-4.13, wy, 1.79), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.005
        )

    # Oil Cans & Toolbox on Workbench
    _make_cylinder("Prop_OilCan_Yellow", 0.065, 0.19, col, mat_can_y, location=(bx + 0.12, by - 0.55, 1.01), outline_thickness=0.006)
    _make_cylinder("Prop_OilCan_Spout1", 0.010, 0.13, col, mat_chrome, location=(bx + 0.14, by - 0.52, 1.15), rotation=(0.25, 0.2, 0.0), outline_thickness=0.004)
    _make_beveled_box("Prop_OilCan_Blue", (0.12, 0.16, 0.22), col, mat_can_b, location=(bx - 0.08, by - 0.32, 1.02), bevel_width=0.015, outline_thickness=0.006)
    _make_beveled_box("Prop_BenchToolbox", (0.26, 0.48, 0.22), col, mat_red, location=(bx + 0.04, by + 0.45, 1.02), bevel_width=0.015, outline_thickness=0.007)

    # Rolling Red Tool Chest Cabinet (Foreground Left Beat 1 Parallax Element!)
    tc_x, tc_y = -3.48, -2.35
    _make_beveled_box("Prop_ToolChest_Body", (0.68, 0.92, 1.08), col, mat_red, location=(tc_x, tc_y, 0.60), bevel_width=0.02, outline_thickness=0.009)
    for d_i in range(4):
        _make_beveled_box(
            f"Prop_ToolChest_Drawer_{d_i}", (0.03, 0.78, 0.16), col, mat_chrome,
            location=(tc_x + 0.345, tc_y, 0.28 + d_i * 0.22), bevel_width=0.005, outline_thickness=0.005
        )

    # Back-Wall Spare Tire Stack & Industrial Drums
    for t_i in range(3):
        tire = _make_cylinder(
            f"Prop_SpareTire_{t_i}", 0.34, 0.22, col, mat_tire,
            location=(-2.35 + (t_i % 2) * 0.03, 2.05, 0.11 + t_i * 0.225), outline_thickness=0.008
        )
    _make_cylinder("Prop_OilDrum_1", 0.29, 0.88, col, mat_can_b, location=(2.65, 2.02, 0.44), outline_thickness=0.009)
    _make_cylinder("Prop_OilDrum_2", 0.29, 0.88, col, mat_red, location=(3.28, 1.88, 0.44), outline_thickness=0.009)

    # 4) Industrial Hanging Pendant Lamps
    pendant_coords = [
        (-0.15, -0.55, 3.05),
        (-2.35, -0.95, 3.12),
        (1.85, 0.55, 3.10),
    ]
    for p_i, (lx, ly, lz) in enumerate(pendant_coords):
        _make_cylinder(f"Env_LampRod_{p_i}", 0.016, 0.85, col, mat_beam, location=(lx, ly, lz + 0.45), outline_thickness=0.004)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.30, radius2=0.08, depth=0.22)
        _new_mesh_obj(f"Env_LampShade_{p_i}", bm, col, mat_lamp, location=(lx, ly, lz), outline_thickness=0.008)
        _make_cylinder(f"Env_LampBulb_{p_i}", 0.075, 0.09, col, mat_bulb, location=(lx, ly, lz - 0.08), outline_thickness=0.0)

    return objs


def _build_wheel_assembly(
    prefix: str,
    col: bpy.types.Collection,
    location: Tuple[float, float, float],
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    mat_tire = get_cel_material("Mat_Rubber_Tire", PALETTE_HEX["car_tire"], shadow_factor=0.36, rim_strength=0.12)
    mat_rim = get_cel_material("Mat_Car_RimAlloy", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.50, lit_factor=1.24, spec_strength=0.8, rim_strength=0.25)

    root = bpy.data.objects.new(prefix + "_Grp", None)
    root.location = location
    root.rotation_euler = rotation
    link_exclusively(root, col)

    tire = _make_cylinder(prefix + "_Tire", 0.33, 0.23, col, mat_tire, rotation=(math.pi * 0.5, 0.0, 0.0), segments=28, outline_thickness=0.008)
    tire.parent = root

    rim = _make_cylinder(prefix + "_Rim", 0.20, 0.242, col, mat_rim, rotation=(math.pi * 0.5, 0.0, 0.0), segments=24, outline_thickness=0.006)
    rim.parent = root

    # 5 Stylized Alloy Spokes
    for s_i in range(5):
        ang = (s_i * 2.0 * math.pi) / 5.0
        sp = _make_beveled_box(
            f"{prefix}_Spoke_{s_i}", (0.042, 0.25, 0.18), col, mat_rim,
            location=(math.cos(ang) * 0.09, 0.0, math.sin(ang) * 0.09),
            rotation=(0.0, -ang, 0.0),
            bevel_width=0.006, outline_thickness=0.004
        )
        sp.parent = root

    return root


def _build_stylized_car_and_jacks(col: bpy.types.Collection) -> Dict[str, Any]:
    """
    Build the Stylized 3D Coupe Car raised on front jack stands with:
      - Open propped front hood + stylized 3D engine bay
      - Front-left wheel removed (exposing brake rotor + orange jack stand)
      - Front-left fender repair panel + glowing/cooling weld seam along
        WELD_SEAM_START -> WELD_SEAM_MID -> WELD_SEAM_END (Y = -0.445, Z ~ 0.96m)
    """
    result: Dict[str, Any] = {}

    mat_car = get_cel_material("Mat_Car_BodyTeal", PALETTE_HEX["car_body_teal"], shadow_factor=0.44, mid_factor=0.88, lit_factor=1.16, spec_strength=0.65, roughness=0.28, rim_strength=0.28)
    mat_stripe = get_cel_material("Mat_Car_Accent", PALETTE_HEX["car_body_accent"], shadow_factor=0.52, spec_strength=0.45, rim_strength=0.18)
    mat_primer = get_cel_material("Mat_Car_PrimerPatch", PALETTE_HEX["car_primer_grey"], shadow_factor=0.46, mid_factor=0.86, lit_factor=1.08, roughness=0.65, rim_strength=0.16)
    mat_dark = get_cel_material("Mat_Car_Chassis", PALETTE_HEX["car_interior"], shadow_factor=0.38, rim_strength=0.10)
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.50, lit_factor=1.25, spec_strength=0.85, rim_strength=0.25)
    mat_glass = get_cel_material("Mat_Car_Windshield", "#5D8AA8", shadow_factor=0.45, lit_factor=1.28, spec_strength=0.90, roughness=0.12, rim_strength=0.35)
    mat_jack = get_cel_material("Mat_Jack_Orange", PALETTE_HEX["jack_orange"], shadow_factor=0.44, spec_strength=0.45, rim_strength=0.20)
    mat_headlight = get_emission_material("Mat_Car_HeadlightGlass", "#DCEEFF", strength=1.4)
    mat_seam_groove = get_cel_material("Mat_Seam_DarkGroove", "#181A22", shadow_factor=0.3, rim_strength=0.0)

    car_y = 0.38  # Car centerline -> left flank sits right at Y = 0.38 - 0.825 = -0.445!

    # 1) Main Lower Chassis & Stylized Body Shell (extruded side profile along Y, sculpted cleanly)
    # Profile in (X, Z) from front bumper X=-1.04 to rear bumper X=+2.08
    profile_xz = [
        (-1.04, 0.44),  # Front lower valence (raised slightly on front jacks!)
        (-1.06, 0.84),  # Front grille top
        (-0.55, 0.99),  # Front fender forward slope
        (-0.18, 1.04),  # Front fender crest (matches FENDER_LEFT_HAND_REST Z=1.035!)
        (0.14, 1.04),   # Cowl / windshield base
        (0.56, 1.52),   # Roof front header
        (1.26, 1.50),   # Roof rear
        (1.68, 1.06),   # Fastback rear deck
        (2.08, 0.96),   # Rear tail top
        (2.06, 0.42),   # Rear lower bumper
        (1.78, 0.40),   # Rear wheel arch aft
        (1.68, 0.68),   # Rear arch top-aft
        (1.42, 0.68),   # Rear arch top-fwd
        (1.30, 0.39),   # Rocker panel rear
        (-0.04, 0.42),  # Front wheel arch aft
        (-0.16, 0.76),  # Front wheel arch top-aft
        (-0.48, 0.77),  # Front wheel arch top-fwd
        (-0.62, 0.43),  # Front wheel arch fwd
    ]

    bm = bmesh.new()
    half_w = 0.825
    front_verts = [bm.verts.new((x, car_y - half_w, z)) for (x, z) in profile_xz]
    back_verts = [bm.verts.new((x, car_y + half_w, z)) for (x, z) in profile_xz]
    n_p = len(profile_xz)
    # Left & Right faces + perimeter quads
    bm.faces.new(front_verts)
    bm.faces.new(list(reversed(back_verts)))
    for i in range(n_p):
        j = (i + 1) % n_p
        bm.faces.new([front_verts[i], back_verts[i], back_verts[j], front_verts[j]])

    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.032, segments=2, profile=0.55, affect="EDGES")
    car_body = _new_mesh_obj("Car_BodyShell", bm, col, mat_car, outline_thickness=0.010, smooth=True)
    _add_collision_modifier(car_body, damping=0.35, friction=0.22)
    result["car_body"] = car_body

    # 2) Windshield & Side Windows Visual Inset Panels
    _make_beveled_box(
        "Car_Windshield", (0.04, 1.44, 0.56), col, mat_glass,
        location=(0.35, car_y, 1.28), rotation=(0.0, -0.68, 0.0),
        bevel_width=0.012, outline_thickness=0.006
    )
    _make_beveled_box(
        "Car_SideWindow_Left", (0.76, 0.025, 0.34), col, mat_glass,
        location=(0.88, car_y - half_w - 0.004, 1.25), rotation=(0.0, 0.02, 0.0),
        bevel_width=0.01, outline_thickness=0.005
    )

    # Side Racing Stripe on Door
    _make_beveled_box(
        "Car_RacingStripe_Left", (1.26, 0.014, 0.085), col, mat_stripe,
        location=(0.68, car_y - half_w - 0.005, 0.82),
        bevel_width=0.004, outline_thickness=0.0
    )

    # Front & Rear Chrome Bumpers, Grille, and Round Stylized Headlights
    _make_beveled_box("Car_FrontBumper", (0.12, 1.72, 0.14), col, mat_chrome, location=(-1.07, car_y, 0.47), bevel_width=0.025, outline_thickness=0.008)
    _make_beveled_box("Car_RearBumper", (0.12, 1.70, 0.14), col, mat_chrome, location=(2.09, car_y, 0.45), bevel_width=0.025, outline_thickness=0.008)
    _make_beveled_box("Car_FrontGrille", (0.05, 1.06, 0.22), col, mat_dark, location=(-1.06, car_y, 0.68), bevel_width=0.01, outline_thickness=0.006)
    for hy in (car_y - 0.62, car_y + 0.62):
        _make_cylinder("Car_HeadlightBezel", 0.115, 0.06, col, mat_chrome, location=(-1.06, hy, 0.72), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.006)
        _make_cylinder("Car_HeadlightLens", 0.092, 0.065, col, mat_headlight, location=(-1.065, hy, 0.72), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.0)

    # 3) Propped Open Hood + Stylized 3D Engine Bay
    _make_beveled_box("Car_EngineBayRecess", (0.95, 1.32, 0.16), col, mat_dark, location=(-0.46, car_y, 0.96), bevel_width=0.01, outline_thickness=0.006)
    _make_beveled_box("Car_EngineBlock", (0.48, 0.44, 0.26), col, mat_primer, location=(-0.44, car_y, 1.06), bevel_width=0.02, outline_thickness=0.007)
    _make_beveled_box("Car_ValveCover_L", (0.44, 0.14, 0.09), col, mat_jack, location=(-0.44, car_y - 0.16, 1.18), bevel_width=0.015, outline_thickness=0.006)
    _make_beveled_box("Car_ValveCover_R", (0.44, 0.14, 0.09), col, mat_jack, location=(-0.44, car_y + 0.16, 1.18), bevel_width=0.015, outline_thickness=0.006)
    _make_cylinder("Car_AirFilter", 0.16, 0.08, col, mat_chrome, location=(-0.44, car_y, 1.25), outline_thickness=0.006)

    # Open Hood hinged at (X=+0.10, Z=1.05), tilted up 36 degrees
    hood = _make_beveled_box(
        "Car_OpenHood", (1.10, 1.46, 0.045), col, mat_car,
        location=(-0.36, car_y, 1.37),
        rotation=(0.0, 0.62, 0.0),
        bevel_width=0.015, outline_thickness=0.009
    )
    # Hood Prop Rod
    _make_cylinder(
        "Car_HoodPropRod", 0.011, 0.68, col, mat_chrome,
        location=(-0.78, car_y + 0.48, 1.32),
        rotation=(0.08, -0.22, 0.0),
        outline_thickness=0.004
    )

    # 4) Front-Left Fender Repair Patch & Beveled Weld Groove + Animated Molten Weld Seam!
    # Primer metal patch flush on the outer front-left fender (-Y = -0.445)
    patch = _make_beveled_box(
        "Car_FenderRepairPatch", (0.44, 0.018, 0.15), col, mat_primer,
        location=(-0.17, -0.442, 0.945),
        rotation=(0.10, 0.0, 0.0),
        bevel_width=0.006, outline_thickness=0.006
    )
    _add_collision_modifier(patch, damping=0.32, friction=0.20)
    result["fender_patch"] = patch

    # Dark pre-weld seam crack line so the repair joint is readable even before welding starts
    seam_bg_curve = bpy.data.curves.new("Car_WeldGroove_Curve", type="CURVE")
    seam_bg_curve.dimensions = "3D"
    seam_bg_curve.bevel_depth = 0.0045
    seam_bg_curve.bevel_resolution = 3
    sp_bg = seam_bg_curve.splines.new("BEZIER")
    sp_bg.bezier_points.add(2)
    for idx, pt in enumerate((WELD_SEAM_START, WELD_SEAM_MID, WELD_SEAM_END)):
        bp = sp_bg.bezier_points[idx]
        bp.co = (pt[0], pt[1] + 0.002, pt[2])
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    seam_groove_obj = bpy.data.objects.new("Car_WeldGroove", seam_bg_curve)
    seam_groove_obj.data.materials.append(mat_seam_groove)
    link_exclusively(seam_groove_obj, col)

    # Glowing Animated Weld Bead Curve right along WELD_SEAM_START -> MID -> END
    seam_curve = bpy.data.curves.new("VFX_WeldSeam_Curve", type="CURVE")
    seam_curve.dimensions = "3D"
    seam_curve.bevel_depth = 0.0085
    seam_curve.bevel_resolution = 4
    seam_curve.use_map_taper = False
    if hasattr(seam_curve, "use_uv_as_generated"):
        seam_curve.use_uv_as_generated = True
    sp = seam_curve.splines.new("BEZIER")
    sp.bezier_points.add(2)
    for idx, pt in enumerate((WELD_SEAM_START, WELD_SEAM_MID, WELD_SEAM_END)):
        bp = sp.bezier_points[idx]
        bp.co = (pt[0], pt[1] - 0.003, pt[2])
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    seam_mat, seam_prog_node, seam_heat_node = create_weld_seam_material()
    seam_obj = bpy.data.objects.new("VFX_WeldSeam", seam_curve)
    seam_obj.data.materials.append(seam_mat)
    link_exclusively(seam_obj, col)
    result["weld_seam_obj"] = seam_obj
    result["seam_prog_node"] = seam_prog_node
    result["seam_heat_node"] = seam_heat_node

    # 5) Wheels, Exposed Front-Left Brake Hub & Heavy-Duty Orange Jack Stands
    # Front-Left Hub (wheel removed for repair! Brake rotor + red caliper visible!)
    _make_cylinder("Car_BrakeDisc_FL", 0.17, 0.035, col, mat_chrome, location=(-0.32, -0.34, 0.44), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.006)
    _make_beveled_box("Car_BrakeCaliper_FL", (0.09, 0.06, 0.13), col, mat_jack, location=(-0.20, -0.34, 0.47), bevel_width=0.01, outline_thickness=0.005)

    # Removed Front-Left Wheel resting flat/angled near the front bumper
    _build_wheel_assembly("Car_Wheel_Removed", col, location=(-1.42, -0.82, 0.12), rotation=(-1.42, 0.0, 0.35))

    # Other 3 Mounted Wheels
    _build_wheel_assembly("Car_Wheel_FR", col, location=(-0.32, car_y + 0.78, 0.44))
    _build_wheel_assembly("Car_Wheel_RL", col, location=(1.55, car_y - 0.78, 0.33))
    _build_wheel_assembly("Car_Wheel_RR", col, location=(1.55, car_y + 0.78, 0.33))

    # Two Orange Jack Stands under the Front Frame Rails
    for j_tag, jy in (("FL", -0.22), ("FR", car_y + 0.56)):
        bm_j = bmesh.new()
        bmesh.ops.create_cone(bm_j, cap_ends=True, cap_tris=False, segments=4, radius1=0.17, radius2=0.07, depth=0.30)
        _new_mesh_obj(f"Prop_JackStand_Base_{j_tag}", bm_j, col, mat_jack, location=(-0.58, jy, 0.15), rotation=(0.0, 0.0, math.pi * 0.25), outline_thickness=0.007)
        _make_beveled_box(f"Prop_JackStand_Post_{j_tag}", (0.055, 0.055, 0.18), col, mat_chrome, location=(-0.58, jy, 0.34), bevel_width=0.006, outline_thickness=0.005)
        _make_beveled_box(f"Prop_JackStand_Saddle_{j_tag}", (0.09, 0.12, 0.03), col, mat_dark, location=(-0.58, jy, 0.42), bevel_width=0.004, outline_thickness=0.005)

    # Hydraulic Floor Jack parked slightly forward-left of the car
    _make_beveled_box("Prop_FloorJack_Body", (0.52, 0.22, 0.11), col, mat_jack, location=(-1.28, -0.25, 0.07), rotation=(0.0, 0.0, 0.35), bevel_width=0.015, outline_thickness=0.007)
    _make_cylinder("Prop_FloorJack_Handle", 0.015, 0.88, col, mat_chrome, location=(-1.56, -0.35, 0.42), rotation=(0.32, -0.65, 0.35), outline_thickness=0.005)

    return result


def _build_welder_torch_and_cable(col: bpy.types.Collection) -> Dict[str, bpy.types.Object]:
    """
    Build:
      1) MIG Welding Machine Cart + Tall Shielding Gas Cylinder + Gauges
      2) Articulated Welding Torch (`Prop_WeldingTorch`) with `Empty_TorchTip` & `Empty_TorchCableBase`
      3) Flexible 3D Bezier Welding Cable (`Prop_WeldingCable`) bound via Hook modifiers
         between the MIG Welder socket and the Torch handle base!
    """
    mat_welder = get_cel_material("Mat_Welder_Red", PALETTE_HEX["welder_red"], shadow_factor=0.44, spec_strength=0.4, rim_strength=0.20)
    mat_panel = get_cel_material("Mat_Welder_Dark", "#252832", shadow_factor=0.38, rim_strength=0.12)
    mat_tank = get_cel_material("Mat_GasTank_Green", PALETTE_HEX["gas_tank_green"], shadow_factor=0.42, spec_strength=0.55, rim_strength=0.22)
    mat_brass = get_cel_material("Mat_Brass", PALETTE_HEX["brass_goggles"], shadow_factor=0.46, lit_factor=1.20, spec_strength=0.75, rim_strength=0.25)
    mat_torch_y = get_cel_material("Mat_Torch_Yellow", PALETTE_HEX["torch_yellow"], shadow_factor=0.46, spec_strength=0.4, rim_strength=0.20)
    mat_copper = get_cel_material("Mat_Torch_Copper", PALETTE_HEX["torch_copper"], shadow_factor=0.48, lit_factor=1.22, spec_strength=0.80, rim_strength=0.25)
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.50, lit_factor=1.25, spec_strength=0.85, rim_strength=0.25)
    mat_cable = get_cel_material("Mat_Welding_Cable", "#1A1B22", shadow_factor=0.38, spec_strength=0.35, roughness=0.55, rim_strength=0.14)
    mat_led = get_emission_material("Mat_Welder_PowerLED", "#52FF7E", strength=4.0)

    wx, wy, wz = WELDER_UNIT_POS
    welder_yaw = 2.45  # Angled toward mechanic (-X, +Y)

    welder_grp = bpy.data.objects.new("Prop_WelderCart_Grp", None)
    welder_grp.location = (wx, wy, wz)
    welder_grp.rotation_euler = (0.0, 0.0, welder_yaw)
    link_exclusively(welder_grp, col)

    # Cart Base & Wheels
    cart_base = _make_beveled_box("Prop_Welder_CartTray", (0.72, 0.42, 0.05), col, mat_panel, location=(0.0, 0.0, 0.11), bevel_width=0.008, outline_thickness=0.007)
    cart_base.parent = welder_grp
    for cx_o in (-0.28, 0.28):
        for cy_o in (-0.17, 0.17):
            wh = _make_cylinder(f"Prop_Welder_Wheel_{cx_o}_{cy_o}", 0.055, 0.035, col, mat_cable, location=(cx_o, cy_o, 0.055), rotation=(math.pi * 0.5, 0.0, 0.0), outline_thickness=0.005)
            wh.parent = welder_grp

    # Red MIG Welder Box + Front Control Dials
    w_box = _make_beveled_box("Prop_Welder_Box", (0.46, 0.34, 0.48), col, mat_welder, location=(0.08, 0.0, 0.37), bevel_width=0.02, outline_thickness=0.008)
    w_box.parent = welder_grp
    w_face = _make_beveled_box("Prop_Welder_Panel", (0.03, 0.28, 0.22), col, mat_panel, location=(0.31, 0.0, 0.45), bevel_width=0.005, outline_thickness=0.005)
    w_face.parent = welder_grp
    for d_y in (-0.07, 0.03):
        dial = _make_cylinder(f"Prop_Welder_Dial_{d_y}", 0.028, 0.03, col, mat_torch_y, location=(0.33, d_y, 0.46), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.004)
        dial.parent = welder_grp
    led = _make_cylinder("Prop_Welder_LED", 0.012, 0.02, col, mat_led, location=(0.33, 0.10, 0.51), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.0)
    led.parent = welder_grp

    # Tall Argon/CO2 Shielding Gas Tank + Brass Regulator Gauges
    tank = _make_cylinder("Prop_GasCylinder_Body", 0.115, 0.96, col, mat_tank, location=(-0.22, 0.0, 0.61), outline_thickness=0.008)
    tank.parent = welder_grp
    bm_dome = bmesh.new()
    bmesh.ops.create_uvsphere(bm_dome, u_segments=20, v_segments=12, radius=0.115)
    tank_dome = _new_mesh_obj("Prop_GasCylinder_Dome", bm_dome, col, mat_tank, location=(-0.22, 0.0, 1.09), outline_thickness=0.008)
    tank_dome.parent = welder_grp
    valve = _make_cylinder("Prop_GasCylinder_Valve", 0.026, 0.11, col, mat_brass, location=(-0.22, 0.0, 1.23), outline_thickness=0.005)
    valve.parent = welder_grp
    for g_off in (-0.055, 0.055):
        gauge = _make_cylinder(f"Prop_GasGauge_{g_off}", 0.036, 0.026, col, mat_brass, location=(-0.18, g_off, 1.27), rotation=(0.0, math.pi * 0.5, 0.0), outline_thickness=0.004)
        gauge.parent = welder_grp

    # Welder Cable Socket Empty (World Anchor)
    socket_empty = bpy.data.objects.new("Empty_WelderSocket", None)
    socket_empty.empty_display_size = 0.06
    socket_empty.location = WELDER_CABLE_SOCKET
    link_exclusively(socket_empty, col)

    # 2) Welding Torch (`Prop_WeldingTorch`)
    # Origin (0,0,0) = Right Hand Palm Grip Center!
    # Forward direction = +Y, Up = +Z
    torch_root = _make_cylinder(
        "Prop_WeldingTorch", 0.022, 0.165, col, mat_panel,
        location=(0.0, -0.005, 0.0),
        rotation=(math.pi * 0.5, 0.0, 0.0),
        segments=20, outline_thickness=0.006
    )
    # Yellow Ergonomic Grip Sleeve & Trigger
    grip_sleeve = _make_beveled_box(
        "Prop_Torch_YellowGrip", (0.046, 0.105, 0.052), col, mat_torch_y,
        location=(0.0, 0.005, 0.002), bevel_width=0.014, outline_thickness=0.005
    )
    grip_sleeve.parent = torch_root

    trigger = _make_beveled_box(
        "Prop_Torch_Trigger", (0.016, 0.042, 0.022), col, mat_welder,
        location=(0.0, 0.032, -0.028), rotation=(0.22, 0.0, 0.0),
        bevel_width=0.004, outline_thickness=0.004
    )
    trigger.parent = torch_root

    # Chrome Curved Swan-Neck Barrel (angled slightly downward for natural welding wrist!)
    neck1 = _make_cylinder(
        "Prop_Torch_SwanNeck1", 0.0095, 0.085, col, mat_chrome,
        location=(0.0, 0.112, -0.008),
        rotation=(math.pi * 0.5 + 0.24, 0.0, 0.0),
        segments=16, outline_thickness=0.004
    )
    neck1.parent = torch_root

    # Copper Conical Gas Nozzle + Contact Tip
    bm_noz = bmesh.new()
    bmesh.ops.create_cone(bm_noz, cap_ends=True, cap_tris=False, segments=18, radius1=0.016, radius2=0.0095, depth=0.056)
    nozzle = _new_mesh_obj(
        "Prop_Torch_CopperNozzle", bm_noz, col, mat_copper,
        location=(0.0, 0.172, -0.028),
        rotation=(math.pi * 0.5 + 0.42, 0.0, 0.0),
        outline_thickness=0.005
    )
    nozzle.parent = torch_root

    wire_tip = _make_cylinder(
        "Prop_Torch_ElectrodeTip", 0.0028, 0.022, col, mat_brass,
        location=(0.0, 0.200, -0.041),
        rotation=(math.pi * 0.5 + 0.42, 0.0, 0.0),
        segments=10, outline_thickness=0.002
    )
    wire_tip.parent = torch_root

    # Exact Torch Nozzle Tip Empty (VFX & Weld Arc anchor!)
    torch_tip = bpy.data.objects.new("Empty_TorchTip", None)
    torch_tip.empty_display_type = "SPHERE"
    torch_tip.empty_display_size = 0.025
    torch_tip.location = (0.0, 0.208, -0.045)
    torch_tip.parent = torch_root
    link_exclusively(torch_tip, col)

    # Torch Rear Strain-Relief Boot + Cable Hook Anchor
    boot = _make_cylinder(
        "Prop_Torch_RearBoot", 0.016, 0.05, col, mat_cable,
        location=(0.0, -0.095, -0.004),
        rotation=(math.pi * 0.5 - 0.18, 0.0, 0.0),
        segments=14, outline_thickness=0.004
    )
    boot.parent = torch_root

    cable_end_empty = bpy.data.objects.new("Empty_TorchCableBase", None)
    cable_end_empty.empty_display_size = 0.03
    cable_end_empty.location = (0.0, -0.115, -0.008)
    cable_end_empty.parent = torch_root
    link_exclusively(cable_end_empty, col)

    cable_mid_sag = bpy.data.objects.new("Empty_CableFloorLoop", None)
    cable_mid_sag.empty_display_size = 0.05
    cable_mid_sag.location = (0.36, -1.16, 0.18)
    link_exclusively(cable_mid_sag, col)

    # 3) Flexible Bezier Welding Cable with Hook Modifiers
    cable_curve = bpy.data.curves.new("Prop_WeldingCable_Curve", type="CURVE")
    cable_curve.dimensions = "3D"
    cable_curve.bevel_depth = 0.014
    cable_curve.bevel_resolution = 4
    cable_curve.resolution_u = 24

    spline = cable_curve.splines.new("BEZIER")
    spline.bezier_points.add(2)  # 3 control points: [0]=TorchBase, [1]=SagLoop, [2]=WelderSocket

    # Initial world coordinates before Hook binding; Hook modifiers bind at rest matrix!
    # Wait: let's place torch_root temporarily at a neutral hand position before binding hooks
    init_torch_pos = Vector((-0.02, -0.88, 0.78))
    torch_root.location = init_torch_pos
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
    apply_cel_outline(cable_obj, thickness=0.005) if cable_obj.type == "MESH" else None
    link_exclusively(cable_obj, col)

    bpy.context.view_layer.update()

    # Bind Bezier Control Point 0 (and its handles) to `Empty_TorchCableBase` via Hook Modifier!
    for idx, target_empty, h_name in [
        (0, cable_end_empty, "Hook_Cable_Torch"),
        (1, cable_mid_sag, "Hook_Cable_Sag"),
        (2, socket_empty, "Hook_Cable_Welder"),
    ]:
        hm = cable_obj.modifiers.new(name=h_name, type="HOOK")
        hm.object = target_empty
        # In Blender Curve Hooks, each Bezier point uses 3 vertex indices: [3*i (left), 3*i+1 (co), 3*i+2 (right)]
        # First switch handles to FREE so AUTO doesn't fight hook deformation
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
    """Build the entire 3D cel-shaded workshop environment, car, and welding equipment."""
    env_col = get_or_create_collection("Col_Workshop_Env")
    props_col = get_or_create_collection("Col_Props_Car_Welder")

    room_objs = _build_workshop_room_and_bg_props(env_col)
    car_data = _build_stylized_car_and_jacks(props_col)
    welder_data = _build_welder_torch_and_cable(props_col)

    return {
        "env_collection": env_col,
        "props_collection": props_col,
        **room_objs,
        **car_data,
        **welder_data,
    }
