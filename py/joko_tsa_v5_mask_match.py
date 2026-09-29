# JOKO - TSA Character Reconstruction V5
# Blender 5.2 LTS
# Goal: refine Joko mask geometry to match turnaround baseline.
# Gate: STATIC MODEL / FORM LOCK only.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "joko_output_v5"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RENDER_RES = 1024
ORTHO_SCALE = 5.45

# RANGGA FAMILY BASE
BASE_W = 2.20
BASE_D = 1.34

# JOKO MAIN PROPORTIONS
HEAD_W = 2.20
HEAD_D = 1.34
HEAD_H = 1.84
HEAD_Z = 3.24
HEAD_FRONT_Y = -(HEAD_D / 2.0)

TORSO_W = 2.08
TORSO_D = 1.30
TORSO_H = 1.34
TORSO_Z = 1.98

PANTS_W = 2.12
PANTS_D = 1.28
PANTS_H = 0.82
PANTS_Z = 0.98

LEG_W = 0.58
LEG_D = 0.72
LEG_H = 0.88
LEG_Z = 0.43

# COLORS
YELLOW = (1.00, 0.82, 0.08, 1.0)
BLACK = (0.018, 0.016, 0.016, 1.0)
BLACK_SOFT = (0.035, 0.030, 0.035, 1.0)
BLUE = (0.055, 0.27, 0.72, 1.0)
RED = (0.90, 0.035, 0.025, 1.0)
GREY = (0.76, 0.76, 0.78, 1.0)
WHITE = (0.97, 0.97, 0.97, 1.0)
IRIS = (0.23, 0.08, 0.28, 1.0)
LINE = (0.055, 0.050, 0.050, 1.0)


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
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def curve_from_points(name, pts, material, bevel_depth, region):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 3
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 5
    spline = curve.splines.new('POLY')
    spline.points.add(len(pts)-1)
    for i, p in enumerate(pts):
        spline.points[i].co = (*p, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def prism_from_xz_profile(name, profile_xz, y_front, thickness, material, region):
    """Extrude an X/Z profile backward (+Y) to make a shallow custom prism."""
    verts = []
    for x, z in profile_xz:
        verts.append((x, y_front, z))
    for x, z in profile_xz:
        verts.append((x, y_front + thickness, z))

    n = len(profile_xz)
    faces = []
    faces.append(tuple(range(n)))
    faces.append(tuple(range(n, 2*n))[::-1])
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n+j, n+i))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    smooth_object(obj)
    return mark_region(obj, region)


def eye(name, x, z, size, lid_tilt=0.0):
    white = uv_part(name, (x, HEAD_FRONT_Y - 0.075, z), (size, 0.12, size), mat_white, name)
    iris = uv_part(name + ".IRIS", (x, HEAD_FRONT_Y - 0.200, z - 0.004),
                   (size*0.38, 0.05, size*0.38), mat_iris, name + ".IRIS")
    lid = uv_part(name + ".LID", (x, HEAD_FRONT_Y - 0.105, z + size*0.41),
                  (size*1.02, 0.06, size*0.47), mat_black_soft, name + ".LID",
                  rotation=(math.radians(lid_tilt), 0, 0))
    return white, iris, lid


clean_scene()

mat_yellow = make_mat("JOKO_YELLOW", YELLOW, 0.28)
mat_black = make_mat("JOKO_BLACK", BLACK, 0.20)
mat_black_soft = make_mat("JOKO_MASK", BLACK_SOFT, 0.24)
mat_blue = make_mat("JOKO_BLUE", BLUE, 0.26)
mat_red = make_mat("JOKO_RED", RED, 0.24)
mat_grey = make_mat("JOKO_GREY", GREY, 0.34)
mat_white = make_mat("JOKO_WHITE", WHITE, 0.18)
mat_iris = make_mat("JOKO_IRIS", IRIS, 0.20)
mat_line = make_mat("JOKO_LINE", LINE, 0.30)

# ============================================================
# 1. BLACK HEAD SHELL = full top/back/side mask
# ============================================================
head_shell = rounded_box(
    "HEAD_SHELL", (0, 0, HEAD_Z), (HEAD_W, HEAD_D, HEAD_H), 0.24,
    mat_black, "HEAD_SHELL"
)

# Integrated side peaks/wings: not detached cones.
left_peak_profile = [
    (-1.03, 4.03),
    (-0.94, 4.72),
    (-0.69, 4.10),
    (-0.74, 3.96),
]
right_peak_profile = [(-x, z) for x, z in reversed(left_peak_profile)]

peak_l = prism_from_xz_profile("MASK_PEAK.L", left_peak_profile, -0.60, 1.20, mat_black, "MASK_PEAK.L")
peak_r = prism_from_xz_profile("MASK_PEAK.R", right_peak_profile, -0.60, 1.20, mat_black, "MASK_PEAK.R")

# ============================================================
# 2. YELLOW FRONT AREAS ONLY
# This is the key mask correction.
# ============================================================
# forehead patch behind top eye
forehead = rounded_box(
    "FOREHEAD_YELLOW", (0.0, HEAD_FRONT_Y - 0.015, 3.79),
    (1.08, 0.16, 0.64), 0.10, mat_yellow, "FOREHEAD_YELLOW"
)

# narrow center bridge that tapers downward between the two lower eyes
bridge_profile = [
    (-0.18, 3.55),
    ( 0.18, 3.55),
    ( 0.11, 3.06),
    ( 0.00, 2.90),
    (-0.11, 3.06),
]
face_bridge = prism_from_xz_profile(
    "FACE_BRIDGE", bridge_profile, HEAD_FRONT_Y - 0.045, 0.16,
    mat_yellow, "FACE_BRIDGE"
)

# ============================================================
# 3. FACE
# top eye on yellow; lower pair sit over black mask field
# ============================================================
eye("EYE.TOP",   0.00, 3.78, 0.28, 0)
eye("EYE.LEFT", -0.48, 3.25, 0.29, -12)
eye("EYE.RIGHT", 0.48, 3.25, 0.29, 12)

mouth_plate = rounded_box(
    "MOUTH_PLATE", (0.0, HEAD_FRONT_Y - 0.03, 2.69),
    (1.46, 0.18, 0.46), 0.10, mat_grey, "MOUTH_PLATE"
)

mouth_pts = []
for i in range(34):
    t = i / 33
    x = -0.36 + 0.72 * t
    z = 2.66 + 0.026 * math.sin(t * math.pi)
    mouth_pts.append((x, HEAD_FRONT_Y - 0.13, z))
curve_from_points("MOUTH_LINE", mouth_pts, mat_line, 0.017, "MOUTH_LINE")

# ============================================================
# 4. BODY = RANGGA FAMILY / visually connected to head
# ============================================================
torso = rounded_box(
    "TORSO", (0, 0, TORSO_Z), (TORSO_W, TORSO_D, TORSO_H), 0.24,
    mat_yellow, "TORSO"
)

# tiny connection overlap hidden behind head/body boundary
neck_fill = rounded_box(
    "NECK_FILL", (0.0, 0.0, 2.44), (1.78, 1.08, 0.20), 0.06,
    mat_yellow, "NECK_FILL"
)

pants = rounded_box(
    "PANTS", (0, 0.02, PANTS_Z), (PANTS_W, PANTS_D, PANTS_H), 0.34,
    mat_blue, "PANTS"
)

# ============================================================
# 5. BELT
# ============================================================
belt_z = 1.38
belt_front = rounded_box("BELT.FRONT", (0, -(TORSO_D/2)-0.065, belt_z),
                         (2.12, 0.14, 0.22), 0.05, mat_red, "BELT")
belt_back = rounded_box("BELT.BACK", (0, (TORSO_D/2)+0.065, belt_z),
                        (2.12, 0.14, 0.22), 0.05, mat_red, "BELT")
belt_l = rounded_box("BELT.L", (-1.02, 0, belt_z),
                     (0.14, 1.22, 0.22), 0.04, mat_red, "BELT")
belt_r = rounded_box("BELT.R", (1.02, 0, belt_z),
                     (0.14, 1.22, 0.22), 0.04, mat_red, "BELT")
buckle = rounded_box("BELT.BUCKLE", (0, -(TORSO_D/2)-0.15, belt_z),
                     (0.48, 0.18, 0.30), 0.06, mat_red, "BELT.BUCKLE")

# ============================================================
# 6. ARMS / GLOVES / CLAWS
# claws hang DOWNWARD and are side-by-side, not sideways.
# ============================================================
arm_l = uv_part("ARM.L", (-1.18, 0.0, 1.84), (0.34, 0.40, 0.70), mat_yellow, "ARM.L",
                rotation=(0, math.radians(-6), math.radians(-4)))
arm_r = uv_part("ARM.R", ( 1.18, 0.0, 1.84), (0.34, 0.40, 0.70), mat_yellow, "ARM.R",
                rotation=(0, math.radians(6), math.radians(4)))

glove_l = uv_part("GLOVE.L", (-1.23, -0.02, 1.14), (0.30, 0.33, 0.34), mat_blue, "GLOVE.L")
glove_r = uv_part("GLOVE.R", ( 1.23, -0.02, 1.14), (0.30, 0.33, 0.34), mat_blue, "GLOVE.R")

# left hand fingers to the OUTSIDE of left glove; right mirrored
for idx, x in enumerate((-1.43, -1.52, -1.61), start=1):
    uv_part(f"CLAW.L.{idx}", (x, -0.05, 1.00), (0.055, 0.10, 0.25), mat_grey, "CLAW.L")
for idx, x in enumerate((1.43, 1.52, 1.61), start=1):
    uv_part(f"CLAW.R.{idx}", (x, -0.05, 1.00), (0.055, 0.10, 0.25), mat_grey, "CLAW.R")

# ============================================================
# 7. LEGS
# ============================================================
leg_l = rounded_box("LEG.L", (-0.61, 0.02, LEG_Z), (LEG_W, LEG_D, LEG_H), 0.22, mat_blue, "LEG.L")
leg_r = rounded_box("LEG.R", ( 0.61, 0.02, LEG_Z), (LEG_W, LEG_D, LEG_H), 0.22, mat_blue, "LEG.R")

# ============================================================
# 8. CHEST MARK
# ============================================================
logo_pts = [(-0.14, -(TORSO_D/2)-0.07, 1.99), (-0.05, -(TORSO_D/2)-0.11, 2.06),
            (0.04, -(TORSO_D/2)-0.07, 1.99), (0.13, -(TORSO_D/2)-0.11, 2.06)]
curve_from_points("CHEST_MARK_1", logo_pts, mat_line, 0.025, "CHEST_DETAIL")
logo_pts2 = [(-0.14, -(TORSO_D/2)-0.07, 1.91), (-0.05, -(TORSO_D/2)-0.11, 1.98),
             (0.04, -(TORSO_D/2)-0.07, 1.91), (0.13, -(TORSO_D/2)-0.11, 1.98)]
curve_from_points("CHEST_MARK_2", logo_pts2, mat_line, 0.025, "CHEST_DETAIL")

# ============================================================
# LIGHTING / CAMERA
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


def point_camera(camera, location, target=(0,0,2.15)):
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
    "front": ((0,-8.0,2.20),(0,0,2.10)),
    "three_q_l": ((-6.3,-6.3,2.45),(0,0,2.10)),
    "left": ((-8.0,0,2.20),(0,0,2.10)),
    "back": ((0,8.0,2.20),(0,0,2.10)),
    "right": ((8.0,0,2.20),(0,0,2.10)),
    "three_q_r": ((6.3,-6.3,2.45),(0,0,2.10)),
    "top": ((0,0,10.0),(0,0,1.95)),
    "bottom": ((0,0,-7.0),(0,0,1.55)),
}

spec = {
    "character":"JOKO",
    "version":"TSA_CHARACTER_005_V5_MASK_MATCH",
    "source_strategy":"Rangga family body baseline + full black shell + yellow center mask geometry",
    "coordinate_system":{"front_axis":"-Y","up_axis":"+Z","symmetry_plane":"X=0"},
    "mask_rules":{
        "top_back":"full black",
        "front":"black field with yellow forehead + narrow center bridge",
        "lower_eyes":"sit on black mask field",
        "peaks":"integrated black side peaks, not detached horns"
    },
    "claw_rules":{"orientation":"downward","layout":"parallel vertical fingers side-by-side"},
    "tsa_gate":"STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR / "joko_spec_v5.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "joko_v5.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT_DIR / "joko_v5.glb"), export_format='GLB', export_apply=True, export_animations=False)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"joko_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("JOKO TSA CHARACTER 005 - V5 MASK MATCH COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("="*60)
