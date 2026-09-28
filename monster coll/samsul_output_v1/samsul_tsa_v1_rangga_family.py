
# SAMSUL - TSA Character Reconstruction V1
# Blender 5.2 LTS
# Goal: static canonical Samsul from supplied turnaround.
# Base family: Rangga canonical body language.
# Gate: STATIC MODEL / FORM LOCK only. No rig / animation.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "samsul_output_v1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.65

# ------------------------------------------------------------
# RANGGA FAMILY BASELINE
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

# Samsul palette
PINK = (0.95, 0.42, 0.56, 1.0)
PINK_LID = (0.95, 0.49, 0.62, 1.0)
RED = (0.95, 0.08, 0.08, 1.0)
YELLOW = (1.00, 0.86, 0.14, 1.0)
CREAM = (1.00, 0.93, 0.64, 1.0)
WHITE = (0.98, 0.98, 0.98, 1.0)
PUPIL = (0.13, 0.08, 0.08, 1.0)
CYAN = (0.25, 0.82, 0.92, 1.0)
BLACK = (0.05, 0.04, 0.05, 1.0)
MAGENTA = (0.90, 0.02, 0.40, 1.0)

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

def make_disc_mesh(name, center, radius_x, radius_z, axis='Y', segments=48):
    verts = []
    for i in range(segments):
        a = (i / segments) * math.tau
        if axis == 'Y':       # XZ plane, normal ±Y
            verts.append((center[0] + radius_x*math.cos(a), center[1], center[2] + radius_z*math.sin(a)))
        elif axis == 'X':     # YZ plane, normal ±X
            verts.append((center[0], center[1] + radius_x*math.cos(a), center[2] + radius_z*math.sin(a)))
        elif axis == 'Z':     # XY plane, normal ±Z
            verts.append((center[0] + radius_x*math.cos(a), center[1] + radius_z*math.sin(a), center[2]))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [list(range(segments))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def conform_decal(obj, target, material, region, offset=0.006):
    obj.data.materials.append(material)

    shrink = obj.modifiers.new("TSA_SKIN_CONFORM", "SHRINKWRAP")
    shrink.target = target
    shrink.wrap_method = 'NEAREST_SURFACEPOINT'
    shrink.wrap_mode = 'OUTSIDE_SURFACE'
    shrink.offset = offset

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=shrink.name)
    obj.select_set(False)

    solid = obj.modifiers.new("TSA_DECAL_MICRO_THICKNESS", "SOLIDIFY")
    solid.thickness = 0.004
    solid.offset = 0.0

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solid.name)
    obj.select_set(False)

    return mark_region(obj, region)

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
        (x, FRONT_Y - 0.13, z - 0.018),
        (size*0.36, 0.05, size*0.36),
        mat_pupil,
        name + ".PUPIL"
    )
    uv_part(
        name + ".LID",
        (x, FRONT_Y - 0.025, z + size*0.48),
        (size*1.04, 0.07, size*0.48),
        mat_pink_lid,
        name + ".LID"
    )

clean_scene()

mat_pink = make_mat("SAMSUL_PINK", PINK, 0.28)
mat_pink_lid = make_mat("SAMSUL_PINK_LID", PINK_LID, 0.24)
mat_red = make_mat("SAMSUL_HAT_RED", RED, 0.24)
mat_yellow = make_mat("SAMSUL_YELLOW", YELLOW, 0.26)
mat_cream = make_mat("SAMSUL_CREAM", CREAM, 0.32)
mat_white = make_mat("SAMSUL_WHITE", WHITE, 0.18)
mat_pupil = make_mat("SAMSUL_PUPIL", PUPIL, 0.20)
mat_cyan = make_mat("SAMSUL_DROPLET", CYAN, 0.22)
mat_black = make_mat("SAMSUL_BLACK", BLACK, 0.28)
mat_magenta = make_mat("SAMSUL_MAGENTA", MAGENTA, 0.24)

# ============================================================
# 1. CORE BODY - RANGGA FAMILY SILHOUETTE
# ============================================================
body = rounded_box(
    "BODY",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.30,
    mat_pink,
    "TORSO_HEAD"
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.02, 1.02),
    (1.05, 0.63, 0.78),
    mat_pink,
    "TORSO_LOWER"
)

arm_l = uv_part(
    "ARM.L",
    (-1.18, -0.01, 1.48),
    (0.34, 0.42, 0.82),
    mat_pink,
    "ARM.L",
    rotation=(0, math.radians(-8), math.radians(-5))
)
arm_r = uv_part(
    "ARM.R",
    (1.18, -0.01, 1.48),
    (0.34, 0.42, 0.82),
    mat_pink,
    "ARM.R",
    rotation=(0, math.radians(8), math.radians(5))
)

leg_l = rounded_box(
    "LEG.L",
    (-0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_pink,
    "LEG.L"
)
leg_r = rounded_box(
    "LEG.R",
    (0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_pink,
    "LEG.R"
)

# back nub
uv_part(
    "BACK_NUB",
    (0.0, 0.73, 0.93),
    (0.17, 0.16, 0.17),
    mat_pink,
    "BACK_DETAIL"
)

FRONT_Y = -(BODY_D / 2.0) - 0.055

# ============================================================
# 2. FACE FORM LOCK
# ============================================================
add_eye("EYE.TOP", 0.00, 2.86, 0.29)
add_eye("EYE.LEFT", -0.52, 2.31, 0.30)
add_eye("EYE.RIGHT", 0.52, 2.31, 0.30)

# nose base
uv_part(
    "NOSE.BASE",
    (0.0, FRONT_Y - 0.06, 1.96),
    (0.12, 0.065, 0.09),
    mat_pink_lid,
    "NOSE"
)

# blue droplet, clearly anchored under nose
uv_part(
    "NOSE.DROPLET",
    (0.0, FRONT_Y - 0.13, 1.78),
    (0.14, 0.09, 0.27),
    mat_cyan,
    "NOSE.DROPLET"
)
cone_part(
    "NOSE.DROPLET_TIP",
    (0.0, FRONT_Y - 0.13, 2.00),
    0.085, 0.18,
    mat_cyan,
    "NOSE.DROPLET",
    rotation=(math.radians(180),0,0)
)

# mouth cavity
mouth_cavity = rounded_box(
    "MOUTH.CAVITY",
    (0.0, FRONT_Y - 0.09, 1.73),
    (1.32, 0.08, 0.17),
    0.055,
    mat_black,
    "MOUTH"
)

# row of cream triangular teeth attached to mouth line
tooth_xs = [-0.50, -0.36, -0.22, -0.08, 0.08, 0.22, 0.36, 0.50]
for idx, x in enumerate(tooth_xs, start=1):
    cone_part(
        f"TOOTH.{idx}",
        (x, FRONT_Y - 0.145, 1.67),
        0.075,
        0.23,
        mat_cream,
        "TOOTH",
        rotation=(math.radians(180),0,0),
        vertices=3
    )

# ============================================================
# 3. BELLY PATCH + LOGO
# ============================================================
belly = uv_part(
    "BELLY_PATCH",
    (0.0, FRONT_Y - 0.01, 1.05),
    (0.72, 0.10, 0.70),
    mat_cream,
    "BELLY_PATCH"
)

# stylized wavy logo on belly patch
logo_y = FRONT_Y - 0.125
logo_pts = []
for i in range(50):
    t = i / 49
    x = -0.30 + 0.60*t
    z = 1.12 + 0.050*math.sin(t*math.pi*4.0)
    logo_pts.append((x, logo_y, z))
curve_from_points("BELLY_LOGO.BLACK", logo_pts, mat_black, 0.030, "BELLY_LOGO")

# magenta leading accent and dot
curve_from_points(
    "BELLY_LOGO.MAGENTA",
    [(-0.34, logo_y, 1.15), (-0.29, logo_y, 1.09), (-0.24, logo_y, 1.11)],
    mat_magenta,
    0.034,
    "BELLY_LOGO"
)
uv_part(
    "BELLY_LOGO.DOT",
    (0.39, logo_y - 0.01, 1.06),
    (0.055, 0.035, 0.055),
    mat_magenta,
    "BELLY_LOGO"
)

# ============================================================
# 4. RED HAT / BEANIE
# ============================================================
# Dome overlaps the upper head, giving the clean rounded cap silhouette.
hat_dome = uv_part(
    "HAT.DOME",
    (0.0, 0.0, 3.67),
    (1.15, 0.76, 0.63),
    mat_red,
    "HAT"
)

# front brim/band slightly embedded against forehead
hat_band = rounded_box(
    "HAT.BAND",
    (0.0, FRONT_Y - 0.015, 3.29),
    (2.10, 0.12, 0.28),
    0.09,
    mat_red,
    "HAT"
)

# drooping side tip and pom-pom at character-left
hat_tail_pts = [
    (-0.80, 0.00, 3.88),
    (-1.05, -0.02, 3.72),
    (-1.22, -0.02, 3.42),
    (-1.23, -0.04, 3.15),
]
curve_from_points(
    "HAT.TAIL",
    hat_tail_pts,
    mat_red,
    0.13,
    "HAT"
)
uv_part(
    "HAT.POM",
    (-1.24, -0.04, 3.02),
    (0.23, 0.23, 0.23),
    mat_red,
    "HAT"
)

# ============================================================
# 5. SKIN / HAT SPOTS - CONFORM TO SURFACE
# ============================================================
# body front spots
spot1 = make_disc_mesh("SPOT.BODY.FRONT.1", (0.32, FRONT_Y - 0.03, 1.47), 0.10, 0.10, 'Y')
conform_decal(spot1, body, mat_yellow, "SKIN_SPOT")
spot2 = make_disc_mesh("SPOT.BODY.FRONT.2", (0.68, FRONT_Y - 0.03, 1.36), 0.17, 0.17, 'Y')
conform_decal(spot2, body, mat_yellow, "SKIN_SPOT")

# body back spots
BACK_Y = (BODY_D / 2.0) + 0.03
spot3 = make_disc_mesh("SPOT.BODY.BACK.1", (0.58, BACK_Y, 1.19), 0.12, 0.12, 'Y')
conform_decal(spot3, body, mat_yellow, "SKIN_SPOT")
spot4 = make_disc_mesh("SPOT.BODY.BACK.2", (0.38, BACK_Y, 0.90), 0.20, 0.20, 'Y')
conform_decal(spot4, body, mat_yellow, "SKIN_SPOT")

# arm side spots, conform to the arm meshes
for idx, (target, x, z, sign) in enumerate([
    (arm_l, -1.39, 1.44, -1),
    (arm_r,  1.39, 1.44,  1),
], start=1):
    d1 = make_disc_mesh(f"SPOT.ARM.{idx}.1", (x, -0.03, z), 0.10, 0.10, 'X')
    conform_decal(d1, target, mat_yellow, "SKIN_SPOT")
    d2 = make_disc_mesh(f"SPOT.ARM.{idx}.2", (x, -0.02, z-0.25), 0.08, 0.08, 'X')
    conform_decal(d2, target, mat_yellow, "SKIN_SPOT")

# hat front spots
hat_spots = [
    (-0.55, -0.67, 3.93, 0.18, 0.15),
    (-0.12, -0.72, 4.00, 0.22, 0.18),
    ( 0.45, -0.65, 3.78, 0.25, 0.20),
    (-0.80, -0.58, 3.65, 0.11, 0.10),
    ( 0.20, -0.70, 4.19, 0.12, 0.10),
]
for idx, (x,y,z,rx,rz) in enumerate(hat_spots, start=1):
    d = make_disc_mesh(f"SPOT.HAT.{idx}", (x,y,z), rx, rz, 'Y')
    conform_decal(d, hat_dome, mat_yellow, "HAT_SPOT")

# ============================================================
# 6. LIGHTING / CAMERA
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
    "character": "SAMSUL",
    "version": "TSA_CHARACTER_006_V1_RANGGA_FAMILY",
    "source_strategy": "Rangga family body baseline + Samsul face/hat/skin cosmetics",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "rangga_family_base": {
        "BODY_W": BODY_W,
        "BODY_D": BODY_D,
        "BODY_H": BODY_H,
        "BODY_Z": BODY_Z
    },
    "samsul_features": {
        "three_eyes": True,
        "pink_eyelids": True,
        "mouth_cavity": True,
        "cream_teeth_row": True,
        "cyan_nose_droplet": True,
        "red_hat": True,
        "drooping_hat_tail": True,
        "yellow_surface_spots": True,
        "cream_belly_patch": True,
        "belly_logo": True,
        "back_nub": True
    },
    "skin_rule": "all skin/hat spots conform to target surface; no floating plates",
    "face_gate": "FACE_FORM_LOCK",
    "tsa_gate": "STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR / "samsul_spec_v1.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "samsul_v1.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "samsul_v1.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"samsul_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("SAMSUL TSA CHARACTER 006 - STATIC V1 COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FACE FORM LOCK")
print("="*60)
