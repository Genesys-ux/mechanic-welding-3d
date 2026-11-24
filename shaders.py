"""
shaders.py — 3D Cel-Shade Material Library & Inverted-Hull Bold Outline Generator
Compatible with Blender 3.6 LTS and Blender 4.2+ LTS (EEVEE & EEVEE Next).
"""

from __future__ import annotations

from typing import Optional, Tuple

import bpy

from config import PALETTE_HEX, hex_to_rgba


def _scale_rgba(
    rgba: Tuple[float, float, float, float],
    factor: float,
    tint_white: float = 0.0,
) -> Tuple[float, float, float, float]:
    # Clamp strictly <= 0.98 linear so non-emissive cel surfaces never trigger HDR bloom!
    r = min(0.98, max(0.0, rgba[0] * factor + tint_white))
    g = min(0.98, max(0.0, rgba[1] * factor + tint_white))
    b = min(0.98, max(0.0, rgba[2] * factor + tint_white))
    return (r, g, b, rgba[3])


def get_ink_outline_material(
    name: str = "Mat_Ink_Outline",
    hex_color: str = PALETTE_HEX["ink_outline"],
) -> bpy.types.Material:
    """
    Create or retrieve the bold cartoon Inverted-Hull outline material (#201720).
    Uses Light Path -> Is Shadow Ray -> Transparent BSDF so the flipped outer shell
    NEVER casts self-shadows onto the inner cel-shaded mesh in EEVEE / EEVEE Next!
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
    thickness: float = 0.0075,
    outline_mat: Optional[bpy.types.Material] = None,
    use_even_offset: bool = False,
) -> Optional[bpy.types.Modifier]:
    """
    Attach an Inverted-Hull Solidify modifier with flipped normals and bold ink outline material.
    `use_even_offset = False` prevents miter spikes on curved limbs and acute bevels!
    """
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


def get_cel_material(
    name: str,
    hex_color: str,
    shadow_factor: float = 0.46,
    mid_factor: float = 0.92,
    lit_factor: float = 1.08,
    spec_strength: float = 0.0,
    rim_strength: float = 0.12,
    roughness: float = 0.45,
    colored_light_mix: float = 0.55,
) -> bpy.types.Material:
    """
    3-Band Stepped Anime/Cartoon Cel-Shade Material:
      Principled BSDF -> Shader to RGB -> Constant ColorRamp
    Features selective Blue-Excess Arc Detection (`Blue - Red * 0.85`) so:
      - Under warm/neutral workshop lighting, colors remain 100% faithful to CHARACTER_CONFIG
        with ZERO overexposure or white wash-out!
      - When the electric cyan-blue Welding Arc fires (Frames 113..203), surfaces facing the
        arc receive a crisp, stepped electric-blue cel reflection band!
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    base_rgba = hex_to_rgba(hex_color)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1080, 0)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-760, 140)
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.45 if spec_strength > 0 else 0.10
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.45 if spec_strength > 0 else 0.10

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-480, 140)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    # 1) 3-Band Stepped Base Color Ramp
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-180, 240)
    ramp.color_ramp.interpolation = "CONSTANT"
    elems = ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = _scale_rgba(base_rgba, shadow_factor)
    elems[1].position = 0.16
    elems[1].color = _scale_rgba(base_rgba, mid_factor)
    e_hi = elems.new(0.52)
    e_hi.color = _scale_rgba(base_rgba, lit_factor, tint_white=0.015)
    if spec_strength > 0.08:
        e_spec = elems.new(0.86)
        e_spec.color = _scale_rgba(base_rgba, lit_factor * 1.08, tint_white=0.12 * spec_strength)
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    # 2) Selective Welding-Arc Cyan-Blue Bounce Detector (`Blue - Red * 0.85`)
    sep_rgb = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_rgb.location = (-460, -100)
    nt.links.new(s2rgb.outputs["Color"], sep_rgb.inputs["Vector"])

    mul_r = nt.nodes.new("ShaderNodeMath")
    mul_r.operation = "MULTIPLY"
    mul_r.location = (-260, -60)
    mul_r.inputs[1].default_value = 0.88
    nt.links.new(sep_rgb.outputs["X"], mul_r.inputs[0])

    blue_diff = nt.nodes.new("ShaderNodeMath")
    blue_diff.operation = "SUBTRACT"
    blue_diff.location = (-80, -100)
    nt.links.new(sep_rgb.outputs["Z"], blue_diff.inputs[0])
    nt.links.new(mul_r.outputs["Value"], blue_diff.inputs[1])

    arc_ramp = nt.nodes.new("ShaderNodeValToRGB")
    arc_ramp.location = (120, -100)
    arc_ramp.color_ramp.interpolation = "CONSTANT"
    arc_ramp.color_ramp.elements[0].position = 0.0
    arc_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    arc_ramp.color_ramp.elements[1].position = 0.14
    arc_col = hex_to_rgba("#38C0FF")
    arc_str = 0.36 * colored_light_mix
    arc_ramp.color_ramp.elements[1].color = (arc_col[0] * arc_str, arc_col[1] * arc_str, arc_col[2] * arc_str, 1.0)
    e_arc2 = arc_ramp.color_ramp.elements.new(0.45)
    e_arc2.color = (arc_col[0] * arc_str * 1.65, arc_col[1] * arc_str * 1.65, arc_col[2] * arc_str * 1.65, 1.0)
    nt.links.new(blue_diff.outputs["Value"], arc_ramp.inputs["Fac"])

    add_arc = nt.nodes.new("ShaderNodeMixRGB")
    add_arc.blend_type = "ADD"
    add_arc.use_clamp = True
    add_arc.location = (460, 120)
    add_arc.inputs["Fac"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], add_arc.inputs[1])
    nt.links.new(arc_ramp.outputs["Color"], add_arc.inputs[2])

    # 3) Subtle Stepped Grazing Rim Accent (clamped so it never blows out!)
    if rim_strength > 0.02:
        layer_w = nt.nodes.new("ShaderNodeLayerWeight")
        layer_w.location = (120, -320)
        layer_w.inputs["Blend"].default_value = 0.22

        rim_ramp = nt.nodes.new("ShaderNodeValToRGB")
        rim_ramp.location = (340, -320)
        rim_ramp.color_ramp.interpolation = "CONSTANT"
        rim_ramp.color_ramp.elements[0].position = 0.0
        rim_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        rim_ramp.color_ramp.elements[1].position = 0.74
        rim_tint = _scale_rgba(base_rgba, 0.35, tint_white=rim_strength * 0.28)
        rim_ramp.color_ramp.elements[1].color = (
            rim_tint[0] * rim_strength,
            rim_tint[1] * rim_strength * 1.08,
            rim_tint[2] * rim_strength * 1.22,
            1.0,
        )
        nt.links.new(layer_w.outputs["Facing"], rim_ramp.inputs["Fac"])

        add_rim = nt.nodes.new("ShaderNodeMixRGB")
        add_rim.blend_type = "ADD"
        add_rim.use_clamp = True
        add_rim.location = (680, 60)
        add_rim.inputs["Fac"].default_value = 1.0
        nt.links.new(add_arc.outputs["Color"], add_rim.inputs[1])
        nt.links.new(rim_ramp.outputs["Color"], add_rim.inputs[2])
        final_col_out = add_rim.outputs["Color"]
    else:
        final_col_out = add_arc.outputs["Color"]

    emis_out = nt.nodes.new("ShaderNodeEmission")
    emis_out.location = (880, 0)
    emis_out.inputs["Strength"].default_value = 1.0
    nt.links.new(final_col_out, emis_out.inputs["Color"])
    nt.links.new(emis_out.outputs["Emission"], out.inputs["Surface"])

    return mat


def get_textured_cel_material(
    name: str,
    image_path: str,
    alpha_cutout: bool = False,
    shadow_floor: float = 0.52,
    lit_ceiling: float = 1.02,
    colored_light_mix: float = 0.50,
) -> bpy.types.Material:
    """
    Cel-shaded material driven by a high-res RGBA texture (e.g. marker-bird back patch),
    clamped cleanly so colors never clip.
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
        if hasattr(mat, "shadow_method"):
            try:
                mat.shadow_method = "CLIP"
            except Exception:
                pass
        mat.use_backface_culling = False

    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (860, 0)

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-520, 240)
    img = bpy.data.images.load(image_path, check_existing=True)
    tex.image = img
    tex.extension = "CLIP" if alpha_cutout else "EXTEND"

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
    ramp.color_ramp.elements[0].color = (shadow_floor, shadow_floor * 0.96, shadow_floor * 1.02, 1.0)
    ramp.color_ramp.elements[1].position = 0.16
    ramp.color_ramp.elements[1].color = (0.94, 0.94, 0.94, 1.0)
    e_hi = ramp.color_ramp.elements.new(0.52)
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
    emis.inputs["Strength"].default_value = 1.0
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
    """
    Procedural glowing weld seam shader along curve U-coordinate (UV.x):
      - `SeamProgress` (0.0 -> 1.0) reveals the laid weld bead from start to end.
      - `SeamHeat` (1.0 while welding -> cools in Beat 4) drives molten orange-white glow.
    """
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
