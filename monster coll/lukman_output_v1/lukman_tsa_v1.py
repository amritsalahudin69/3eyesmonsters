
# LUKMAN - TSA Character Reconstruction V1
# Blender 5.2 LTS
# Goal: static canonical Lukman model from supplied turnaround.
# TSA gate: STATIC MODEL / FACE FORM LOCK.
# No rig / animation yet.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "lukman_output_v1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.55

# ------------------------------------------------------------
# FAMILY BASELINE
# Same rounded-box family language as Rangga/Jono/Samsul,
# with Lukman's distinctive jagged top silhouette.
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

GREEN = (0.39, 0.86, 0.66, 1.0)
GREEN_DARK = (0.25, 0.66, 0.49, 1.0)
YELLOW = (1.00, 0.88, 0.36, 1.0)
WHITE = (0.98, 0.98, 0.98, 1.0)
PUPIL = (0.12, 0.07, 0.05, 1.0)
BLACK = (0.035, 0.035, 0.035, 1.0)
ORANGE = (1.00, 0.38, 0.00, 1.0)
SPIKE = (0.78, 0.78, 0.80, 1.0)
RED = (0.90, 0.12, 0.10, 1.0)

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

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 4
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

def create_jagged_crest(name, y_half=0.61):
    """
    Full-depth green crest that overlaps the rounded body.
    This is not a floating decoration: it forms the top silhouette.
    """
    profile = [
        (-1.02, 3.48),
        (-0.88, 3.85),
        (-0.66, 3.72),
        (-0.48, 4.12),
        (-0.30, 3.97),
        ( 0.02, 4.35),  # highest peak
        ( 0.24, 4.15),
        ( 0.62, 3.84),
        ( 0.90, 3.90),
        ( 1.02, 3.58),
        ( 1.02, 3.45),
        (-1.02, 3.45),
    ]

    verts = []
    for y in (-y_half, y_half):
        for x, z in profile:
            verts.append((x, y, z))

    n = len(profile)
    faces = []

    # front/back polygon faces
    faces.append(list(range(n)))
    faces.append(list(range(n, 2*n))[::-1])

    # perimeter side faces
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n+j, n+i))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_green)

    bevel = obj.modifiers.new("TSA_Crest_Bevel", "BEVEL")
    bevel.width = 0.10
    bevel.segments = 5
    bevel.limit_method = 'ANGLE'

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.select_set(False)

    smooth_object(obj)
    return mark_region(obj, "HEAD_CREST")

def add_eye(name, x, z, size):
    uv_part(
        name,
        (x, FRONT_Y, z),
        (size, 0.12, size),
        mat_white,
        name
    )
    uv_part(
        name + ".PUPIL",
        (x, FRONT_Y - 0.13, z - 0.005),
        (size*0.34, 0.05, size*0.34),
        mat_pupil,
        name + ".PUPIL"
    )

clean_scene()

mat_green = make_mat("LUKMAN_GREEN", GREEN, 0.28)
mat_green_dark = make_mat("LUKMAN_GREEN_DARK", GREEN_DARK, 0.30)
mat_yellow = make_mat("LUKMAN_YELLOW", YELLOW, 0.30)
mat_white = make_mat("LUKMAN_WHITE", WHITE, 0.18)
mat_pupil = make_mat("LUKMAN_PUPIL", PUPIL, 0.18)
mat_black = make_mat("LUKMAN_BLACK", BLACK, 0.25)
mat_orange = make_mat("LUKMAN_ORANGE", ORANGE, 0.25)
mat_spike = make_mat("LUKMAN_SPIKE_GREY", SPIKE, 0.28)
mat_red = make_mat("LUKMAN_LOGO_RED", RED, 0.25)

# ============================================================
# 1. CORE BODY / FAMILY SHAPE
# ============================================================
body = rounded_box(
    "BODY",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.28,
    mat_green,
    "TORSO_HEAD"
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.02, 1.02),
    (1.03, 0.63, 0.78),
    mat_green,
    "TORSO_LOWER"
)

create_jagged_crest("HEAD_CREST")

# arms
arm_l = uv_part(
    "ARM.L",
    (-1.17, -0.01, 1.48),
    (0.34, 0.42, 0.82),
    mat_green,
    "ARM.L",
    rotation=(0, math.radians(-8), math.radians(-5))
)
arm_r = uv_part(
    "ARM.R",
    (1.17, -0.01, 1.48),
    (0.34, 0.42, 0.82),
    mat_green,
    "ARM.R",
    rotation=(0, math.radians(8), math.radians(5))
)

# short feet/legs
leg_l = rounded_box(
    "LEG.L",
    (-0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_green,
    "LEG.L"
)
leg_r = rounded_box(
    "LEG.R",
    (0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_green,
    "LEG.R"
)

# back nub
uv_part(
    "BACK_NUB",
    (0.0, 0.73, 0.95),
    (0.18, 0.16, 0.18),
    mat_green_dark,
    "BACK_DETAIL"
)

FRONT_Y = -(BODY_D / 2.0) - 0.055

# ============================================================
# 2. FACE FORM LOCK
# ============================================================
add_eye("EYE.TOP", 0.00, 2.90, 0.29)
add_eye("EYE.LEFT", -0.52, 2.34, 0.30)
add_eye("EYE.RIGHT", 0.52, 2.34, 0.30)

# stitched mouth seam
mouth_z = 1.98
curve_from_points(
    "MOUTH.SEAM",
    [(-0.58, FRONT_Y - 0.10, mouth_z),
     ( 0.58, FRONT_Y - 0.10, mouth_z)],
    mat_black,
    0.018,
    "MOUTH"
)

# individual vertical stitches
stitch_xs = [-0.50,-0.39,-0.28,-0.17,-0.06,0.06,0.17,0.28,0.39,0.50]
for i, x in enumerate(stitch_xs, start=1):
    curve_from_points(
        f"MOUTH.STITCH.{i}",
        [(x, FRONT_Y - 0.115, mouth_z - 0.065),
         (x, FRONT_Y - 0.115, mouth_z + 0.065)],
        mat_black,
        0.015,
        "MOUTH_STITCH"
    )

# ============================================================
# 3. BELLY PATCH
# ============================================================
belly = uv_part(
    "BELLY_PATCH",
    (0.0, FRONT_Y - 0.015, 1.12),
    (0.74, 0.10, 0.72),
    mat_yellow,
    "BELLY_PATCH"
)

# ============================================================
# 4. ZIPPER
# ============================================================
zip_y = FRONT_Y - 0.145

# vertical black zipper line
curve_from_points(
    "ZIPPER.CENTER",
    [(0.0, zip_y, 1.75),
     (0.0, zip_y, 1.10)],
    mat_black,
    0.026,
    "ZIPPER"
)

# short zipper teeth
for i, z in enumerate([1.70,1.60,1.50,1.40,1.30,1.20], start=1):
    direction = -1 if i % 2 == 0 else 1
    curve_from_points(
        f"ZIPPER.TOOTH.{i}",
        [(-0.095, zip_y, z + 0.025*direction),
         ( 0.095, zip_y, z - 0.025*direction)],
        mat_black,
        0.022,
        "ZIPPER"
    )

# orange slider
rounded_box(
    "ZIPPER.SLIDER",
    (0.0, zip_y - 0.015, 1.08),
    (0.26, 0.11, 0.22),
    0.06,
    mat_orange,
    "ZIPPER_PULL"
)

# orange elongated pull loop
curve_from_points(
    "ZIPPER.PULL_LOOP",
    [
        (-0.14, zip_y - 0.025, 1.02),
        (-0.18, zip_y - 0.025, 0.78),
        (-0.13, zip_y - 0.025, 0.57),
        ( 0.13, zip_y - 0.025, 0.57),
        ( 0.18, zip_y - 0.025, 0.78),
        ( 0.14, zip_y - 0.025, 1.02),
    ],
    mat_orange,
    0.055,
    "ZIPPER_PULL",
    cyclic=True
)

# ============================================================
# 5. HAND SPIKES / CLAWS
# ============================================================
# Three grey claws on each arm, angled outward and slightly downward.
# Character-left side (viewer-left)
for idx, (z, dz) in enumerate([(1.45,0.12),(1.24,0.02),(1.03,-0.08)], start=1):
    cone_part(
        f"CLAW.L.{idx}",
        (-1.48, -0.01, z),
        0.10,
        0.46,
        mat_spike,
        "CLAW.L",
        rotation=(0, math.radians(-90), math.radians(-10 + idx*3)),
        vertices=48
    )

# Character-right side
for idx, (z, dz) in enumerate([(1.45,0.12),(1.24,0.02),(1.03,-0.08)], start=1):
    cone_part(
        f"CLAW.R.{idx}",
        (1.48, -0.01, z),
        0.10,
        0.46,
        mat_spike,
        "CLAW.R",
        rotation=(0, math.radians(90), math.radians(10 - idx*3)),
        vertices=48
    )

# ============================================================
# 6. LOGO DETAIL
# ============================================================
# compact black abstract logo at upper-left belly edge
logo_y = FRONT_Y - 0.14

for row, z in enumerate((1.64, 1.56), start=1):
    pts = []
    for i in range(30):
        t = i/29
        x = -0.70 + 0.38*t
        zz = z + 0.035*math.sin(t*math.pi*4)
        pts.append((x, logo_y, zz))
    curve_from_points(
        f"LOGO.BLACK.{row}",
        pts,
        mat_black,
        0.024,
        "BELLY_LOGO"
    )

curve_from_points(
    "LOGO.RED_ACCENT",
    [(-0.74, logo_y, 1.64),(-0.69, logo_y, 1.69),(-0.64, logo_y, 1.66)],
    mat_red,
    0.026,
    "BELLY_LOGO"
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

add_area("KEY", (-4.5,-5.5,7.5), 1000, 5.0)
add_area("FILL", (4.5,-3.0,4.0), 650, 4.0)
add_area("RIM", (0.0,4.5,6.5), 900, 4.0)

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
    "character": "LUKMAN",
    "version": "TSA_CHARACTER_007_V1",
    "source_strategy": "Rangga-family rounded body + Lukman jagged crest and zipper/claw cosmetics",
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
    "lukman_features": {
        "jagged_top_crest": True,
        "three_eyes": True,
        "stitched_mouth": True,
        "yellow_belly_patch": True,
        "vertical_zipper": True,
        "orange_puller": True,
        "three_claws_each_side": True,
        "back_nub": True
    },
    "face_gate": "FACE_FORM_LOCK",
    "tsa_gate": "STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR / "lukman_spec_v1.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "lukman_v1.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "lukman_v1.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"lukman_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("LUKMAN TSA CHARACTER 007 - STATIC V1 COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FACE FORM LOCK")
print("="*60)
