# ALIF - TSA Character Reconstruction V2
# Blender 5.2 LTS
# Goal: preserve Alif V1 identity (head, face, bolts, zipper seam, suit, tie, true torn openings)
# and upgrade the limbs to TSA anatomy lock.
# TSA locks:
# - Preserve body/head/face/clothing identity.
# - Eyes must remain embedded/read as part of the face, not tempelan stickers.
# - Torn suit holes must stay true boolean openings with visible green underlayer.
# - Arms/hands must have readable anatomy: shoulder, upper arm, elbow, forearm, wrist, hand.
# - Legs/feet must have readable anatomy: thigh, knee, calf, ankle, foot.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "alif_output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.65

# ------------------------------------------------------------
# FAMILY / CHARACTER SCALE
# ------------------------------------------------------------
HEAD_W = 2.25
HEAD_D = 1.52
HEAD_H = 2.20
HEAD_Z = 3.06

TORSO_W = 2.06
TORSO_D = 1.38
TORSO_H = 2.15
TORSO_Z = 1.58

GREEN = (0.47, 0.80, 0.26, 1.0)
GREEN_DARK = (0.32, 0.59, 0.17, 1.0)
BLACK = (0.10, 0.10, 0.10, 1.0)
SUIT_GREY = (0.17, 0.17, 0.18, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
PUPIL = (0.10, 0.10, 0.10, 1.0)
RED = (0.86, 0.20, 0.18, 1.0)
TOOTH = (0.95, 0.93, 0.84, 1.0)
BOLT_DARK = (0.29, 0.29, 0.29, 1.0)
BOLT_LIGHT = (0.56, 0.56, 0.56, 1.0)

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def make_mat(name, color, roughness=0.34, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mark_region(obj, region):
    obj["tsa_region"] = region
    return obj


def smooth_object(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True


def apply_modifier(obj, mod_name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_name)
    obj.select_set(False)


def apply_bevel(obj, width=0.12, segments=6):
    mod = obj.modifiers.new("TSA_Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    apply_modifier(obj, mod.name)


def rounded_box(name, location, dimensions, bevel, material, region, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_bevel(obj, bevel, 8)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def uv_part(name, location, scale, material, region, rotation=(0,0,0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def cone_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=32):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius,
        radius2=0.02,
        depth=depth,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 8
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 5
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(pts) - 1)
    for bp, p in zip(spline.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def boolean_difference(base_obj, cutter_obj, apply=True):
    mod = base_obj.modifiers.new(name=f"BOOL_{cutter_obj.name}", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter_obj
    if apply:
        apply_modifier(base_obj, mod.name)
        bpy.data.objects.remove(cutter_obj, do_unlink=True)


def jagged_hole_cutter(name, location, scale=(0.22, 0.12, 0.20), rotation=(0,0,0)):
    parts = []
    offsets = [
        (0.00, 0.00, 0.00),
        (0.08, 0.00, 0.05),
        (-0.07, 0.00, 0.04),
        (0.03, 0.00, -0.06),
        (-0.06, 0.00, -0.05),
    ]
    for i, off in enumerate(offsets):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2,
            location=(location[0]+off[0], location[1]+off[1], location[2]+off[2]),
            rotation=rotation
        )
        obj = bpy.context.object
        obj.name = f"{name}_{i}"
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        parts.append(obj)
    for obj in parts[1:]:
        mod = parts[0].modifiers.new(name=f"UNION_{obj.name}", type='BOOLEAN')
        mod.operation = 'UNION'
        mod.object = obj
        mod.solver = 'EXACT'
        apply_modifier(parts[0], mod.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    return parts[0]


def capsule_between(name, a, b, radius, material, region):
    a = Vector(a)
    b = Vector(b)
    mid = (a + b) * 0.5
    vec = b - a
    length = vec.length
    obj = cyl_part(name, tuple(mid), radius, length, material, region)
    obj.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    uv_part(name + ".CAP_A", tuple(a), (radius, radius, radius), material, region)
    uv_part(name + ".CAP_B", tuple(b), (radius, radius, radius), material, region)
    return obj

# ------------------------------------------------------------
# SCENE SETUP
# ------------------------------------------------------------
clean_scene()

mat_green = make_mat("MAT_GREEN", GREEN, 0.34)
mat_green_dark = make_mat("MAT_GREEN_DARK", GREEN_DARK, 0.45)
mat_black = make_mat("MAT_BLACK", BLACK, 0.38)
mat_suit = make_mat("MAT_SUIT", SUIT_GREY, 0.42)
mat_white = make_mat("MAT_WHITE", WHITE, 0.24)
mat_pupil = make_mat("MAT_PUPIL", PUPIL, 0.18)
mat_red = make_mat("MAT_RED", RED, 0.28)
mat_tooth = make_mat("MAT_TOOTH", TOOTH, 0.32)
mat_bolt_dark = make_mat("MAT_BOLT_DARK", BOLT_DARK, 0.35, 0.1)
mat_bolt_light = make_mat("MAT_BOLT_LIGHT", BOLT_LIGHT, 0.28, 0.18)

# ------------------------------------------------------------
# 1. CORE BODY / HEAD (PRESERVE)
# ------------------------------------------------------------
head = rounded_box("HEAD", (0, 0, HEAD_Z), (HEAD_W, HEAD_D, HEAD_H), 0.15, mat_green, "HEAD")
neck_bridge = rounded_box("NECK_BRIDGE", (0, 0, 2.18), (1.72, 1.06, 0.28), 0.08, mat_green, "TORSO")
torso_under = rounded_box("TORSO_UNDER", (0, 0, TORSO_Z), (TORSO_W, TORSO_D, TORSO_H), 0.14, mat_green, "TORSO")
belly = uv_part("BELLY_CORE", (0, 0.02, 0.95), (0.66, 0.56, 0.48), mat_green, "TORSO")

# ------------------------------------------------------------
# 2. SUIT SHELL WITH TRUE TEARS (PRESERVE)
# ------------------------------------------------------------
suit_shell = rounded_box("SUIT_SHELL", (0, -0.01, 1.58), (2.16, 1.44, 2.12), 0.11, mat_suit, "SUIT")

collar_cut = rounded_box("COLLAR_CUT", (0, 0.28, 2.35), (1.05, 0.80, 0.72), 0.06, mat_white, "CUTTER")
boolean_difference(suit_shell, collar_cut)

for idx, loc in enumerate([(-0.83, 0.36, 1.66), (0.82, 0.34, 1.63)]):
    cutter = jagged_hole_cutter(f"TEAR_HOLE_{idx}", loc, scale=(0.15, 0.18, 0.18), rotation=(0, math.radians(90), 0))
    cutter.scale.y *= 2.1
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean_difference(suit_shell, cutter)

cutter = jagged_hole_cutter("BACK_TEAR", (0.70, -0.26, 1.74), scale=(0.13, 0.18, 0.16), rotation=(0, math.radians(90), 0))
cutter.scale.y *= 2.0
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
boolean_difference(suit_shell, cutter)

for i, x in enumerate([-0.88, -0.52, -0.18, 0.16, 0.50, 0.84]):
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.11, radius2=0.01, depth=0.34,
                                    location=(x, 0.0, 0.58), rotation=(0, 0, math.radians(180)))
    tri = bpy.context.object
    tri.name = f"HEM_NOTCH_{i}"
    tri.scale.y = 2.2
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean_difference(suit_shell, tri)

for name, loc, rot, sc in [
    ("INNER_PATCH_L", (-0.83, 0.07, 1.66), (math.radians(90), 0, 0), (0.18, 0.18, 0.03)),
    ("INNER_PATCH_R", (0.82, 0.07, 1.63), (math.radians(90), 0, 0), (0.18, 0.18, 0.03)),
    ("INNER_PATCH_B", (0.70, -0.56, 1.74), (math.radians(90), 0, 0), (0.16, 0.16, 0.03)),
]:
    uv_part(name, loc, sc, mat_green_dark, "SUIT_TEAR_INNER", rotation=rot)

shirt_v = rounded_box("SHIRT_V_L", (0, 0.38, 2.04), (0.56, 0.22, 0.58), 0.05, mat_white, "CLOTH")
shirt_v.rotation_euler = (math.radians(55), 0, math.radians(45))
shirt_v2 = rounded_box("SHIRT_V_R", (0, 0.38, 2.04), (0.56, 0.22, 0.58), 0.05, mat_white, "CLOTH")
shirt_v2.rotation_euler = (math.radians(55), 0, math.radians(-45))

rounded_box("COLLAR_L", (-0.16, 0.41, 2.17), (0.24, 0.10, 0.18), 0.03, mat_white, "CLOTH", rotation=(0,0,math.radians(18)))
rounded_box("COLLAR_R", (0.16, 0.41, 2.17), (0.24, 0.10, 0.18), 0.03, mat_white, "CLOTH", rotation=(0,0,math.radians(-18)))
rounded_box("TIE_KNOT", (0, 0.44, 1.95), (0.20, 0.08, 0.16), 0.03, mat_red, "CLOTH")
rounded_box("TIE_BODY", (0, 0.42, 1.67), (0.22, 0.06, 0.52), 0.03, mat_red, "CLOTH", rotation=(0,0,math.radians(45)))

for i, z in enumerate([1.52, 1.24]):
    uv_part(f"BUTTON_{i}", (0, 0.72, z), (0.06, 0.03, 0.06), mat_black, "SUIT")

# ------------------------------------------------------------
# 3. TSA LIMBS - REBUILT ONLY HERE
# ------------------------------------------------------------
def build_hand(side, wrist, palm_center, tag):
    uv_part(f"WRIST_{tag}", wrist, (0.10, 0.10, 0.10), mat_green, f"WRIST_{tag}")
    uv_part(f"HAND_{tag}_PALM", palm_center, (0.16, 0.12, 0.20), mat_green, f"HAND_{tag}")
    for idx, dz in enumerate([0.07, 0.00, -0.07], start=1):
        uv_part(
            f"HAND_{tag}_DIGIT_{idx}",
            (palm_center[0] + side * 0.02, palm_center[1] + 0.03, palm_center[2] + dz),
            (0.045, 0.030, 0.050),
            mat_green,
            f"DIGIT_{tag}"
        )
    # small thumb mass
    uv_part(f"HAND_{tag}_THUMB", (palm_center[0] - side * 0.06, palm_center[1] + 0.02, palm_center[2] - 0.01), (0.05, 0.04, 0.045), mat_green, f"THUMB_{tag}")


def build_arm(side):
    tag = "L" if side < 0 else "R"
    # preserve the relaxed hanging silhouette but add anatomy
    shoulder = (side * 1.03, 0.00, 1.95)
    elbow = (side * 1.08, 0.04, 1.48)
    wrist = (side * 1.00, 0.07, 1.02)
    palm = (side * 0.96, 0.08, 0.84)

    # rounded shoulder cap
    uv_part(f"SHOULDER_{tag}", shoulder, (0.20, 0.24, 0.23), mat_suit, f"SHOULDER_{tag}")
    capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.15, mat_suit, f"UPPER_ARM_{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.12, 0.13, 0.13), mat_suit, f"ELBOW_{tag}")
    capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.13, mat_suit, f"FOREARM_{tag}")
    build_hand(side, wrist, palm, tag)


def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * 0.40, 0.00, 0.83)
    knee = (side * 0.40, 0.00, 0.52)
    ankle = (side * 0.40, 0.02, 0.23)
    foot = (side * 0.40, 0.02, 0.09)
    toe = (side * 0.40, -0.13, 0.08)

    # upper trouser / thigh shell
    rounded_box(f"LEG_{tag}_SUIT", (side * 0.40, 0.0, 0.56), (0.44, 0.54, 0.56), 0.07, mat_suit, f"LEG_SUIT_{tag}")
    capsule_between(f"CALF_{tag}", knee, ankle, 0.13, mat_green, f"CALF_{tag}")
    uv_part(f"KNEE_{tag}", knee, (0.13, 0.13, 0.13), mat_green, f"KNEE_{tag}")
    uv_part(f"ANKLE_{tag}", ankle, (0.09, 0.10, 0.09), mat_green, f"ANKLE_{tag}")
    uv_part(f"FOOT_{tag}", foot, (0.17, 0.20, 0.12), mat_green, f"FOOT_{tag}")
    uv_part(f"TOE_{tag}", toe, (0.13, 0.08, 0.06), mat_green, f"TOE_{tag}")

build_arm(-1)
build_arm(1)
build_leg(-1)
build_leg(1)

# ------------------------------------------------------------
# 4. FACE - EMBEDDED / PRESERVED CHARACTER LOOK
# ------------------------------------------------------------
def make_eye(name, center, scale):
    # Eye whites slightly intersect into the head so they read as embedded, not sticker tempelan.
    uv_part(name + "_WHITE", (center[0], center[1], center[2]), scale, mat_white, "EYE")
    veins = [
        ((-0.06, 0.10), (-0.10, 0.06), (-0.13, 0.00)),
        ((0.07, 0.09), (0.11, 0.04), (0.13, -0.02)),
        ((-0.02, -0.10), (-0.08, -0.12), (-0.13, -0.08)),
    ]
    for vi, pts2d in enumerate(veins):
        pts = [(center[0] + a*scale[0], center[1] + scale[1] + 0.003, center[2] + b*scale[2]) for a,b in pts2d]
        curve_from_points(f"{name}_VEIN_{vi}", pts, mat_red, 0.0036, "EYE_VEIN")
    uv_part(name + "_PUPIL", (center[0], center[1] + scale[1] + 0.05, center[2]), (scale[0]*0.33, scale[1]*0.16, scale[2]*0.33), mat_pupil, "PUPIL")

make_eye("EYE_TOP", (0.0, 0.73, 3.27), (0.26, 0.16, 0.26))
make_eye("EYE_L", (-0.42, 0.73, 2.77), (0.28, 0.16, 0.28))
make_eye("EYE_R", (0.42, 0.73, 2.77), (0.28, 0.16, 0.28))

rounded_box("TOOTH_L", (-0.13, 0.77, 2.26), (0.10, 0.04, 0.12), 0.02, mat_tooth, "MOUTH")
rounded_box("TOOTH_R", (0.13, 0.77, 2.26), (0.10, 0.04, 0.12), 0.02, mat_tooth, "MOUTH")

# ------------------------------------------------------------
# 5. FOREHEAD ZIPPER / SEAM (PRESERVE)
# ------------------------------------------------------------
cyl_part("HEAD_SEAM_BAR", (0, 0.77, 3.92), 0.035, 1.46, mat_black, "HEAD_SEAM", rotation=(math.radians(90),0,math.radians(90)))
for i, x in enumerate([v/100 for v in range(-66, 67, 12)]):
    cyl_part(f"SEAM_TOOTH_{i}", (x, 0.78, 3.92), 0.012, 0.12, mat_black, "HEAD_SEAM", rotation=(math.radians(25),0,0))

# ------------------------------------------------------------
# 6. SIDE BOLTS / ELECTRODES (PRESERVE)
# ------------------------------------------------------------
def bolt_assembly(side=1):
    x = side * 1.20
    cyl_part(f"BOLT_BASE_{'R' if side>0 else 'L'}", (x, 0.0, 3.26), 0.16, 0.12, mat_bolt_dark, "BOLT", rotation=(0, math.radians(90), 0))
    cyl_part(f"BOLT_TIP_{'R' if side>0 else 'L'}", (side*1.30, 0.0, 3.26), 0.11, 0.20, mat_bolt_light, "BOLT", rotation=(0, math.radians(90), 0))
    cyl_part(f"BOLT_CAP_{'R' if side>0 else 'L'}", (side*1.36, 0.0, 3.26), 0.07, 0.08, mat_bolt_dark, "BOLT", rotation=(0, math.radians(90), 0))

bolt_assembly(-1)
bolt_assembly(1)

# ------------------------------------------------------------
# 7. GREEN UNDERLAYER REVEAL + LEG LOGO (PRESERVE)
# ------------------------------------------------------------
for i, loc in enumerate([(-0.84, 0.51, 1.66), (0.81, 0.49, 1.63), (0.70, -0.42, 1.74)]):
    uv_part(f"TEAR_REVEAL_{i}", loc, (0.14, 0.02, 0.16), mat_green, "SUIT_TEAR_REVEAL")

for i, (x, z) in enumerate([(-1.03, 0.78), (-1.02, 0.58), (1.03, 0.78), (1.02, 0.58)]):
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.07, radius2=0.01, depth=0.22,
                                    location=(x, 0.02, z), rotation=(math.radians(90), math.radians(90 if x<0 else -90), 0))
    notch = bpy.context.object
    notch.name = f"SIDE_NOTCH_{i}"
    notch.scale.y = 1.8
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean_difference(suit_shell, notch)

curve_from_points("LEG_S_UP", [(0.53, 0.29, 0.68), (0.46, 0.29, 0.76), (0.56, 0.29, 0.82)], mat_green, 0.014, "LEG_LOGO")
curve_from_points("LEG_S_LOW", [(0.56, 0.29, 0.82), (0.66, 0.29, 0.88), (0.54, 0.29, 0.96)], mat_green, 0.014, "LEG_LOGO")

# ------------------------------------------------------------
# 8. LIGHTING / CAMERA / EXPORT
# ------------------------------------------------------------
def add_area(name, loc, energy, size, color=(1,1,1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.data.color = color
    return light

add_area("KEY", (-4.7,-5.3,7.4), 1100, 5.0)
add_area("FILL", (4.5,-3.1,4.4), 650, 4.0)
add_area("RIM", (0.0,4.8,6.8), 900, 4.2)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.96,0.96,0.96,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.82

bpy.ops.object.camera_add(location=(0,-8.2,2.1))
cam = bpy.context.object
cam.name = "TSA_CAMERA"
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
bpy.context.scene.camera = cam


def point_camera(camera, location, target=(0,0,2.0)):
    camera.location = location
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = RENDER_RES
scene.render.resolution_y = RENDER_RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False

try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass

views = {
    "front": ((0,-8.2,2.10),(0,0,2.0)),
    "three_q_l": ((-6.4,-6.4,2.35),(0,0,2.0)),
    "left": ((-8.2,0,2.1),(0,0,2.0)),
    "back": ((0,8.2,2.1),(0,0,2.0)),
    "right": ((8.2,0,2.1),(0,0,2.0)),
    "three_q_r": ((6.4,-6.4,2.35),(0,0,2.0)),
    "top": ((0,0,10.0),(0,0,2.0)),
    "bottom": ((0,0,-7.0),(0,0,1.35)),
}

spec = {
    "character": "ALIF",
    "version": "TSA_CHARACTER_009_V2_TSA_ANATOMY_FACE_LOCK",
    "source_strategy": "Alif V1 preserved for head, face identity, bolts, zipper seam, suit shell, tie, and real suit tears. Arms and legs rebuilt to TSA anatomy lock.",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "family_base": {
        "HEAD_W": HEAD_W,
        "HEAD_D": HEAD_D,
        "HEAD_H": HEAD_H,
        "TORSO_W": TORSO_W,
        "TORSO_D": TORSO_D,
        "TORSO_H": TORSO_H
    },
    "locked_preserve": {
        "three_bloodshot_eyes": True,
        "frankenstein_side_bolts": True,
        "forehead_zipper_seam": True,
        "black_suit": True,
        "red_tie": True,
        "ragged_hem": True,
        "torn_suit_openings_are_true_holes": True,
        "green_underlayer_visible_through_holes": True,
        "body_face_clothing_identity_preserved": True
    },
    "tsa_locks": {
        "anatomy_rule": "Arms must read as shoulder-upperarm-elbow-forearm-wrist-hand; legs must read as thigh-knee-calf-ankle-foot.",
        "face_rule": "Eyes must read as embedded facial forms, not flat stickers.",
        "suit_damage_rule": "All tears and holes in the black suit must be true cut-through geometry via boolean subtraction, never decal-like tempelan.",
        "tear_depth_rule": "Inner green torso/body must remain visible behind openings so damage reads as cloth thickness + depth."
    },
    "tsa_gate": "FORM_LOCK / ANATOMY_LOCK / FACE_LOCK / SUIT-TEAR_DEPTH_LOCK"
}

with open(OUT_DIR / "alif_spec_v2.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "alif_v2.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "alif_v2.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"alif_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("ALIF TSA CHARACTER 009 - V2 TSA ANATOMY FACE LOCK COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: FORM_LOCK / ANATOMY_LOCK / FACE_LOCK / SUIT-TEAR_DEPTH_LOCK")
print("Lock: suit tears remain true openings; only limbs upgraded for TSA anatomy")
print("="*60)
