"""
short_75s/env_world_6loc.py — Expanded 6-Location Seamless 3D Cel-Shaded Compound:
  - LOC 1: Sunlit Outdoor Courtyard & Open Roll-Up Garage Gate (`X = -9.5 .. -4.15`)
  - LOC 2: Main Service Bay & Cleaned Classic Red Sedan on 0-Gap Jack Stands
  - LOC 3: Master Workbench, Pegboard Wall & Rotated Red Rolling Tool Chest
  - LOC 4: MIG Welder & Argon Cylinder Station
  - LOC 5: Spare-Parts Storage Alcove (`Y = +2.4 .. +4.8`) with Steel Racks & Sheet Metal
  - LOC 6: Front-Left Fender / Rocker Macro Inspection & Welding Zone
Plus Volumetric God-Ray Light Shafts streaming through the open gate and windows!
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import bmesh
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import PALETTE_HEX, hex_to_rgba  # noqa: E402
from env_props import (  # noqa: E402
    _make_beveled_box,
    _make_cylinder,
    _make_ibeam_column,
    _make_torus,
    _make_uv_quad,
    _new_mesh_obj,
    build_environment_and_props,
    get_or_create_collection,
    link_exclusively,
)
from shaders import get_cel_material, get_emission_material, get_textured_cel_material  # noqa: E402


def _create_godray_material(name: str = "Mat_VFX_GodRayShaft") -> Tuple[bpy.types.Material, bpy.types.Node, bpy.types.Node]:
    """
    Create a clean, noise-free Volumetric God-Ray light-shaft shader using soft Fresnel/LayerWeight
    edge falloff + vertical gradient -> Mix(Transparent, Emission) so god rays look dramatic
    in EEVEE Next CPU renders AND animate color/opacity as the story turns!
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    if hasattr(mat, "shadow_method"):
        try:
            mat.shadow_method = "NONE"
        except Exception:
            pass

    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (820, 0)

    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (220, 260)

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.location = (-460, 140)
    lw.inputs["Blend"].default_value = 0.35

    inv_fres = nt.nodes.new("ShaderNodeMath")
    inv_fres.operation = "SUBTRACT"
    inv_fres.location = (-240, 140)
    inv_fres.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv_fres.inputs[1])

    pow_edge = nt.nodes.new("ShaderNodeMath")
    pow_edge.operation = "POWER"
    pow_edge.location = (-40, 140)
    pow_edge.inputs[1].default_value = 2.2
    nt.links.new(inv_fres.outputs["Value"], pow_edge.inputs[0])

    alpha_node = nt.nodes.new("ShaderNodeValue")
    alpha_node.name = "GodRayAlpha"
    alpha_node.label = "GodRayAlpha"
    alpha_node.outputs[0].default_value = 0.32
    alpha_node.location = (-240, -60)

    mul_a = nt.nodes.new("ShaderNodeMath")
    mul_a.operation = "MULTIPLY"
    mul_a.location = (180, 60)
    nt.links.new(pow_edge.outputs["Value"], mul_a.inputs[0])
    nt.links.new(alpha_node.outputs["Value"], mul_a.inputs[1])

    # Only visible to camera rays (never casts shadows or corrupts reflections)
    cam_mask = nt.nodes.new("ShaderNodeMath")
    cam_mask.operation = "MULTIPLY"
    cam_mask.location = (380, 120)
    nt.links.new(mul_a.outputs["Value"], cam_mask.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], cam_mask.inputs[1])

    color_node = nt.nodes.new("ShaderNodeRGB")
    color_node.name = "GodRayColor"
    color_node.label = "GodRayColor"
    color_node.outputs[0].default_value = hex_to_rgba("#FFD28E")
    color_node.location = (0, -240)

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (260, -200)
    emis.inputs["Strength"].default_value = 2.2
    nt.links.new(color_node.outputs["Color"], emis.inputs["Color"])

    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    transp.location = (260, -40)

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.location = (580, 0)
    nt.links.new(cam_mask.outputs["Value"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(emis.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

    return mat, color_node, alpha_node


def _remove_objects_by_prefix(prefixes: Tuple[str, ...]) -> None:
    for obj in list(bpy.data.objects):
        if any(obj.name.startswith(p) for p in prefixes):
            md = obj.data if obj.type == "MESH" else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if md is not None and md.users == 0:
                bpy.data.meshes.remove(md)


def build_6location_workshop_world() -> Dict[str, Any]:
    """
    Build the complete 6-location continuous 3D workshop compound:
      1. Base workshop, cleaned classic red car, 0-gap jack stands, conformal fender patch/seam,
         orange ground clamp, right workbench, pegboard, rotated red tool chest, MIG welder & gas tank.
      2. Open Left Roll-Up Gate leading out to LOC 1 (Sunlit Outdoor Courtyard).
      3. Open Back Wall Archway leading into LOC 5 (Spare-Parts Storage Alcove).
      4. Animated Volumetric God-Ray Light Shafts through the open gate & barred windows.
    """
    env_data = build_environment_and_props()
    env_col = env_data["env_collection"]
    vfx_col = get_or_create_collection("Col_VFX_Lighting")

    # Remove solid Left Wall & Left Bench so the Open Roll-Up Gate connects LOC 1 <-> LOC 2 seamlessly!
    # Also replace Back Wall with a split wall framing the wide archway into LOC 5!
    _remove_objects_by_prefix((
        "Env_LeftWall_",
        "Prop_LeftBench_",
        "Prop_LeftPegboard",
        "Prop_LeftWrench_",
        "Env_BackWall_",
        "Env_Win_BackL",
    ))

    mat_wall_up = get_cel_material("Mat_Wall_Brick", PALETTE_HEX["wall_brick"], shadow_factor=0.45, mid_factor=0.85, lit_factor=0.98, surface_type="brick", ao_strength=0.48)
    mat_wall_low = get_cel_material("Mat_Wall_Lower", PALETTE_HEX["wall_lower"], shadow_factor=0.44, mid_factor=0.84, surface_type="concrete", ao_strength=0.48)
    mat_beam = get_cel_material("Mat_Steel_Beam", PALETTE_HEX["steel_beam"], shadow_factor=0.40, spec_strength=0.45, surface_type="metal")
    mat_asphalt = get_cel_material("Mat_Courtyard_Asphalt", "#303540", shadow_factor=0.44, surface_type="concrete", ao_strength=0.45)
    mat_shutter = get_cel_material("Mat_RollUp_Shutter", "#4A586E", shadow_factor=0.42, spec_strength=0.55, surface_type="metal")
    mat_red = get_cel_material("Mat_Tool_Red", PALETTE_HEX["tool_red"], shadow_factor=0.44, spec_strength=0.45, surface_type="metal")
    mat_can_y = get_cel_material("Mat_OilCan_Yellow", PALETTE_HEX["oil_can_yellow"], shadow_factor=0.45, spec_strength=0.4, surface_type="painted")
    mat_can_b = get_cel_material("Mat_OilCan_Blue", PALETTE_HEX["oil_can_blue"], shadow_factor=0.45, spec_strength=0.4, surface_type="painted")
    mat_green = get_cel_material("Mat_Lamp_GreenEnamel", "#24543C", shadow_factor=0.42, spec_strength=0.55, surface_type="metal")
    mat_wood = get_cel_material("Mat_Bench_Wood", PALETTE_HEX["bench_wood"], shadow_factor=0.46, surface_type="wood")
    mat_chrome = get_cel_material("Mat_Tool_Chrome", PALETTE_HEX["car_rim_alloy"], shadow_factor=0.46, lit_factor=1.05, spec_strength=0.85, surface_type="chrome")
    mat_cardboard = get_cel_material("Mat_Cardboard_Box", "#A67C52", shadow_factor=0.48, surface_type="concrete")
    mat_tire = get_cel_material("Mat_Rubber_Tire", PALETTE_HEX["car_tire"], shadow_factor=0.36, surface_type="painted")
    mat_sign_glow = get_emission_material("Mat_Sign_Bengkel", "#FFB94D", strength=2.6)
    mat_hazard = get_textured_cel_material("Mat_Decal_HazardStripe", str(PROJECT_ROOT / "generated_textures" / "hazard_stripe.png"))
    mat_oil_lbl = get_textured_cel_material("Mat_Decal_OilLabel", str(PROJECT_ROOT / "generated_textures" / "oil_bottle_label.png"))

    # ==========================================================================
    # LOC 1: SUNLIT OUTDOOR COURTYARD & OPEN ROLL-UP GARAGE GATE (`X = -9.5..-4.15`)
    # ==========================================================================
    # Extended Courtyard Concrete/Asphalt Apron
    _make_beveled_box(
        "Loc1_Courtyard_Floor", (6.2, 10.5, 0.12), env_col, mat_asphalt,
        location=(-7.8, -0.5, -0.062), bevel_width=0.0, outline_thickness=0.0
    )
    # Yellow Courtyard Entrance Guide Lines
    _make_beveled_box("Loc1_GuideLine_L", (4.8, 0.09, 0.004), env_col, mat_can_y, location=(-6.6, -2.55, 0.002), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc1_GuideLine_R", (4.8, 0.09, 0.004), env_col, mat_can_y, location=(-6.6,  0.85, 0.002), bevel_width=0.0, outline_thickness=0.0)

    # Left Wall Framed Around Wide Open Roll-Up Gate (`Y = -2.8 .. +0.9` is OPEN!)
    left_x = -4.15
    _make_beveled_box("Loc1_GateWall_North", (0.24, 2.2, 3.85), env_col, mat_wall_up, location=(left_x, 2.05, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc1_GateWall_South", (0.24, 1.8, 3.85), env_col, mat_wall_up, location=(left_x, -3.75, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc1_GateHeader", (0.28, 4.0, 1.05), env_col, mat_wall_low, location=(left_x, -0.95, 3.35), bevel_width=0.010, outline_thickness=0.006)

    # Corrugated Half-Raised Roll-Up Shutter Slats at top of Gate
    for sl_i in range(6):
        _make_beveled_box(
            f"Loc1_RollShutter_Slat_{sl_i}", (0.06, 3.68, 0.085), env_col, mat_shutter,
            location=(left_x - 0.14, -0.95, 2.48 + sl_i * 0.092), bevel_width=0.004, outline_thickness=0.004
        )
    # Vintage Glowing Overhead Workshop Signboard above Gate
    _make_beveled_box("Loc1_SignBoard_Frame", (0.14, 2.85, 0.56), env_col, mat_red, location=(left_x - 0.22, -0.95, 3.28), bevel_width=0.012, outline_thickness=0.006)
    _make_beveled_box("Loc1_SignBoard_GlowBar", (0.04, 2.55, 0.34), env_col, mat_sign_glow, location=(left_x - 0.30, -0.95, 3.28), bevel_width=0.006, outline_thickness=0.0)

    # Rich Courtyard Set Dressing (Oil Drums, Wooden Crates, Outdoor Tire Stack, Corrugated Fence)
    for d_i, (dx, dy, dmat) in enumerate([(-5.15, -2.95, mat_can_b), (-5.78, -2.75, mat_red), (-4.95, 1.35, mat_green)]):
        _make_cylinder(f"Loc1_Drum_{d_i}", 0.28, 0.88, env_col, dmat, location=(dx, dy, 0.44), outline_thickness=0.007)
        _make_torus(f"Loc1_DrumRib_{d_i}", 0.284, 0.012, env_col, mat_beam, location=(dx, dy, 0.87), outline_thickness=0.003)

    _make_beveled_box("Loc1_Crate_1", (0.72, 0.68, 0.62), env_col, mat_wood, location=(-6.55, 1.45, 0.31), rotation=(0.0, 0.0, 0.18), bevel_width=0.012, outline_thickness=0.006)
    _make_beveled_box("Loc1_Crate_2", (0.54, 0.52, 0.48), env_col, mat_wood, location=(-6.48, 1.42, 0.86), rotation=(0.0, 0.0, -0.22), bevel_width=0.010, outline_thickness=0.005)

    for ti in range(4):
        _make_cylinder(f"Loc1_TireStack_{ti}", 0.34, 0.21, env_col, mat_tire, location=(-5.65 + (ti % 2) * 0.03, 1.55, 0.105 + ti * 0.215), outline_thickness=0.006)

    # Corrugated Industrial Courtyard Fence along North Courtyard (`Y = +2.65`)
    _make_beveled_box("Loc1_Fence_North", (5.4, 0.14, 2.25), env_col, mat_shutter, location=(-7.0, 2.65, 1.12), bevel_width=0.008, outline_thickness=0.006)
    for fp_x in (-9.2, -7.0, -4.8):
        _make_ibeam_column(f"Loc1_FencePost_{fp_x}", 2.45, env_col, mat_beam, location=(fp_x, 2.55, 0.0))

    # ==========================================================================
    # LOC 5: SPARE-PARTS STORAGE ALCOVE (`Y = +2.38 .. +4.85`, behind Archway!)
    # ==========================================================================
    back_y = 2.38
    # Split Back Wall leaving wide archway `X in [-2.45 .. +0.35]` open into LOC 5!
    _make_beveled_box("Loc5_BackWall_Left", (1.85, 0.22, 3.85), env_col, mat_wall_up, location=(-3.32, back_y, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc5_BackWall_Right", (3.10, 0.22, 3.85), env_col, mat_wall_up, location=(1.90, back_y, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc5_ArchHeader", (2.95, 0.24, 1.15), env_col, mat_wall_low, location=(-1.05, back_y, 3.28), bevel_width=0.008, outline_thickness=0.006)
    _make_uv_quad("Loc5_BackWall_HazardR", 2.9, 0.11, env_col, mat_hazard, location=(1.88, back_y - 0.12, 1.19), rotation=(math.pi * 0.5, 0.0, 0.0), u_repeat=4.5)

    # Alcove Floor, Rear Wall & Side Walls
    _make_beveled_box("Loc5_Alcove_Floor", (4.8, 2.8, 0.12), env_col, mat_asphalt, location=(-1.05, 3.65, -0.06), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_RearWall", (5.0, 0.20, 3.85), env_col, mat_wall_up, location=(-1.05, 4.95, 1.92), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_WallL", (0.20, 2.8, 3.85), env_col, mat_wall_low, location=(-3.45, 3.65, 1.92), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_WallR", (0.20, 2.8, 3.85), env_col, mat_wall_low, location=(1.35, 3.65, 1.92), bevel_width=0.0, outline_thickness=0.0)

    # Heavy Multi-Tier Spare-Parts Racks in LOC 5 (`X = -1.05, Y = +3.95`)
    ax, ay = -1.05, 3.95
    for rx_o in (-1.35, 0.0, 1.35):
        for ry_o in (-0.36, 0.36):
            _make_beveled_box(f"Loc5_RackPost_{rx_o}_{ry_o}", (0.05, 0.05, 2.25), env_col, mat_beam, location=(ax + rx_o, ay + ry_o, 1.12), bevel_width=0.004, outline_thickness=0.005)
    for sh_z in (0.22, 0.84, 1.46, 2.08):
        _make_beveled_box(f"Loc5_RackShelf_{sh_z}", (2.78, 0.78, 0.04), env_col, mat_shutter, location=(ax, ay, sh_z), bevel_width=0.005, outline_thickness=0.005)

    # Colorful Oil Jugs, Fresh Steel Repair Sheets, Spare Pistons & Cardboard Parts Boxes in LOC 5!
    for oi, (ox_off, omat) in enumerate([(-1.05, mat_red), (-0.75, mat_can_y), (-0.45, mat_can_b), (-0.15, mat_red), (0.15, mat_can_y)]):
        _make_beveled_box(f"Loc5_OilJug_{oi}", (0.18, 0.14, 0.28), env_col, omat, location=(ax + ox_off, ay - 0.12, 1.62), bevel_width=0.020, outline_thickness=0.005)
        _make_uv_quad(f"Loc5_OilLbl_{oi}", 0.13, 0.14, env_col, mat_oil_lbl, location=(ax + ox_off, ay - 0.195, 1.61), rotation=(math.pi * 0.5, 0.0, 0.0))

    # Stack of Fresh Brushed Steel Repair Plates (Hero Prop grabbed in Act 2A!)
    for pl_i in range(4):
        _make_beveled_box(
            f"Loc5_SteelPlate_{pl_i}", (0.48, 0.34, 0.012), env_col, mat_chrome,
            location=(ax + 0.10, ay - 0.10, 0.89 + pl_i * 0.018),
            rotation=(0.0, 0.0, 0.06 * pl_i), bevel_width=0.002, outline_thickness=0.003
        )
    # Spare Parts Boxes & Chrome Cylinders on Lower/Upper Shelves
    _make_beveled_box("Loc5_PartsBox_1", (0.58, 0.46, 0.38), env_col, mat_cardboard, location=(ax - 0.72, ay, 0.43), rotation=(0.0, 0.0, 0.05), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Loc5_PartsBox_2", (0.52, 0.42, 0.34), env_col, mat_cardboard, location=(ax + 0.72, ay, 0.41), rotation=(0.0, 0.0, -0.07), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Loc5_PartsBox_3", (0.48, 0.40, 0.32), env_col, mat_red, location=(ax + 0.78, ay - 0.06, 1.02), bevel_width=0.010, outline_thickness=0.005)

    # ==========================================================================
    # VOLUMETRIC GOD-RAY LIGHT SHAFTS (Open Gate & Barred Windows!)
    # ==========================================================================
    godray_mat, godray_col_node, godray_alpha_node = _create_godray_material()
    godray_objs: List[bpy.types.Object] = []

    ray_specs = [
        # Wide low-sun shafts pouring through the Open Roll-Up Gate into the Service Bay!
        ("VFX_GodRay_GateMain", (-2.65, -0.95, 1.55), (0.0, math.radians(74.0), math.radians(-14.0)), 1.05, 0.42, 5.2),
        ("VFX_GodRay_GateLow",  (-2.20, -1.65, 1.25), (0.0, math.radians(76.0), math.radians(-10.0)), 0.85, 0.34, 4.8),
        # Shafts cutting down from Right & Back Barred Windows!
        ("VFX_GodRay_WinBack",  ( 0.45,  1.25, 1.72), (math.radians(-68.0), 0.0, math.radians(12.0)), 0.75, 0.28, 3.6),
        ("VFX_GodRay_WinRight", ( 1.85,  0.25, 1.68), (0.0, math.radians(-68.0), math.radians(10.0)), 0.72, 0.26, 3.8),
    ]
    for r_name, r_loc, r_rot, r_rad1, r_rad2, r_len in ray_specs:
        bm_r = bmesh.new()
        bmesh.ops.create_cone(bm_r, cap_ends=False, cap_tris=False, segments=20, radius1=r_rad1, radius2=r_rad2, depth=r_len)
        r_obj = _new_mesh_obj(r_name, bm_r, vfx_col, godray_mat, location=r_loc, rotation=r_rot, outline_thickness=0.0, smooth=True)
        godray_objs.append(r_obj)

    env_data["godray_objs"] = godray_objs
    env_data["godray_col_node"] = godray_col_node
    env_data["godray_alpha_node"] = godray_alpha_node
    return env_data
