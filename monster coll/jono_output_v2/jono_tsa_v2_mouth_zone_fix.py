
# JONO - TSA Character Reconstruction V1
# Blender 5.2 LTS
# Goal: static canonical Jono model from turnaround baseline.
# Base geometry: literal Rangga family baseline.
# Gate: STATIC MODEL / FORM LOCK only. No rig / animation.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "jono_output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.50

# ------------------------------------------------------------
# RANGGA FAMILY CANONICAL BASELINE - PRESERVED
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

BLUE = (0.035, 0.45, 0.90, 1.0)
BLUE_LID = (0.025, 0.38, 0.80, 1.0)
BLACK = (0.025, 0.025, 0.028, 1.0)
BLACK_SOFT = (0.08, 0.06, 0.12, 1.0)
DARK_GREY = (0.16, 0.16, 0.17, 1.0)
MID_GREY = (0.47, 0.47, 0.50, 1.0)
LIGHT_GREY = (0.74, 0.74, 0.76, 1.0)
SILVER = (0.64, 0.64, 0.66, 1.0)
WHITE = (0.98, 0.98, 0.98, 1.0)
GREEN = (0.25, 0.90, 0.20, 1.0)
RED = (1.00, 0.08, 0.12, 1.0)

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

def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def torus_part(name, location, major_radius, minor_radius, material, region, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=64,
        minor_segments=24,
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

def add_eye(name, x, z, size):
    white = uv_part(
        name, (x, FRONT_Y, z),
        (size, 0.12, size),
        mat_white, name
    )
    pupil = uv_part(
        name + ".PUPIL",
        (x, FRONT_Y - 0.13, z - 0.005),
        (size*0.37, 0.05, size*0.37),
        mat_pupil, name + ".PUPIL"
    )
    # blue eyelid as a shallow, flattened sphere section
    lid = uv_part(
        name + ".LID",
        (x, FRONT_Y - 0.025, z + size*0.50),
        (size*1.02, 0.07, size*0.48),
        mat_blue_lid, name + ".LID"
    )
    return white, pupil, lid

clean_scene()

mat_blue = make_mat("JONO_BLUE", BLUE, 0.26)
mat_blue_lid = make_mat("JONO_BLUE_LID", BLUE_LID, 0.24)
mat_black = make_mat("JONO_BLACK", BLACK, 0.24)
mat_pupil = make_mat("JONO_PUPIL", BLACK_SOFT, 0.18)
mat_dgrey = make_mat("JONO_DARK_GREY", DARK_GREY, 0.28)
mat_mgrey = make_mat("JONO_MID_GREY", MID_GREY, 0.30)
mat_lgrey = make_mat("JONO_LIGHT_GREY", LIGHT_GREY, 0.32)
mat_silver = make_mat("JONO_SILVER", SILVER, 0.26, metallic=0.15)
mat_white = make_mat("JONO_WHITE", WHITE, 0.16)
mat_green = make_mat("JONO_GREEN", GREEN, 0.22)
mat_red = make_mat("JONO_RED", RED, 0.24)

# ============================================================
# 1. CORE BODY - EXACT RANGGA FAMILY BASE
# ============================================================
body = rounded_box(
    "BODY",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.28,
    mat_blue,
    "TORSO_HEAD"
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.02, 1.03),
    (1.05, 0.63, 0.78),
    mat_blue,
    "TORSO_LOWER"
)

arm_l = uv_part(
    "ARM.L",
    (-1.18, -0.01, 1.55),
    (0.34, 0.42, 0.82),
    mat_blue,
    "ARM.L",
    rotation=(0, math.radians(-8), math.radians(-5))
)

arm_r = uv_part(
    "ARM.R",
    (1.18, -0.01, 1.55),
    (0.34, 0.42, 0.82),
    mat_blue,
    "ARM.R",
    rotation=(0, math.radians(8), math.radians(5))
)

leg_l = rounded_box(
    "LEG.L",
    (-0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_blue,
    "LEG.L"
)

leg_r = rounded_box(
    "LEG.R",
    (0.61, 0.02, 0.43),
    (0.58, 0.74, 0.90),
    0.22,
    mat_blue,
    "LEG.R"
)

tail_nub = uv_part(
    "BACK_NUB",
    (0.0, 0.73, 1.05),
    (0.17, 0.16, 0.17),
    mat_blue,
    "BACK_DETAIL"
)

FRONT_Y = -(BODY_D / 2.0) - 0.055

# ============================================================
# 2. FACE - 3 EYES + BLUE LIDS
# ============================================================
add_eye("EYE.TOP", 0.00, 2.90, 0.30)
add_eye("EYE.LEFT", -0.53, 2.33, 0.30)
add_eye("EYE.RIGHT", 0.53, 2.33, 0.30)

# ============================================================
# JONO MOUTH ZONE - V2 CLEAN FACE PATCH
# Keep this zone exclusive: no cable / logo is allowed to cross it.
# Baseline: short subtle mouth, two centered buck teeth.
# ============================================================

# shallow dark lip/slit: slightly frowning, compact width
mouth_pts = []
for i in range(42):
    t = i / 41
    x = -0.42 + 0.84 * t
    # corners slightly higher, center slightly lower
    z = 1.88 - 0.028 * math.sin(t * math.pi)
    mouth_pts.append((x, FRONT_Y - 0.115, z))
curve_from_points("MOUTH", mouth_pts, mat_black, 0.018, "MOUTH")

# tiny dark backing behind the two teeth so they visibly belong to the mouth
rounded_box(
    "MOUTH.TEETH_BACKING",
    (0.0, FRONT_Y - 0.105, 1.775),
    (0.48, 0.055, 0.18),
    0.05,
    mat_black,
    "MOUTH"
)

# centered buck teeth; narrower and closer together than V1
rounded_box(
    "TOOTH.L",
    (-0.105, FRONT_Y - 0.135, 1.755),
    (0.18, 0.10, 0.22),
    0.045,
    mat_white,
    "TOOTH.L"
)
rounded_box(
    "TOOTH.R",
    (0.105, FRONT_Y - 0.135, 1.755),
    (0.18, 0.10, 0.22),
    0.045,
    mat_white,
    "TOOTH.R"
)

# ============================================================
# 3. HEADPHONES - TRUE 3D VOLUMES
# ============================================================
# earcups: cylinders whose axis points left/right
for side, x in (("L", -1.23), ("R", 1.23)):
    sign = -1 if side == "L" else 1

    # outer black cup
    cyl_part(
        f"HEADPHONE.{side}.OUTER",
        (x, 0.0, 2.95),
        0.42, 0.24,
        mat_black,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0)
    )

    # grey inner ring
    cyl_part(
        f"HEADPHONE.{side}.INNER",
        (x + sign*0.08, 0.0, 2.95),
        0.32, 0.13,
        mat_mgrey,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0)
    )

    # darker center disk
    cyl_part(
        f"HEADPHONE.{side}.CENTER",
        (x + sign*0.145, 0.0, 2.95),
        0.24, 0.08,
        mat_dgrey,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0)
    )

# headband path goes behind/around the top of the head, not a front sticker
band_pts = [
    (-1.23, 0.10, 3.06),
    (-1.35, 0.12, 3.55),
    (-1.08, 0.10, 3.96),
    (-0.58, 0.10, 4.22),
    (0.00, 0.10, 4.30),
    (0.58, 0.10, 4.22),
    (1.08, 0.10, 3.96),
    (1.35, 0.12, 3.55),
    (1.23, 0.10, 3.06),
]
curve_from_points(
    "HEADPHONE.BAND",
    band_pts,
    mat_black,
    0.095,
    "HEADPHONE.BAND"
)

# small grey joints near the top side
for side, x in (("L", -1.10), ("R", 1.10)):
    rounded_box(
        f"HEADPHONE.JOINT.{side}",
        (x, 0.08, 3.93),
        (0.22, 0.22, 0.20),
        0.04,
        mat_mgrey,
        "HEADPHONE.JOINT"
    )

# ============================================================
# 4. HEADPHONE CABLE / CHEST CABLE
# ============================================================
# ============================================================
# HEADPHONE CABLE - V2 SAFE ROUTE
# Cable must NEVER cross the face / mouth / teeth.
# It descends along character-left side, then loops only on the chest.
# ============================================================
cable_pts = [
    (-1.30, -0.10, 2.80),                 # earcup
    (-1.39, -0.28, 2.46),                 # down beside head
    (-1.32, FRONT_Y - 0.12, 2.05),        # reaches upper chest at far left
    (-1.05, FRONT_Y - 0.15, 1.77),
    (-0.78, FRONT_Y - 0.16, 1.63),
    (-0.92, FRONT_Y - 0.16, 1.43),
    (-0.70, FRONT_Y - 0.16, 1.25),
    (-0.43, FRONT_Y - 0.16, 1.34),
    (-0.24, FRONT_Y - 0.16, 1.48),        # approach player wire
]
curve_from_points(
    "HEADPHONE.CABLE",
    cable_pts,
    mat_black,
    0.026,
    "HEADPHONE.CABLE"
)

# small connector on cable
rounded_box(
    "CABLE.CONNECTOR",
    (-1.34, -0.26, 2.50),
    (0.12, 0.10, 0.28),
    0.03,
    mat_dgrey,
    "HEADPHONE.CABLE"
)

# ============================================================
# 5. JONO LOGO - BODY-CONFORMING STYLE DETAIL
# ============================================================
# ============================================================
# JONO CHEST LOGO - moved away from mouth zone
# Baseline logo belongs to the upper chest, not directly under the teeth.
# ============================================================
logo_y = FRONT_Y - 0.10
for row, z in enumerate((1.56, 1.47)):
    pts = []
    for i in range(33):
        t = i / 32
        x = -0.28 + 0.56*t
        zz = z + 0.045*math.sin(t*math.pi*4.0)
        pts.append((x, logo_y, zz))
    curve_from_points(
        f"LOGO.WAVE.{row+1}",
        pts,
        mat_black,
        0.022,
        "CHEST_LOGO"
    )

# red logo dot
uv_part(
    "LOGO.RED_DOT",
    (0.36, logo_y - 0.015, 1.47),
    (0.055, 0.032, 0.055),
    mat_red,
    "CHEST_LOGO"
)

# ============================================================
# 6. MUSIC PLAYER
# ============================================================
PLAYER_Y = FRONT_Y - 0.13

player = rounded_box(
    "PLAYER.BODY",
    (0.05, PLAYER_Y, 1.08),
    (0.52, 0.16, 0.78),
    0.07,
    mat_silver,
    "PLAYER"
)

screen = rounded_box(
    "PLAYER.SCREEN",
    (0.05, PLAYER_Y - 0.10, 1.28),
    (0.38, 0.05, 0.30),
    0.025,
    mat_dgrey,
    "PLAYER.SCREEN"
)

# signal bars
bar_specs = [
    (-0.08, 1.20, 0.07),
    (0.00, 1.23, 0.11),
    (0.08, 1.27, 0.15),
    (0.16, 1.31, 0.19),
]
for idx, (x, z, h) in enumerate(bar_specs, start=1):
    rounded_box(
        f"PLAYER.BAR.{idx}",
        (x, PLAYER_Y - 0.135, z),
        (0.06, 0.03, h),
        0.01,
        mat_green,
        "PLAYER.SCREEN"
    )

# dial
torus_part(
    "PLAYER.DIAL.OUTER",
    (0.05, PLAYER_Y - 0.105, 0.88),
    0.15, 0.035,
    mat_lgrey,
    "PLAYER.DIAL",
    rotation=(math.radians(90), 0, 0)
)

cyl_part(
    "PLAYER.DIAL.CENTER",
    (0.05, PLAYER_Y - 0.145, 0.88),
    0.07, 0.045,
    mat_mgrey,
    "PLAYER.DIAL",
    rotation=(math.radians(90), 0, 0)
)

# short wire from chest cable to player top
# stays below logo and entirely outside mouth zone
curve_from_points(
    "PLAYER.WIRE",
    [
        (-0.24, FRONT_Y - 0.16, 1.48),
        (-0.10, FRONT_Y - 0.16, 1.38),
        (0.02, FRONT_Y - 0.16, 1.45),
    ],
    mat_black,
    0.023,
    "PLAYER.WIRE"
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
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.96, 0.96, 0.96, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75

bpy.ops.object.camera_add(location=(0, -8, 2.1))
cam = bpy.context.object
cam.name = "TSA_CAMERA"
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
bpy.context.scene.camera = cam

def point_camera(camera, location, target=(0,0,2.0)):
    camera.location = location
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

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
    "front": ((0, -8.0, 2.15), (0, 0, 2.0)),
    "three_q_l": ((-6.3, -6.3, 2.45), (0, 0, 2.0)),
    "left": ((-8.0, 0, 2.15), (0, 0, 2.0)),
    "back": ((0, 8.0, 2.15), (0, 0, 2.0)),
    "right": ((8.0, 0, 2.15), (0, 0, 2.0)),
    "three_q_r": ((6.3, -6.3, 2.45), (0, 0, 2.0)),
    "top": ((0, 0, 10.0), (0, 0, 1.8)),
    "bottom": ((0, 0, -7.0), (0, 0, 1.5)),
}

spec = {
    "character": "JONO",
    "version": "TSA_CHARACTER_005_V2_MOUTH_ZONE_FIX",
    "source_strategy": "V1 Rangga-family base preserved; targeted mouth-zone, cable-route and logo-spacing correction",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "rangga_base": {
        "BODY_W": BODY_W,
        "BODY_D": BODY_D,
        "BODY_H": BODY_H,
        "BODY_Z": BODY_Z
    },
    "jono_features": {
        "three_eyes": True,
        "blue_eyelids": True,
        "buck_teeth": True,
        "headphone_true_3d": True,
        "headphone_band_wraps_head": True,
        "headphone_cable_curve": True,
        "music_player": True,
        "chest_logo": True,
        "mouth_zone_exclusion": True,
        "cable_avoids_face": True,
        "back_nub": True
    },
    "skin_rule": "body markings must conform to body surface; no floating plates",
    "tsa_gate": "STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR / "jono_spec_v2.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "jono_v2.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "jono_v2.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"jono_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 60)
print("JONO TSA CHARACTER 005 - V2 MOUTH ZONE FIX COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("=" * 60)
