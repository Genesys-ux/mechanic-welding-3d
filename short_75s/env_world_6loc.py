"""
short_75s/env_world_6loc.py — Expanded 6-Location Seamless 3D Cel-Shaded Compound:
  - Wide collision-free corridors around Front, Side, and Rear of the classic red car!
  - ONE realistic 3D Hero Window with open casement & steel mullions + localized Haze Domain
    so real shadowed Volumetric God Rays NEVER penetrate props or character!
  - THREE raycasted flush Weld Patches & Molten Weld Seams on the car:
      1) FRONT fender nose (`X = -0.92 .. -0.62`)
      2) SIDE door/panel   (`X = +0.20 .. +0.68`)
      3) REAR quarter      (`X = +1.85 .. +2.35`)
  - Natural held 3D props (`Prop_Held_SteelPlate`, `Prop_Held_Wrench`) for Act 2!
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
    _build_conformal_fender_patch,
    _build_world_car_surface_proxy,
    _make_beveled_box,
    _make_cylinder,
    _make_ibeam_column,
    _make_torus,
    _make_uv_quad,
    _new_mesh_obj,
    _project_onto_left_car_panel,
    build_environment_and_props,
    get_or_create_collection,
    link_exclusively,
)
from shaders import (  # noqa: E402
    create_weld_seam_material,
    get_cel_material,
    get_emission_material,
    get_textured_cel_material,
)


def _create_localized_haze_volume_material(name: str = "Mat_VFX_WorkshopHaze") -> Tuple[bpy.types.Material, bpy.types.NodeSocket, bpy.types.NodeSocket]:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (420, 0)

    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.location = (80, 0)
    vol.inputs["Color"].default_value = hex_to_rgba("#FFD699")
    vol.inputs["Density"].default_value = 0.014
    vol.inputs["Anisotropy"].default_value = 0.76
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    return mat, vol.inputs["Color"], vol.inputs["Density"]


def _build_realistic_hero_window(
    col: bpy.types.Collection,
    mat_frame: bpy.types.Material,
    mat_sill: bpy.types.Material,
    mat_glass_glow: bpy.types.Material,
    location: Tuple[float, float, float],
    rot_z: float,
) -> bpy.types.Object:
    wgrp = bpy.data.objects.new("Env_HeroGodRayWindow_Grp", None)
    wgrp.location = location
    wgrp.rotation_euler = (0.0, 0.0, rot_z)
    link_exclusively(wgrp, col)

    win_w, win_h, depth = 1.65, 1.15, 0.24
    top_f = _make_beveled_box("Env_HeroWin_Top", (win_w + 0.12, depth, 0.08), col, mat_frame, location=(0.0, 0.0, win_h * 0.5 + 0.04), bevel_width=0.006, outline_thickness=0.005)
    bot_f = _make_beveled_box("Env_HeroWin_Bot", (win_w + 0.16, depth + 0.08, 0.09), col, mat_sill, location=(0.0, 0.02, -win_h * 0.5 - 0.045), bevel_width=0.008, outline_thickness=0.005)
    lft_f = _make_beveled_box("Env_HeroWin_Lft", (0.08, depth, win_h), col, mat_frame, location=(-win_w * 0.5 - 0.04, 0.0, 0.0), bevel_width=0.006, outline_thickness=0.005)
    rgt_f = _make_beveled_box("Env_HeroWin_Rgt", (0.08, depth, win_h), col, mat_frame, location=(win_w * 0.5 + 0.04, 0.0, 0.0), bevel_width=0.006, outline_thickness=0.005)
    for p in (top_f, bot_f, lft_f, rgt_f):
        p.parent = wgrp

    for mx in (-0.28, 0.28):
        vm = _make_beveled_box(f"Env_HeroWin_VMullion_{mx}", (0.036, 0.06, win_h), col, mat_frame, location=(mx, 0.0, 0.0), bevel_width=0.003, outline_thickness=0.003)
        vm.parent = wgrp
    hm = _make_beveled_box("Env_HeroWin_HMullion", (win_w, 0.06, 0.036), col, mat_frame, location=(0.0, 0.0, 0.04), bevel_width=0.003, outline_thickness=0.003)
    hm.parent = wgrp

    sash_top = _make_beveled_box("Env_HeroWin_OpenSashFrame", (win_w - 0.08, 0.035, 0.04), col, mat_frame, location=(0.0, 0.24, 0.24), rotation=(0.45, 0.0, 0.0), bevel_width=0.003, outline_thickness=0.003)
    sash_top.parent = wgrp
    for sx in (-0.75, 0.75):
        stay = _make_cylinder(f"Env_HeroWin_StayBar_{sx}", 0.007, 0.34, col, mat_frame, location=(sx, 0.14, 0.36), rotation=(1.05, 0.0, 0.0), outline_thickness=0.002)
        stay.parent = wgrp

    sky_rim = _make_beveled_box("Env_HeroWin_ExteriorGlowTrim", (win_w, 0.015, 0.025), col, mat_glass_glow, location=(0.0, -depth * 0.5 - 0.02, win_h * 0.5 - 0.02), bevel_width=0.0, outline_thickness=0.0)
    sky_rim.parent = wgrp
    return wgrp


def _remove_objects_by_prefix(prefixes: Tuple[str, ...]) -> None:
    for obj in list(bpy.data.objects):
        if any(obj.name.startswith(p) for p in prefixes):
            md = obj.data if obj.type == "MESH" else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if md is not None and md.users == 0:
                bpy.data.meshes.remove(md)


def _shift_objects_by_prefix(prefixes: Tuple[str, ...], dx: float, dy: float, dz: float = 0.0) -> None:
    for obj in bpy.data.objects:
        if obj.parent is None and any(obj.name.startswith(p) for p in prefixes):
            obj.location = (obj.location.x + dx, obj.location.y + dy, obj.location.z + dz)


def _build_zone_weld_seam(
    zone_name: str,
    proxy_obj: bpy.types.Object,
    col: bpy.types.Collection,
    mat_primer: bpy.types.Material,
    mat_groove: bpy.types.Material,
    x_start: float,
    x_end: float,
    z_center: float,
) -> Dict[str, Any]:
    """Project a conformal steel repair plate + glowing weld seam onto the car's left flank."""
    patch = _build_conformal_fender_patch(
        proxy_obj, col, mat_primer,
        x_min=x_start - 0.03, x_max=x_end + 0.03,
        z_min=z_center - 0.038, z_max=z_center + 0.038,
        nx_steps=13, nz_steps=6, outer_offset=0.0030, inner_offset=0.0006,
    )
    patch.name = f"Car_Patch_{zone_name}"

    num_pts = 9
    pts: List[Vector] = []
    norms: List[Vector] = []
    groove_pts: List[Vector] = []
    for i in range(num_pts):
        u = i / float(num_pts - 1)
        sx = x_start + (x_end - x_start) * u
        sz = z_center + 0.006 * math.sin(math.pi * u)
        hit_pt, hit_n = _project_onto_left_car_panel(proxy_obj, sx, sz)
        pts.append(hit_pt + hit_n * 0.0036)
        groove_pts.append(hit_pt + hit_n * 0.0031)
        norms.append(hit_n)

    bg_c = bpy.data.curves.new(f"Car_Groove_{zone_name}_Curve", type="CURVE")
    bg_c.dimensions = "3D"
    bg_c.bevel_depth = 0.0030
    bg_c.bevel_resolution = 3
    sp_bg = bg_c.splines.new("BEZIER")
    sp_bg.bezier_points.add(len(groove_pts) - 1)
    for idx, gp in enumerate(groove_pts):
        bp = sp_bg.bezier_points[idx]
        bp.co = gp
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    bg_o = bpy.data.objects.new(f"Car_Groove_{zone_name}", bg_c)
    bg_o.data.materials.append(mat_groove)
    link_exclusively(bg_o, col)

    sc = bpy.data.curves.new(f"VFX_WeldSeam_{zone_name}_Curve", type="CURVE")
    sc.dimensions = "3D"
    sc.bevel_depth = 0.0045
    sc.bevel_resolution = 4
    if hasattr(sc, "use_uv_as_generated"):
        sc.use_uv_as_generated = True
    sp = sc.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for idx, spt in enumerate(pts):
        bp = sp.bezier_points[idx]
        bp.co = spt
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    seam_mat, prog_node, heat_node = create_weld_seam_material(name=f"Mat_WeldSeam_{zone_name}")
    seam_o = bpy.data.objects.new(f"VFX_WeldSeam_{zone_name}", sc)
    seam_o.data.materials.append(seam_mat)
    link_exclusively(seam_o, col)

    print(f"[WeldZone {zone_name}] Projected {len(pts)} pts: {tuple(round(v, 3) for v in pts[0])} -> {tuple(round(v, 3) for v in pts[-1])}")
    return {
        "points": pts,
        "normals": norms,
        "prog_node": prog_node,
        "heat_node": heat_node,
        "seam_obj": seam_o,
        "patch_obj": patch,
    }


def build_6location_workshop_world() -> Dict[str, Any]:
    env_data = build_environment_and_props()
    env_col = env_data["env_collection"]
    props_col = env_data["props_collection"]
    vfx_col = get_or_create_collection("Col_VFX_Lighting")

    # Widen Right Wall & Workbench by +0.90m (`right_x = +4.25`) so character & camera have
    # generous collision-free room around the car's rear & right side!
    _shift_objects_by_prefix((
        "Env_RightWall_", "Env_IBeam_Right_", "Env_AirPipe_Right", "Env_Win_Right",
        "Prop_RightBench_", "Prop_BenchVise_", "Prop_BoltTin_", "Prop_BenchToolbox_",
        "Prop_BenchHammer_", "Prop_RightPegboard", "Prop_Peg", "Prop_Rack",
        "Prop_OilJug", "Prop_Spray", "Prop_PartsBox", "Prop_FirstAid", "Prop_HoseReel",
        "Prop_AirHose", "Prop_ToolChest_Right", "Prop_Poster_SafetyFirst", "Prop_OilDrum_BackRight",
    ), dx=0.90, dy=0.0)

    # Shift MIG Welder Cart cleanly to (1.45, -2.75) & Floor Jack to (-2.65, -2.05) for wide collision-free walkway!
    _shift_objects_by_prefix(("Prop_WelderCart_Grp", "Empty_WelderSocket"), dx=0.53, dy=-1.43)
    _shift_objects_by_prefix(("Prop_FloorJack_",), dx=-1.20, dy=-1.45)

    # Remove old single fender patch & walls where open gate/archway belong
    _remove_objects_by_prefix((
        "Env_LeftWall_", "Prop_LeftBench_", "Prop_LeftPegboard", "Prop_LeftWrench_",
        "Env_BackWall_", "Env_Win_BackL",
        "Car_FenderRepairPatch", "Car_WeldGroove", "VFX_WeldSeam",
    ))

    # Expand concrete floor slightly to cover widened right bay
    floor_obj = bpy.data.objects.get("Env_Floor")
    if floor_obj:
        floor_obj.scale.x = 1.22

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
    mat_primer = get_cel_material("Mat_Car_PrimerPatch", PALETTE_HEX["car_primer_grey"], shadow_factor=0.45, roughness=0.62, surface_type="metal")
    mat_groove = get_cel_material("Mat_Seam_DarkGroove", "#181A22", shadow_factor=0.3, surface_type="metal")
    mat_cardboard = get_cel_material("Mat_Cardboard_Box", "#A67C52", shadow_factor=0.48, surface_type="concrete")
    mat_tire = get_cel_material("Mat_Rubber_Tire", PALETTE_HEX["car_tire"], shadow_factor=0.36, surface_type="painted")
    mat_sign_glow = get_emission_material("Mat_Sign_Bengkel", "#FFB94D", strength=2.6)
    mat_hazard = get_textured_cel_material("Mat_Decal_HazardStripe", str(PROJECT_ROOT / "generated_textures" / "hazard_stripe.png"))
    mat_oil_lbl = get_textured_cel_material("Mat_Decal_OilLabel", str(PROJECT_ROOT / "generated_textures" / "oil_bottle_label.png"))

    # ==========================================================================
    # BUILD 3 RAYCASTED WELD ZONES ON THE RED CAR (FRONT, SIDE, REAR!)
    # ==========================================================================
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    proxy_obj = _build_world_car_surface_proxy(env_data["solid_body_meshes"], deps, props_col)

    weld_zones: Dict[str, Dict[str, Any]] = {
        "FRONT": _build_zone_weld_seam("FRONT", proxy_obj, props_col, mat_primer, mat_groove, x_start=-0.92, x_end=-0.62, z_center=0.72),
        "SIDE":  _build_zone_weld_seam("SIDE",  proxy_obj, props_col, mat_primer, mat_groove, x_start= 0.22, x_end= 0.66, z_center=0.72),
        "REAR":  _build_zone_weld_seam("REAR",  proxy_obj, props_col, mat_primer, mat_groove, x_start= 1.88, x_end= 2.32, z_center=0.75),
    }
    proxy_data = proxy_obj.data
    bpy.data.objects.remove(proxy_obj, do_unlink=True)
    if proxy_data and proxy_data.users == 0:
        bpy.data.meshes.remove(proxy_data)

    # ==========================================================================
    # NATURAL HELD 3D PROPS (Steel Repair Plate & Chrome Wrench!)
    # ==========================================================================
    held_plate = _make_beveled_box(
        "Prop_Held_SteelPlate", (0.36, 0.014, 0.16), props_col, mat_chrome,
        location=(-0.95, 3.85, 0.96), bevel_width=0.003, outline_thickness=0.0035,
    )
    held_wrench = _make_beveled_box(
        "Prop_Held_Wrench", (0.28, 0.032, 0.012), props_col, mat_chrome,
        location=(3.48, -0.78, 0.93), bevel_width=0.003, outline_thickness=0.0035,
    )
    wr_head = _make_cylinder("Prop_Held_WrenchHead", 0.026, 0.014, props_col, mat_chrome, location=(0.14, 0.0, 0.0), outline_thickness=0.003)
    wr_head.parent = held_wrench

    # ==========================================================================
    # LOC 1: SUNLIT OUTDOOR COURTYARD & OPEN ROLL-UP GARAGE GATE (`X = -4.15`)
    # ==========================================================================
    _make_beveled_box("Loc1_Courtyard_Floor", (6.2, 10.5, 0.12), env_col, mat_asphalt, location=(-7.8, -0.5, -0.062), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc1_GuideLine_L", (4.8, 0.09, 0.004), env_col, mat_can_y, location=(-6.6, -2.55, 0.002), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc1_GuideLine_R", (4.8, 0.09, 0.004), env_col, mat_can_y, location=(-6.6,  0.85, 0.002), bevel_width=0.0, outline_thickness=0.0)

    left_x = -4.15
    _make_beveled_box("Loc1_GateWall_South", (0.24, 1.8, 3.85), env_col, mat_wall_up, location=(left_x, -3.75, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc1_GateHeader", (0.28, 4.0, 1.05), env_col, mat_wall_low, location=(left_x, -0.95, 3.35), bevel_width=0.010, outline_thickness=0.006)
    for sl_i in range(6):
        _make_beveled_box(f"Loc1_RollShutter_Slat_{sl_i}", (0.06, 3.68, 0.085), env_col, mat_shutter, location=(left_x - 0.14, -0.95, 2.48 + sl_i * 0.092), bevel_width=0.004, outline_thickness=0.004)
    _make_beveled_box("Loc1_SignBoard_Frame", (0.14, 2.85, 0.56), env_col, mat_red, location=(left_x - 0.22, -0.95, 3.28), bevel_width=0.012, outline_thickness=0.006)
    _make_beveled_box("Loc1_SignBoard_GlowBar", (0.04, 2.55, 0.34), env_col, mat_sign_glow, location=(left_x - 0.30, -0.95, 3.28), bevel_width=0.006, outline_thickness=0.0)

    for d_i, (dx, dy, dmat) in enumerate([(-5.15, -2.95, mat_can_b), (-5.78, -2.75, mat_red), (-4.95, 1.35, mat_green)]):
        _make_cylinder(f"Loc1_Drum_{d_i}", 0.28, 0.88, env_col, dmat, location=(dx, dy, 0.44), outline_thickness=0.007)
        _make_torus(f"Loc1_DrumRib_{d_i}", 0.284, 0.012, env_col, mat_beam, location=(dx, dy, 0.87), outline_thickness=0.003)

    _make_beveled_box("Loc1_Crate_1", (0.72, 0.68, 0.62), env_col, mat_wood, location=(-6.55, 1.45, 0.31), rotation=(0.0, 0.0, 0.18), bevel_width=0.012, outline_thickness=0.006)
    _make_beveled_box("Loc1_Crate_2", (0.54, 0.52, 0.48), env_col, mat_wood, location=(-6.48, 1.42, 0.86), rotation=(0.0, 0.0, -0.22), bevel_width=0.010, outline_thickness=0.005)
    for ti in range(4):
        _make_cylinder(f"Loc1_TireStack_{ti}", 0.34, 0.21, env_col, mat_tire, location=(-5.65 + (ti % 2) * 0.03, 1.55, 0.105 + ti * 0.215), outline_thickness=0.006)
    _make_beveled_box("Loc1_Fence_North", (5.4, 0.14, 2.25), env_col, mat_shutter, location=(-7.0, 2.65, 1.12), bevel_width=0.008, outline_thickness=0.006)
    for fp_x in (-9.2, -7.0, -4.8):
        _make_ibeam_column(f"Loc1_FencePost_{fp_x}", 2.45, env_col, mat_beam, location=(fp_x, 2.55, 0.0))

    # ==========================================================================
    # LOC 5: SPARE-PARTS STORAGE ALCOVE (`Y = +2.38 .. +4.85`)
    # ==========================================================================
    back_y = 2.38
    _make_beveled_box("Loc5_BackWall_Left", (1.85, 0.22, 3.85), env_col, mat_wall_up, location=(-3.32, back_y, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc5_BackWall_Right", (4.00, 0.22, 3.85), env_col, mat_wall_up, location=(2.35, back_y, 1.92), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc5_ArchHeader", (2.95, 0.24, 1.15), env_col, mat_wall_low, location=(-1.05, back_y, 3.28), bevel_width=0.008, outline_thickness=0.006)
    _make_uv_quad("Loc5_BackWall_HazardR", 3.6, 0.11, env_col, mat_hazard, location=(2.20, back_y - 0.12, 1.19), rotation=(math.pi * 0.5, 0.0, 0.0), u_repeat=5.5)

    _make_beveled_box("Loc5_Alcove_Floor", (4.8, 2.8, 0.12), env_col, mat_asphalt, location=(-1.05, 3.65, -0.06), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_RearWall", (5.0, 0.20, 3.85), env_col, mat_wall_up, location=(-1.05, 4.95, 1.92), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_WallL", (0.20, 2.8, 3.85), env_col, mat_wall_low, location=(-3.45, 3.65, 1.92), bevel_width=0.0, outline_thickness=0.0)
    _make_beveled_box("Loc5_Alcove_WallR", (0.20, 2.8, 3.85), env_col, mat_wall_low, location=(1.35, 3.65, 1.92), bevel_width=0.0, outline_thickness=0.0)

    ax, ay = -1.05, 3.95
    for rx_o in (-1.35, 0.0, 1.35):
        for ry_o in (-0.36, 0.36):
            _make_beveled_box(f"Loc5_RackPost_{rx_o}_{ry_o}", (0.05, 0.05, 2.25), env_col, mat_beam, location=(ax + rx_o, ay + ry_o, 1.12), bevel_width=0.004, outline_thickness=0.005)
    for sh_z in (0.22, 0.84, 1.46, 2.08):
        _make_beveled_box(f"Loc5_RackShelf_{sh_z}", (2.78, 0.78, 0.04), env_col, mat_shutter, location=(ax, ay, sh_z), bevel_width=0.005, outline_thickness=0.005)

    for oi, (ox_off, omat) in enumerate([(-1.05, mat_red), (-0.75, mat_can_y), (-0.45, mat_can_b), (-0.15, mat_red), (0.15, mat_can_y)]):
        _make_beveled_box(f"Loc5_OilJug_{oi}", (0.18, 0.14, 0.28), env_col, omat, location=(ax + ox_off, ay - 0.12, 1.62), bevel_width=0.020, outline_thickness=0.005)
        _make_uv_quad(f"Loc5_OilLbl_{oi}", 0.13, 0.14, env_col, mat_oil_lbl, location=(ax + ox_off, ay - 0.195, 1.61), rotation=(math.pi * 0.5, 0.0, 0.0))

    for pl_i in range(3):
        _make_beveled_box(f"Loc5_SteelPlate_{pl_i}", (0.48, 0.34, 0.012), env_col, mat_chrome, location=(ax + 0.10, ay - 0.10, 0.89 + pl_i * 0.018), rotation=(0.0, 0.0, 0.06 * pl_i), bevel_width=0.002, outline_thickness=0.003)
    _make_beveled_box("Loc5_PartsBox_1", (0.58, 0.46, 0.38), env_col, mat_cardboard, location=(ax - 0.72, ay, 0.43), rotation=(0.0, 0.0, 0.05), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Loc5_PartsBox_2", (0.52, 0.42, 0.34), env_col, mat_cardboard, location=(ax + 0.72, ay, 0.41), rotation=(0.0, 0.0, -0.07), bevel_width=0.008, outline_thickness=0.005)
    _make_beveled_box("Loc5_PartsBox_3", (0.48, 0.40, 0.32), env_col, mat_red, location=(ax + 0.78, ay - 0.06, 1.02), bevel_width=0.010, outline_thickness=0.005)

    # ==========================================================================
    # ONE REALISTIC HERO WORKSHOP WINDOW + LOCALIZED VOLUMETRIC HAZE DOMAIN
    # ==========================================================================
    _make_beveled_box("Loc1_GateWall_NorthLow", (0.24, 2.2, 1.72), env_col, mat_wall_up, location=(left_x, 2.05, 0.86), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc1_GateWall_NorthTop", (0.24, 2.2, 0.90), env_col, mat_wall_up, location=(left_x, 2.05, 3.40), bevel_width=0.008, outline_thickness=0.006)
    _make_beveled_box("Loc1_GateWall_NorthPillarS", (0.24, 0.28, 1.30), env_col, mat_wall_up, location=(left_x, 1.05, 2.35), bevel_width=0.006, outline_thickness=0.005)
    _make_beveled_box("Loc1_GateWall_NorthPillarN", (0.24, 0.28, 1.30), env_col, mat_wall_up, location=(left_x, 3.05, 2.35), bevel_width=0.006, outline_thickness=0.005)

    hero_win_loc = (left_x, 2.05, 2.35)
    _build_realistic_hero_window(env_col, mat_beam, mat_wall_low, mat_sign_glow, location=hero_win_loc, rot_z=math.pi * 0.5)

    haze_mat, haze_col_sock, haze_dens_sock = _create_localized_haze_volume_material()
    bm_vol = bmesh.new()
    bmesh.ops.create_cube(bm_vol, size=1.0)
    bmesh.ops.scale(bm_vol, vec=(8.8, 7.6, 3.9), verts=bm_vol.verts)
    vol_mesh = bpy.data.meshes.new("VFX_WorkshopHaze_Mesh")
    bm_vol.to_mesh(vol_mesh)
    bm_vol.free()
    haze_box = bpy.data.objects.new("VFX_WorkshopHaze_Domain", vol_mesh)
    haze_box.location = (0.0, 0.2, 1.95)
    haze_box.data.materials.append(haze_mat)
    link_exclusively(haze_box, vfx_col)

    env_data["hero_window_loc"] = hero_win_loc
    env_data["haze_col_sock"] = haze_col_sock
    env_data["haze_dens_sock"] = haze_dens_sock
    env_data["weld_zones"] = weld_zones
    env_data["held_plate"] = held_plate
    env_data["held_wrench"] = held_wrench
    return env_data
