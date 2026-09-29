# GALIH - TSA Character Reconstruction V6
# Blender 5.2 LTS
# Goal: preserve Galih V5 exactly in spirit (body, face, horns, tail, front marks),
# and change ONLY the arms/hands and legs/feet so they follow TSA anatomy lock.
# No trident. No extra accessory. No other redesign.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "galih_output_v6"
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

FRONT_Y = -(BODY_D / 2.0) - 0.055

# ============================================================
# HELPERS
# ============================================================
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


def capsule_between(name, a, b, radius, material, region):
    a = Vector(a)
    b = Vector(b)
    mid = (a + b) * 0.5
    vec = b - a
    cyl = cyl_part(name, tuple(mid), radius, vec.length, material, region)
    cyl.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    uv_part(name + ".CAP_A", tuple(a), (radius, radius, radius), material, region)
    uv_part(name + ".CAP_B", tuple(b), (radius, radius, radius), material, region)
    return cyl


def add_eye(name, x, z, size, lid_angle=0.0, lid_scale=0.46):
    uv_part(name, (x, FRONT_Y + 0.035, z), (size, 0.095, size), mat_white, name)
    uv_part(name + ".PUPIL", (x, FRONT_Y - 0.065, z - 0.015), (size*0.35, 0.035, size*0.35), mat_pupil, name + ".PUPIL")
    uv_part(
        name + ".LID",
        (x, FRONT_Y - 0.010, z + size*0.49),
        (size*1.02, 0.040, size*lid_scale),
        mat_red,
        name + ".LID",
        rotation=(0, math.radians(lid_angle), 0)
    )

# ============================================================
# TSA LIMB REBUILD HELPERS
# ============================================================
def build_standard_hand(side, wrist, palm, tag):
    # a readable wrist + palm + soft digit mass, not a simple oval arm ending
    uv_part(f"WRIST.{tag}", wrist, (0.11, 0.11, 0.10), mat_red, f"WRIST.{tag}")
    uv_part(f"HAND.{tag}.PALM", palm, (0.17, 0.14, 0.22), mat_red, f"HAND.{tag}")
    for idx, dz in enumerate([0.08, 0.00, -0.08], start=1):
        uv_part(
            f"HAND.{tag}.DIGIT.{idx}",
            (palm[0] + side * 0.015, palm[1] - 0.02, palm[2] + dz),
            (0.06, 0.05, 0.06),
            mat_red,
            f"DIGIT.{tag}"
        )


def build_arm(side, pose="down"):
    tag = "L" if side < 0 else "R"
    shoulder = (side * 1.05, 0.00, 1.98)

    if pose == "down":
        elbow = (side * 1.18, 0.00, 1.50)
        wrist = (side * 1.18, -0.03, 1.02)
        palm = (side * 1.17, -0.05, 0.82)
    elif pose == "hip":
        # keep Galih's character-left side a bit bent toward hip without changing the whole character design
        elbow = (side * 1.08, -0.01, 1.50)
        wrist = (side * 0.95, -0.03, 1.04)
        palm = (side * 0.98, -0.04, 0.90)
    else:
        raise ValueError("Unknown arm pose")

    uv_part(f"SHOULDER.{tag}", shoulder, (0.22, 0.25, 0.26), mat_red, f"SHOULDER.{tag}")
    capsule_between(f"UPPER_ARM.{tag}", shoulder, elbow, 0.16, mat_red, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW.{tag}", elbow, (0.14, 0.14, 0.15), mat_red, f"ELBOW.{tag}")
    capsule_between(f"FOREARM.{tag}", elbow, wrist, 0.145, mat_red, f"FOREARM.{tag}")
    build_standard_hand(side, wrist, palm, tag)


def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * 0.57, 0.02, 0.84)
    knee = (side * 0.57, 0.02, 0.50)
    ankle = (side * 0.57, -0.02, 0.21)
    foot = (side * 0.57, -0.15, 0.08)
    toe = (side * 0.57, -0.27, 0.08)

    capsule_between(f"THIGH.{tag}", hip, knee, 0.20, mat_red, f"THIGH.{tag}")
    uv_part(f"KNEE.{tag}", knee, (0.17, 0.17, 0.16), mat_red, f"KNEE.{tag}")
    capsule_between(f"CALF.{tag}", knee, ankle, 0.16, mat_red, f"CALF.{tag}")
    uv_part(f"ANKLE.{tag}", ankle, (0.12, 0.13, 0.10), mat_red, f"ANKLE.{tag}")
    uv_part(f"FOOT.{tag}", foot, (0.22, 0.28, 0.14), mat_red, f"FOOT.{tag}")
    uv_part(f"TOE.{tag}", toe, (0.17, 0.10, 0.08), mat_red, f"TOE.{tag}")


clean_scene()

mat_red = make_mat("GALIH_RED", BODY_RED, 0.24)
mat_red_shadow = make_mat("GALIH_SHADOW_RED", SHADOW_RED, 0.28)
mat_white = make_mat("GALIH_EYE_WHITE", EYE_WHITE, 0.16)
mat_pupil = make_mat("GALIH_PUPIL", PUPIL_DARK, 0.18)
mat_tooth = make_mat("GALIH_TOOTH", TOOTH, 0.24)
mat_black = make_mat("GALIH_BLACK", BLACK, 0.24)

# ============================================================
# 1. CORE BODY - PRESERVED
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
# 2. LIMBS ONLY - REBUILT PER TSA ANATOMY LOCK
# ============================================================
# viewer-left / character-right arm hangs down
build_arm(-1, pose="down")
# viewer-right / character-left arm stays slightly bent toward the hip zone
build_arm(1, pose="hip")

build_leg(-1)
build_leg(1)

# ============================================================
# 3. HORNS - PRESERVED
# ============================================================
left_horn_pts = [
    (-0.88, 0.00, 3.58),
    (-0.99, 0.00, 3.77),
    (-0.94, 0.00, 3.95),
]
curve_from_points("HORN.L.BASE", left_horn_pts, mat_red_shadow, 0.11, "HORN.L")
cone_along("HORN.L.TIP", (-0.94, 0.00, 3.91), (-0.84, 0.00, 4.14), 0.14, mat_red_shadow, "HORN.L")

right_horn_pts = [
    (0.88, 0.00, 3.58),
    (0.99, 0.00, 3.77),
    (0.94, 0.00, 3.95),
]
curve_from_points("HORN.R.BASE", right_horn_pts, mat_red_shadow, 0.11, "HORN.R")
cone_along("HORN.R.TIP", (0.94, 0.00, 3.91), (0.84, 0.00, 4.14), 0.14, mat_red_shadow, "HORN.R")

# ============================================================
# 4. FACE - PRESERVED
# ============================================================
add_eye("EYE.TOP", 0.00, 2.91, 0.30, lid_angle=0.0, lid_scale=0.43)
add_eye("EYE.LEFT", -0.52, 2.34, 0.30, lid_angle=-18.0, lid_scale=0.44)
add_eye("EYE.RIGHT", 0.52, 2.34, 0.30, lid_angle=18.0, lid_scale=0.44)

rounded_box("MOUTH.BACKING", (0.0, FRONT_Y - 0.045, 1.84), (1.08, 0.055, 0.16), 0.055, mat_red_shadow, "MOUTH")

mouth_pts = []
for i in range(42):
    t = i / 41
    x = -0.45 + 0.90*t
    z = 1.87 + 0.035*math.sin(t*math.pi)
    mouth_pts.append((x, FRONT_Y - 0.090, z))
curve_from_points("MOUTH.LIP", mouth_pts, mat_red_shadow, 0.022, "MOUTH")

cone_part("FANG.L", (-0.38, FRONT_Y - 0.095, 1.785), 0.075, 0.21, mat_tooth, "FANG.L", rotation=(math.radians(180),0,0), vertices=48)
cone_part("FANG.R", (0.38, FRONT_Y - 0.095, 1.785), 0.075, 0.21, mat_tooth, "FANG.R", rotation=(math.radians(180),0,0), vertices=48)

# ============================================================
# 5. TAIL - PRESERVED
# ============================================================
tail_pts = [
    (0.70, 0.55, 0.92),
    (1.08, 0.63, 0.72),
    (1.38, 0.48, 0.66),
    (1.56, 0.16, 0.80),
    (1.48, -0.14, 1.02),
]
curve_from_points("TAIL", tail_pts, mat_red_shadow, 0.095, "TAIL")
cone_along("TAIL.ARROW", (1.48, -0.14, 1.00), (1.72, -0.20, 1.22), 0.20, mat_red_shadow, "TAIL")

# ============================================================
# 6. SMALL FRONT MARKS - PRESERVED
# ============================================================
logo_y = FRONT_Y - 0.055
logo_pts = []
for i in range(28):
    t = i/27
    x = -0.25 + 0.50*t
    z = 0.73 + 0.028*math.sin(t*math.pi*4)
    logo_pts.append((x, logo_y, z))
curve_from_points("BELLY.LOGO", logo_pts, mat_black, 0.022, "BELLY_LOGO")

s_pts = [
    (0.63, FRONT_Y - 0.015, 0.62),
    (0.77, FRONT_Y - 0.018, 0.68),
    (0.72, FRONT_Y - 0.018, 0.78),
    (0.58, FRONT_Y - 0.018, 0.82),
]
curve_from_points("LEG.MARK", s_pts, mat_black, 0.020, "LEG_MARK")

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
    "version": "TSA_CHARACTER_008_V6_ANATOMY_LOCK_KEEP_ALL_ELSE",
    "source_strategy": "Galih V5 preserved for body, face, horns, tail, and front marks. Only arms/hands and legs/feet rebuilt to satisfy TSA anatomy lock.",
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
    "locked_preserve": {
        "body": True,
        "lower_volume": True,
        "three_eyes": True,
        "angry_eyelids": True,
        "mouth_and_fangs": True,
        "two_small_horns": True,
        "devil_tail": True,
        "front_marks": True,
        "no_trident": True,
    },
    "limb_rebuild_only": {
        "shoulder_upperarm_elbow_forearm_wrist_hand": True,
        "thigh_knee_calf_ankle_foot": True,
    },
    "tsa_gate": "STATIC_MODEL_FORM_LOCK",
    "face_gate": "FACE_FORM_LOCK",
    "anatomy_gate": "LIMB_ANATOMY_LOCK"
}

with open(OUT_DIR / "galih_spec_v6.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "galih_v6.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "galih_v6.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"galih_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 60)
print("GALIH TSA CHARACTER 008 - V6 ANATOMY LOCK KEEP ALL ELSE COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gates: STATIC MODEL FORM LOCK + FACE FORM LOCK + LIMB ANATOMY LOCK")
print("=" * 60)
