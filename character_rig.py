"""
character_rig.py — Imports MekanikMudaCharacter from tr/mekanik_muda_character.py
and constructs the full 3D/2.5D Cel-Shaded Articulated Mechanic Rig in Blender:
  - Bendy-Bone (B-Bone) + 2-Bone IK + Pole Targets for organic curved noodle limbs
  - Squash & Stretch Spine + Secondary Motion bones (2 Lightning Hair Tufts, Nape, Ear Pencil)
  - Sliding/Rotating Articulated Brass Welding Goggles + Hinged Magnifying Loupe
  - Facial Rig: Honey-Iris Gaze Tracking, Eyelid Blink, Expressive Brows & Mouth Switch
  - Child-Of Prop Constraint binding the 3D Welding Torch solidly into Hand.R
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from config import (
    CHARACTER_SCRIPT_PATH,
    GENERATED_TEX_DIR,
    MECHANIC_ROOT_POS,
    PALETTE_HEX,
)
from env_props import get_or_create_collection, link_exclusively
from shaders import (
    apply_cel_outline,
    get_cel_material,
    get_emission_material,
    get_ink_outline_material,
    get_textured_cel_material,
)


def load_source_character_blueprint() -> Dict[str, Any]:
    """
    Import `tr/mekanik_muda_character.py` directly to read CHARACTER_CONFIG and verify
    fidelity to the source 2.5D character definition.
    """
    if not CHARACTER_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Character script not found: {CHARACTER_SCRIPT_PATH}")

    spec = importlib.util.spec_from_file_location("mekanik_muda_character", str(CHARACTER_SCRIPT_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load spec from {CHARACTER_SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    cfg = dict(getattr(mod, "CHARACTER_CONFIG", {}))
    # Also instantiate MekanikMudaCharacter to verify SVG/pose engine works
    char_cls = getattr(mod, "MekanikMudaCharacter", None)
    sample_pose = None
    if char_cls is not None:
        char_inst = char_cls(scale=1.0, fps=24)
        sample_pose = char_inst.compute_pose(frame=0, animation="idle")

    return {"module": mod, "config": cfg, "sample_pose": sample_pose}


def _generate_bird_patch_texture(out_dir: Path) -> str:
    """
    Generate the signature back-vest rectangular cream cloth patch with black marker
    bird doodle & perimeter stitch marks (faithful to lines 5710-5783 of mekanik_muda_character.py)
    using pure NumPy + bpy.data.images (zero external font/cairo dependencies).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "vest_bird_patch.png"
    if tex_path.exists():
        return str(tex_path)

    W, H = 512, 384
    img_arr = np.zeros((H, W, 4), dtype=np.float32)

    # Cream canvas background (#F2E9D5) with subtle weave grain
    yy, xx = np.mgrid[0:H, 0:W]
    grain = 0.025 * np.sin(xx * 0.35 + yy * 0.35)
    img_arr[:, :, 0] = np.clip(0.95 + grain, 0.0, 1.0)
    img_arr[:, :, 1] = np.clip(0.91 + grain, 0.0, 1.0)
    img_arr[:, :, 2] = np.clip(0.83 + grain, 0.0, 1.0)
    img_arr[:, :, 3] = 1.0

    def draw_seg(x0: float, y0: float, x1: float, y1: float, r: float, col: Tuple[float, float, float]):
        dx, dy = x1 - x0, y1 - y0
        l2 = max(1e-6, dx * dx + dy * dy)
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / l2, 0.0, 1.0)
        px = x0 + t * dx
        py = y0 + t * dy
        dist = np.hypot(xx - px, py - yy)
        mask = dist <= r
        for c_i in range(3):
            img_arr[:, :, c_i][mask] = col[c_i]

    def draw_ring(cx: float, cy: float, rx: float, ry: float, thick: float, col: Tuple[float, float, float]):
        norm = np.hypot((xx - cx) / rx, (yy - cy) / ry)
        mask = np.abs(norm - 1.0) <= (thick / max(rx, ry))
        for c_i in range(3):
            img_arr[:, :, c_i][mask] = col[c_i]

    def draw_disc(cx: float, cy: float, rad: float, col: Tuple[float, float, float]):
        mask = np.hypot(xx - cx, yy - cy) <= rad
        for c_i in range(3):
            img_arr[:, :, c_i][mask] = col[c_i]

    ink = (0.11, 0.09, 0.13)
    stitch = (0.24, 0.16, 0.12)

    # Dark border & perimeter stitch marks
    draw_seg(14, 14, W - 14, 14, 6.0, ink)
    draw_seg(W - 14, 14, W - 14, H - 14, 6.0, ink)
    draw_seg(W - 14, H - 14, 14, H - 14, 6.0, ink)
    draw_seg(14, H - 14, 14, 14, 6.0, ink)
    for sx in range(38, W - 34, 38):
        draw_seg(sx, 6, sx + 8, 28, 3.2, stitch)
        draw_seg(sx, H - 28, sx - 8, H - 6, 3.2, stitch)
    for sy in range(38, H - 34, 38):
        draw_seg(6, sy, 28, sy + 7, 3.2, stitch)
        draw_seg(W - 28, sy, W - 6, sy - 7, 3.2, stitch)

    # Marker Bird Doodle in center (note: image row 0 is bottom in Blender float_buffer, so flip Y at end)
    cx, cy = 265.0, 185.0
    draw_ring(cx, cy, 96.0, 72.0, 9.5, ink)         # Plump bird body
    draw_ring(cx - 10, cy + 4, 42.0, 26.0, 7.0, ink)  # Cute wing arc
    draw_disc(cx + 52, cy - 26, 11.5, ink)          # Marker dot eye
    # Beak pointing right
    draw_seg(cx + 94, cy - 24, cx + 142, cy - 12, 7.5, ink)
    draw_seg(cx + 142, cy - 12, cx + 95, cy + 2, 7.5, ink)
    # 3 Tail feathers on left
    draw_seg(cx - 94, cy + 6, cx - 152, cy - 22, 7.5, ink)
    draw_seg(cx - 96, cy + 18, cx - 158, cy + 14, 7.5, ink)
    draw_seg(cx - 90, cy + 30, cx - 146, cy + 44, 7.5, ink)
    # Stick legs & feet at bottom (higher yy before vertical flip)
    draw_seg(cx - 18, cy + 72, cx - 24, cy + 118, 6.5, ink)
    draw_seg(cx - 42, cy + 120, cx - 4, cy + 118, 6.5, ink)
    draw_seg(cx + 28, cy + 70, cx + 34, cy + 118, 6.5, ink)
    draw_seg(cx + 14, cy + 120, cx + 52, cy + 118, 6.5, ink)

    # Flip vertically for Blender bottom-up pixel order
    flipped = np.ascontiguousarray(np.flipud(img_arr), dtype=np.float32)
    b_img = bpy.data.images.new("Tex_VestBirdPatch", width=W, height=H, alpha=True)
    b_img.pixels.foreach_set(flipped.ravel())
    b_img.filepath_raw = str(tex_path)
    b_img.file_format = "PNG"
    b_img.save()
    return str(tex_path)


def _make_torus_bmesh(
    major_radius: float,
    minor_radius: float,
    major_segments: int = 28,
    minor_segments: int = 12,
    scale_y: float = 1.0,
) -> bmesh.types.BMesh:
    bm = bmesh.new()
    rings: List[List[bmesh.types.BMVert]] = []
    for i in range(major_segments):
        theta = (2.0 * math.pi * i) / major_segments
        ct, st = math.cos(theta), math.sin(theta)
        ring = []
        for j in range(minor_segments):
            phi = (2.0 * math.pi * j) / minor_segments
            r = major_radius + minor_radius * math.cos(phi)
            x = r * ct
            y = r * st * scale_y
            z = minor_radius * math.sin(phi)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for i in range(major_segments):
        i_next = (i + 1) % major_segments
        for j in range(minor_segments):
            j_next = (j + 1) % minor_segments
            bm.faces.new([
                rings[i][j],
                rings[i_next][j],
                rings[i_next][j_next],
                rings[i][j_next],
            ])
    return bm


def _create_bone_parented_mesh(
    name: str,
    bm: bmesh.types.BMesh,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    arm_obj: bpy.types.Object,
    bone_name: str,
    world_loc: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    world_rot: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    outline_thickness: float = 0.006,
    smooth: bool = True,
) -> bpy.types.Object:
    """
    Create a mesh object in world coordinates, then parent it cleanly to a specific
    Armature Bone (`parent_type = 'BONE'`) preserving its exact world transform!
    """
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    link_exclusively(obj, col)

    if outline_thickness > 0.0:
        apply_cel_outline(obj, thickness=outline_thickness)

    world_mat = Matrix.Translation(world_loc) @ Euler(world_rot, "XYZ").to_matrix().to_4x4()

    # In Blender, BONE parenting attaches child relative to the bone's TAIL in armature space:
    # parent_bone_mat = arm_obj.matrix_world @ bone.matrix_local @ Translation(0, bone.length, 0)
    bone = arm_obj.data.bones[bone_name]
    bone_tail_arm = bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))
    parent_world = arm_obj.matrix_world @ bone_tail_arm

    obj.parent = arm_obj
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = parent_world.inverted()
    obj.matrix_world = world_mat
    return obj


def _create_skinned_noodle_tube(
    name: str,
    p_start: Vector,
    p_mid: Vector,
    p_end: Vector,
    radius: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    arm_obj: bpy.types.Object,
    bone_upper: str,
    bone_lower: str,
    outline_thickness: float = 0.005,
    rings: int = 40,
    sectors: int = 16,
) -> bpy.types.Object:
    """
    Create a high-subdivision organic noodle limb mesh along a smooth Quadratic Bezier
    curve p_start -> p_mid -> p_end with wide Hermite blended weights across `bone_upper`
    and `bone_lower` and open ends (tucked inside sleeve/mitt) so Solidify NEVER spikes!
    """
    bm = bmesh.new()
    ring_verts: List[List[bmesh.types.BMVert]] = []
    ring_ts: List[float] = []

    arm_inv = arm_obj.matrix_world.inverted()
    s_loc = arm_inv @ p_start
    m_loc = arm_inv @ p_mid
    e_loc = arm_inv @ p_end
    # Quadratic Bezier control point passing near m_loc for round cartoon limb rest shape
    ctrl = m_loc * 1.45 - (s_loc + e_loc) * 0.225

    def sample_pos(u: float) -> Vector:
        omt = 1.0 - u
        return (omt * omt) * s_loc + (2.0 * omt * u) * ctrl + (u * u) * e_loc

    for r_i in range(rings + 1):
        u = r_i / rings
        ring_ts.append(u)
        c_pt = sample_pos(u)
        u_prev = max(0.0, u - 0.02)
        u_next = min(1.0, u + 0.02)
        tangent = (sample_pos(u_next) - sample_pos(u_prev)).normalized()
        if tangent.length < 1e-6:
            tangent = Vector((0.0, 0.0, -1.0))

        ref = Vector((0.0, 1.0, 0.0)) if abs(tangent.y) < 0.9 else Vector((1.0, 0.0, 0.0))
        n1 = tangent.cross(ref).normalized()
        n2 = tangent.cross(n1).normalized()

        v_ring = []
        for s_i in range(sectors):
            ang = (2.0 * math.pi * s_i) / sectors
            off = (n1 * math.cos(ang) + n2 * math.sin(ang)) * radius
            v_ring.append(bm.verts.new(c_pt + off))
        ring_verts.append(v_ring)

    # Connect rings (no N-gon end caps — ends tuck cleanly inside sleeve/hip & mitt/foot!)
    for r_i in range(rings):
        for s_i in range(sectors):
            s_next = (s_i + 1) % sectors
            bm.faces.new([
                ring_verts[r_i][s_i],
                ring_verts[r_i][s_next],
                ring_verts[r_i + 1][s_next],
                ring_verts[r_i + 1][s_i],
            ])

    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = arm_obj.matrix_world.copy()
    obj.data.materials.append(mat)
    link_exclusively(obj, col)

    # Wide smoothstep blend over u in [0.22 .. 0.78] for silky rubber-hose elbow/knee arc!
    vg_up = obj.vertex_groups.new(name=bone_upper)
    vg_lo = obj.vertex_groups.new(name=bone_lower)

    for r_i, u in enumerate(ring_ts):
        x = max(0.0, min(1.0, (u - 0.22) / 0.56))
        w_lo = x * x * (3.0 - 2.0 * x)
        w_up = 1.0 - w_lo
        v_indices = [r_i * sectors + s_i for s_i in range(sectors)]
        if w_up > 1e-4:
            vg_up.add(v_indices, w_up, "REPLACE")
        if w_lo > 1e-4:
            vg_lo.add(v_indices, w_lo, "REPLACE")

    arm_mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    arm_mod.object = arm_obj
    arm_mod.use_deform_preserve_volume = True

    if outline_thickness > 0.0:
        apply_cel_outline(obj, thickness=outline_thickness, use_even_offset=False)

    return obj


def build_mechanic_character(torch_obj: Optional[bpy.types.Object] = None) -> Dict[str, Any]:
    """
    Construct the complete rigged 3D/2.5D Mekanik Muda character at MECHANIC_ROOT_POS
    facing +Y (towards the car's front-left fender) and bind `torch_obj` to Hand.R!
    """
    src_info = load_source_character_blueprint()
    src_cfg = src_info["config"]

    char_col = get_or_create_collection("Col_Mechanic_Character")
    rx, ry, rz = MECHANIC_ROOT_POS

    # ==========================================================================
    # 1. MATERIALS (100% Exact Hex Palette from tr/mekanik_muda_character.py)
    # ==========================================================================
    mat_skin = get_cel_material("Mat_Char_Skin", src_cfg.get("skinColor", PALETTE_HEX["skin"]), shadow_factor=0.62, mid_factor=0.92, lit_factor=1.08, rim_strength=0.24, colored_light_mix=0.62)
    mat_ear_in = get_cel_material("Mat_Char_Blush", src_cfg.get("blushColor", PALETTE_HEX["skin_blush"]), shadow_factor=0.58, rim_strength=0.05)
    mat_hair = get_cel_material("Mat_Char_Hair", src_cfg.get("hairColor", PALETTE_HEX["hair_dark"]), shadow_factor=0.45, mid_factor=0.88, lit_factor=1.22, spec_strength=0.35, rim_strength=0.26, colored_light_mix=0.58)
    mat_vest = get_cel_material("Mat_Char_Vest", src_cfg.get("robeColor", PALETTE_HEX["vest_mustard"]), shadow_factor=0.48, mid_factor=0.90, lit_factor=1.14, rim_strength=0.25, colored_light_mix=0.60)
    mat_tee = get_cel_material("Mat_Char_Tee", src_cfg.get("innerColor", PALETTE_HEX["tee_ivory"]), shadow_factor=0.56, mid_factor=0.92, lit_factor=1.10, rim_strength=0.20, colored_light_mix=0.60)
    mat_belt = get_cel_material("Mat_Char_Belt", src_cfg.get("sashColor", PALETTE_HEX["belt_leather"]), shadow_factor=0.44, mid_factor=0.86, lit_factor=1.14, spec_strength=0.25, rim_strength=0.18)
    mat_buckle = get_cel_material("Mat_Char_Buckle", src_cfg.get("trimColor", PALETTE_HEX["buckle_metal"]), shadow_factor=0.48, lit_factor=1.25, spec_strength=0.80, rim_strength=0.25)
    mat_limb = get_cel_material("Mat_Char_NoodleLimb", src_cfg.get("limbColor", PALETTE_HEX["noodle_limb"]), shadow_factor=0.50, mid_factor=0.88, lit_factor=1.25, rim_strength=0.28, colored_light_mix=0.55)
    mat_brass = get_cel_material("Mat_Char_GoggleBrass", src_cfg.get("hatPrimary", PALETTE_HEX["brass_goggles"]), shadow_factor=0.46, lit_factor=1.26, spec_strength=0.85, rim_strength=0.28, colored_light_mix=0.68)
    mat_strap = get_cel_material("Mat_Char_GoggleStrap", src_cfg.get("hatAccent", PALETTE_HEX["strap_black"]), shadow_factor=0.44, lit_factor=1.15, spec_strength=0.35, rim_strength=0.20)
    mat_lens = get_cel_material("Mat_Char_GoggleLens", PALETTE_HEX["goggle_lens"], shadow_factor=0.42, lit_factor=1.32, spec_strength=0.95, roughness=0.12, rim_strength=0.35, colored_light_mix=0.75)
    mat_loupe = get_cel_material("Mat_Char_LoupeGlass", PALETTE_HEX["loupe_glass"], shadow_factor=0.58, lit_factor=1.30, spec_strength=0.95, roughness=0.10, rim_strength=0.30)
    mat_sclera = get_emission_material("Mat_Char_EyeWhite", "#FFFFFF", strength=1.02)
    mat_iris = get_cel_material("Mat_Char_IrisHoney", src_cfg.get("irisColor", PALETTE_HEX["iris_honey"]), shadow_factor=0.65, lit_factor=1.22, spec_strength=0.5, rim_strength=0.0)
    mat_pupil = get_emission_material("Mat_Char_Pupil", "#1A1216", strength=1.0)
    mat_glint = get_emission_material("Mat_Char_EyeGlint", "#FFFFFF", strength=1.35)
    mat_mouth_bg = get_emission_material("Mat_Char_MouthDark", "#481A22", strength=1.0)
    mat_tongue = get_emission_material("Mat_Char_Tongue", "#D85C6A", strength=1.0)
    mat_bandage = get_cel_material("Mat_Char_Bandage", PALETTE_HEX["bandage_cream"], shadow_factor=0.62, rim_strength=0.10)
    mat_smudge = get_cel_material("Mat_Char_OilSmudge", "#3A3338", shadow_factor=0.5, rim_strength=0.0)
    mat_pencil_y = get_cel_material("Mat_Char_PencilYellow", PALETTE_HEX["pencil_yellow"], shadow_factor=0.52, lit_factor=1.16, rim_strength=0.15)
    mat_pencil_w = get_cel_material("Mat_Char_PencilWood", "#E8C69C", shadow_factor=0.55, rim_strength=0.10)
    mat_eraser = get_cel_material("Mat_Char_PencilEraser", PALETTE_HEX["pencil_eraser"], shadow_factor=0.54, rim_strength=0.12)
    mat_red_sd = get_cel_material("Mat_Char_ScrewdriverRed", PALETTE_HEX["screwdriver_red"], shadow_factor=0.48, spec_strength=0.45, rim_strength=0.15)
    mat_copper = get_cel_material("Mat_Char_CopperCoil", PALETTE_HEX["copper_wire"], shadow_factor=0.48, lit_factor=1.24, spec_strength=0.80, rim_strength=0.22)
    mat_badge_bg = get_cel_material("Mat_Char_BadgeNavy", "#2B3646", shadow_factor=0.48, rim_strength=0.12)

    bird_patch_path = _generate_bird_patch_texture(GENERATED_TEX_DIR)
    mat_bird_patch = get_textured_cel_material("Mat_Char_VestBirdPatch", bird_patch_path, alpha_cutout=False)

    # ==========================================================================
    # 2. BUILD ARMATURE (`Armature_Mechanic`) IN EDIT MODE
    # ==========================================================================
    # Convention: All control bones point +Y (length 0.06m, roll=0) so Pose-Mode
    # local (X, Y, Z) matches World (Right +X, Forward +Y, Up +Z) 1-to-1!
    arm_data = bpy.data.armatures.new("Armature_Mechanic_Data")
    arm_data.display_type = "BBONE"
    arm_obj = bpy.data.objects.new("Armature_Mechanic", arm_data)
    arm_obj.location = (rx, ry, rz)
    link_exclusively(arm_obj, char_col)

    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = arm_data.edit_bones

    def add_ctrl_bone(name: str, loc: Tuple[float, float, float], length: float = 0.06, parent_name: Optional[str] = None, deform: bool = False) -> bpy.types.EditBone:
        b = ebones.new(name)
        b.head = Vector(loc)
        b.tail = Vector((loc[0], loc[1] + length, loc[2]))
        b.roll = 0.0
        b.use_deform = deform
        if parent_name:
            b.parent = ebones[parent_name]
            b.use_connect = False
        return b

    def add_limb_bone(name: str, head: Tuple[float, float, float], tail: Tuple[float, float, float], parent_name: str, connected: bool = False, bbone_segs: int = 6) -> bpy.types.EditBone:
        b = ebones.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.align_roll(Vector((0.0, 1.0, 0.0)))
        b.use_deform = True
        b.bbone_segments = bbone_segs
        b.bbone_x = 0.016
        b.bbone_z = 0.016
        b.parent = ebones[parent_name]
        b.use_connect = connected
        return b

    # Core Hierarchy (Armature-local coordinates relative to MECHANIC_ROOT_POS)
    add_ctrl_bone("Root", (0.0, 0.0, 0.0), 0.12, None, deform=False)
    add_ctrl_bone("Pelvis", (0.0, 0.0, 0.56), 0.08, "Root", deform=True)
    b_spine = add_ctrl_bone("Spine", (0.0, 0.0, 0.62), 0.08, "Pelvis", deform=True)
    add_ctrl_bone("Chest", (0.0, 0.0, 0.84), 0.08, "Spine", deform=True)
    add_ctrl_bone("Neck", (0.0, 0.0, 1.00), 0.05, "Chest", deform=True)
    add_ctrl_bone("Head", (0.0, 0.0, 1.03), 0.08, "Neck", deform=True)

    # Secondary Follow-Through Bones on Head
    add_ctrl_bone("Hair_Bolt_1", (-0.01, 0.02, 1.40), 0.06, "Head", deform=True)
    add_ctrl_bone("Hair_Bolt_2", (-0.06, 0.01, 1.39), 0.05, "Head", deform=True)
    add_ctrl_bone("Hair_Nape", (0.0, -0.18, 1.09), 0.05, "Head", deform=True)
    add_ctrl_bone("Ear_Pencil.R", (0.225, -0.01, 1.24), 0.05, "Head", deform=True)

    # Articulated Welding Goggles Rig on Forehead (+Y front of head)
    add_ctrl_bone("Goggles_Ctrl", (0.0, 0.0, 1.355), 0.07, "Head", deform=True)
    add_ctrl_bone("Goggles_Loupe", (0.145, 0.195, 1.355), 0.04, "Goggles_Ctrl", deform=True)

    # Facial Rig Bones (Pupils, Eyelids, Eyebrows, Mouth Switch)
    add_ctrl_bone("Eye_Target", (0.0, 0.65, 1.18), 0.06, "Root", deform=False)
    add_ctrl_bone("Eye_Iris.L", (-0.064, 0.196, 1.235), 0.03, "Head", deform=True)
    add_ctrl_bone("Eye_Iris.R", (0.064, 0.196, 1.235), 0.03, "Head", deform=True)
    add_ctrl_bone("Blink.L", (-0.064, 0.198, 1.235), 0.03, "Head", deform=True)
    add_ctrl_bone("Blink.R", (0.064, 0.198, 1.235), 0.03, "Head", deform=True)
    add_ctrl_bone("Brow.L", (-0.066, 0.200, 1.300), 0.03, "Head", deform=True)
    add_ctrl_bone("Brow.R", (0.066, 0.200, 1.300), 0.03, "Head", deform=True)
    add_ctrl_bone("Mouth_Smile_Bone", (0.0, 0.196, 1.132), 0.03, "Head", deform=True)
    add_ctrl_bone("Mouth_Focus_Bone", (0.0, 0.196, 1.132), 0.03, "Head", deform=True)

    # Left & Right Arms (Character faces +Y: Left = -X, Right = +X!)
    # Slight natural rest bend so 2-Bone IK solver always knows preferred elbow plane
    sh_L = (-0.185, 0.0, 0.945)
    elb_L = (-0.325, -0.050, 0.745)
    hnd_L = (-0.240, 0.070, 0.555)

    sh_R = (0.185, 0.0, 0.945)
    elb_R = (0.325, -0.050, 0.745)
    hnd_R = (0.240, 0.070, 0.555)

    add_ctrl_bone("Shoulder.L", (-0.14, 0.0, 0.95), 0.04, "Chest", deform=False)
    add_limb_bone("UpperArm.L", sh_L, elb_L, "Shoulder.L", connected=False, bbone_segs=6)
    add_limb_bone("Forearm.L", elb_L, hnd_L, "UpperArm.L", connected=True, bbone_segs=6)
    b_hl = add_ctrl_bone("Hand.L", hnd_L, 0.055, "Forearm.L", deform=True)
    b_hl.use_connect = True

    add_ctrl_bone("Shoulder.R", (0.14, 0.0, 0.95), 0.04, "Chest", deform=False)
    add_limb_bone("UpperArm.R", sh_R, elb_R, "Shoulder.R", connected=False, bbone_segs=6)
    add_limb_bone("Forearm.R", elb_R, hnd_R, "UpperArm.R", connected=True, bbone_segs=6)
    b_hr = add_ctrl_bone("Hand.R", hnd_R, 0.055, "Forearm.R", deform=True)
    b_hr.use_connect = True

    # Arm IK Targets & Elbow Pole Targets (parented to Root so hands stay world-locked on car!)
    add_ctrl_bone("IK_Hand.L", hnd_L, 0.06, "Root", deform=False)
    add_ctrl_bone("Pole_Arm.L", (-0.42, -0.35, 0.75), 0.05, "Root", deform=False)
    add_ctrl_bone("IK_Hand.R", hnd_R, 0.06, "Root", deform=False)
    add_ctrl_bone("Pole_Arm.R", (0.42, -0.35, 0.75), 0.05, "Root", deform=False)

    # Left & Right Legs (with slight forward knee pre-bend for stable 2-Bone IK)
    hip_L = (-0.085, 0.0, 0.565)
    knee_L = (-0.095, 0.035, 0.295)
    ank_L = (-0.095, 0.0, 0.035)

    hip_R = (0.085, 0.0, 0.565)
    knee_R = (0.095, 0.035, 0.295)
    ank_R = (0.095, 0.0, 0.035)

    add_limb_bone("Thigh.L", hip_L, knee_L, "Pelvis", connected=False, bbone_segs=6)
    add_limb_bone("Shin.L", knee_L, ank_L, "Thigh.L", connected=True, bbone_segs=6)
    b_fl = add_ctrl_bone("Foot.L", ank_L, 0.09, "Shin.L", deform=True)
    b_fl.use_connect = True

    add_limb_bone("Thigh.R", hip_R, knee_R, "Pelvis", connected=False, bbone_segs=6)
    add_limb_bone("Shin.R", knee_R, ank_R, "Thigh.R", connected=True, bbone_segs=6)
    b_fr = add_ctrl_bone("Foot.R", ank_R, 0.09, "Shin.R", deform=True)
    b_fr.use_connect = True

    add_ctrl_bone("IK_Foot.L", ank_L, 0.08, "Root", deform=False)
    add_ctrl_bone("Pole_Leg.L", (-0.12, 0.42, 0.30), 0.05, "Root", deform=False)
    add_ctrl_bone("IK_Foot.R", ank_R, 0.08, "Root", deform=False)
    add_ctrl_bone("Pole_Leg.R", (0.12, 0.42, 0.30), 0.05, "Root", deform=False)

    bpy.ops.object.mode_set(mode="OBJECT")

    # ==========================================================================
    # 3. POSE MODE CONSTRAINTS (2-Bone IK, Squash & Stretch, Gaze Track)
    # ==========================================================================
    pbones = arm_obj.pose.bones

    # Maintain Volume on Spine for cartoon Squash & Stretch breathing/anticipation
    mv = pbones["Spine"].constraints.new("MAINTAIN_VOLUME")
    mv.free_axis = "SAMEVOL_Z"
    mv.volume = 1.0

    # Configure 2-Bone IK + Hand/Foot Copy Rotation
    ik_configs = [
        ("Forearm.L", "Hand.L", "IK_Hand.L", "Pole_Arm.L", -90.0),
        ("Forearm.R", "Hand.R", "IK_Hand.R", "Pole_Arm.R", -90.0),
        ("Shin.L", "Foot.L", "IK_Foot.L", "Pole_Leg.L", 90.0),
        ("Shin.R", "Foot.R", "IK_Foot.R", "Pole_Leg.R", 90.0),
    ]
    for mid_b, end_b, ik_t, pole_t, pole_deg in ik_configs:
        ik = pbones[mid_b].constraints.new("IK")
        ik.target = arm_obj
        ik.subtarget = ik_t
        ik.pole_target = arm_obj
        ik.pole_subtarget = pole_t
        ik.chain_count = 2
        ik.pole_angle = math.radians(pole_deg)

        cr = pbones[end_b].constraints.new("COPY_ROTATION")
        cr.target = arm_obj
        cr.subtarget = ik_t
        cr.target_space = "WORLD"
        cr.owner_space = "WORLD"

    # Calibrate pole_angle automatically so Rest Pose has ZERO twist jump!
    bpy.context.view_layer.update()
    for mid_b, _, _, _, _ in ik_configs:
        ik_con = pbones[mid_b].constraints["IK"]
        best_deg = 0.0
        best_err = 999.0
        for deg_test in (0.0, 90.0, -90.0, 180.0):
            ik_con.pole_angle = math.radians(deg_test)
            bpy.context.view_layer.update()
            err = pbones[mid_b].matrix_basis.to_euler().x ** 2 + pbones[mid_b].matrix_basis.to_euler().y ** 2 + pbones[mid_b].matrix_basis.to_euler().z ** 2
            if err < best_err:
                best_err = err
                best_deg = deg_test
        ik_con.pole_angle = math.radians(best_deg)

    # Eye Gaze Tracking: Pupils subtly shift on face toward `Eye_Target`
    for side_s, base_x in (("L", -0.064), ("R", 0.064)):
        p_eye = pbones[f"Eye_Iris.{side_s}"]
        dt = p_eye.constraints.new("DAMPED_TRACK")
        dt.target = arm_obj
        dt.subtarget = "Eye_Target"
        dt.track_axis = "TRACK_Y"
        dt.influence = 0.28

    # Set initial Goggles rest tilt (-6 deg as in CHARACTER_CONFIG["hatTilt"])
    pbones["Goggles_Ctrl"].rotation_mode = "XYZ"
    for pb in pbones:
        pb.rotation_mode = "XYZ"

    bpy.context.view_layer.update()

    # ==========================================================================
    # 4. BUILD 3D CHARACTER GEOMETRY (FAITHFUL TO MEKANIK MUDA DESIGN)
    # ==========================================================================
    # Helper to convert armature-local coords to world coords
    def W(lx: float, ly: float, lz: float) -> Tuple[float, float, float]:
        return (rx + lx, ry + ly, rz + lz)

    # ---- A) TORSO: Chubby Capsule Ivory Tee + Open Mustard Mechanic Vest ----
    bm_torso = bmesh.new()
    bmesh.ops.create_uvsphere(bm_torso, u_segments=32, v_segments=20, radius=1.0)
    for v in bm_torso.verts:
        # Bean/pill proportions matching mekanik_muda_front_0deg.png
        taper = 1.0 - 0.14 * max(0.0, v.co.z)
        v.co.x *= 0.192 * taper
        v.co.y *= 0.162 * taper
        v.co.z *= 0.245
    _create_bone_parented_mesh("Char_Torso_Tee", bm_torso, char_col, mat_tee, arm_obj, "Spine", W(0.0, 0.0, 0.785), outline_thickness=0.010)

    # Ribbed Crew Neck Collar
    bm_col = bmesh.new()
    bmesh.ops.create_cone(bm_col, cap_ends=True, cap_tris=False, segments=24, radius1=0.095, radius2=0.072, depth=0.045)
    _create_bone_parented_mesh("Char_Tee_Collar", bm_col, char_col, mat_tee, arm_obj, "Chest", W(0.0, 0.01, 1.005), outline_thickness=0.006)

    # Open Mustard Canvas Mechanic Vest Shell (wraps back & sides, open front gap X in [-0.068..+0.068])
    bm_vest = bmesh.new()
    u_segs, v_segs = 32, 16
    vest_rings: List[List[bmesh.types.BMVert]] = []
    # Angle from front-right (+X/+Y edge) around back (-Y) to front-left (-X/+Y edge)
    ang_start = math.radians(68.0)    # ~ +68 deg from +X (front-left gap edge is ~112 deg)
    # Wait: in (X, Y), angle 90 deg is +Y (front center)!
    # So front opening is [68 deg .. 112 deg]. Vest wraps from 112 deg -> 180 -> 270 (-Y back) -> 360 -> 428 deg (68+360)!
    a0 = math.radians(111.0)
    a1 = math.radians(360.0 + 69.0)
    for vi in range(v_segs + 1):
        vz = -0.215 + (vi / v_segs) * 0.435  # Z relative to 0.79
        z_norm = vz / 0.22
        rad_scale = math.sqrt(max(0.18, 1.0 - 0.62 * (z_norm ** 2)))
        taper = 1.0 - 0.12 * max(0.0, z_norm)
        rx_v = 0.204 * rad_scale * taper
        ry_v = 0.174 * rad_scale * taper
        row = []
        for ui in range(u_segs + 1):
            ang = a0 + (a1 - a0) * (ui / u_segs)
            row.append(bm_vest.verts.new((math.cos(ang) * rx_v, math.sin(ang) * ry_v, vz)))
        vest_rings.append(row)
    for vi in range(v_segs):
        for ui in range(u_segs):
            bm_vest.faces.new([
                vest_rings[vi][ui],
                vest_rings[vi][ui + 1],
                vest_rings[vi + 1][ui + 1],
                vest_rings[vi + 1][ui],
            ])
    bmesh.ops.solidify(bm_vest, geom=list(bm_vest.faces), thickness=0.014)
    _create_bone_parented_mesh("Char_MechanicVest", bm_vest, char_col, mat_vest, arm_obj, "Spine", W(0.0, 0.0, 0.79), outline_thickness=0.008)

    # Vest Chest Details:
    # Right Chest (+X): Puffed Buttoned Flap Pocket + 3 Vest Buttons
    bm_rp = bmesh.new()
    bmesh.ops.create_cube(bm_rp, size=1.0)
    bmesh.ops.scale(bm_rp, vec=(0.075, 0.028, 0.082), verts=bm_rp.verts)
    bmesh.ops.bevel(bm_rp, geom=list(bm_rp.edges), offset=0.008, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_Vest_RightPocket", bm_rp, char_col, mat_vest, arm_obj, "Chest", W(0.122, 0.148, 0.855), world_rot=(0.08, 0.0, -0.45), outline_thickness=0.005)

    for b_idx, bz in enumerate((0.91, 0.85, 0.79)):
        bm_bt = bmesh.new()
        bmesh.ops.create_cone(bm_bt, cap_ends=True, cap_tris=False, segments=12, radius1=0.008, radius2=0.008, depth=0.008)
        _create_bone_parented_mesh(f"Char_Vest_Button_{b_idx}", bm_bt, char_col, mat_belt, arm_obj, "Spine", W(0.078, 0.166, bz), world_rot=(math.pi * 0.5, 0.0, -0.2), outline_thickness=0.003)

    # Left Chest (-X): Pocket + Round Navy/Gold Gear Pin Badge + 2 Silver Safety Pins!
    bm_lp = bmesh.new()
    bmesh.ops.create_cube(bm_lp, size=1.0)
    bmesh.ops.scale(bm_lp, vec=(0.072, 0.024, 0.075), verts=bm_lp.verts)
    bmesh.ops.bevel(bm_lp, geom=list(bm_lp.edges), offset=0.007, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_Vest_LeftPocket", bm_lp, char_col, mat_vest, arm_obj, "Chest", W(-0.122, 0.148, 0.850), world_rot=(0.08, 0.0, 0.45), outline_thickness=0.005)

    bm_bg = bmesh.new()
    bmesh.ops.create_cone(bm_bg, cap_ends=True, cap_tris=False, segments=18, radius1=0.025, radius2=0.025, depth=0.010)
    _create_bone_parented_mesh("Char_GearBadge_Base", bm_bg, char_col, mat_badge_bg, arm_obj, "Chest", W(-0.098, 0.168, 0.885), world_rot=(math.pi * 0.5, 0.0, 0.35), outline_thickness=0.004)
    bm_gr = bmesh.new()
    bmesh.ops.create_cone(bm_gr, cap_ends=True, cap_tris=False, segments=8, radius1=0.015, radius2=0.015, depth=0.012)
    _create_bone_parented_mesh("Char_GearBadge_Star", bm_gr, char_col, mat_pencil_y, arm_obj, "Chest", W(-0.100, 0.171, 0.885), world_rot=(math.pi * 0.5, 0.0, 0.35), outline_thickness=0.002)

    for sp_i, (sp_z, sp_r) in enumerate(((0.855, 0.32), (0.832, 0.12))):
        bm_sp = bmesh.new()
        bmesh.ops.create_cube(bm_sp, size=1.0)
        bmesh.ops.scale(bm_sp, vec=(0.032, 0.008, 0.009), verts=bm_sp.verts)
        _create_bone_parented_mesh(f"Char_SafetyPin_{sp_i}", bm_sp, char_col, mat_buckle, arm_obj, "Chest", W(-0.132, 0.160, sp_z), world_rot=(0.0, sp_r, 0.48), outline_thickness=0.0025)

    # Back of Vest (-Y): Rectangular Stitched Cloth Patch with Black Marker Bird!
    bm_patch = bmesh.new()
    v0 = bm_patch.verts.new((-0.095, 0.0, -0.068))
    v1 = bm_patch.verts.new((0.095, 0.0, -0.068))
    v2 = bm_patch.verts.new((0.095, 0.0, 0.068))
    v3 = bm_patch.verts.new((-0.095, 0.0, 0.068))
    f_p = bm_patch.faces.new([v0, v1, v2, v3])
    uv_lay = bm_patch.loops.layers.uv.new("UVMap")
    # Facing -Y from behind: viewer's left is +X, viewer's right is -X
    uvs = [(1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    for loop, uv in zip(f_p.loops, uvs):
        loop[uv_lay].uv = uv
    _create_bone_parented_mesh("Char_Vest_BackBirdPatch", bm_patch, char_col, mat_bird_patch, arm_obj, "Chest", W(0.0, -0.184, 0.855), world_rot=(0.05, -0.03, 0.0), outline_thickness=0.0)

    # ---- B) SLANTED LEATHER TOOLBELT + METAL BUCKLE + HIP TOOL POUCHES ----
    # Oversized belt tilted lower on Right Hip (+X), just like mekanik_muda_front_0deg.png!
    bm_belt = bmesh.new()
    bmesh.ops.create_cone(bm_belt, cap_ends=True, cap_tris=False, segments=32, radius1=0.208, radius2=0.205, depth=0.068)
    for v in bm_belt.verts:
        v.co.y *= 0.84
    _create_bone_parented_mesh("Char_ToolBelt_Strap", bm_belt, char_col, mat_belt, arm_obj, "Pelvis", W(0.0, 0.0, 0.705), world_rot=(0.0, 0.14, 0.0), outline_thickness=0.007)

    # Large Dull-Metal Rectangular Buckle at Front
    bm_bk = bmesh.new()
    bmesh.ops.create_cube(bm_bk, size=1.0)
    bmesh.ops.scale(bm_bk, vec=(0.115, 0.032, 0.092), verts=bm_bk.verts)
    bmesh.ops.bevel(bm_bk, geom=list(bm_bk.edges), offset=0.008, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_ToolBelt_Buckle", bm_bk, char_col, mat_buckle, arm_obj, "Pelvis", W(-0.015, 0.178, 0.705), world_rot=(0.0, 0.14, 0.0), outline_thickness=0.006)
    bm_bkin = bmesh.new()
    bmesh.ops.create_cube(bm_bkin, size=1.0)
    bmesh.ops.scale(bm_bkin, vec=(0.068, 0.036, 0.052), verts=bm_bkin.verts)
    _create_bone_parented_mesh("Char_ToolBelt_BuckleIn", bm_bkin, char_col, mat_belt, arm_obj, "Pelvis", W(-0.015, 0.180, 0.705), world_rot=(0.0, 0.14, 0.0), outline_thickness=0.003)

    # Right Hip Pouch (+X): Leather Pouch + Chrome Wrench + Red Screwdriver
    bm_rpouch = bmesh.new()
    bmesh.ops.create_cube(bm_rpouch, size=1.0)
    bmesh.ops.scale(bm_rpouch, vec=(0.062, 0.098, 0.118), verts=bm_rpouch.verts)
    bmesh.ops.bevel(bm_rpouch, geom=list(bm_rpouch.edges), offset=0.012, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_RightHip_Pouch", bm_rpouch, char_col, mat_belt, arm_obj, "Pelvis", W(0.205, 0.02, 0.655), outline_thickness=0.006)

    bm_pw = bmesh.new()
    bmesh.ops.create_cube(bm_pw, size=1.0)
    bmesh.ops.scale(bm_pw, vec=(0.014, 0.028, 0.095), verts=bm_pw.verts)
    _create_bone_parented_mesh("Char_Pouch_Wrench", bm_pw, char_col, mat_buckle, arm_obj, "Pelvis", W(0.212, 0.042, 0.735), world_rot=(-0.18, 0.12, 0.0), outline_thickness=0.004)
    bm_psd = bmesh.new()
    bmesh.ops.create_cone(bm_psd, cap_ends=True, cap_tris=False, segments=12, radius1=0.016, radius2=0.014, depth=0.068)
    _create_bone_parented_mesh("Char_Pouch_RedScrewdriver", bm_psd, char_col, mat_red_sd, arm_obj, "Pelvis", W(0.212, -0.012, 0.742), world_rot=(0.16, 0.10, 0.0), outline_thickness=0.004)

    # Left Hip Pouch (-X): Leather Pouch + Coiled Copper Wire Ring
    bm_lpouch = bmesh.new()
    bmesh.ops.create_cube(bm_lpouch, size=1.0)
    bmesh.ops.scale(bm_lpouch, vec=(0.058, 0.092, 0.105), verts=bm_lpouch.verts)
    bmesh.ops.bevel(bm_lpouch, geom=list(bm_lpouch.edges), offset=0.012, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_LeftHip_Pouch", bm_lpouch, char_col, mat_belt, arm_obj, "Pelvis", W(-0.205, 0.02, 0.715), outline_thickness=0.006)

    # Coiled Copper Torus on Left Hip
    bm_coil = _make_torus_bmesh(major_radius=0.045, minor_radius=0.011, major_segments=24, minor_segments=10)
    _create_bone_parented_mesh(
        "Char_LeftHip_CopperCoil", bm_coil, char_col, mat_copper, arm_obj, "Pelvis",
        W(-0.238, 0.02, 0.695), world_rot=(0.0, math.pi * 0.5 - 0.18, 0.0), outline_thickness=0.004
    )

    # ---- C) CHUBBY-OVAL HEAD, EARS, RIGHT-EAR PENCIL & WINDSWEPT BOLT HAIR ----
    bm_head = bmesh.new()
    bmesh.ops.create_uvsphere(bm_head, u_segments=36, v_segments=24, radius=1.0)
    for v in bm_head.verts:
        # Chubby cheeks (wider slightly below equator, rounded chin)
        cheek_swell = 1.0 + 0.08 * max(0.0, -v.co.z) * (1.0 - v.co.z ** 2)
        v.co.x *= 0.226 * cheek_swell
        v.co.y *= 0.202 * cheek_swell
        v.co.z *= 0.206
    _create_bone_parented_mesh("Char_Head", bm_head, char_col, mat_skin, arm_obj, "Head", W(0.0, 0.0, 1.225), outline_thickness=0.0105)

    # Left (-X) & Right (+X) Ears
    for e_tag, ex in (("L", -0.228), ("R", 0.228)):
        bm_ear = bmesh.new()
        bmesh.ops.create_uvsphere(bm_ear, u_segments=16, v_segments=12, radius=1.0)
        for v in bm_ear.verts:
            v.co.x *= 0.032
            v.co.y *= 0.026
            v.co.z *= 0.044
        _create_bone_parented_mesh(f"Char_Ear_{e_tag}", bm_ear, char_col, mat_skin, arm_obj, "Head", W(ex, -0.005, 1.215), outline_thickness=0.006)

    # Yellow Wooden Pencil behind Right Ear (`Ear_Pencil.R` secondary motion bone!)
    p_rot = (0.35, -0.58, -0.25)
    bm_pbody = bmesh.new()
    bmesh.ops.create_cone(bm_pbody, cap_ends=True, cap_tris=False, segments=6, radius1=0.013, radius2=0.013, depth=0.115)
    _create_bone_parented_mesh("Char_EarPencil_Barrel", bm_pbody, char_col, mat_pencil_y, arm_obj, "Ear_Pencil.R", W(0.242, -0.015, 1.265), world_rot=p_rot, outline_thickness=0.0045)

    # Pencil Ferrule + Worn Pink Eraser at upper-outer end + Wood Cone Tip
    p_dir = Euler(p_rot, "XYZ").to_matrix() @ Vector((0.0, 0.0, 1.0))
    p_base = Vector(W(0.242, -0.015, 1.265))
    bm_fer = bmesh.new()
    bmesh.ops.create_cone(bm_fer, cap_ends=True, cap_tris=False, segments=12, radius1=0.0135, radius2=0.0135, depth=0.022)
    _create_bone_parented_mesh("Char_EarPencil_Ferrule", bm_fer, char_col, mat_buckle, arm_obj, "Ear_Pencil.R", tuple(p_base + p_dir * 0.066), world_rot=p_rot, outline_thickness=0.0035)
    bm_era = bmesh.new()
    bmesh.ops.create_uvsphere(bm_era, u_segments=12, v_segments=8, radius=0.0135)
    _create_bone_parented_mesh("Char_EarPencil_Eraser", bm_era, char_col, mat_eraser, arm_obj, "Ear_Pencil.R", tuple(p_base + p_dir * 0.082), world_rot=p_rot, outline_thickness=0.0035)
    bm_tip = bmesh.new()
    bmesh.ops.create_cone(bm_tip, cap_ends=True, cap_tris=False, segments=12, radius1=0.013, radius2=0.002, depth=0.034)
    _create_bone_parented_mesh("Char_EarPencil_WoodTip", bm_tip, char_col, mat_pencil_w, arm_obj, "Ear_Pencil.R", tuple(p_base - p_dir * 0.074), world_rot=(p_rot[0] + math.pi, -p_rot[1], p_rot[2]), outline_thickness=0.0035)

    # Messy Wavy Dark-Brown Hair Cap + Sideburns + Pointed Nape + Two Lightning-Bolt Tufts!
    bm_hcap = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hcap, u_segments=32, v_segments=20, radius=1.0)
    to_del = []
    for v in bm_hcap.verts:
        # Cut open the front face window (v.co.y > 0.18 and v.co.z < 0.36) so face is completely clear!
        if v.co.z < -0.38 or (v.co.y > 0.22 and v.co.z < 0.38):
            to_del.append(v)
        else:
            wave = 1.0 + 0.045 * math.sin(v.co.x * 9.0) * math.cos(v.co.y * 7.0)
            v.co.x *= 0.244 * wave
            v.co.y *= 0.220 * wave
            v.co.z *= 0.218
    bmesh.ops.delete(bm_hcap, geom=to_del, context="VERTS")
    bmesh.ops.solidify(bm_hcap, geom=list(bm_hcap.faces), thickness=0.022)
    _create_bone_parented_mesh("Char_Hair_Cap", bm_hcap, char_col, mat_hair, arm_obj, "Head", W(0.0, -0.012, 1.255), outline_thickness=0.009)

    # Wavy Side-Swept Forehead Bang Volume (tucked neatly above the brass goggles Z=1.41..1.45)
    for b_idx, (bx_h, by_h, bz_h, sx_h, sy_h, sz_h, rz_h) in enumerate([
        (-0.10, 0.08, 1.408, 0.115, 0.078, 0.048, 0.25),
        (0.02, 0.09, 1.418, 0.125, 0.080, 0.052, -0.10),
        (0.12, 0.07, 1.402, 0.110, 0.076, 0.046, -0.32),
        (-0.21, 0.03, 1.325, 0.058, 0.075, 0.055, 0.35),
        (0.21, 0.03, 1.325, 0.058, 0.075, 0.055, -0.35),
    ]):
        bm_b = bmesh.new()
        bmesh.ops.create_uvsphere(bm_b, u_segments=18, v_segments=12, radius=1.0)
        bmesh.ops.scale(bm_b, vec=(sx_h, sy_h, sz_h), verts=bm_b.verts)
        _create_bone_parented_mesh(f"Char_Hair_Puff_{b_idx}", bm_b, char_col, mat_hair, arm_obj, "Head", W(bx_h, by_h, bz_h), world_rot=(0.0, 0.0, rz_h), outline_thickness=0.007)

    # Pointed Windswept Nape Hair (`Hair_Nape` secondary bone)
    bm_nape = bmesh.new()
    bmesh.ops.create_cone(bm_nape, cap_ends=True, cap_tris=False, segments=12, radius1=0.085, radius2=0.008, depth=0.11)
    for v in bm_nape.verts:
        v.co.x *= 1.35
        v.co.y *= 0.55
    _create_bone_parented_mesh("Char_Hair_NapePoint", bm_nape, char_col, mat_hair, arm_obj, "Hair_Nape", W(-0.04, -0.21, 1.09), world_rot=(2.25, 0.25, 0.0), outline_thickness=0.007)

    # TWO ICONIC LIGHTNING-BOLT HAIR TUFTS (`Hair_Bolt_1` & `Hair_Bolt_2` secondary bones!)
    # Sculpted 3D zig-zag lightning silhouette leaning toward -X (viewer's right from front!)
    bolt_profiles = [
        ("Char_Hair_BoltMain", "Hair_Bolt_1", W(-0.01, 0.03, 1.41), 1.0, 0.0),
        ("Char_Hair_BoltSub", "Hair_Bolt_2", W(-0.065, 0.02, 1.395), 0.78, 0.14),
    ]
    bolt_pts_2d = [
        (0.028, 0.0),
        (-0.012, 0.085),
        (-0.052, 0.068),
        (-0.118, 0.168),  # Sharp lightning tip!
        (-0.058, 0.028),
        (-0.018, 0.042),
        (-0.010, -0.015),
    ]
    for b_name, b_bone, b_loc, b_sc, b_tilt in bolt_profiles:
        bm_bolt = bmesh.new()
        f_verts = [bm_bolt.verts.new((px * b_sc, -0.020 * b_sc, pz * b_sc)) for (px, pz) in bolt_pts_2d]
        b_verts = [bm_bolt.verts.new((px * b_sc, 0.020 * b_sc, pz * b_sc)) for (px, pz) in bolt_pts_2d]
        bm_bolt.faces.new(f_verts)
        bm_bolt.faces.new(list(reversed(b_verts)))
        nb = len(bolt_pts_2d)
        for i in range(nb):
            j = (i + 1) % nb
            bm_bolt.faces.new([f_verts[i], b_verts[i], b_verts[j], f_verts[j]])
        bmesh.ops.bevel(bm_bolt, geom=list(bm_bolt.edges), offset=0.004, segments=1, affect="EDGES")
        _create_bone_parented_mesh(b_name, bm_bolt, char_col, mat_hair, arm_obj, b_bone, b_loc, world_rot=(0.0, b_tilt, 0.0), outline_thickness=0.0075)

    # ---- D) FACIAL RIG: Honey Oval Eyes, Blinking Lids, Brows, Bandage Nose & Mouths ----
    for side_s, sx_sgn in (("L", -1.0), ("R", 1.0)):
        ex = sx_sgn * 0.063
        # White Sclera (vertical oval flat-top matching honey_oval)
        bm_sc = bmesh.new()
        bmesh.ops.create_uvsphere(bm_sc, u_segments=20, v_segments=14, radius=1.0)
        for v in bm_sc.verts:
            v.co.x *= 0.043
            v.co.y *= 0.012
            v.co.z *= 0.052
            if v.co.z > 0.036:
                v.co.z = 0.036 + (v.co.z - 0.036) * 0.25
        _create_bone_parented_mesh(f"Char_EyeSclera.{side_s}", bm_sc, char_col, mat_sclera, arm_obj, "Head", W(ex, 0.197, 1.235), world_rot=(0.0, 0.0, sx_sgn * -0.18), outline_thickness=0.0055)

        # Honey-Amber Iris + Dark Pupil + White Specular Glint (parented to `Eye_Iris.L/R`)
        bm_ir = bmesh.new()
        bmesh.ops.create_cone(bm_ir, cap_ends=True, cap_tris=False, segments=20, radius1=0.028, radius2=0.028, depth=0.008)
        for v in bm_ir.verts:
            v.co.z *= 1.15
        _create_bone_parented_mesh(f"Char_EyeIris.{side_s}", bm_ir, char_col, mat_iris, arm_obj, f"Eye_Iris.{side_s}", W(ex, 0.207, 1.233), world_rot=(math.pi * 0.5, 0.0, sx_sgn * -0.18), outline_thickness=0.0025)

        bm_pu = bmesh.new()
        bmesh.ops.create_cone(bm_pu, cap_ends=True, cap_tris=False, segments=16, radius1=0.015, radius2=0.015, depth=0.009)
        _create_bone_parented_mesh(f"Char_EyePupil.{side_s}", bm_pu, char_col, mat_pupil, arm_obj, f"Eye_Iris.{side_s}", W(ex, 0.210, 1.234), world_rot=(math.pi * 0.5, 0.0, sx_sgn * -0.18), outline_thickness=0.0)

        bm_gl = bmesh.new()
        bmesh.ops.create_uvsphere(bm_gl, u_segments=10, v_segments=8, radius=0.0085)
        _create_bone_parented_mesh(f"Char_EyeGlint.{side_s}", bm_gl, char_col, mat_glint, arm_obj, f"Eye_Iris.{side_s}", W(ex - 0.010, 0.214, 1.248), outline_thickness=0.0)

        # Blinking Eyelid Hood (parented to `Blink.L/R`, scaled Z=0.06 when open, Z=1.0 when blinking!)
        bm_lid = bmesh.new()
        bmesh.ops.create_uvsphere(bm_lid, u_segments=18, v_segments=12, radius=1.0)
        for v in bm_lid.verts:
            v.co.x *= 0.048
            v.co.y *= 0.018
            v.co.z *= 0.056
        _create_bone_parented_mesh(f"Char_Eyelid.{side_s}", bm_lid, char_col, mat_skin, arm_obj, f"Blink.{side_s}", W(ex, 0.203, 1.238), world_rot=(0.0, 0.0, sx_sgn * -0.18), outline_thickness=0.005)
        pbones[f"Blink.{side_s}"].scale = (1.0, 1.0, 0.05)  # Open by default!

        # Thick Expressive Arched Eyebrow (`Brow.L/R`)
        bm_br = bmesh.new()
        bmesh.ops.create_cube(bm_br, size=1.0)
        bmesh.ops.scale(bm_br, vec=(0.072, 0.020, 0.021), verts=bm_br.verts)
        bmesh.ops.bevel(bm_br, geom=list(bm_br.edges), offset=0.007, segments=2, affect="EDGES")
        _create_bone_parented_mesh(f"Char_Eyebrow.{side_s}", bm_br, char_col, mat_hair, arm_obj, f"Brow.{side_s}", W(ex, 0.206, 1.300), world_rot=(0.0, sx_sgn * 0.08, sx_sgn * -0.18), outline_thickness=0.0035)

    # Upturned Tiny Nose + Cream Nose Bandage + Cheek Oil Smudge & Freckles
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=14, v_segments=10, radius=1.0)
    bmesh.ops.scale(bm_nose, vec=(0.018, 0.024, 0.015), verts=bm_nose.verts)
    _create_bone_parented_mesh("Char_Nose", bm_nose, char_col, mat_skin, arm_obj, "Head", W(0.0, 0.214, 1.192), outline_thickness=0.004)

    bm_band = bmesh.new()
    bmesh.ops.create_cube(bm_band, size=1.0)
    bmesh.ops.scale(bm_band, vec=(0.074, 0.012, 0.026), verts=bm_band.verts)
    bmesh.ops.bevel(bm_band, geom=list(bm_band.edges), offset=0.006, segments=2, affect="EDGES")
    _create_bone_parented_mesh("Char_NoseBandage", bm_band, char_col, mat_bandage, arm_obj, "Head", W(0.003, 0.216, 1.210), world_rot=(0.0, -0.08, 0.0), outline_thickness=0.0035)

    # Oil Smudge & 2 Freckles on Left Cheekbone (-X)
    bm_oil = bmesh.new()
    bmesh.ops.create_cube(bm_oil, size=1.0)
    bmesh.ops.scale(bm_oil, vec=(0.042, 0.006, 0.010), verts=bm_oil.verts)
    bmesh.ops.bevel(bm_oil, geom=list(bm_oil.edges), offset=0.003, segments=1, affect="EDGES")
    _create_bone_parented_mesh("Char_CheekOilSmudge", bm_oil, char_col, mat_smudge, arm_obj, "Head", W(-0.092, 0.186, 1.168), world_rot=(0.0, 0.22, 0.35), outline_thickness=0.0)
    for f_i, (fx, fz) in enumerate(((-0.076, 1.182), (-0.092, 1.186))):
        bm_frk = bmesh.new()
        bmesh.ops.create_uvsphere(bm_frk, u_segments=8, v_segments=6, radius=0.0045)
        _create_bone_parented_mesh(f"Char_Freckle_{f_i}", bm_frk, char_col, mat_belt, arm_obj, "Head", W(fx, 0.194, fz), outline_thickness=0.0)

    # Mouth State 1 (`Mouth_Smile_Bone`): Wide Confident Gap-Tooth Grin!
    bm_ms = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ms, u_segments=20, v_segments=12, radius=1.0)
    for v in bm_ms.verts:
        v.co.x *= 0.068
        v.co.y *= 0.012
        v.co.z *= 0.028
        if v.co.z > 0.006:
            v.co.z = 0.006 + v.co.x * (-0.12)  # Confident tilted smirk top line!
    _create_bone_parented_mesh("Char_Mouth_SmileBg", bm_ms, char_col, mat_mouth_bg, arm_obj, "Mouth_Smile_Bone", W(-0.004, 0.200, 1.132), world_rot=(0.0, 0.08, 0.0), outline_thickness=0.0045)

    # Two White Upper Teeth Blocks with the Signature Front Incisor Gap!
    for t_tag, tx_m in (("L", -0.028), ("R", 0.028)):
        bm_th = bmesh.new()
        bmesh.ops.create_cube(bm_th, size=1.0)
        bmesh.ops.scale(bm_th, vec=(0.044, 0.014, 0.014), verts=bm_th.verts)
        bmesh.ops.bevel(bm_th, geom=list(bm_th.edges), offset=0.002, segments=1, affect="EDGES")
        _create_bone_parented_mesh(f"Char_Mouth_Teeth_{t_tag}", bm_th, char_col, mat_sclera, arm_obj, "Mouth_Smile_Bone", W(tx_m - 0.004, 0.206, 1.138), world_rot=(0.0, 0.08, 0.0), outline_thickness=0.0015)

    bm_tg = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tg, u_segments=12, v_segments=8, radius=1.0)
    bmesh.ops.scale(bm_tg, vec=(0.032, 0.010, 0.010), verts=bm_tg.verts)
    _create_bone_parented_mesh("Char_Mouth_Tongue", bm_tg, char_col, mat_tongue, arm_obj, "Mouth_Smile_Bone", W(-0.004, 0.205, 1.118), outline_thickness=0.0)

    # Mouth State 2 (`Mouth_Focus_Bone`): Serious Concentrated Determined Line during Welding!
    bm_mf = bmesh.new()
    bmesh.ops.create_cube(bm_mf, size=1.0)
    bmesh.ops.scale(bm_mf, vec=(0.056, 0.012, 0.009), verts=bm_mf.verts)
    bmesh.ops.bevel(bm_mf, geom=list(bm_mf.edges), offset=0.003, segments=1, affect="EDGES")
    _create_bone_parented_mesh("Char_Mouth_Focused", bm_mf, char_col, mat_ink_outline := get_ink_outline_material(), arm_obj, "Mouth_Focus_Bone", W(0.0, 0.205, 1.132), world_rot=(0.0, -0.06, 0.0), outline_thickness=0.0)
    pbones["Mouth_Focus_Bone"].scale = (0.001, 0.001, 0.001)  # Hidden initially

    # ---- E) ARTICULATED BRASS WELDING GOGGLES RIG (`Goggles_Ctrl` & `Goggles_Loupe`) ----
    # Black Elastic Strap around Head
    bm_strap = _make_torus_bmesh(major_radius=0.236, minor_radius=0.018, major_segments=36, minor_segments=12, scale_y=0.89)
    _create_bone_parented_mesh(
        "Char_Goggles_Strap", bm_strap, char_col, mat_strap, arm_obj, "Goggles_Ctrl",
        W(0.0, -0.008, 1.355), world_rot=(-0.10, -0.08, 0.0), outline_thickness=0.005
    )

    # Asymmetric Brass Cups: Left (-X) is LARGER (r=0.058), Right (+X) is SMALLER (r=0.045)
    # Positioned clearly proud of the forehead (+Y = 0.208) with thick brass torus bezels!
    for cup_tag, cx_g, r_cup in (("LeftLarge", -0.066, 0.058), ("RightSmall", 0.064, 0.045)):
        cz_g = 1.356 - (0.006 if cx_g > 0 else 0.0)
        c_rot = (math.pi * 0.5 - 0.10, 0.0, (-0.16 if cx_g > 0 else 0.16))

        bm_cup = bmesh.new()
        bmesh.ops.create_cone(bm_cup, cap_ends=True, cap_tris=False, segments=24, radius1=r_cup, radius2=r_cup * 0.95, depth=0.052)
        _create_bone_parented_mesh(f"Char_Goggles_Cup_{cup_tag}", bm_cup, char_col, mat_strap, arm_obj, "Goggles_Ctrl", W(cx_g, 0.202, cz_g), world_rot=c_rot, outline_thickness=0.0055)

        # Prominent Gleaming Brass Outer Rim Bezel Torus!
        bm_bez = _make_torus_bmesh(major_radius=r_cup * 0.92, minor_radius=0.0105, major_segments=26, minor_segments=10)
        _create_bone_parented_mesh(f"Char_Goggles_Bezel_{cup_tag}", bm_bez, char_col, mat_brass, arm_obj, "Goggles_Ctrl", W(cx_g, 0.226, cz_g + 0.002), world_rot=c_rot, outline_thickness=0.0045)

        bm_lns = bmesh.new()
        bmesh.ops.create_cone(bm_lns, cap_ends=True, cap_tris=False, segments=22, radius1=r_cup * 0.82, radius2=r_cup * 0.82, depth=0.012)
        _create_bone_parented_mesh(f"Char_Goggles_Lens_{cup_tag}", bm_lns, char_col, mat_lens, arm_obj, "Goggles_Ctrl", W(cx_g, 0.224, cz_g + 0.002), world_rot=c_rot, outline_thickness=0.0)

        # Crisp Specular Glint on Welding Lens
        bm_lg = bmesh.new()
        bmesh.ops.create_uvsphere(bm_lg, u_segments=10, v_segments=8, radius=r_cup * 0.18)
        _create_bone_parented_mesh(f"Char_Goggles_Glint_{cup_tag}", bm_lg, char_col, mat_glint, arm_obj, "Goggles_Ctrl", W(cx_g - r_cup * 0.24, 0.233, cz_g + r_cup * 0.24), outline_thickness=0.0)

    # Center Nose Bridge Link between Cups
    bm_brg = bmesh.new()
    bmesh.ops.create_cube(bm_brg, size=1.0)
    bmesh.ops.scale(bm_brg, vec=(0.042, 0.018, 0.020), verts=bm_brg.verts)
    _create_bone_parented_mesh("Char_Goggles_Bridge", bm_brg, char_col, mat_strap, arm_obj, "Goggles_Ctrl", W(0.0, 0.214, 1.356), outline_thickness=0.004)

    # Hinged Flip-Out Magnifying Loupe on Right (+X) Outer Cup (`Goggles_Loupe` bone!)
    bm_larm = bmesh.new()
    bmesh.ops.create_cube(bm_larm, size=1.0)
    bmesh.ops.scale(bm_larm, vec=(0.036, 0.010, 0.010), verts=bm_larm.verts)
    _create_bone_parented_mesh("Char_Goggles_LoupeArm", bm_larm, char_col, mat_brass, arm_obj, "Goggles_Loupe", W(0.125, 0.202, 1.350), outline_thickness=0.0035)

    bm_lring = bmesh.new()
    bmesh.ops.create_cone(bm_lring, cap_ends=True, cap_tris=False, segments=18, radius1=0.026, radius2=0.026, depth=0.014)
    _create_bone_parented_mesh("Char_Goggles_LoupeFrame", bm_lring, char_col, mat_brass, arm_obj, "Goggles_Loupe", W(0.155, 0.198, 1.354), world_rot=(math.pi * 0.5, 0.0, -0.45), outline_thickness=0.0045)

    bm_lgl = bmesh.new()
    bmesh.ops.create_cone(bm_lgl, cap_ends=True, cap_tris=False, segments=16, radius1=0.020, radius2=0.020, depth=0.016)
    _create_bone_parented_mesh("Char_Goggles_LoupeGlass", bm_lgl, char_col, mat_loupe, arm_obj, "Goggles_Loupe", W(0.155, 0.198, 1.354), world_rot=(math.pi * 0.5, 0.0, -0.45), outline_thickness=0.0)

    # ---- F) SKINNED NOODLE ARMS, SLEEVES, HANDS, LEGS & BOOTS ----
    # Short Ivory T-Shirt Sleeves on UpperArm.L / UpperArm.R
    for s_tag, sh_p, elb_p in (("L", sh_L, elb_L), ("R", sh_R, elb_R)):
        v_dir = (Vector(elb_p) - Vector(sh_p)).normalized()
        sl_mid = Vector(sh_p) + v_dir * 0.048
        rot_q = Vector((0.0, 0.0, -1.0)).rotation_difference(v_dir).to_euler()
        bm_sl = bmesh.new()
        bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=20, radius1=0.036, radius2=0.048, depth=0.095)
        _create_bone_parented_mesh(f"Char_Sleeve.{s_tag}", bm_sl, char_col, mat_tee, arm_obj, f"UpperArm.{s_tag}", W(sl_mid.x, sl_mid.y, sl_mid.z), world_rot=tuple(rot_q), outline_thickness=0.0065)

    # Skinned Noodle Arms (`UpperArm` + `Forearm`)
    _create_skinned_noodle_tube(
        "Char_Arm_Noodle.L", Vector(W(*sh_L)), Vector(W(*elb_L)), Vector(W(*hnd_L)),
        radius=0.0155, col=char_col, mat=mat_limb, arm_obj=arm_obj,
        bone_upper="UpperArm.L", bone_lower="Forearm.L", outline_thickness=0.0055
    )
    _create_skinned_noodle_tube(
        "Char_Arm_Noodle.R", Vector(W(*sh_R)), Vector(W(*elb_R)), Vector(W(*hnd_R)),
        radius=0.0155, col=char_col, mat=mat_limb, arm_obj=arm_obj,
        bone_upper="UpperArm.R", bone_lower="Forearm.R", outline_thickness=0.0055
    )

    # Rounded Cartoon Mitts / Hands (`Hand.L`, `Hand.R`)
    for s_tag, hp in (("L", hnd_L), ("R", hnd_R)):
        bm_h = bmesh.new()
        bmesh.ops.create_uvsphere(bm_h, u_segments=16, v_segments=12, radius=1.0)
        bmesh.ops.scale(bm_h, vec=(0.028, 0.034, 0.026), verts=bm_h.verts)
        _create_bone_parented_mesh(f"Char_HandMitt.{s_tag}", bm_h, char_col, mat_limb, arm_obj, f"Hand.{s_tag}", W(hp[0], hp[1] + 0.022, hp[2]), outline_thickness=0.005)

    # Skinned Noodle Legs (`Thigh` + `Shin`)
    _create_skinned_noodle_tube(
        "Char_Leg_Noodle.L", Vector(W(*hip_L)), Vector(W(*knee_L)), Vector(W(*ank_L)),
        radius=0.0165, col=char_col, mat=mat_limb, arm_obj=arm_obj,
        bone_upper="Thigh.L", bone_lower="Shin.L", outline_thickness=0.0055
    )
    _create_skinned_noodle_tube(
        "Char_Leg_Noodle.R", Vector(W(*hip_R)), Vector(W(*knee_R)), Vector(W(*ank_R)),
        radius=0.0165, col=char_col, mat=mat_limb, arm_obj=arm_obj,
        bone_upper="Thigh.R", bone_lower="Shin.R", outline_thickness=0.0055
    )

    # Stylized Flat Rounded Feet (`Foot.L`, `Foot.R`)
    for s_tag, ap, yaw_f in (("L", ank_L, 0.22), ("R", ank_R, -0.22)):
        bm_ft = bmesh.new()
        bmesh.ops.create_cube(bm_ft, size=1.0)
        bmesh.ops.scale(bm_ft, vec=(0.044, 0.115, 0.032), verts=bm_ft.verts)
        bmesh.ops.bevel(bm_ft, geom=list(bm_ft.edges), offset=0.012, segments=2, affect="EDGES")
        _create_bone_parented_mesh(f"Char_Foot.{s_tag}", bm_ft, char_col, mat_limb, arm_obj, f"Foot.{s_tag}", W(ap[0], ap[1] + 0.038, ap[2] - 0.014), world_rot=(0.0, 0.0, yaw_f), outline_thickness=0.005)

    # ==========================================================================
    # 5. PROP INTERACTION CONSTRAINT: BIND WELDING TORCH TO `Hand.R`!
    # ==========================================================================
    # Because `Hand.R` points +Y with roll=0, setting `inverse_matrix = Identity`
    # places `torch_obj.location = (0, 0.028, 0)` directly inside `Hand.R`'s palm!
    # In `Hand.R` local coordinates:
    #   Palm center = (0.0, 0.028, 0.0)
    #   `Empty_TorchTip` = (0.0, 0.028 + 0.208, -0.045) = (0.0, 0.236, -0.045)!
    if torch_obj is not None:
        torch_obj.location = (0.0, 0.028, 0.0)
        torch_obj.rotation_euler = (0.0, 0.0, 0.0)
        con = torch_obj.constraints.new(type="CHILD_OF")
        con.name = "ChildOf_RightHand"
        con.target = arm_obj
        con.subtarget = "Hand.R"
        con.inverse_matrix = Matrix.Identity(4)
        con.influence = 1.0

    bpy.context.view_layer.update()

    return {
        "armature": arm_obj,
        "collection": char_col,
        "source_config": src_cfg,
        "torch_local_tip_in_hand": Vector((0.0, 0.236, -0.045)),
    }
