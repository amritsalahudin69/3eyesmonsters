
# GALIH - TSA Character Reconstruction V1
# Blender 5.2 LTS
# Goal: static canonical Galih model from supplied turnaround.
# Base family: Rangga canonical rounded-box body language.
# TSA gate: STATIC MODEL / FACE FORM LOCK.
# No rig / animation yet.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "galih_output_v5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.75

# ============================================================
# RANGGA-FAMILY BASE PROPORTIONS
# ============================================================
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

BODY_RED = (0.90, 0.08, 0.06, 1.0)
SHADOW_RED = (0.66, 0.035, 0.025, 1.0)
EYE_WHITE = (0.98, 0.98, 0.98, 1.0)
PUPIL_DARK = (0.05, 0.045, 0.07, 1.0)
TOOTH = (0.94, 0.89, 0.76, 1.0)
BLACK = (0.025, 0.025, 0.025, 1.0)

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def make_mat(name, color, roughness=0.30, metallic=0.0):
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

def apply_bevel(obj, width=0.18, segments=8):
    mod = obj.modifiers.new("TSA_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)

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
        segments=segments, ring_count=rings,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def cone_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=48):
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

def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64):
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

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 5
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 5

    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(pts)-1)

    for bp, p in zip(spline.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def cone_along(name, start, end, radius, material, region):
    """
    Create a cone whose local Z axis follows start -> end.
    Pointed tip is toward 'end'.
    """
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    depth = direction.length
    midpoint = (start_v + end_v) * 0.5

    bpy.ops.mesh.primitive_cone_add(
        vertices=48,
        radius1=radius,
        radius2=0.01,
        depth=depth,
        location=midpoint
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def add_eye(name, x, z, size, lid_angle=0.0, lid_scale=0.46):
    # TSA V2:
    # eye volume is partially embedded into the face, not mounted as a button.
    eye = uv_part(
        name,
        (x, FRONT_Y + 0.035, z),
        (size, 0.095, size),
        mat_white,
        name
    )

    uv_part(
        name + ".PUPIL",
        (x, FRONT_Y - 0.065, z - 0.015),
        (size*0.35, 0.035, size*0.35),
        mat_pupil,
        name + ".PUPIL"
    )

    # shallow red eyelid: visually part of the face/eye, not a floating lump.
    uv_part(
        name + ".LID",
        (x, FRONT_Y - 0.010, z + size*0.49),
        (size*1.02, 0.040, size*lid_scale),
        mat_red,
        name + ".LID",
        rotation=(0, math.radians(lid_angle), 0)
    )

clean_scene()

mat_red = make_mat("GALIH_RED", BODY_RED, 0.24)
mat_red_shadow = make_mat("GALIH_SHADOW_RED", SHADOW_RED, 0.28)
mat_white = make_mat("GALIH_EYE_WHITE", EYE_WHITE, 0.16)
mat_pupil = make_mat("GALIH_PUPIL", PUPIL_DARK, 0.18)
mat_tooth = make_mat("GALIH_TOOTH", TOOTH, 0.24)
mat_black = make_mat("GALIH_BLACK", BLACK, 0.24)

# ============================================================
# 1. CORE BODY - PRESERVE RANGGA FAMILY
# ============================================================
body = rounded_box(
    "BODY",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.28,
    mat_red,
    "TORSO_HEAD"
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.02, 1.03),
    (1.05, 0.63, 0.78),
    mat_red,
    "TORSO_LOWER"
)

# ============================================================
# GALIH V5 - STANDARD FAMILY ARMS
#
# TSA correction:
# NO trident.
# NO weapon grip.
# NO elbow/finger construction.
#
# Both arms return to the proven rounded hanging-arm language
# used by the other family characters.
#
# Anatomy must read simply:
# shoulder -> single rounded arm volume -> soft hand end.
# ============================================================

# Viewer-left / character-right arm
arm_l = uv_part(
    "ARM.L",
    (-1.17, -0.01, 1.47),
    (0.34, 0.42, 0.80),
    mat_red,
    "ARM.L",
    rotation=(0, math.radians(-8), math.radians(-5))
)

# subtle hand-end volume integrated into arm silhouette
hand_l = uv_part(
    "HAND.L",
    (-1.19, -0.06, 0.98),
    (0.24, 0.25, 0.27),
    mat_red,
    "HAND.L"
)

# Viewer-right / character-left arm
arm_r = uv_part(
    "ARM.R",
    (1.17, -0.01, 1.47),
    (0.34, 0.42, 0.80),
    mat_red,
    "ARM.R",
    rotation=(0, math.radians(8), math.radians(5))
)

# subtle hand-end volume integrated into arm silhouette
hand_r = uv_part(
    "HAND.R",
    (1.19, -0.06, 0.98),
    (0.24, 0.25, 0.27),
    mat_red,
    "HAND.R"
)

leg_l = rounded_box(
    "LEG.L",
    (-0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_red,
    "LEG.L"
)
leg_r = rounded_box(
    "LEG.R",
    (0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_red,
    "LEG.R"
)

FRONT_Y = -(BODY_D / 2.0) - 0.055

# ============================================================
# 2. HORNS - SMALL DEVIL HORNS
# ============================================================
# Curved base + pointed tip. Same body red family.
left_horn_pts = [
    (-0.88, 0.00, 3.58),
    (-0.99, 0.00, 3.77),
    (-0.94, 0.00, 3.95),
]
curve_from_points(
    "HORN.L.BASE",
    left_horn_pts,
    mat_red_shadow,
    0.11,
    "HORN.L"
)
cone_along(
    "HORN.L.TIP",
    (-0.94, 0.00, 3.91),
    (-0.84, 0.00, 4.14),
    0.14,
    mat_red_shadow,
    "HORN.L"
)

right_horn_pts = [
    (0.88, 0.00, 3.58),
    (0.99, 0.00, 3.77),
    (0.94, 0.00, 3.95),
]
curve_from_points(
    "HORN.R.BASE",
    right_horn_pts,
    mat_red_shadow,
    0.11,
    "HORN.R"
)
cone_along(
    "HORN.R.TIP",
    (0.94, 0.00, 3.91),
    (0.84, 0.00, 4.14),
    0.14,
    mat_red_shadow,
    "HORN.R"
)

# ============================================================
# 3. FACE FORM LOCK - 3 EYES / ANGRY LIDS / FANGS
# ============================================================
add_eye("EYE.TOP", 0.00, 2.91, 0.30, lid_angle=0.0, lid_scale=0.43)
add_eye("EYE.LEFT", -0.52, 2.34, 0.30, lid_angle=-18.0, lid_scale=0.44)
add_eye("EYE.RIGHT", 0.52, 2.34, 0.30, lid_angle=18.0, lid_scale=0.44)

# ============================================================
# V2 MOUTH ASSEMBLY
# Mouth is one semantic structure:
# mouth backing -> lip/slit -> fang bases overlap backing -> tips descend.
# ============================================================

# shallow recessed mouth backing; mostly hidden, but gives the fangs a real anchor
rounded_box(
    "MOUTH.BACKING",
    (0.0, FRONT_Y - 0.045, 1.84),
    (1.08, 0.055, 0.16),
    0.055,
    mat_red_shadow,
    "MOUTH"
)

# frown lip line sits on top of backing
mouth_pts = []
for i in range(42):
    t = i / 41
    x = -0.45 + 0.90*t
    z = 1.87 + 0.035*math.sin(t*math.pi)
    mouth_pts.append((x, FRONT_Y - 0.090, z))
curve_from_points(
    "MOUTH.LIP",
    mouth_pts,
    mat_red_shadow,
    0.022,
    "MOUTH"
)

# Fang bases overlap the mouth backing.
# Shorter and slightly inward so they read as teeth, not hanging ornaments.
cone_part(
    "FANG.L",
    (-0.38, FRONT_Y - 0.095, 1.785),
    0.075, 0.21,
    mat_tooth,
    "FANG.L",
    rotation=(math.radians(180),0,0),
    vertices=48
)
cone_part(
    "FANG.R",
    (0.38, FRONT_Y - 0.095, 1.785),
    0.075, 0.21,
    mat_tooth,
    "FANG.R",
    rotation=(math.radians(180),0,0),
    vertices=48
)

# ============================================================
# 4. STANDARD HAND STATE
# ============================================================
# Trident removed by design.
# Both hands use family baseline and remain empty.
# No weapon geometry, no grip fingers, no special wrist chain.

# ============================================================
# 5. DEVIL TAIL - TRUE 3D CURVE + ARROW TIP
# ============================================================
tail_pts = [
    (0.70, 0.55, 0.92),   # attachment behind body
    (1.08, 0.63, 0.72),
    (1.38, 0.48, 0.66),
    (1.56, 0.16, 0.80),
    (1.48, -0.14, 1.02),
]
curve_from_points(
    "TAIL",
    tail_pts,
    mat_red_shadow,
    0.095,
    "TAIL"
)

# arrowhead points up/right in front/3q silhouette
cone_along(
    "TAIL.ARROW",
    (1.48, -0.14, 1.00),
    (1.72, -0.20, 1.22),
    0.20,
    mat_red_shadow,
    "TAIL"
)

# ============================================================
# 6. SMALL FRONT MARKS
# ============================================================
# tiny belly logo approximation
logo_y = FRONT_Y - 0.055
logo_pts = []
for i in range(28):
    t = i/27
    x = -0.25 + 0.50*t
    z = 0.73 + 0.028*math.sin(t*math.pi*4)
    logo_pts.append((x, logo_y, z))

curve_from_points(
    "BELLY.LOGO",
    logo_pts,
    mat_black,
    0.022,
    "BELLY_LOGO"
)

# simple S-like leg mark on character-left leg (viewer-right)
s_pts = [
    (0.63, FRONT_Y - 0.015, 0.62),
    (0.77, FRONT_Y - 0.018, 0.68),
    (0.72, FRONT_Y - 0.018, 0.78),
    (0.58, FRONT_Y - 0.018, 0.82),
]
curve_from_points(
    "LEG.MARK",
    s_pts,
    mat_black,
    0.020,
    "LEG_MARK"
)

# ============================================================
# 7. LIGHTING / CAMERA
# ============================================================
def add_area(name, loc, energy, size, color=(1,1,1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.data.color = color
    return light

add_area("KEY", (-4.5, -5.5, 7.5), 1000, 5.0)
add_area("FILL", (4.5, -3.0, 4.0), 650, 4.0)
add_area("RIM", (0.0, 4.5, 6.5), 900, 4.0)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.96,0.96,0.96,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75

bpy.ops.object.camera_add(location=(0,-8,2.1))
cam = bpy.context.object
cam.name = "TSA_CAMERA"
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
bpy.context.scene.camera = cam

def point_camera(camera, location, target=(0,0,2.05)):
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
    "front": ((0,-8.0,2.15),(0,0,2.05)),
    "three_q_l": ((-6.3,-6.3,2.45),(0,0,2.05)),
    "left": ((-8.0,0,2.15),(0,0,2.05)),
    "back": ((0,8.0,2.15),(0,0,2.05)),
    "right": ((8.0,0,2.15),(0,0,2.05)),
    "three_q_r": ((6.3,-6.3,2.45),(0,0,2.05)),
    "top": ((0,0,10.0),(0,0,1.95)),
    "bottom": ((0,0,-7.0),(0,0,1.55)),
}

spec = {
    "character": "GALIH",
    "version": "TSA_CHARACTER_008_V5_STANDARD_ARMS_NO_TRIDENT",
    "source_strategy": "V4 body/face/horns/tail preserved; trident and special weapon-hand construction removed; both arms restored to standard family baseline",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "family_base": {
        "BODY_W": BODY_W,
        "BODY_D": BODY_D,
        "BODY_H": BODY_H,
        "BODY_Z": BODY_Z
    },
    "galih_features": {
        "three_eyes": True,
        "angry_red_eyelids": True,
        "mouth_fangs": True,
        "mouth_backing_anchor": True,
        "embedded_face_parts": True,
        "two_small_horns": True,
        "devil_tail_arrow_tip": True,
        "trident": False,
        "standard_empty_hands": True,
        "arm_pose": "standard relaxed hanging arms matching family baseline",
        "character_left_hand_on_hip": True
    },
    "face_rule": "mouth/fangs remain inside exclusive face zone; no accessory crosses face",
    "hand_rule": "both hands are empty standard family hands; no weapon-specific wrist/finger chain",
    "tsa_gate": "STATIC_MODEL_FORM_LOCK",
    "face_gate": "FACE_FORM_LOCK"
}

with open(OUT_DIR / "galih_spec_v5.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "galih_v5.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "galih_v5.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"galih_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("GALIH TSA CHARACTER 008 - V5 STANDARD ARMS / NO TRIDENT COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gates: STATIC MODEL FORM LOCK + FACE FORM LOCK")
print("="*60)
