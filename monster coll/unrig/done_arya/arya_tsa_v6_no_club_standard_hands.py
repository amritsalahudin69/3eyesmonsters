# ARYA - TSA Character Reconstruction V6
# Blender 5.2 LTS
# Gate: FAMILY BASE LOCK + FACE DEPTH LOCK + ANATOMY LOCK + SKIN CONFORM LOCK
#
# LOCKS
# - Arya stays on the Rangga family body baseline.
# - Single center horn only.
# - Eyes must be embedded in real sockets, not sticker discs.
# - Arms and legs must preserve simplified anatomy:
#   shoulder -> upper arm -> elbow -> forearm -> wrist -> hand,
#   thigh -> knee -> calf -> ankle -> foot.
# - Tiger stripes must conform to the body surface, not float.
# - No weapon. Both hands use the same healthy neutral anatomical construction.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "arya_output_v6"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.40

# ============================================================
# FAMILY PROPORTION LOCK
# ============================================================
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05
FRONT_SURFACE_Y = -(BODY_D / 2.0)

SHOULDER_Z = 2.08
HIP_Z = 0.84

# ============================================================
# COLORS
# ============================================================
YELLOW = (1.00, 0.82, 0.24, 1.0)
YELLOW_SPIKE = (1.00, 0.86, 0.23, 1.0)
BLACK = (0.06, 0.06, 0.07, 1.0)
BLACK_SOFT = (0.14, 0.12, 0.11, 1.0)
BLACK_SOCKET = (0.03, 0.03, 0.035, 1.0)
WHITE = (0.985, 0.985, 0.985, 1.0)
PUPIL = (0.29, 0.20, 0.16, 1.0)
RED = (0.86, 0.20, 0.13, 1.0)
TONGUE_RED = (0.97, 0.45, 0.48, 1.0)
FANG = (0.94, 0.92, 0.86, 1.0)
GROOVE = (0.78, 0.18, 0.16, 1.0)

# ============================================================
# HELPERS
# ============================================================

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if getattr(block, 'users', 0) == 0:
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


def apply_mod(obj, mod_name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_name)
    obj.select_set(False)


def bevel(obj, width=0.1, segments=6):
    mod = obj.modifiers.new("TSA_Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    apply_mod(obj, mod.name)


def rounded_box(name, location, dimensions, bevel_width, material, region, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, bevel_width, 8)
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def uv_part(name, location, scale, material, region, rotation=(0,0,0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def cone_part(name, location, radius1, radius2, depth, material, region, rotation=(0,0,0), vertices=64):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False, bezier=True):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12 if bezier else 3
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 5
    if bezier:
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(pts)-1)
        for bp, p in zip(spline.bezier_points, pts):
            bp.co = p
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
    else:
        spline = curve.splines.new('POLY')
        spline.points.add(len(pts)-1)
        for i, p in enumerate(pts):
            spline.points[i].co = (*p, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark(obj, region)


def spiral_points(cx, cy, cz, radius, turns, steps=160, phase=0.0):
    pts = []
    for i in range(steps):
        t = i / (steps - 1)
        a = phase + t * turns * math.tau
        r = radius * (0.10 + 0.90 * t)
        pts.append((cx + r*math.cos(a), cy, cz + r*math.sin(a)))
    return pts


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
    length = vec.length
    cyl = cyl_part(name, tuple(mid), radius, length, material, region)
    cyl.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    uv_part(name + "_A_CAP", tuple(a), (radius, radius, radius), material, region)
    uv_part(name + "_B_CAP", tuple(b), (radius, radius, radius), material, region)
    return cyl


def make_hand(name, palm_loc, side, material, region="HAND"):
    x, y, z = palm_loc
    uv_part(name + "_PALM", (x, y, z), (0.22, 0.19, 0.27), material, region)
    uv_part(name + "_WRIST_PAD", (x - side*0.02, y, z+0.22), (0.13, 0.13, 0.12), material, region)
    # three compact digits + thumb, so the hand is not a simple oval.
    for i, dz in enumerate((0.10, 0.00, -0.10), start=1):
        uv_part(
            f"{name}_FINGER_{i}",
            (x - side*0.15, y-0.01, z+dz-0.02),
            (0.070, 0.10, 0.09),
            material, region
        )
    uv_part(name + "_THUMB", (x + side*0.14, y-0.01, z-0.01), (0.078, 0.10, 0.10), material, region)


def finish_skin_decal(obj, target, region, offset=0.006):
    shrink = obj.modifiers.new("TSA_SKIN_CONFORM", 'SHRINKWRAP')
    shrink.target = target
    shrink.wrap_method = 'NEAREST_SURFACEPOINT'
    shrink.wrap_mode = 'OUTSIDE_SURFACE'
    shrink.offset = offset
    apply_mod(obj, shrink.name)

    solid = obj.modifiers.new("TSA_DECAL_SOLIDIFY", 'SOLIDIFY')
    solid.thickness = 0.004
    solid.offset = 0.0
    apply_mod(obj, solid.name)
    return mark(obj, region)


def flat_poly(name, coords_xz, y, material, region, target):
    verts = [(x, y, z) for (x, z) in coords_xz]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return finish_skin_decal(obj, target, region)


def side_poly(name, coords_yz, x, material, region, target):
    verts = [(x, y, z) for (y, z) in coords_yz]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return finish_skin_decal(obj, target, region)


# ============================================================
# BUILD
# ============================================================
clean_scene()

mat_yellow = make_mat("ARYA_YELLOW", YELLOW, 0.28)
mat_spike = make_mat("ARYA_SPIKE", YELLOW_SPIKE, 0.27)
mat_black = make_mat("ARYA_BLACK", BLACK, 0.25)
mat_black_soft = make_mat("ARYA_BLACK_SOFT", BLACK_SOFT, 0.22)
mat_socket = make_mat("ARYA_SOCKET", BLACK_SOCKET, 0.45)
mat_white = make_mat("ARYA_WHITE", WHITE, 0.17)
mat_pupil = make_mat("ARYA_PUPIL", PUPIL, 0.20)
mat_tongue = make_mat("ARYA_TONGUE", TONGUE_RED, 0.28)
mat_fang = make_mat("ARYA_FANG", FANG, 0.32)
mat_groove = make_mat("ARYA_GROOVE", GROOVE, 0.35)

# ------------------------------------------------------------
# 1) BODY FAMILY BASE
# ------------------------------------------------------------
body = rounded_box(
    "BODY_CORE", (0, 0, BODY_Z), (BODY_W, BODY_D, BODY_H),
    0.30, mat_yellow, "TORSO_HEAD"
)

uv_part(
    "LOWER_VOLUME", (0, 0.03, 1.02), (1.03, 0.62, 0.76),
    mat_yellow, "TORSO_LOWER"
)

uv_part(
    "BACK_NUB", (0.0, BODY_D/2.0 + 0.05, 1.03), (0.17, 0.15, 0.17),
    mat_yellow, "BACK_DETAIL"
)

# ------------------------------------------------------------
# 2) HORN + BLACK BANDS
# ------------------------------------------------------------
cone_part(
    "HORN_CENTER", (0, 0, 3.98), 0.29, 0.02, 0.82,
    mat_spike, "HORN.CENTER"
)
for i, (z, rad) in enumerate(((3.71, 0.26), (3.85, 0.22), (3.99, 0.18), (4.12, 0.14)), start=1):
    cyl_part(
        f"HORN_BAND_{i}", (0, 0, z), rad, 0.060,
        mat_black, "HORN_BAND"
    )

# ------------------------------------------------------------
# 3) EYES - REAL SOCKETS + EMBEDDED EYEBALLS
# ------------------------------------------------------------
eye_specs = {
    "EYE.TOP":   (0.00, 2.92, 0.30),
    "EYE.LEFT":  (-0.52, 2.37, 0.31),
    "EYE.RIGHT": (0.52, 2.37, 0.31),
}

for name, (x, z, r) in eye_specs.items():
    cutter = uv_part(
        name + "_SOCKET_CUTTER",
        (x, FRONT_SURFACE_Y - 0.015, z),
        (r * 1.08, 0.18, r * 1.08),
        mat_socket, "CUTTER"
    )
    boolean_difference(body, cutter)

    uv_part(
        name + "_SOCKET",
        (x, FRONT_SURFACE_Y + 0.055, z),
        (r * 1.00, 0.10, r * 1.00),
        mat_socket, "EYE_SOCKET"
    )

    uv_part(
        name + "_EYEBALL",
        (x, FRONT_SURFACE_Y - 0.020, z),
        (r * 0.92, 0.13, r * 0.92),
        mat_white, name
    )

    uv_part(
        name + "_PUPIL",
        (x, FRONT_SURFACE_Y - 0.145, z),
        (r * 0.34, 0.05, r * 0.34),
        mat_pupil, name + ".PUPIL"
    )

# ------------------------------------------------------------
# 4) MOUTH / FANGS / TONGUE
# ------------------------------------------------------------
mouth_cavity = rounded_box(
    "MOUTH_CAVITY",
    (0.0, FRONT_SURFACE_Y - 0.090, 1.98),
    (0.98, 0.12, 0.21),
    0.08, mat_black, "MOUTH"
)

# shallow smile/frown edge
curve_from_points(
    "MOUTH_LINE",
    [(-0.52, FRONT_SURFACE_Y - 0.075, 2.04), (-0.20, FRONT_SURFACE_Y - 0.078, 2.01),
     (0.20, FRONT_SURFACE_Y - 0.078, 2.01), (0.52, FRONT_SURFACE_Y - 0.075, 2.04)],
    mat_black, 0.015, "MOUTH_LINE"
)

cone_part(
    "FANG_L", (-0.49, FRONT_SURFACE_Y - 0.125, 1.96),
    0.085, 0.015, 0.26, mat_fang, "FANG.L", rotation=(math.radians(180), 0, 0)
)
cone_part(
    "FANG_R", (0.49, FRONT_SURFACE_Y - 0.125, 1.96),
    0.085, 0.015, 0.26, mat_fang, "FANG.R", rotation=(math.radians(180), 0, 0)
)

rounded_box(
    "TONGUE",
    (0.0, FRONT_SURFACE_Y - 0.160, 1.68),
    (0.40, 0.16, 0.74),
    0.14, mat_tongue, "TONGUE"
)
curve_from_points(
    "TONGUE_GROOVE",
    [(0.0, FRONT_SURFACE_Y - 0.245, 1.94), (0.0, FRONT_SURFACE_Y - 0.245, 1.46)],
    mat_groove, 0.014, "TONGUE_DETAIL", bezier=False
)

# ------------------------------------------------------------
# 5) BELLY TARGET - SURFACE RELIEF
# ------------------------------------------------------------
for i, radius in enumerate((0.14, 0.27, 0.40, 0.53, 0.66), start=1):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=0.035,
        location=(0.0, FRONT_SURFACE_Y - 0.100, 1.11),
        rotation=(math.radians(90), 0, 0),
        major_segments=64,
        minor_segments=16
    )
    ring = bpy.context.object
    ring.name = f"BELLY_RING_{i}"
    ring.data.materials.append(mat_black)
    mark(ring, "BELLY_TARGET")

cyl_part(
    "BELLY_CENTER", (0.0, FRONT_SURFACE_Y - 0.110, 1.11),
    0.10, 0.045, mat_black, "BELLY_TARGET", rotation=(math.radians(90), 0, 0)
)

# ------------------------------------------------------------
# 6) ARMS - TSA ANATOMY LOCK / NO WEAPON
# ------------------------------------------------------------
def build_standard_arm(side):
    """
    TSA V6: both arms use the same healthy neutral anatomy.
    No club, no grip pose, no fingers wrapped around an absent prop.
    shoulder -> upper arm -> elbow -> forearm -> wrist -> palm -> digits
    """
    tag = "L" if side < 0 else "R"
    shoulder = (side * 1.15, -0.01, SHOULDER_Z)
    elbow = (side * 1.29, -0.01, 1.72)
    wrist = (side * 1.24, -0.03, 1.16)

    uv_part(f"SHOULDER_{tag}", shoulder, (0.30, 0.34, 0.32), mat_yellow, f"SHOULDER.{tag}")
    capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.20, mat_yellow, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.21, 0.22, 0.21), mat_yellow, f"ELBOW.{tag}")
    capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.17, mat_yellow, f"FOREARM.{tag}")
    uv_part(f"WRIST_{tag}", wrist, (0.13, 0.14, 0.13), mat_yellow, f"WRIST.{tag}")

    # Neutral compact hand, anatomically separated from the forearm.
    make_hand(f"HAND_{tag}", (side * 1.20, -0.04, 0.94), side, mat_yellow, f"HAND.{tag}")

build_standard_arm(-1)
build_standard_arm(1)

# ------------------------------------------------------------
# 7) LEGS - TSA ANATOMY LOCK
# ------------------------------------------------------------
def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * 0.56, 0.03, HIP_Z)
    knee = (side * 0.57, 0.02, 0.50)
    ankle = (side * 0.57, -0.03, 0.22)

    capsule_between(f"THIGH_{tag}", hip, knee, 0.24, mat_yellow, f"THIGH.{tag}")
    uv_part(f"KNEE_{tag}", knee, (0.22, 0.24, 0.21), mat_yellow, f"KNEE.{tag}")
    capsule_between(f"CALF_{tag}", knee, ankle, 0.19, mat_yellow, f"CALF.{tag}")
    uv_part(f"ANKLE_{tag}", ankle, (0.15, 0.17, 0.13), mat_yellow, f"ANKLE.{tag}")
    uv_part(f"FOOT_{tag}", (side * 0.57, -0.14, 0.08), (0.28, 0.40, 0.16), mat_yellow, f"FOOT.{tag}")
    uv_part(f"TOE_{tag}", (side * 0.57, -0.32, 0.07), (0.24, 0.18, 0.12), mat_yellow, f"TOE.{tag}")

build_leg(-1)
build_leg(1)

# ------------------------------------------------------------
# 8) TIGER STRIPES - BODY-CONFORMING DECALS
# ------------------------------------------------------------
front_y = FRONT_SURFACE_Y - 0.12
front_stripes = [
    ("STRIPE_FL_TOP", [(-1.02,3.38),(-0.64,3.34),(-0.88,3.19),(-0.52,3.12),(-1.02,3.06)]),
    ("STRIPE_FR_TOP", [(1.02,3.38),(0.64,3.34),(0.88,3.19),(0.52,3.12),(1.02,3.06)]),
    ("STRIPE_FL_MID", [(-1.04,2.62),(-0.68,2.58),(-0.88,2.43),(-0.56,2.36),(-1.04,2.28)]),
    ("STRIPE_FR_MID", [(1.04,2.62),(0.68,2.58),(0.88,2.43),(0.56,2.36),(1.04,2.28)]),
    ("STRIPE_FL_LOW", [(-1.02,1.62),(-0.70,1.58),(-0.90,1.43),(-0.60,1.36),(-1.02,1.28)]),
    ("STRIPE_FR_LOW", [(1.02,1.62),(0.70,1.58),(0.90,1.43),(0.60,1.36),(1.02,1.28)]),
]
for name, coords in front_stripes:
    flat_poly(name, coords, front_y, mat_black, "STRIPE_FRONT", body)

side_pattern = [
    ((-0.52,3.12),(-0.18,3.08),(-0.40,2.92),(0.02,2.85),(-0.54,2.79)),
    ((-0.50,2.44),(-0.12,2.40),(-0.36,2.23),(0.04,2.16),(-0.52,2.10)),
    ((-0.48,1.48),(-0.10,1.45),(-0.34,1.30),(0.06,1.22),(-0.50,1.16)),
]
for side, x in (("L", -1.105), ("R", 1.105)):
    for idx, coords in enumerate(side_pattern, start=1):
        side_poly(f"STRIPE_{side}_{idx}", list(coords), x, mat_black, "STRIPE_SIDE", body)

back_y = (BODY_D / 2.0) + 0.065
back_stripes = [
    ("STRIPE_BACK_L1", [(-1.00,2.72),(-0.64,2.67),(-0.86,2.52),(-0.48,2.46),(-1.00,2.38)]),
    ("STRIPE_BACK_R1", [(1.00,2.72),(0.64,2.67),(0.86,2.52),(0.48,2.46),(1.00,2.38)]),
    ("STRIPE_BACK_L2", [(-0.98,1.48),(-0.62,1.44),(-0.84,1.28),(-0.46,1.22),(-0.98,1.14)]),
    ("STRIPE_BACK_R2", [(0.98,1.48),(0.62,1.44),(0.84,1.28),(0.46,1.22),(0.98,1.14)]),
]
for name, coords in back_stripes:
    flat_poly(name, coords, back_y, mat_black, "STRIPE_BACK", body)

# ------------------------------------------------------------
# 9) NO WEAPON
# ------------------------------------------------------------
# TSA V6 lock: Arya carries no club. Both hands stay in a healthy neutral pose.

# ------------------------------------------------------------
# 10) LEG MARK
# ------------------------------------------------------------
bpy.ops.object.text_add(
    location=(0.66, FRONT_SURFACE_Y - 0.10, 0.39),
    rotation=(math.radians(90), 0, 0)
)
leg_mark = bpy.context.object
leg_mark.name = "LEG_MARK"
leg_mark.data.body = "S"
leg_mark.data.align_x = 'CENTER'
leg_mark.data.align_y = 'CENTER'
leg_mark.data.size = 0.25
leg_mark.data.extrude = 0.006
leg_mark.data.materials.append(mat_black)
mark(leg_mark, "LEG_DETAIL")

# ------------------------------------------------------------
# LIGHTING / CAMERA
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

add_area("KEY", (-4.7, -5.4, 7.4), 1020, 5.0)
add_area("FILL", (4.4, -3.0, 4.3), 620, 4.0)
add_area("RIM", (0.0, 4.8, 6.6), 880, 4.2)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.97, 0.97, 0.97, 1.0)
    bg.inputs["Strength"].default_value = 0.62

bpy.ops.object.camera_add(location=(0, -8.1, 2.14))
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
    "front": ((0,-8.1,2.12),(0,0,2.0)),
    "three_q_l": ((-6.35,-6.35,2.38),(0,0,2.0)),
    "left": ((-8.1,0,2.12),(0,0,2.0)),
    "back": ((0,8.1,2.12),(0,0,2.0)),
    "right": ((8.1,0,2.12),(0,0,2.0)),
    "three_q_r": ((6.35,-6.35,2.38),(0,0,2.0)),
    "top": ((0,0,10.0),(0,0,1.85)),
    "bottom": ((0,0,-7.0),(0,0,1.40)),
}

# ------------------------------------------------------------
# SPEC / TSA LOCK
# ------------------------------------------------------------
spec = {
    "character": "ARYA",
    "version": "TSA_CHARACTER_004_V6_NO_CLUB_STANDARD_HANDS",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "locked_rangga_base": {
        "body_width": BODY_W,
        "body_depth": BODY_D,
        "body_height": BODY_H,
        "body_center_z": BODY_Z
    },
    "identity_features": {
        "single_center_horn": True,
        "horn_black_bands": True,
        "three_eyes": True,
        "eye_style": "white embedded eyeballs with brown pupils",
        "mouth": "visible mouth cavity with two fangs and centered tongue",
        "belly_pattern": "black concentric target",
        "skin_pattern": "jagged tiger stripes conforming to surface",
        "weapon": None,
        "back_nub": True
    },
    "tsa_locks": {
        "family_base_rule": "Arya body and head remain on the Rangga family baseline; only cosmetics/accessories differ.",
        "eye_depth_rule": "Eyes must sit in real sockets and never read as flat stickers.",
        "arm_anatomy_rule": "Every arm preserves shoulder, upper arm, elbow, forearm, wrist and hand.",
        "leg_anatomy_rule": "Every leg preserves thigh, knee, calf, ankle and foot even at compact scale.",
        "hand_pose_rule": "Both hands use neutral healthy anatomy; no weapon-grip pose and no detached prop interaction.",
        "skin_mark_rule": "Tiger stripes must conform to body curvature, not appear as detached floating plates.",
        "static_gate": "No rig or animation until canonical anatomy and form are approved."
    },
    "tsa_gate": "FAMILY_BASE_LOCK / FACE_DEPTH_LOCK / ANATOMY_LOCK / NO_WEAPON_LOCK / SKIN_CONFORM_LOCK"
}

with open(OUT_DIR / "arya_spec_v6.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "arya_v6.blend"))

bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "arya_v6.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"arya_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 68)
print("ARYA TSA CHARACTER 004 - V6 NO CLUB STANDARD HANDS COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: FAMILY_BASE_LOCK / FACE_DEPTH_LOCK / ANATOMY_LOCK / NO_WEAPON_LOCK / SKIN_CONFORM_LOCK")
print("=" * 68)
