# JONO - TSA Character Reconstruction V3
# Blender 5.2 LTS
# Goal: rebuild Jono using the locked TSA baseline with improved face/anatomy quality.
# Gate: FORM LOCK + FACE DEPTH LOCK + ANATOMY LOCK + SURFACE DETAIL LOCK
#
# LOCKS
# - Preserve Rangga-family primary proportion baseline.
# - Eyes must read as seated/integrated into the head, not flat stickers.
# - Mouth zone must be clean and readable: subtle mouth line + two buck teeth.
# - Arms must have shoulder -> upper arm -> elbow -> forearm -> wrist -> hand.
# - Legs must have thigh -> knee -> calf -> ankle -> foot.
# - Headphones are true 3D volumes that wrap around the head.
# - Headphone cable must stay out of the mouth zone.
# - Chest logo and music player must stay separated from the face.
# - No rig/animation in this gate. Static canonical model only.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------
OUT_DIR = Path.home() / "jono_output_v3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.55

# ------------------------------------------------------------
# FAMILY / PROPORTION LOCK
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.08

SHOULDER_X = 1.16
SHOULDER_Z = 2.10
HIP_X = 0.56
HIP_Z = 0.82
FRONT_SURFACE_Y = -(BODY_D / 2.0)

# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------
BLUE = (0.17, 0.56, 0.96, 1.0)
BLUE_DARK = (0.10, 0.42, 0.82, 1.0)
BLUE_LID = (0.22, 0.66, 0.98, 1.0)
BLACK = (0.025, 0.025, 0.030, 1.0)
BLACK_SOFT = (0.08, 0.06, 0.12, 1.0)
SOCKET_DARK = (0.020, 0.022, 0.030, 1.0)
DARK_GREY = (0.16, 0.16, 0.17, 1.0)
MID_GREY = (0.47, 0.47, 0.50, 1.0)
LIGHT_GREY = (0.74, 0.74, 0.76, 1.0)
SILVER = (0.78, 0.78, 0.79, 1.0)
WHITE = (0.98, 0.98, 0.98, 1.0)
PUPIL = (0.18, 0.15, 0.28, 1.0)
GREEN = (0.55, 0.93, 0.30, 1.0)
RED = (1.0, 0.22, 0.25, 1.0)
MOUTH_DARK = (0.15, 0.16, 0.18, 1.0)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if getattr(block, "users", 0) == 0:
                datablocks.remove(block)


def make_mat(name, color, roughness=0.30, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mark(obj, region):
    obj["tsa_region"] = region
    return obj


def smooth(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True


def apply_mod(obj, name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=name)
    obj.select_set(False)


def bevel(obj, width=0.10, segments=6):
    mod = obj.modifiers.new("TSA_Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    apply_mod(obj, mod.name)


def rounded_box(name, location, dimensions, bevel_width, material, region, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, bevel_width, 8)
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def uv_part(name, location, scale, material, region, rotation=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def cyl_part(name, location, radius, depth, material, region, rotation=(0, 0, 0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 10
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
    return mark(obj, region)


def boolean_difference(base, cutter):
    mod = base.modifiers.new("BOOL_" + cutter.name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    apply_mod(base, mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def capsule_between(name, a, b, radius, material, region):
    a = Vector(a)
    b = Vector(b)
    mid = (a + b) * 0.5
    vec = b - a
    cyl = cyl_part(name, tuple(mid), radius, vec.length, material, region)
    cyl.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    uv_part(name + "_A_CAP", tuple(a), (radius, radius, radius), material, region)
    uv_part(name + "_B_CAP", tuple(b), (radius, radius, radius), material, region)
    return cyl


def teardrop_hand(name, loc, side, material):
    x, y, z = loc
    uv_part(name + "_PALM", (x, y, z), (0.21, 0.18, 0.25), material, "HAND")
    uv_part(name + "_WRIST_PAD", (x - side * 0.01, y, z + 0.21), (0.13, 0.13, 0.12), material, "WRIST")
    for i, dz in enumerate([0.09, 0.00, -0.09]):
        uv_part(
            f"{name}_FINGER_{i}",
            (x - side * 0.13, y - 0.01, z + dz - 0.02),
            (0.060, 0.095, 0.085),
            material,
            "FINGER",
        )
    uv_part(name + "_THUMB", (x + side * 0.12, y - 0.01, z - 0.01), (0.065, 0.095, 0.10), material, "THUMB")


def add_eye_cluster(name, x, z, r):
    # Shallow socket carved into the body/head block so the eye does not read as a sticker.
    cutter = uv_part(
        name + "_SOCKET_CUTTER",
        (x, FRONT_SURFACE_Y - 0.03, z),
        (r * 1.04, 0.16, r * 1.04),
        mat_socket,
        "CUTTER",
    )
    boolean_difference(body, cutter)

    uv_part(
        name + "_SOCKET",
        (x, FRONT_SURFACE_Y + 0.010, z),
        (r * 0.98, 0.08, r * 0.98),
        mat_socket,
        "EYE_SOCKET",
    )

    # White eye bulges outward but remains seated into the socket.
    eye_y = FRONT_SURFACE_Y - 0.055
    uv_part(name + "_WHITE", (x, eye_y, z), (r * 0.94, 0.14, r * 0.94), mat_white, name)
    uv_part(name + "_PUPIL", (x, eye_y - 0.115, z + 0.005), (r * 0.32, 0.045, r * 0.32), mat_pupil, name + ".PUPIL")
    uv_part(name + "_LID", (x, eye_y - 0.030, z + r * 0.47), (r * 0.98, 0.06, r * 0.42), mat_blue_lid, name + ".LID")


# ------------------------------------------------------------
# BUILD
# ------------------------------------------------------------
clean_scene()

mat_blue = make_mat("JONO_BLUE", BLUE, 0.26)
mat_blue_dark = make_mat("JONO_BLUE_DARK", BLUE_DARK, 0.30)
mat_blue_lid = make_mat("JONO_BLUE_LID", BLUE_LID, 0.22)
mat_black = make_mat("JONO_BLACK", BLACK, 0.24)
mat_pupil = make_mat("JONO_PUPIL", PUPIL, 0.18)
mat_socket = make_mat("JONO_SOCKET", SOCKET_DARK, 0.48)
mat_dgrey = make_mat("JONO_DGREY", DARK_GREY, 0.28)
mat_mgrey = make_mat("JONO_MGREY", MID_GREY, 0.30)
mat_lgrey = make_mat("JONO_LGREY", LIGHT_GREY, 0.30)
mat_silver = make_mat("JONO_SILVER", SILVER, 0.25, metallic=0.10)
mat_white = make_mat("JONO_WHITE", WHITE, 0.18)
mat_green = make_mat("JONO_GREEN", GREEN, 0.20)
mat_red = make_mat("JONO_RED", RED, 0.24)
mat_mouth = make_mat("JONO_MOUTH", MOUTH_DARK, 0.36)

# ------------------------------------------------------------
# 1) PRIMARY BODY FORM
# ------------------------------------------------------------
body = rounded_box(
    "BODY_CORE",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.30,
    mat_blue,
    "TORSO_HEAD",
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.03, 1.03),
    (1.03, 0.62, 0.74),
    mat_blue,
    "TORSO_LOWER",
)

# ------------------------------------------------------------
# 2) EYES / FACE LOCK
# ------------------------------------------------------------
add_eye_cluster("EYE_TOP", 0.00, 2.90, 0.30)
add_eye_cluster("EYE_LEFT", -0.53, 2.33, 0.30)
add_eye_cluster("EYE_RIGHT", 0.53, 2.33, 0.30)

# Subtle mouth line separated from chest cable/logo area.
mouth_pts = []
for i in range(36):
    t = i / 35
    x = -0.43 + 0.86 * t
    z = 1.86 - 0.030 * math.sin(t * math.pi)
    mouth_pts.append((x, FRONT_SURFACE_Y - 0.090, z))
curve_from_points("MOUTH_LINE", mouth_pts, mat_mouth, 0.018, "MOUTH")

# dark mouth backing - compact so the face stays clean
rounded_box(
    "MOUTH_BACKING",
    (0.0, FRONT_SURFACE_Y - 0.112, 1.76),
    (0.44, 0.055, 0.14),
    0.040,
    mat_mouth,
    "MOUTH",
)

rounded_box(
    "TOOTH_L",
    (-0.09, FRONT_SURFACE_Y - 0.125, 1.725),
    (0.15, 0.08, 0.20),
    0.035,
    mat_white,
    "TOOTH.L",
)
rounded_box(
    "TOOTH_R",
    (0.09, FRONT_SURFACE_Y - 0.125, 1.725),
    (0.15, 0.08, 0.20),
    0.035,
    mat_white,
    "TOOTH.R",
)

# ------------------------------------------------------------
# 3) HEADPHONES - TRUE 3D
# ------------------------------------------------------------
for side, x in (("L", -1.23), ("R", 1.23)):
    sign = -1 if side == "L" else 1
    cyl_part(
        f"HEADPHONE_{side}_OUTER",
        (x, 0.0, 2.96),
        0.42,
        0.25,
        mat_black,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0),
    )
    cyl_part(
        f"HEADPHONE_{side}_INNER",
        (x + sign * 0.08, 0.0, 2.96),
        0.32,
        0.14,
        mat_mgrey,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0),
    )
    cyl_part(
        f"HEADPHONE_{side}_CENTER",
        (x + sign * 0.145, 0.0, 2.96),
        0.24,
        0.08,
        mat_dgrey,
        f"HEADPHONE.{side}",
        rotation=(0, math.radians(90), 0),
    )

band_pts = [
    (-1.23, 0.10, 3.08),
    (-1.34, 0.12, 3.57),
    (-1.08, 0.10, 3.99),
    (-0.56, 0.10, 4.25),
    (0.00, 0.10, 4.34),
    (0.56, 0.10, 4.25),
    (1.08, 0.10, 3.99),
    (1.34, 0.12, 3.57),
    (1.23, 0.10, 3.08),
]
curve_from_points("HEADPHONE_BAND", band_pts, mat_black, 0.095, "HEADPHONE.BAND")

for side, x in (("L", -1.10), ("R", 1.10)):
    rounded_box(
        f"HEADPHONE_JOINT_{side}",
        (x, 0.08, 3.94),
        (0.22, 0.22, 0.20),
        0.040,
        mat_lgrey,
        "HEADPHONE.JOINT",
    )

# ------------------------------------------------------------
# 4) CABLE / LOGO / PLAYER
# ------------------------------------------------------------
# Cable drops on character-left side, never across the teeth/mouth.
cable_pts = [
    (-1.28, -0.10, 2.78),
    (-1.38, -0.26, 2.42),
    (-1.32, FRONT_SURFACE_Y - 0.10, 2.06),
    (-1.06, FRONT_SURFACE_Y - 0.13, 1.78),
    (-0.80, FRONT_SURFACE_Y - 0.14, 1.63),
    (-0.90, FRONT_SURFACE_Y - 0.14, 1.43),
    (-0.66, FRONT_SURFACE_Y - 0.14, 1.27),
    (-0.42, FRONT_SURFACE_Y - 0.14, 1.37),
    (-0.22, FRONT_SURFACE_Y - 0.14, 1.49),
]
curve_from_points("HEADPHONE_CABLE", cable_pts, mat_black, 0.026, "HEADPHONE.CABLE")

rounded_box(
    "CABLE_CONNECTOR",
    (-1.33, -0.24, 2.47),
    (0.12, 0.10, 0.28),
    0.030,
    mat_dgrey,
    "HEADPHONE.CABLE",
)

logo_y = FRONT_SURFACE_Y - 0.095
for row, z in enumerate((1.56, 1.47)):
    pts = []
    for i in range(31):
        t = i / 30
        x = -0.28 + 0.56 * t
        zz = z + 0.043 * math.sin(t * math.pi * 4.0)
        pts.append((x, logo_y, zz))
    curve_from_points(f"LOGO_WAVE_{row+1}", pts, mat_black, 0.021, "CHEST_LOGO")
uv_part("LOGO_RED_DOT", (0.35, logo_y - 0.015, 1.47), (0.055, 0.032, 0.055), mat_red, "CHEST_LOGO")

PLAYER_Y = FRONT_SURFACE_Y - 0.125
rounded_box(
    "PLAYER_BODY",
    (0.05, PLAYER_Y, 1.08),
    (0.52, 0.16, 0.78),
    0.070,
    mat_silver,
    "PLAYER",
)
rounded_box(
    "PLAYER_SCREEN",
    (0.05, PLAYER_Y - 0.09, 1.28),
    (0.38, 0.05, 0.30),
    0.025,
    mat_dgrey,
    "PLAYER.SCREEN",
)

bar_specs = [
    (-0.08, 1.20, 0.07),
    (0.00, 1.23, 0.11),
    (0.08, 1.27, 0.15),
    (0.16, 1.31, 0.19),
]
for idx, (x, z, h) in enumerate(bar_specs, start=1):
    rounded_box(
        f"PLAYER_BAR_{idx}",
        (x, PLAYER_Y - 0.125, z),
        (0.06, 0.03, h),
        0.010,
        mat_green,
        "PLAYER.SCREEN",
    )

# Dial
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.15,
    minor_radius=0.035,
    major_segments=64,
    minor_segments=24,
    location=(0.05, PLAYER_Y - 0.10, 0.88),
    rotation=(math.radians(90), 0, 0),
)
player_dial_outer = bpy.context.object
player_dial_outer.name = "PLAYER_DIAL_OUTER"
smooth(player_dial_outer)
player_dial_outer.data.materials.append(mat_lgrey)
mark(player_dial_outer, "PLAYER.DIAL")

cyl_part(
    "PLAYER_DIAL_CENTER",
    (0.05, PLAYER_Y - 0.14, 0.88),
    0.07,
    0.045,
    mat_mgrey,
    "PLAYER.DIAL",
    rotation=(math.radians(90), 0, 0),
)

curve_from_points(
    "PLAYER_WIRE",
    [
        (-0.22, FRONT_SURFACE_Y - 0.14, 1.49),
        (-0.10, FRONT_SURFACE_Y - 0.14, 1.40),
        (0.02, FRONT_SURFACE_Y - 0.14, 1.46),
    ],
    mat_black,
    0.022,
    "PLAYER.WIRE",
)

# ------------------------------------------------------------
# 5) ARMS - ANATOMY LOCK
# ------------------------------------------------------------
def build_arm(side):
    tag = "L" if side < 0 else "R"
    shoulder = (side * SHOULDER_X, -0.01, SHOULDER_Z)
    elbow = (side * 1.22, -0.02, 1.55)
    wrist = (side * 1.16, -0.04, 1.10)

    uv_part(f"SHOULDER_{tag}", shoulder, (0.28, 0.32, 0.30), mat_blue, f"SHOULDER.{tag}")
    capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.20, mat_blue, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.20, 0.22, 0.20), mat_blue, f"ELBOW.{tag}")
    capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.17, mat_blue, f"FOREARM.{tag}")
    uv_part(f"WRIST_{tag}", wrist, (0.13, 0.14, 0.12), mat_blue, f"WRIST.{tag}")
    hand_loc = (side * 1.12, -0.05, 0.87)
    teardrop_hand(f"HAND_{tag}", hand_loc, side, mat_blue)

build_arm(-1)
build_arm(1)

# ------------------------------------------------------------
# 6) LEGS - ANATOMY LOCK
# ------------------------------------------------------------
def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * HIP_X, 0.02, HIP_Z)
    knee = (side * 0.57, 0.01, 0.49)
    ankle = (side * 0.57, -0.04, 0.22)

    capsule_between(f"THIGH_{tag}", hip, knee, 0.23, mat_blue, f"THIGH.{tag}")
    uv_part(f"KNEE_{tag}", knee, (0.22, 0.24, 0.20), mat_blue, f"KNEE.{tag}")
    capsule_between(f"CALF_{tag}", knee, ankle, 0.18, mat_blue, f"CALF.{tag}")
    uv_part(f"ANKLE_{tag}", ankle, (0.15, 0.17, 0.12), mat_blue, f"ANKLE.{tag}")
    uv_part(f"FOOT_{tag}", (side * 0.57, -0.15, 0.09), (0.28, 0.40, 0.16), mat_blue, f"FOOT.{tag}")
    uv_part(f"TOE_{tag}", (side * 0.57, -0.33, 0.08), (0.24, 0.18, 0.12), mat_blue, f"TOE.{tag}")

build_leg(-1)
build_leg(1)

# ------------------------------------------------------------
# 7) BACK DETAIL
# ------------------------------------------------------------
uv_part("BACK_NUB", (0.0, BODY_D / 2.0 + 0.05, 1.05), (0.17, 0.14, 0.17), mat_blue, "BACK_DETAIL")

# ------------------------------------------------------------
# 8) LIGHT / CAMERA / EXPORT
# ------------------------------------------------------------
def add_area(name, loc, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.data.color = color
    return light

add_area("KEY", (-4.7, -5.5, 7.5), 1000, 5.0)
add_area("FILL", (4.5, -3.0, 4.2), 650, 4.0)
add_area("RIM", (0.0, 4.5, 6.7), 900, 4.1)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.96, 0.96, 0.96, 1.0)
    bg.inputs["Strength"].default_value = 0.78

bpy.ops.object.camera_add(location=(0, -8, 2.1))
cam = bpy.context.object
cam.name = "TSA_CAMERA"
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
bpy.context.scene.camera = cam


def point_camera(camera, location, target=(0, 0, 2.0)):
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
    "three_q_l": ((-6.3, -6.3, 2.40), (0, 0, 2.0)),
    "left": ((-8.0, 0, 2.15), (0, 0, 2.0)),
    "back": ((0, 8.0, 2.15), (0, 0, 2.0)),
    "right": ((8.0, 0, 2.15), (0, 0, 2.0)),
    "three_q_r": ((6.3, -6.3, 2.40), (0, 0, 2.0)),
    "top": ((0, 0, 10.2), (0, 0, 1.8)),
    "bottom": ((0, 0, -7.0), (0, 0, 1.5)),
}

spec = {
    "character": "JONO",
    "version": "TSA_CHARACTER_005_V3_TSA_ANATOMY_FACE_LOCK",
    "source_strategy": "Rangga-family baseline preserved; rebuilt face, mouth zone, true anatomy limbs, and clean chest layout.",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0",
    },
    "rangga_base": {
        "BODY_W": BODY_W,
        "BODY_D": BODY_D,
        "BODY_H": BODY_H,
        "BODY_Z": BODY_Z,
    },
    "locks": {
        "eyes_integrated_not_sticker": True,
        "mouth_zone_clean": True,
        "headphones_true_3d": True,
        "cable_avoids_face": True,
        "arms_anatomy_chain": True,
        "legs_anatomy_chain": True,
        "player_and_logo_separated": True,
    },
    "tsa_gate": "STATIC_MODEL_FORM_LOCK",
}

with open(OUT_DIR / "jono_spec_v3.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "jono_v3.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "jono_v3.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False,
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"jono_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 60)
print("JONO TSA CHARACTER 005 - V3 TSA ANATOMY FACE LOCK COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("=" * 60)
