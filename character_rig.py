"""
character_rig.py — Stage 3 (Blender Native 2.5D Dynamic Billboard):
Replaces all manual 3D character meshes with a single proportional 2.5D Billboard Plane
(`BASE_WIDTH : BASE_HEIGHT`, origin at Z=0 soles of feet on `Empty_Mechanic`) using:
  - `Locked Track` constraint (`Up Axis = Z`) facing the active camera
  - Shadeless `Emission (Strength=1.0)` + `Transparent BSDF` guided by PNG Alpha
    loading the rendered PNG sequence `output/char_frames/char_XXXX.png` so 100% of
    the original MekanikMudaCharacter 2.5D style, bold outlines, vest textures, and
    360° turnaround fidelity remain completely intact!
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

import bmesh
import bpy

from config import (
    CHAR_BILLBOARD_HEIGHT,
    CHAR_BILLBOARD_WIDTH,
    CHAR_FRAMES_DIR,
    CHAR_Z_BOTTOM_OFFSET,
    FRAME_END,
    FRAME_START,
    MECHANIC_BASE_YAW_DEG,
    MECHANIC_ROOT_POS,
)
from env_props import get_or_create_collection, link_exclusively


def _create_shadeless_25d_sequence_material(
    char_frames_dir: Path,
    name: str = "Mat_Char25D_Billboard",
) -> bpy.types.Material:
    """
    Create a 100% Shadeless 2.5D Sprite Material:
      Image Texture (PNG Sequence) -> Color -> Emission (Strength = 1.0)
                                   -> Alpha -> Mix Shader (Transparent BSDF, Emission)
    Zero 3D specular reflection, zero lighting distortion, crisp alpha cutout!
    """
    png_files: List[Path] = sorted(char_frames_dir.glob("char_*.png"))
    if not png_files:
        raise FileNotFoundError(
            f"No rendered 2.5D character PNGs found in {char_frames_dir}! "
            "Run export_camera_sync.py and render_char_25d.py before main.py."
        )

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "CLIP"
        except Exception:
            pass
    if hasattr(mat, "shadow_method"):
        try:
            mat.shadow_method = "CLIP"
        except Exception:
            pass

    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (540, 0)

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-360, 80)
    tex.interpolation = "Linear"
    tex.extension = "CLIP"

    img = bpy.data.images.load(str(png_files[0].resolve()))
    img.source = "SEQUENCE"
    if hasattr(img, "alpha_mode"):
        img.alpha_mode = "STRAIGHT"
    tex.image = img

    iuser = tex.image_user
    iuser.frame_duration = FRAME_END
    iuser.frame_start = FRAME_START
    iuser.frame_offset = 0
    iuser.use_auto_refresh = True
    iuser.use_cyclic = False

    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    transp.location = (40, -100)

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (40, 100)
    emis.inputs["Strength"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], emis.inputs["Color"])

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.location = (300, 20)
    nt.links.new(tex.outputs["Alpha"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(emis.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

    return mat


def build_mechanic_character(camera_obj: bpy.types.Object) -> Dict[str, Any]:
    """
    Build `Empty_Mechanic` + proportional 2.5D `Char_Billboard` plane with origin at Z=0
    soles of feet and `Locked Track` (Up Axis = Z) facing `camera_obj`.
    """
    char_col = get_or_create_collection("Col_Mechanic_Character")

    # 1) Root Anchor `Empty_Mechanic` at Z=0 floor contact
    mech_empty = bpy.data.objects.new("Empty_Mechanic", None)
    mech_empty.empty_display_type = "SINGLE_ARROW"
    mech_empty.empty_display_size = 0.35
    mech_empty.location = MECHANIC_ROOT_POS
    link_exclusively(mech_empty, char_col)

    yaw_keys = [
        (1,   math.radians(MECHANIC_BASE_YAW_DEG)),
        (85,  math.radians(MECHANIC_BASE_YAW_DEG + 4.0)),
        (113, math.radians(32.0)),
        (155, math.radians(28.0)),
        (203, math.radians(22.0)),
        (232, math.radians(56.0)),
        (240, math.radians(58.0)),
        (264, math.radians(56.0)),
    ]
    for f, rz in yaw_keys:
        mech_empty.rotation_euler = (0.0, 0.0, rz)
        mech_empty.keyframe_insert(data_path="rotation_euler", frame=f)

    # 2) Proportional 2.5D Plane (`BASE_WIDTH : BASE_HEIGHT`, origin at Z=0 soles of feet!)
    half_w = CHAR_BILLBOARD_WIDTH * 0.5
    z_bot = CHAR_Z_BOTTOM_OFFSET
    z_top = z_bot + CHAR_BILLBOARD_HEIGHT

    bm = bmesh.new()
    # Face normal points along -Y so `TRACK_NEGATIVE_Y` + `LOCK_Z` faces camera upright:
    # Viewer's Left = -X (u=0), Viewer's Right = +X (u=1), Bottom = z_bot (v=0), Top = z_top (v=1)
    v0 = bm.verts.new((-half_w, 0.0, z_bot))
    v1 = bm.verts.new((half_w, 0.0, z_bot))
    v2 = bm.verts.new((half_w, 0.0, z_top))
    v3 = bm.verts.new((-half_w, 0.0, z_top))
    face = bm.faces.new([v0, v1, v2, v3])

    uv_layer = bm.loops.layers.uv.new("UVMap")
    uv_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for loop, uv in zip(face.loops, uv_coords):
        loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new("Char_Billboard_Mesh")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    mat_25d = _create_shadeless_25d_sequence_material(CHAR_FRAMES_DIR)
    billboard = bpy.data.objects.new("Char_Billboard", mesh)
    billboard.data.materials.append(mat_25d)
    billboard.parent = mech_empty
    billboard.location = (0.0, 0.0, 0.0)
    link_exclusively(billboard, char_col)

    # 3) Locked Track Constraint: rotates strictly around Z (Up Axis = Z) facing active camera!
    lt = billboard.constraints.new(type="LOCKED_TRACK")
    lt.name = "Billboard_FaceCamera"
    lt.target = camera_obj
    lt.track_axis = "TRACK_NEGATIVE_Y"
    lt.lock_axis = "LOCK_Z"

    return {
        "empty_mechanic": mech_empty,
        "billboard": billboard,
        "material": mat_25d,
        "collection": char_col,
    }
