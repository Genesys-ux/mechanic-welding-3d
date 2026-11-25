"""
shaders.py — Rich 3D Cel-Shade Material Library, AO + Procedural Surface Detail,
GLB Reference Material Converter, Decal Shaders & Inverted-Hull Bold Outlines.
Compatible with Blender 4.2+ LTS (EEVEE Next) and Standard View Transform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import bpy

from config import PALETTE_HEX, hex_to_rgba


def _scale_rgba(
    rgba: Tuple[float, float, float, float],
    factor: float,
    tint_white: float = 0.0,
) -> Tuple[float, float, float, float]:
    # Clamp strictly <= 0.96 linear so non-emissive cel surfaces never trigger HDR bloom
    r = min(0.96, max(0.0, rgba[0] * factor + tint_white))
    g = min(0.96, max(0.0, rgba[1] * factor + tint_white))
    b = min(0.96, max(0.0, rgba[2] * factor + tint_white))
    return (r, g, b, rgba[3])


def get_ink_outline_material(
    name: str = "Mat_Ink_Outline",
    hex_color: str = PALETTE_HEX["ink_outline"],
) -> bpy.types.Material:
    """
    Create or retrieve the bold cartoon Inverted-Hull outline material (#201720).
    Uses Light Path -> Is Shadow Ray -> Transparent BSDF so the flipped outer shell
    NEVER casts self-shadows onto the inner cel-shaded mesh.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    if hasattr(mat, "use_backface_culling_shadow"):
        mat.use_backface_culling_shadow = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "CLIP"
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
    out.location = (420, 0)

    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (-180, 180)

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (-180, -20)
    emis.inputs["Color"].default_value = hex_to_rgba(hex_color)
    emis.inputs["Strength"].default_value = 1.0

    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    transp.location = (-180, -160)

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.location = (160, 0)

    nt.links.new(lp.outputs["Is Shadow Ray"], mix_sh.inputs["Fac"])
    nt.links.new(emis.outputs["Emission"], mix_sh.inputs[1])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

    return mat


def apply_cel_outline(
    obj: bpy.types.Object,
    thickness: float = 0.0065,
    outline_mat: Optional[bpy.types.Material] = None,
    use_even_offset: bool = False,
) -> Optional[bpy.types.Modifier]:
    """Attach an Inverted-Hull Solidify modifier with flipped normals and bold ink outline."""
    if obj.type != "MESH" or obj.data is None:
        return None

    ink_mat = outline_mat or get_ink_outline_material()

    if len(obj.data.materials) == 0:
        obj.data.materials.append(get_cel_material("Mat_Default_Cel", "#CCCCCC"))

    mat_idx = -1
    for i, m in enumerate(obj.data.materials):
        if m == ink_mat:
            mat_idx = i
            break
    if mat_idx < 0:
        obj.data.materials.append(ink_mat)
        mat_idx = len(obj.data.materials) - 1

    mod_name = "CelOutline"
    mod = obj.modifiers.get(mod_name)
    if mod is None:
        mod = obj.modifiers.new(name=mod_name, type="SOLIDIFY")

    mod.thickness = -abs(thickness)
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.use_even_offset = use_even_offset
    mod.material_offset = mat_idx
    return mod


def _build_ao_factor_socket(nt: bpy.types.NodeTree, loc_x: float, loc_y: float, strength: float = 0.45):
    """Create an Ambient Occlusion crevice darkening factor socket (1.0 - strength .. 1.0)."""
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 2
    ao.only_local = False
    ao.location = (loc_x, loc_y)
    ao.inputs["Distance"].default_value = 0.42

    ao_ramp = nt.nodes.new("ShaderNodeValToRGB")
    ao_ramp.location = (loc_x + 200, loc_y)
    ao_ramp.color_ramp.interpolation = "EASE"
    ao_ramp.color_ramp.elements[0].position = 0.12
    dark = max(0.25, 1.0 - strength)
    ao_ramp.color_ramp.elements[0].color = (dark, dark * 0.96, dark * 1.02, 1.0)
    ao_ramp.color_ramp.elements[1].position = 0.78
    ao_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(ao.outputs["AO"], ao_ramp.inputs["Fac"])
    return ao_ramp.outputs["Color"]


def _build_procedural_surface_detail(
    nt: bpy.types.NodeTree,
    base_rgba: Tuple[float, float, float, float],
    surface_type: str,
    loc_x: float = -760,
    loc_y: float = -260,
):
    """
    Generate rich procedural surface variation (brick courses, concrete grain & cracks,
    brushed metal wear, wood planks, car paint flake) so 3D surfaces never look like flat plastic!
    """
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (loc_x - 220, loc_y)

    if surface_type == "brick":
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.location = (loc_x, loc_y)
        brick.offset = 0.5
        brick.squash = 1.0
        brick.inputs["Scale"].default_value = 4.2
        brick.inputs["Mortar Size"].default_value = 0.022
        brick.inputs["Mortar Smooth"].default_value = 0.15
        brick.inputs["Bias"].default_value = -0.15
        brick.inputs["Brick Width"].default_value = 0.52
        brick.inputs["Row Height"].default_value = 0.24
        brick.inputs["Color1"].default_value = _scale_rgba(base_rgba, 1.10)
        brick.inputs["Color2"].default_value = _scale_rgba(base_rgba, 0.80)
        brick.inputs["Mortar"].default_value = _scale_rgba(base_rgba, 0.45)
        nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])

        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.location = (loc_x, loc_y - 240)
        noise.inputs["Scale"].default_value = 6.5
        noise.inputs["Detail"].default_value = 5.0
        noise.inputs["Roughness"].default_value = 0.65
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        grime = nt.nodes.new("ShaderNodeMixRGB")
        grime.blend_type = "MULTIPLY"
        grime.location = (loc_x + 240, loc_y)
        grime.inputs["Fac"].default_value = 0.28
        nt.links.new(brick.outputs["Color"], grime.inputs[1])
        nt.links.new(noise.outputs["Fac"], grime.inputs[2])
        return grime.outputs["Color"]

    if surface_type == "concrete":
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.location = (loc_x, loc_y)
        noise.inputs["Scale"].default_value = 5.5
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.72
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        # Subtle Voronoi hairline concrete cracks
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.location = (loc_x, loc_y - 220)
        vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = 1.65
        nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])

        crack_ramp = nt.nodes.new("ShaderNodeValToRGB")
        crack_ramp.location = (loc_x + 200, loc_y - 220)
        crack_ramp.color_ramp.interpolation = "CONSTANT"
        crack_ramp.color_ramp.elements[0].position = 0.0
        crack_ramp.color_ramp.elements[0].color = _scale_rgba(base_rgba, 0.50)
        crack_ramp.color_ramp.elements[1].position = 0.016
        crack_ramp.color_ramp.elements[1].color = _scale_rgba(base_rgba, 1.0)
        nt.links.new(vor.outputs["Distance"], crack_ramp.inputs["Fac"])

        grain_ramp = nt.nodes.new("ShaderNodeValToRGB")
        grain_ramp.location = (loc_x + 200, loc_y)
        grain_ramp.color_ramp.elements[0].position = 0.28
        grain_ramp.color_ramp.elements[0].color = (0.82, 0.82, 0.84, 1.0)
        grain_ramp.color_ramp.elements[1].position = 0.75
        grain_ramp.color_ramp.elements[1].color = (1.08, 1.08, 1.06, 1.0)
        nt.links.new(noise.outputs["Fac"], grain_ramp.inputs["Fac"])

        mul = nt.nodes.new("ShaderNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        mul.location = (loc_x + 460, loc_y - 60)
        mul.inputs["Fac"].default_value = 1.0
        nt.links.new(crack_ramp.outputs["Color"], mul.inputs[1])
        nt.links.new(grain_ramp.outputs["Color"], mul.inputs[2])
        return mul.outputs["Color"]

    if surface_type == "wood":
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.location = (loc_x, loc_y)
        wave.wave_type = "BANDS"
        wave.bands_direction = "Y"
        wave.inputs["Scale"].default_value = 3.6
        wave.inputs["Distortion"].default_value = 4.8
        wave.inputs["Detail"].default_value = 4.0
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])

        w_ramp = nt.nodes.new("ShaderNodeValToRGB")
        w_ramp.location = (loc_x + 220, loc_y)
        w_ramp.color_ramp.interpolation = "CONSTANT"
        w_ramp.color_ramp.elements[0].position = 0.0
        w_ramp.color_ramp.elements[0].color = _scale_rgba(base_rgba, 0.78)
        w_ramp.color_ramp.elements[1].position = 0.42
        w_ramp.color_ramp.elements[1].color = _scale_rgba(base_rgba, 1.06)
        nt.links.new(wave.outputs["Fac"], w_ramp.inputs["Fac"])
        return w_ramp.outputs["Color"]

    # Default subtle workshop wear / brushed metal / painted surface micro-variation
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (loc_x, loc_y)
    noise.inputs["Scale"].default_value = 14.0 if surface_type in ("metal", "chrome") else 8.5
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    n_ramp = nt.nodes.new("ShaderNodeValToRGB")
    n_ramp.location = (loc_x + 200, loc_y)
    n_ramp.color_ramp.elements[0].position = 0.25
    n_ramp.color_ramp.elements[0].color = _scale_rgba(base_rgba, 0.90)
    n_ramp.color_ramp.elements[1].position = 0.78
    n_ramp.color_ramp.elements[1].color = _scale_rgba(base_rgba, 1.06)
    nt.links.new(noise.outputs["Fac"], n_ramp.inputs["Fac"])
    return n_ramp.outputs["Color"]


def _infer_surface_type(mat_name: str, spec_strength: float) -> str:
    low = mat_name.lower()
    if "brick" in low:
        return "brick"
    if "concrete" in low or "floor" in low or "dado" in low or "wall_lower" in low:
        return "concrete"
    if "wood" in low:
        return "wood"
    if "chrome" in low or "rim" in low or "steel" in low or "brass" in low or spec_strength >= 0.65:
        return "chrome"
    if spec_strength >= 0.35:
        return "metal"
    return "painted"


def get_cel_material(
    name: str,
    hex_color: str,
    shadow_factor: float = 0.42,
    mid_factor: float = 0.85,
    lit_factor: float = 0.98,
    spec_strength: float = 0.0,
    rim_strength: float = 0.08,
    roughness: float = 0.48,
    colored_light_mix: float = 0.50,
    surface_type: Optional[str] = None,
    ao_strength: float = 0.42,
) -> bpy.types.Material:
    """
    Rich 3-Band Cel-Shade Material with:
      - `Principled BSDF -> Shader to RGB -> Constant ColorRamp`
      - `Ambient Occlusion` crevice dirt/shadowing
      - Procedural surface detail (brick, concrete cracks/grain, wood planks, brushed metal)
      - Selective Welding-Arc Cyan-Blue Bounce (`Blue - Red * 0.88`)
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    base_rgba = hex_to_rgba(hex_color)
    surf = surface_type or _infer_surface_type(name, spec_strength)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1320, 0)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-820, 220)
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.22 if surf == "chrome" else roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.65 if spec_strength > 0 else 0.12
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.65 if spec_strength > 0 else 0.12

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-540, 220)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    # 1) Stepped Cel Lighting Multiplier Ramp (Shadow / Mid / Lit / Metallic Glint)
    shade_ramp = nt.nodes.new("ShaderNodeValToRGB")
    shade_ramp.location = (-240, 260)
    shade_ramp.color_ramp.interpolation = "CONSTANT"
    elems = shade_ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = (shadow_factor, shadow_factor * 0.98, shadow_factor * 1.04, 1.0)
    elems[1].position = 0.14
    elems[1].color = (mid_factor, mid_factor, mid_factor, 1.0)
    e_hi = elems.new(0.48)
    e_hi.color = (lit_factor, lit_factor, lit_factor, 1.0)
    if spec_strength > 0.10 or surf == "chrome":
        e_sp = elems.new(0.78)
        sp_b = min(1.28, lit_factor + 0.26 * max(spec_strength, 0.5))
        e_sp.color = (sp_b, sp_b, sp_b, 1.0)
    nt.links.new(s2rgb.outputs["Color"], shade_ramp.inputs["Fac"])

    # 2) Procedural Surface Color Texture (Brick / Concrete / Wood / Brushed Metal)
    surf_col_sock = _build_procedural_surface_detail(nt, base_rgba, surf, loc_x=-780, loc_y=-160)

    cel_base = nt.nodes.new("ShaderNodeMixRGB")
    cel_base.blend_type = "MULTIPLY"
    cel_base.use_clamp = True
    cel_base.location = (160, 140)
    cel_base.inputs["Fac"].default_value = 1.0
    nt.links.new(surf_col_sock, cel_base.inputs[1])
    nt.links.new(shade_ramp.outputs["Color"], cel_base.inputs[2])

    # Add crisp white metallic specular glint on chrome/metals
    if surf == "chrome" or spec_strength >= 0.6:
        glint_ramp = nt.nodes.new("ShaderNodeValToRGB")
        glint_ramp.location = (-120, 440)
        glint_ramp.color_ramp.interpolation = "CONSTANT"
        glint_ramp.color_ramp.elements[0].position = 0.0
        glint_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        glint_ramp.color_ramp.elements[1].position = 0.82
        g_amt = 0.22 * max(spec_strength, 0.65)
        glint_ramp.color_ramp.elements[1].color = (g_amt, g_amt * 1.02, g_amt * 1.06, 1.0)
        nt.links.new(s2rgb.outputs["Color"], glint_ramp.inputs["Fac"])

        add_sp = nt.nodes.new("ShaderNodeMixRGB")
        add_sp.blend_type = "ADD"
        add_sp.use_clamp = True
        add_sp.location = (360, 220)
        add_sp.inputs["Fac"].default_value = 1.0
        nt.links.new(cel_base.outputs["Color"], add_sp.inputs[1])
        nt.links.new(glint_ramp.outputs["Color"], add_sp.inputs[2])
        shaded_sock = add_sp.outputs["Color"]
    else:
        shaded_sock = cel_base.outputs["Color"]

    # 3) Multiply Ambient Occlusion for deep crevice & contact dirt
    if ao_strength > 0.02:
        ao_sock = _build_ao_factor_socket(nt, loc_x=80, loc_y=-140, strength=ao_strength)
        mul_ao = nt.nodes.new("ShaderNodeMixRGB")
        mul_ao.blend_type = "MULTIPLY"
        mul_ao.use_clamp = True
        mul_ao.location = (560, 120)
        mul_ao.inputs["Fac"].default_value = 1.0
        nt.links.new(shaded_sock, mul_ao.inputs[1])
        nt.links.new(ao_sock, mul_ao.inputs[2])
        ao_shaded_sock = mul_ao.outputs["Color"]
    else:
        ao_shaded_sock = shaded_sock

    # 4) Selective Welding-Arc Cyan-Blue Bounce Detector
    sep_rgb = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_rgb.location = (-240, -380)
    nt.links.new(s2rgb.outputs["Color"], sep_rgb.inputs["Vector"])

    mul_r = nt.nodes.new("ShaderNodeMath")
    mul_r.operation = "MULTIPLY"
    mul_r.location = (-60, -340)
    mul_r.inputs[1].default_value = 0.88
    nt.links.new(sep_rgb.outputs["X"], mul_r.inputs[0])

    blue_diff = nt.nodes.new("ShaderNodeMath")
    blue_diff.operation = "SUBTRACT"
    blue_diff.location = (120, -380)
    nt.links.new(sep_rgb.outputs["Z"], blue_diff.inputs[0])
    nt.links.new(mul_r.outputs["Value"], blue_diff.inputs[1])

    arc_ramp = nt.nodes.new("ShaderNodeValToRGB")
    arc_ramp.location = (320, -380)
    arc_ramp.color_ramp.interpolation = "CONSTANT"
    arc_ramp.color_ramp.elements[0].position = 0.0
    arc_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    arc_ramp.color_ramp.elements[1].position = 0.14
    arc_col = hex_to_rgba("#38C0FF")
    arc_str = 0.34 * colored_light_mix
    arc_ramp.color_ramp.elements[1].color = (arc_col[0] * arc_str, arc_col[1] * arc_str, arc_col[2] * arc_str, 1.0)
    e_arc2 = arc_ramp.color_ramp.elements.new(0.45)
    e_arc2.color = (arc_col[0] * arc_str * 1.6, arc_col[1] * arc_str * 1.6, arc_col[2] * arc_str * 1.6, 1.0)
    nt.links.new(blue_diff.outputs["Value"], arc_ramp.inputs["Fac"])

    add_arc = nt.nodes.new("ShaderNodeMixRGB")
    add_arc.blend_type = "ADD"
    add_arc.use_clamp = True
    add_arc.location = (820, 80)
    add_arc.inputs["Fac"].default_value = 1.0
    nt.links.new(ao_shaded_sock, add_arc.inputs[1])
    nt.links.new(arc_ramp.outputs["Color"], add_arc.inputs[2])

    emis_out = nt.nodes.new("ShaderNodeEmission")
    emis_out.location = (1080, 0)
    emis_out.inputs["Strength"].default_value = 1.0
    nt.links.new(add_arc.outputs["Color"], emis_out.inputs["Color"])
    nt.links.new(emis_out.outputs["Emission"], out.inputs["Surface"])

    return mat


def upgrade_glb_material_to_cel(mat: bpy.types.Material) -> None:
    """
    Convert an imported GLTF/GLB PBR material (`car_reference.glb`) into a stylized
    Textured Cel-Shaded + AO + Stepped Specular + Welding-Arc-Bounce material while
    preserving its embedded `baseColorTexture` image datablock!
    """
    if mat is None or mat.get("_cel_upgraded"):
        return
    mat["_cel_upgraded"] = True
    mat.use_nodes = True
    nt = mat.node_tree

    low_name = mat.name.lower()

    # Preserve embedded baseColorTexture image if present
    base_img: Optional[bpy.types.Image] = None
    for nd in nt.nodes:
        if nd.type == "TEX_IMAGE" and getattr(nd, "image", None) is not None:
            # Prefer textures wired to Base Color or the first image texture
            for lk in nt.links:
                if lk.from_node == nd and "Base Color" in lk.to_socket.name:
                    base_img = nd.image
                    break
            if base_img is None:
                base_img = nd.image

    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1080, 0)

    # Stylized Automotive Glass (tinted dark slate-blue with crisp diagonal cel reflection!)
    if "glass" in low_name or "window" in low_name:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (-520, 120)
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.12

        s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
        s2rgb.location = (-260, 120)
        nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

        g_ramp = nt.nodes.new("ShaderNodeValToRGB")
        g_ramp.location = (0, 120)
        g_ramp.color_ramp.interpolation = "CONSTANT"
        g_ramp.color_ramp.elements[0].position = 0.0
        g_ramp.color_ramp.elements[0].color = hex_to_rgba("#182432")
        g_ramp.color_ramp.elements[1].position = 0.25
        g_ramp.color_ramp.elements[1].color = hex_to_rgba("#2B4358")
        e_glint = g_ramp.color_ramp.elements.new(0.68)
        e_glint.color = hex_to_rgba("#7CA8C8")
        nt.links.new(s2rgb.outputs["Color"], g_ramp.inputs["Fac"])

        emis = nt.nodes.new("ShaderNodeEmission")
        emis.location = (420, 80)
        emis.inputs["Strength"].default_value = 1.0
        nt.links.new(g_ramp.outputs["Color"], emis.inputs["Color"])
        nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
        return

    # Headlights / Taillights subtle cel-glow
    is_front_light = "lights_front" in low_name or "fog_light" in low_name
    is_tail_light = "taillight" in low_name

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-680, -80)
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.32

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-420, -80)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-160, -40)
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.44, 0.43, 0.47, 1.0)
    ramp.color_ramp.elements[1].position = 0.14
    ramp.color_ramp.elements[1].color = (0.88, 0.88, 0.88, 1.0)
    e_hi = ramp.color_ramp.elements.new(0.50)
    e_hi.color = (1.04, 1.04, 1.04, 1.0)
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    if base_img is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.location = (-680, 260)
        tex.image = base_img
        color_src = tex.outputs["Color"]
    else:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.location = (-680, 260)
        rgb.outputs[0].default_value = hex_to_rgba(PALETTE_HEX["car_body_teal"])
        color_src = rgb.outputs[0]

    # Subtle procedural paint wear / micro-grime variation
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-900, 120)
    wear_noise = nt.nodes.new("ShaderNodeTexNoise")
    wear_noise.location = (-680, 80)
    wear_noise.inputs["Scale"].default_value = 9.0
    wear_noise.inputs["Detail"].default_value = 5.0
    nt.links.new(tc.outputs["Object"], wear_noise.inputs["Vector"])

    wear_mix = nt.nodes.new("ShaderNodeMixRGB")
    wear_mix.blend_type = "MULTIPLY"
    wear_mix.location = (-360, 220)
    wear_mix.inputs["Fac"].default_value = 0.14
    nt.links.new(color_src, wear_mix.inputs[1])
    nt.links.new(wear_noise.outputs["Fac"], wear_mix.inputs[2])

    mul_cel = nt.nodes.new("ShaderNodeMixRGB")
    mul_cel.blend_type = "MULTIPLY"
    mul_cel.use_clamp = True
    mul_cel.location = (160, 140)
    mul_cel.inputs["Fac"].default_value = 1.0
    nt.links.new(wear_mix.outputs["Color"], mul_cel.inputs[1])
    nt.links.new(ramp.outputs["Color"], mul_cel.inputs[2])

    # Multiply AO for deep wheel-well, door-seam, and grille shadows!
    ao_sock = _build_ao_factor_socket(nt, loc_x=-140, loc_y=-280, strength=0.48)
    mul_ao = nt.nodes.new("ShaderNodeMixRGB")
    mul_ao.blend_type = "MULTIPLY"
    mul_ao.use_clamp = True
    mul_ao.location = (420, 120)
    mul_ao.inputs["Fac"].default_value = 1.0
    nt.links.new(mul_cel.outputs["Color"], mul_ao.inputs[1])
    nt.links.new(ao_sock, mul_ao.inputs[2])

    # Add Welding-Arc Cyan-Blue Bounce so the car fender reacts to the welding torch!
    sep_rgb = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_rgb.location = (-140, -480)
    nt.links.new(s2rgb.outputs["Color"], sep_rgb.inputs["Vector"])
    mul_r = nt.nodes.new("ShaderNodeMath")
    mul_r.operation = "MULTIPLY"
    mul_r.location = (40, -440)
    mul_r.inputs[1].default_value = 0.88
    nt.links.new(sep_rgb.outputs["X"], mul_r.inputs[0])
    blue_diff = nt.nodes.new("ShaderNodeMath")
    blue_diff.operation = "SUBTRACT"
    blue_diff.location = (220, -480)
    nt.links.new(sep_rgb.outputs["Z"], blue_diff.inputs[0])
    nt.links.new(mul_r.outputs["Value"], blue_diff.inputs[1])

    arc_ramp = nt.nodes.new("ShaderNodeValToRGB")
    arc_ramp.location = (400, -480)
    arc_ramp.color_ramp.interpolation = "CONSTANT"
    arc_ramp.color_ramp.elements[0].position = 0.0
    arc_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    arc_ramp.color_ramp.elements[1].position = 0.14
    arc_col = hex_to_rgba("#38C0FF")
    arc_ramp.color_ramp.elements[1].color = (arc_col[0] * 0.25, arc_col[1] * 0.25, arc_col[2] * 0.25, 1.0)
    nt.links.new(blue_diff.outputs["Value"], arc_ramp.inputs["Fac"])

    add_arc = nt.nodes.new("ShaderNodeMixRGB")
    add_arc.blend_type = "ADD"
    add_arc.use_clamp = True
    add_arc.location = (680, 100)
    add_arc.inputs["Fac"].default_value = 1.0
    nt.links.new(mul_ao.outputs["Color"], add_arc.inputs[1])
    nt.links.new(arc_ramp.outputs["Color"], add_arc.inputs[2])

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (880, 40)
    emis.inputs["Strength"].default_value = 1.35 if (is_front_light or is_tail_light) else 1.0
    nt.links.new(add_arc.outputs["Color"], emis.inputs["Color"])
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])


def get_textured_cel_material(
    name: str,
    image_path: str,
    alpha_cutout: bool = False,
    shadow_floor: float = 0.48,
    lit_ceiling: float = 1.00,
    emissive_boost: float = 1.0,
) -> bpy.types.Material:
    """
    Cel-shaded material driven by a 2D Pillow Decal PNG (`generated_textures/*.png`)
    with stepped shadow response and crisp readability.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if alpha_cutout:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
        if hasattr(mat, "blend_method"):
            try:
                mat.blend_method = "CLIP"
            except Exception:
                pass
        mat.use_backface_culling = False

    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (860, 0)

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-520, 240)
    if Path(image_path).exists():
        img = bpy.data.images.load(str(Path(image_path).resolve()), check_existing=True)
        tex.image = img
    tex.extension = "REPEAT" if "stripe" in name.lower() else ("CLIP" if alpha_cutout else "EXTEND")

    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.location = (-520, -60)
    bsdf.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-280, -60)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-40, -20)
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (shadow_floor, shadow_floor * 0.98, shadow_floor * 1.02, 1.0)
    ramp.color_ramp.elements[1].position = 0.14
    ramp.color_ramp.elements[1].color = (0.90, 0.90, 0.90, 1.0)
    e_hi = ramp.color_ramp.elements.new(0.48)
    e_hi.color = (lit_ceiling, lit_ceiling, lit_ceiling, 1.0)
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.use_clamp = True
    mul.location = (320, 120)
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], mul.inputs[1])
    nt.links.new(ramp.outputs["Color"], mul.inputs[2])

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (560, 120)
    emis.inputs["Strength"].default_value = emissive_boost
    nt.links.new(mul.outputs["Color"], emis.inputs["Color"])

    if alpha_cutout:
        transp = nt.nodes.new("ShaderNodeBsdfTransparent")
        transp.location = (560, -60)
        mix_sh = nt.nodes.new("ShaderNodeMixShader")
        mix_sh.location = (720, 40)
        nt.links.new(tex.outputs["Alpha"], mix_sh.inputs["Fac"])
        nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
        nt.links.new(emis.outputs["Emission"], mix_sh.inputs[2])
        nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    else:
        nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])

    return mat


def get_emission_material(
    name: str,
    hex_color: str,
    strength: float = 8.0,
) -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (260, 0)
    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (0, 0)
    emis.inputs["Color"].default_value = hex_to_rgba(hex_color)
    emis.inputs["Strength"].default_value = strength
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
    return mat


def create_weld_seam_material(name: str = "Mat_WeldSeam_Ember") -> Tuple[bpy.types.Material, bpy.types.Node, bpy.types.Node]:
    """Procedural glowing weld seam shader along curve U-coordinate (UV.x)."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "CLIP"
        except Exception:
            pass

    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1120, 0)

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-780, 120)

    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-560, 120)
    nt.links.new(tex_coord.outputs["UV"], sep.inputs["Vector"])

    prog_node = nt.nodes.new("ShaderNodeValue")
    prog_node.name = "SeamProgress"
    prog_node.label = "SeamProgress"
    prog_node.outputs[0].default_value = 0.0
    prog_node.location = (-560, -80)

    heat_node = nt.nodes.new("ShaderNodeValue")
    heat_node.name = "SeamHeat"
    heat_node.label = "SeamHeat"
    heat_node.outputs[0].default_value = 0.0
    heat_node.location = (-560, -240)

    sub_vis = nt.nodes.new("ShaderNodeMath")
    sub_vis.operation = "SUBTRACT"
    sub_vis.location = (-300, 120)
    nt.links.new(prog_node.outputs["Value"], sub_vis.inputs[0])
    nt.links.new(sep.outputs["X"], sub_vis.inputs[1])

    vis_mask = nt.nodes.new("ShaderNodeMath")
    vis_mask.operation = "GREATER_THAN"
    vis_mask.location = (-100, 160)
    vis_mask.inputs[1].default_value = 0.0
    nt.links.new(sub_vis.outputs["Value"], vis_mask.inputs[0])

    dist_map = nt.nodes.new("ShaderNodeMapRange")
    if hasattr(dist_map, "clamp"):
        dist_map.clamp = True
    dist_map.location = (-100, -40)
    dist_map.inputs["From Min"].default_value = 0.0
    dist_map.inputs["From Max"].default_value = 0.42
    dist_map.inputs["To Min"].default_value = 1.0
    dist_map.inputs["To Max"].default_value = 0.42
    nt.links.new(sub_vis.outputs["Value"], dist_map.inputs["Value"])

    eff_heat = nt.nodes.new("ShaderNodeMath")
    eff_heat.operation = "MULTIPLY"
    eff_heat.location = (140, -100)
    nt.links.new(dist_map.outputs["Result"], eff_heat.inputs[0])
    nt.links.new(heat_node.outputs["Value"], eff_heat.inputs[1])

    ember_ramp = nt.nodes.new("ShaderNodeValToRGB")
    ember_ramp.location = (360, -80)
    ember_ramp.color_ramp.interpolation = "EASE"
    elems = ember_ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = hex_to_rgba("#383C46")
    elems[1].position = 0.22
    elems[1].color = hex_to_rgba("#B5280A")
    e_mid = elems.new(0.52)
    e_mid.color = hex_to_rgba("#FF6810")
    e_hot = elems.new(0.88)
    e_hot.color = hex_to_rgba("#FFF4BA")
    nt.links.new(eff_heat.outputs["Value"], ember_ramp.inputs["Fac"])

    str_math = nt.nodes.new("ShaderNodeMath")
    str_math.operation = "MULTIPLY_ADD"
    str_math.location = (380, -300)
    str_math.inputs[1].default_value = 12.0
    str_math.inputs[2].default_value = 1.5
    nt.links.new(eff_heat.outputs["Value"], str_math.inputs[0])

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (660, -80)
    nt.links.new(ember_ramp.outputs["Color"], emis.inputs["Color"])
    nt.links.new(str_math.outputs["Value"], emis.inputs["Strength"])

    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    transp.location = (660, 120)

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.location = (900, 20)
    nt.links.new(vis_mask.outputs["Value"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(emis.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

    return mat, prog_node, heat_node
