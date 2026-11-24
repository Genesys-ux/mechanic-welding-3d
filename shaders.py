"""
shaders.py — 3D Cel-Shade Material Library & Inverted-Hull Bold Outline Generator
Compatible with Blender 3.6 LTS and Blender 4.2+ LTS (EEVEE & EEVEE Next).
"""

from __future__ import annotations

from typing import Optional, Tuple

import bpy

from config import PALETTE_HEX, hex_to_rgba, srgb_to_linear_channel


def _scale_rgba(
    rgba: Tuple[float, float, float, float],
    factor: float,
    tint_white: float = 0.0,
) -> Tuple[float, float, float, float]:
    r = min(1.5, max(0.0, rgba[0] * factor + tint_white))
    g = min(1.5, max(0.0, rgba[1] * factor + tint_white))
    b = min(1.5, max(0.0, rgba[2] * factor + tint_white))
    return (r, g, b, rgba[3])


def get_ink_outline_material(
    name: str = "Mat_Ink_Outline",
    hex_color: str = PALETTE_HEX["ink_outline"],
) -> bpy.types.Material:
    """
    Create or retrieve the bold cartoon Inverted-Hull outline material.
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
    thickness: float = 0.0085,
    outline_mat: Optional[bpy.types.Material] = None,
    use_even_offset: bool = True,
) -> Optional[bpy.types.Modifier]:
    """
    Attach an Inverted-Hull Solidify modifier with flipped normals and bold ink outline material.
    """
    if obj.type != "MESH" or obj.data is None:
        return None

    ink_mat = outline_mat or get_ink_outline_material()

    # Ensure slot 0 exists; append ink_mat if not present
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

    # Negative thickness pushes outward when normals are flipped
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
    shadow_factor: float = 0.44,
    mid_factor: float = 0.88,
    lit_factor: float = 1.12,
    spec_strength: float = 0.0,
    rim_strength: float = 0.22,
    roughness: float = 0.45,
    colored_light_mix: float = 0.55,
) -> bpy.types.Material:
    """
    3-Band Stepped Cel-Shade Material:
      Principled/Diffuse BSDF -> Shader to RGB -> Constant ColorRamp
    Plus chromatic incident-light tinting so bright blue-white welding arc light
    casts dramatic electric-blue cel highlights across skin, goggles, vest, and car!
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    base_rgba = hex_to_rgba(hex_color)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (960, 0)

    # 1) White probe BSDF to capture both shadow intensity AND light color (e.g., blue welding arc)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-680, 120)
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.5 if spec_strength > 0 else 0.12
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.5 if spec_strength > 0 else 0.12

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-400, 120)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    # 2) Constant 3-stop ColorRamp for crisp stepped toon bands
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-140, 220)
    ramp.color_ramp.interpolation = "CONSTANT"
    elems = ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = _scale_rgba(base_rgba, shadow_factor)
    elems[1].position = 0.22
    elems[1].color = _scale_rgba(base_rgba, mid_factor)
    e_hi = elems.new(0.62)
    e_hi.color = _scale_rgba(base_rgba, lit_factor, tint_white=0.025)
    if spec_strength > 0.05:
        e_spec = elems.new(0.92)
        e_spec.color = _scale_rgba(base_rgba, lit_factor * 1.15, tint_white=0.18 * spec_strength)

    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    # 3) Incident Colored Light Response (captures blue-white welding arc & warm overhead key)
    # Mix neutral white with clamped ShaderToRGB light color, then multiply with stepped ramp
    light_mix = nt.nodes.new("ShaderNodeMixRGB")
    light_mix.blend_type = "MIX"
    light_mix.location = (180, -40)
    light_mix.inputs["Fac"].default_value = colored_light_mix
    light_mix.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(s2rgb.outputs["Color"], light_mix.inputs[2])

    # Boost light_mix slightly so midtones stay vibrant
    bright = nt.nodes.new("ShaderNodeBrightContrast")
    bright.location = (360, -40)
    bright.inputs["Bright"].default_value = 0.32
    bright.inputs["Contrast"].default_value = 0.15
    nt.links.new(light_mix.outputs["Color"], bright.inputs["Color"])

    mul_col = nt.nodes.new("ShaderNodeMixRGB")
    mul_col.blend_type = "MULTIPLY"
    mul_col.location = (560, 120)
    mul_col.inputs["Fac"].default_value = 0.72
    nt.links.new(ramp.outputs["Color"], mul_col.inputs[1])
    nt.links.new(bright.outputs["Color"], mul_col.inputs[2])

    # 4) Stepped Grazing Fresnel Rim Accent (matches mekanik_muda_character.py rimIntensity)
    if rim_strength > 0.01:
        layer_w = nt.nodes.new("ShaderNodeLayerWeight")
        layer_w.location = (-140, -180)
        layer_w.inputs["Blend"].default_value = 0.30

        rim_ramp = nt.nodes.new("ShaderNodeValToRGB")
        rim_ramp.location = (120, -200)
        rim_ramp.color_ramp.interpolation = "CONSTANT"
        rim_ramp.color_ramp.elements[0].position = 0.0
        rim_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        rim_ramp.color_ramp.elements[1].position = 0.68
        rim_ramp.color_ramp.elements[1].color = (
            rim_strength * 0.65,
            rim_strength * 0.78,
            rim_strength * 0.95,
            1.0,
        )
        nt.links.new(layer_w.outputs["Facing"], rim_ramp.inputs["Fac"])

        add_rim = nt.nodes.new("ShaderNodeMixRGB")
        add_rim.blend_type = "ADD"
        add_rim.location = (760, 60)
        add_rim.inputs["Fac"].default_value = 1.0
        nt.links.new(mul_col.outputs["Color"], add_rim.inputs[1])
        nt.links.new(rim_ramp.outputs["Color"], add_rim.inputs[2])
        final_col_out = add_rim.outputs["Color"]
    else:
        final_col_out = mul_col.outputs["Color"]

    emis_out = nt.nodes.new("ShaderNodeEmission")
    emis_out.location = (780, -120)
    emis_out.inputs["Strength"].default_value = 1.0
    nt.links.new(final_col_out, emis_out.inputs["Color"])
    nt.links.new(emis_out.outputs["Emission"], out.inputs["Surface"])

    return mat


def get_textured_cel_material(
    name: str,
    image_path: str,
    alpha_cutout: bool = False,
    shadow_floor: float = 0.48,
    lit_ceiling: float = 1.12,
    colored_light_mix: float = 0.50,
) -> bpy.types.Material:
    """
    Cel-shaded material driven by a high-res RGBA texture generated from
    mekanik_muda_character.py (vest front/back patch, toolbelt, face details),
    still reacting to 3D stepped shadows and the blue-white welding light!
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
    out.location = (920, 0)

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-560, 260)
    img = bpy.data.images.load(image_path, check_existing=True)
    tex.image = img
    tex.extension = "CLIP" if alpha_cutout else "EXTEND"

    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.location = (-560, -60)
    bsdf.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (-320, -60)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-80, -20)
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (shadow_floor, shadow_floor * 0.96, shadow_floor * 1.04, 1.0)
    ramp.color_ramp.elements[1].position = 0.20
    ramp.color_ramp.elements[1].color = (0.94, 0.94, 0.94, 1.0)
    e_hi = ramp.color_ramp.elements.new(0.62)
    e_hi.color = (lit_ceiling, lit_ceiling, lit_ceiling, 1.0)
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    # Blend incident colored light (welding arc cyan-blue)
    tint_mix = nt.nodes.new("ShaderNodeMixRGB")
    tint_mix.blend_type = "ADD"
    tint_mix.location = (180, -100)
    tint_mix.inputs["Fac"].default_value = colored_light_mix * 0.35
    nt.links.new(ramp.outputs["Color"], tint_mix.inputs[1])
    nt.links.new(s2rgb.outputs["Color"], tint_mix.inputs[2])

    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.location = (420, 140)
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], mul.inputs[1])
    nt.links.new(tint_mix.outputs["Color"], mul.inputs[2])

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (620, 140)
    emis.inputs["Strength"].default_value = 1.0
    nt.links.new(mul.outputs["Color"], emis.inputs["Color"])

    if alpha_cutout:
        transp = nt.nodes.new("ShaderNodeBsdfTransparent")
        transp.location = (620, -60)
        mix_sh = nt.nodes.new("ShaderNodeMixShader")
        mix_sh.location = (780, 40)
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
    Procedural glowing weld seam shader along curve U-coordinate (Generated/UV X):
    - Value node `SeamProgress` (0.0 -> 1.0) reveals the laid weld bead from start to end.
    - Value node `SeamHeat` (1.0 while welding -> cools to 0.12 in Beat 4) controls the
      molten orange-white ember glow fading smoothly into warm dark welded steel!
    Returns (material, progress_node, heat_node).
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
    # Curve U maps along UV.x
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

    # Visibility mask: UV.x <= SeamProgress -> 1 else 0
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

    # Local hotness near the moving torch head (small sub_vis = white-hot puddle, larger = orange ember)
    dist_map = nt.nodes.new("ShaderNodeMapRange")
    dist_map.use_clamp = True
    dist_map.location = (-100, -40)
    dist_map.inputs["From Min"].default_value = 0.0
    dist_map.inputs["From Max"].default_value = 0.38
    dist_map.inputs["To Min"].default_value = 1.0
    dist_map.inputs["To Max"].default_value = 0.38
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
    elems[0].color = hex_to_rgba("#3B3F4A")  # Cooled dark steel bead
    elems[1].position = 0.25
    elems[1].color = hex_to_rgba("#9E2208")  # Dull cherry-red ember
    e_mid = elems.new(0.55)
    e_mid.color = hex_to_rgba("#FF620A")     # Bright glowing molten orange
    e_hot = elems.new(0.88)
    e_hot.color = hex_to_rgba("#FFF2B2")     # White-hot arc puddle
    nt.links.new(eff_heat.outputs["Value"], ember_ramp.inputs["Fac"])

    str_math = nt.nodes.new("ShaderNodeMath")
    str_math.operation = "MULTIPLY_ADD"
    str_math.location = (380, -300)
    str_math.inputs[1].default_value = 14.0
    str_math.inputs[2].default_value = 1.1
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
