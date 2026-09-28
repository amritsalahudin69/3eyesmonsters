# SAMSUL - TSA Character Reconstruction V2
# Blender 5.2 LTS
# Goal: rebuild Samsul using the locked TSA baseline with correct anatomy,
# integrated face features, surface-conformed spots, and cleaner static form.
# Gate: STATIC MODEL / FORM LOCK

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "samsul_output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.70

# ------------------------------------------------------------
# RANGGA FAMILY BASELINE LOCK
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

FRONT_SURFACE_Y = -(BODY_D / 2.0)
SHOULDER_X = 1.15
SHOULDER_Z = 2.10
HIP_X = 0.56
HIP_Z = 0.82

# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------
PINK = (0.96, 0.66, 0.72, 1.0)
PINK_LID = (0.96, 0.78, 0.83, 1.0)
RED = (0.96, 0.23, 0.21, 1.0)
YELLOW = (1.00, 0.90, 0.33, 1.0)
CREAM = (0.98, 0.95, 0.72, 1.0)
WHITE = (0.985, 0.985, 0.985, 1.0)
PUPIL = (0.23, 0.17, 0.17, 1.0)
CYAN = (0.55, 0.87, 0.91, 1.0)
BLACK = (0.05, 0.05, 0.07, 1.0)
SOCKET = (0.16, 0.13, 0.14, 1.0)
MAGENTA = (0.86, 0.08, 0.50, 1.0)

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


def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64):
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


def cone_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=48, radius2=0.02):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius,
        radius2=radius2,
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
    curve.resolution_u = 8
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
    return mark(obj, region)


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


def boolean_difference(base, cutter):
    mod = base.modifiers.new("BOOL_" + cutter.name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    apply_mod(base, mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def make_disc_mesh(name, center, radius_x, radius_z, axis='Y', segments=48):
    verts = []
    for i in range(segments):
        a = (i / segments) * math.tau
        if axis == 'Y':
            verts.append((center[0] + radius_x * math.cos(a), center[1], center[2] + radius_z * math.sin(a)))
        elif axis == 'X':
            verts.append((center[0], center[1] + radius_x * math.cos(a), center[2] + radius_z * math.sin(a)))
        elif axis == 'Z':
            verts.append((center[0] + radius_x * math.cos(a), center[1] + radius_z * math.sin(a), center[2]))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [list(range(segments))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def conform_decal(obj, target, material, region, offset=0.006, thickness=0.004):
    obj.data.materials.append(material)
    shrink = obj.modifiers.new("TSA_SKIN_CONFORM", 'SHRINKWRAP')
    shrink.target = target
    shrink.wrap_method = 'NEAREST_SURFACEPOINT'
    shrink.wrap_mode = 'OUTSIDE_SURFACE'
    shrink.offset = offset
    apply_mod(obj, shrink.name)

    solid = obj.modifiers.new("TSA_DECAL_THICKNESS", 'SOLIDIFY')
    solid.thickness = thickness
    solid.offset = 0.0
    apply_mod(obj, solid.name)
    return mark(obj, region)


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
    cutter = uv_part(
        name + "_SOCKET_CUTTER",
        (x, FRONT_SURFACE_Y - 0.03, z),
        (r * 1.05, 0.16, r * 1.05),
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

    eye_y = FRONT_SURFACE_Y - 0.055
    uv_part(name + "_WHITE", (x, eye_y, z), (r * 0.94, 0.14, r * 0.94), mat_white, name)
    uv_part(name + "_PUPIL", (x, eye_y - 0.115, z + 0.005), (r * 0.32, 0.045, r * 0.32), mat_pupil, name + ".PUPIL")
    uv_part(name + "_LID", (x, eye_y - 0.030, z + r * 0.46), (r * 1.00, 0.06, r * 0.42), mat_pink_lid, name + ".LID")


# ------------------------------------------------------------
# SCENE SETUP
# ------------------------------------------------------------
clean_scene()

mat_pink = make_mat("SAMSUL_PINK", PINK, 0.28)
mat_pink_lid = make_mat("SAMSUL_PINK_LID", PINK_LID, 0.24)
mat_red = make_mat("SAMSUL_RED", RED, 0.24)
mat_yellow = make_mat("SAMSUL_YELLOW", YELLOW, 0.24)
mat_cream = make_mat("SAMSUL_CREAM", CREAM, 0.32)
mat_white = make_mat("SAMSUL_WHITE", WHITE, 0.18)
mat_pupil = make_mat("SAMSUL_PUPIL", PUPIL, 0.18)
mat_cyan = make_mat("SAMSUL_CYAN", CYAN, 0.22)
mat_black = make_mat("SAMSUL_BLACK", BLACK, 0.26)
mat_socket = make_mat("SAMSUL_SOCKET", SOCKET, 0.42)
mat_magenta = make_mat("SAMSUL_MAGENTA", MAGENTA, 0.24)

# ------------------------------------------------------------
# 1) CORE BODY / FAMILY BASELINE
# ------------------------------------------------------------
body = rounded_box(
    "BODY_CORE",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.30,
    mat_pink,
    "TORSO_HEAD",
)

lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.02, 1.04),
    (1.04, 0.62, 0.76),
    mat_pink,
    "TORSO_LOWER",
)

uv_part("BACK_NUB", (0.0, BODY_D / 2.0 + 0.05, 0.95), (0.17, 0.15, 0.17), mat_pink, "BACK_DETAIL")

# ------------------------------------------------------------
# 2) FACE LOCK
# ------------------------------------------------------------
add_eye_cluster("EYE_TOP", 0.00, 2.84, 0.29)
add_eye_cluster("EYE_LEFT", -0.52, 2.31, 0.30)
add_eye_cluster("EYE_RIGHT", 0.52, 2.31, 0.30)

# nose bridge anchor
uv_part("NOSE_BASE", (0.0, FRONT_SURFACE_Y - 0.060, 1.96), (0.12, 0.065, 0.09), mat_pink_lid, "NOSE")

# droplet under the nose
uv_part("NOSE_DROPLET", (0.0, FRONT_SURFACE_Y - 0.13, 1.78), (0.13, 0.09, 0.26), mat_cyan, "NOSE_DROPLET")
cone_part(
    "NOSE_DROPLET_TIP",
    (0.0, FRONT_SURFACE_Y - 0.13, 1.97),
    0.075,
    0.16,
    mat_cyan,
    "NOSE_DROPLET",
    rotation=(math.radians(180), 0, 0),
)

# mouth bar / cavity
rounded_box(
    "MOUTH_CAVITY",
    (0.0, FRONT_SURFACE_Y - 0.105, 1.72),
    (1.28, 0.09, 0.16),
    0.045,
    mat_black,
    "MOUTH",
)

# triangular teeth row
for idx, x in enumerate([-0.52, -0.37, -0.22, -0.07, 0.08, 0.23, 0.38, 0.53], start=1):
    cone_part(
        f"TOOTH_{idx}",
        (x, FRONT_SURFACE_Y - 0.145, 1.66),
        0.070,
        0.22,
        mat_cream,
        "TOOTH",
        rotation=(math.radians(180), 0, 0),
        vertices=3,
        radius2=0.001,
    )

# ------------------------------------------------------------
# 3) BELLY PATCH + LOGO
# ------------------------------------------------------------
uv_part(
    "BELLY_PATCH",
    (0.0, FRONT_SURFACE_Y - 0.01, 1.04),
    (0.72, 0.10, 0.69),
    mat_cream,
    "BELLY_PATCH",
)

logo_y = FRONT_SURFACE_Y - 0.125
logo_pts = []
for i in range(45):
    t = i / 44
    x = -0.27 + 0.54 * t
    z = 1.11 + 0.048 * math.sin(t * math.pi * 4.0)
    logo_pts.append((x, logo_y, z))
curve_from_points("BELLY_LOGO_BLACK", logo_pts, mat_black, 0.028, "BELLY_LOGO")
curve_from_points(
    "BELLY_LOGO_MAGENTA",
    [(-0.34, logo_y, 1.14), (-0.30, logo_y, 1.08), (-0.25, logo_y, 1.10)],
    mat_magenta,
    0.032,
    "BELLY_LOGO",
)
uv_part("BELLY_LOGO_DOT", (0.39, logo_y - 0.01, 1.06), (0.052, 0.032, 0.052), mat_magenta, "BELLY_LOGO")

# ------------------------------------------------------------
# 4) HAT LOCK
# ------------------------------------------------------------
hat_dome = uv_part("HAT_DOME", (0.0, 0.0, 3.67), (1.15, 0.76, 0.63), mat_red, "HAT")
rounded_box(
    "HAT_BAND",
    (0.0, FRONT_SURFACE_Y - 0.015, 3.29),
    (2.10, 0.12, 0.28),
    0.09,
    mat_red,
    "HAT",
)
curve_from_points(
    "HAT_TAIL",
    [(-0.82, 0.00, 3.88), (-1.04, -0.02, 3.72), (-1.20, -0.02, 3.42), (-1.22, -0.04, 3.15)],
    mat_red,
    0.13,
    "HAT",
)
uv_part("HAT_POM", (-1.23, -0.04, 3.02), (0.23, 0.23, 0.23), mat_red, "HAT")

# ------------------------------------------------------------
# 5) ANATOMY LOCK - ARMS
# ------------------------------------------------------------
arm_targets = {}

def build_arm(side):
    tag = "L" if side < 0 else "R"
    shoulder = (side * SHOULDER_X, -0.01, 1.96)
    elbow = (side * 1.22, -0.02, 1.45)
    wrist = (side * 1.13, -0.03, 0.98)

    shoulder_obj = uv_part(f"SHOULDER_{tag}", shoulder, (0.28, 0.33, 0.30), mat_pink, f"SHOULDER.{tag}")
    upper_arm_obj = capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.20, mat_pink, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.20, 0.22, 0.20), mat_pink, f"ELBOW.{tag}")
    forearm_obj = capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.17, mat_pink, f"FOREARM.{tag}")
    uv_part(f"WRIST_{tag}", wrist, (0.13, 0.14, 0.12), mat_pink, f"WRIST.{tag}")
    hand_loc = (side * 1.10, -0.05, 0.77)
    teardrop_hand(f"HAND_{tag}", hand_loc, side, mat_pink)
    arm_targets[tag] = upper_arm_obj
    return shoulder_obj, upper_arm_obj, forearm_obj

build_arm(-1)
build_arm(1)

# ------------------------------------------------------------
# 6) ANATOMY LOCK - LEGS
# ------------------------------------------------------------
def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * HIP_X, 0.02, HIP_Z)
    knee = (side * 0.57, 0.01, 0.48)
    ankle = (side * 0.57, -0.04, 0.21)

    capsule_between(f"THIGH_{tag}", hip, knee, 0.23, mat_pink, f"THIGH.{tag}")
    uv_part(f"KNEE_{tag}", knee, (0.22, 0.24, 0.20), mat_pink, f"KNEE.{tag}")
    capsule_between(f"CALF_{tag}", knee, ankle, 0.18, mat_pink, f"CALF.{tag}")
    uv_part(f"ANKLE_{tag}", ankle, (0.15, 0.17, 0.12), mat_pink, f"ANKLE.{tag}")
    uv_part(f"FOOT_{tag}", (side * 0.57, -0.15, 0.08), (0.28, 0.40, 0.16), mat_pink, f"FOOT.{tag}")
    uv_part(f"TOE_{tag}", (side * 0.57, -0.33, 0.08), (0.24, 0.18, 0.12), mat_pink, f"TOE.{tag}")

build_leg(-1)
build_leg(1)

# ------------------------------------------------------------
# 7) SKIN / HAT SPOTS - TRUE SURFACE CONFORM
# ------------------------------------------------------------
# body front spots
conform_decal(make_disc_mesh("SPOT_BODY_FRONT_1", (0.32, FRONT_SURFACE_Y - 0.03, 1.47), 0.10, 0.10, 'Y'), body, mat_yellow, "SKIN_SPOT")
conform_decal(make_disc_mesh("SPOT_BODY_FRONT_2", (0.68, FRONT_SURFACE_Y - 0.03, 1.36), 0.17, 0.17, 'Y'), body, mat_yellow, "SKIN_SPOT")

# back spots
BACK_Y = (BODY_D / 2.0) + 0.03
conform_decal(make_disc_mesh("SPOT_BODY_BACK_1", (0.58, BACK_Y, 1.19), 0.12, 0.12, 'Y'), body, mat_yellow, "SKIN_SPOT")
conform_decal(make_disc_mesh("SPOT_BODY_BACK_2", (0.38, BACK_Y, 0.90), 0.20, 0.20, 'Y'), body, mat_yellow, "SKIN_SPOT")

# arm spots on both sides
for idx, (target, x, z) in enumerate([
    (arm_targets['L'], -1.30, 1.44),
    (arm_targets['R'], 1.30, 1.44),
], start=1):
    conform_decal(make_disc_mesh(f"SPOT_ARM_{idx}_A", (x, -0.02, z), 0.10, 0.10, 'X'), target, mat_yellow, "SKIN_SPOT")
    conform_decal(make_disc_mesh(f"SPOT_ARM_{idx}_B", (x, -0.02, z - 0.24), 0.08, 0.08, 'X'), target, mat_yellow, "SKIN_SPOT")

# hat front spots
for idx, (x, y, z, rx, rz) in enumerate([
    (-0.55, -0.67, 3.93, 0.18, 0.15),
    (-0.12, -0.72, 4.00, 0.22, 0.18),
    (0.45, -0.65, 3.78, 0.25, 0.20),
    (-0.80, -0.58, 3.65, 0.11, 0.10),
    (0.20, -0.70, 4.19, 0.12, 0.10),
], start=1):
    conform_decal(make_disc_mesh(f"SPOT_HAT_{idx}", (x, y, z), rx, rz, 'Y'), hat_dome, mat_yellow, "HAT_SPOT")

# ------------------------------------------------------------
# 8) LIGHTING / CAMERA
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

add_area("KEY", (-4.5, -5.5, 7.5), 1000, 5.0)
add_area("FILL", (4.5, -3.0, 4.0), 650, 4.0)
add_area("RIM", (0.0, 4.5, 6.5), 900, 4.0)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.96, 0.96, 0.96, 1.0)
    bg.inputs["Strength"].default_value = 0.75

bpy.ops.object.camera_add(location=(0, -8, 2.1))
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
    "version": "TSA_CHARACTER_006_V2_TSA_ANATOMY_FACE_LOCK",
    "source_strategy": "Rangga-family baseline preserved; rebuilt Samsul with integrated eyes, true limb anatomy, surface-conformed spots, and corrected static form.",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0",
    },
    "rangga_family_base": {
        "BODY_W": BODY_W,
        "BODY_D": BODY_D,
        "BODY_H": BODY_H,
        "BODY_Z": BODY_Z,
    },
    "locks": {
        "eyes_integrated_not_sticker": True,
        "arms_anatomy_chain": True,
        "legs_anatomy_chain": True,
        "skin_spots_conform_to_surface": True,
        "hat_spots_conform_to_surface": True,
        "nose_droplet_anchored": True,
        "mouth_cavity_with_tooth_row": True,
        "belly_patch_logo": True,
    },
    "tsa_gate": "STATIC_MODEL_FORM_LOCK",
}

with open(OUT_DIR / "samsul_spec_v2.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "samsul_v2.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "samsul_v2.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False,
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"samsul_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("SAMSUL TSA CHARACTER 006 - V2 TSA ANATOMY FACE LOCK COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("="*60)
