# RANGGA - TSA Character Reconstruction V2
# Blender 5.2 LTS
# Goal: rebuild Rangga using the locked TSA character baseline.
# Gate: FORM LOCK + FACE DEPTH LOCK + ANATOMY LOCK + SURFACE DETAIL LOCK
#
# IMPORTANT LOCKS
# - Eyes are embedded in real sockets, not sticker-like circles.
# - Arms use shoulder -> upper arm -> elbow -> forearm -> wrist -> hand.
# - Legs use hip/thigh -> knee -> calf -> ankle -> foot.
# - Anatomy may be stylized and compact, but those functional sections must exist.
# - Horns have integrated bases.
# - Spirals sit as shallow surface relief, not floating ornaments.
# - No rig/animation yet; this is a static canonical modeling gate.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------
OUT_DIR = Path.home() / "rangga_output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.35

# Coordinate lock
# front = -Y, up = +Z, symmetry = X=0

# ------------------------------------------------------------
# FAMILY / CHARACTER PROPORTION LOCK
# ------------------------------------------------------------
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.08

# Compact stylized anatomy while preserving Rangga silhouette.
SHOULDER_X = 1.17
SHOULDER_Z = 2.15
HIP_X = 0.56
HIP_Z = 0.80

# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------
BLACK = (0.015, 0.012, 0.012, 1.0)
BLACK_SOFT = (0.030, 0.026, 0.027, 1.0)
BLACK_SOCKET = (0.008, 0.006, 0.008, 1.0)
RED = (0.95, 0.12, 0.09, 1.0)
RED_DARK = (0.55, 0.018, 0.012, 1.0)
MOUTH = (0.17, 0.16, 0.17, 1.0)

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

def make_mat(name, color, roughness=0.32, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    # use_nodes still works in Blender 5.2; keep for predictable Principled output.
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

def bevel(obj, width=0.1, segments=6):
    mod = obj.modifiers.new("TSA_Bevel", "BEVEL")
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

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
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

def spiral_points(cx, cy, cz, radius, turns, steps=180, phase=0.0):
    pts = []
    for i in range(steps):
        t = i / (steps - 1)
        a = phase + t * turns * math.tau
        r = radius * (0.08 + 0.92*t)
        pts.append((cx + r*math.cos(a), cy, cz + r*math.sin(a)))
    return pts

def boolean_difference(base, cutter):
    mod = base.modifiers.new("BOOL_" + cutter.name, "BOOLEAN")
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    apply_mod(base, mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def capsule_between(name, a, b, radius, material, region):
    """Cylinder between two joints + rounded caps. Used for real limb segments."""
    a = Vector(a)
    b = Vector(b)
    mid = (a+b)*0.5
    vec = b-a
    length = vec.length
    cyl = cyl_part(name, tuple(mid), radius, length, material, region)
    cyl.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    # small spheres at each end make the capsule read organically
    uv_part(name+"_A_CAP", tuple(a), (radius, radius, radius), material, region)
    uv_part(name+"_B_CAP", tuple(b), (radius, radius, radius), material, region)
    return cyl

def teardrop_hand(name, loc, side, material):
    # Palm volume, wrist pad and 3 compact digits. Not an oval-only hand.
    x,y,z = loc
    palm = uv_part(name+"_PALM", (x,y,z), (0.23,0.20,0.28), material, "HAND")
    # wrist transition
    uv_part(name+"_WRIST_PAD", (x - side*0.01, y, z+0.24), (0.15,0.15,0.14), material, "WRIST")
    # fingers stacked vertically with slight lateral fan
    for i, dz in enumerate([0.10, 0.00, -0.10]):
        uv_part(
            f"{name}_FINGER_{i}",
            (x - side*0.16, y-0.01, z+dz-0.03),
            (0.075,0.11,0.10),
            material, "FINGER"
        )
    # thumb
    uv_part(name+"_THUMB", (x + side*0.16, y-0.01, z-0.01), (0.08,0.11,0.12), material, "THUMB")
    return palm

# ------------------------------------------------------------
# BUILD
# ------------------------------------------------------------
clean_scene()

mat_black = make_mat("RANGGA_BLACK", BLACK, 0.25)
mat_black_soft = make_mat("RANGGA_EYE", BLACK_SOFT, 0.20)
mat_socket = make_mat("RANGGA_SOCKET", BLACK_SOCKET, 0.50)
mat_red = make_mat("RANGGA_RED", RED, 0.25)
mat_red_dark = make_mat("RANGGA_RED_DARK", RED_DARK, 0.30)
mat_mouth = make_mat("RANGGA_MOUTH", MOUTH, 0.38)

# ------------------------------------------------------------
# 1) PRIMARY BODY FORM
# ------------------------------------------------------------
body = rounded_box(
    "BODY_CORE",
    (0, 0, BODY_Z),
    (BODY_W, BODY_D, BODY_H),
    0.30,
    mat_black,
    "TORSO_HEAD"
)

# Softer lower mass keeps original Rangga toy silhouette.
lower = uv_part(
    "LOWER_VOLUME",
    (0, 0.03, 1.03),
    (1.02, 0.62, 0.72),
    mat_black,
    "TORSO_LOWER"
)

# ------------------------------------------------------------
# 2) HORN BASES + HORNS
# ------------------------------------------------------------
for side in (-1, 1):
    x = side * 0.83
    uv_part(
        f"HORN_BASE_{'L' if side<0 else 'R'}",
        (x, 0.0, 3.56),
        (0.22, 0.22, 0.15),
        mat_black,
        "HORN_BASE"
    )
    cone_part(
        f"HORN_{'L' if side<0 else 'R'}",
        (x, 0.0, 3.90),
        0.22, 0.025, 0.72,
        mat_black,
        f"HORN.{'L' if side<0 else 'R'}",
        rotation=(0, math.radians(-12*side), 0)
    )

# ------------------------------------------------------------
# 3) TRUE EYE SOCKETS + EMBEDDED EYES
# ------------------------------------------------------------
FRONT_SURFACE_Y = -(BODY_D/2.0)
eye_specs = {
    "EYE.TOP":   (0.00, 2.92, 0.30),
    "EYE.LEFT":  (-0.53, 2.34, 0.31),
    "EYE.RIGHT": (0.53, 2.34, 0.31),
}

for name, (x,z,r) in eye_specs.items():
    # Socket cutter actually removes body volume.
    cutter = uv_part(
        name+"_SOCKET_CUTTER",
        (x, FRONT_SURFACE_Y-0.015, z),
        (r*1.12, 0.19, r*1.12),
        mat_socket,
        "CUTTER"
    )
    boolean_difference(body, cutter)

    # Dark socket bowl sits inside the recess.
    uv_part(
        name+"_SOCKET",
        (x, FRONT_SURFACE_Y+0.055, z),
        (r*1.04, 0.10, r*1.04),
        mat_socket,
        "EYE_SOCKET"
    )

    # Eye lens is embedded; center remains behind the former front tangent.
    eye_y = FRONT_SURFACE_Y-0.025
    uv_part(
        name+"_LENS",
        (x, eye_y, z),
        (r*0.92, 0.13, r*0.92),
        mat_black_soft,
        name
    )

    # Red spiral relief hugs the lens surface.
    pts = spiral_points(
        x, eye_y-0.135, z,
        r*0.61, 2.55,
        phase=math.radians(28)
    )
    curve_from_points(name+"_SPIRAL", pts, mat_red, 0.028, name+"_DETAIL")

# ------------------------------------------------------------
# 4) MOUTH GROOVE
# ------------------------------------------------------------
mouth_pts = []
for i in range(48):
    t = i/47
    x = -0.47 + 0.94*t
    # very shallow frown
    z = 1.86 - 0.055*(1.0 - ((t-0.5)/0.5)**2)
    mouth_pts.append((x, FRONT_SURFACE_Y-0.020, z))
curve_from_points("MOUTH_GROOVE", mouth_pts, mat_mouth, 0.020, "MOUTH")

# ------------------------------------------------------------
# 5) BODY SPIRAL - SHALLOW RELIEF, NOT FLOATING
# ------------------------------------------------------------
body_spiral_y = FRONT_SURFACE_Y - 0.028
pts = spiral_points(
    0.0, body_spiral_y, 1.23,
    0.58, 2.20,
    phase=math.radians(18)
)
curve_from_points("BODY_SPIRAL", pts, mat_red, 0.050, "TORSO_DETAIL")

# ------------------------------------------------------------
# 6) ARMS - ANATOMY LOCK
# shoulder -> upper arm -> elbow -> forearm -> wrist -> hand
# ------------------------------------------------------------
def build_arm(side):
    tag = "L" if side < 0 else "R"
    x_sh = side*SHOULDER_X
    # Shoulder joint integrated with body
    shoulder = (x_sh, -0.01, SHOULDER_Z)
    elbow = (side*1.31, -0.02, 1.62)
    wrist = (side*1.26, -0.04, 1.18)

    uv_part(f"SHOULDER_{tag}", shoulder, (0.30,0.34,0.32), mat_black, f"SHOULDER.{tag}")

    # upper arm and forearm are distinct segments
    capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.21, mat_black, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.22,0.24,0.22), mat_black, f"ELBOW.{tag}")
    capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.18, mat_black, f"FOREARM.{tag}")
    uv_part(f"WRIST_{tag}", wrist, (0.15,0.16,0.14), mat_black, f"WRIST.{tag}")

    # hand is small, but functionally separated from forearm
    hand_loc = (side*1.24, -0.05, 0.91)
    teardrop_hand(f"HAND_{tag}", hand_loc, side, mat_black)

build_arm(-1)
build_arm(1)

# ------------------------------------------------------------
# 7) LEGS - ANATOMY LOCK
# thigh -> knee -> calf -> ankle -> foot
# ------------------------------------------------------------
def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side*HIP_X, 0.02, HIP_Z)
    knee = (side*0.57, 0.01, 0.50)
    ankle = (side*0.57, -0.04, 0.22)

    # Compact thigh still exists as a separate volume.
    capsule_between(f"THIGH_{tag}", hip, knee, 0.24, mat_black, f"THIGH.{tag}")
    uv_part(f"KNEE_{tag}", knee, (0.23,0.25,0.21), mat_black, f"KNEE.{tag}")
    capsule_between(f"CALF_{tag}", knee, ankle, 0.19, mat_black, f"CALF.{tag}")
    uv_part(f"ANKLE_{tag}", ankle, (0.16,0.18,0.13), mat_black, f"ANKLE.{tag}")

    # Foot extends toward front (-Y), giving a real toe/heel direction.
    foot_center = (side*0.57, -0.15, 0.08)
    uv_part(f"FOOT_{tag}", foot_center, (0.29,0.42,0.17), mat_black, f"FOOT.{tag}")
    # toe pad
    uv_part(f"TOE_{tag}", (side*0.57,-0.34,0.07), (0.26,0.20,0.13), mat_black, f"TOE.{tag}")

build_leg(-1)
build_leg(1)

# ------------------------------------------------------------
# 8) BACK DETAIL
# ------------------------------------------------------------
uv_part("BACK_NUB", (0.0, BODY_D/2.0 + 0.05, 1.05), (0.17,0.14,0.17), mat_black, "BACK_DETAIL")

# ------------------------------------------------------------
# 9) LIGHTING / CAMERA
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

add_area("KEY", (-4.8,-5.3,7.4), 1050, 5.0)
add_area("FILL", (4.6,-3.1,4.5), 650, 4.0)
add_area("RIM", (0.0,4.8,6.8), 900, 4.2)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.96,0.96,0.96,1.0)
    bg.inputs["Strength"].default_value = 0.80

bpy.ops.object.camera_add(location=(0,-8.2,2.15))
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
    "left": ((-8.2,0,2.10),(0,0,2.0)),
    "back": ((0,8.2,2.10),(0,0,2.0)),
    "right": ((8.2,0,2.10),(0,0,2.0)),
    "three_q_r": ((6.4,-6.4,2.35),(0,0,2.0)),
    "top": ((0,0,10.0),(0,0,1.85)),
    "bottom": ((0,0,-7.0),(0,0,1.45)),
}

# ------------------------------------------------------------
# 10) SPEC / TSA LOCK
# ------------------------------------------------------------
spec = {
    "character": "RANGGA",
    "version": "TSA_CHARACTER_001_V2_ANATOMY_LOCK",
    "coordinate_system": {
        "front_axis": "-Y",
        "up_axis": "+Z",
        "symmetry_plane": "X=0"
    },
    "dimensions": {
        "body_width": BODY_W,
        "body_depth": BODY_D,
        "body_height": BODY_H,
        "body_center_z": BODY_Z
    },
    "identity_features": {
        "body": "black rounded tall rectangular monster body",
        "horns": 2,
        "eyes": 3,
        "eye_pattern": "red spiral embedded in recessed black lenses",
        "belly_pattern": "large red spiral shallow surface relief",
        "mouth": "small shallow frown",
        "back_nub": True
    },
    "tsa_locks": {
        "eye_depth_rule": "Eyes must be embedded into real socket recesses; never sticker-like discs floating on the front surface.",
        "arm_anatomy_rule": "Every arm preserves shoulder, upper arm, elbow, forearm, wrist, palm and simplified digits.",
        "leg_anatomy_rule": "Every leg preserves hip/thigh, knee, calf, ankle, foot and toe direction even when proportions are compact.",
        "surface_detail_rule": "Spiral details must sit as shallow surface-following relief, not free-floating ornaments.",
        "static_gate": "No rig or animation until canonical form, anatomy and all-angle consistency are approved."
    },
    "semantic_regions": [
        "TORSO_HEAD","TORSO_LOWER",
        "SHOULDER.L","UPPER_ARM.L","ELBOW.L","FOREARM.L","WRIST.L","HAND.L",
        "SHOULDER.R","UPPER_ARM.R","ELBOW.R","FOREARM.R","WRIST.R","HAND.R",
        "THIGH.L","KNEE.L","CALF.L","ANKLE.L","FOOT.L",
        "THIGH.R","KNEE.R","CALF.R","ANKLE.R","FOOT.R",
        "HORN.L","HORN.R",
        "EYE.TOP","EYE.LEFT","EYE.RIGHT",
        "MOUTH","TORSO_DETAIL","BACK_DETAIL"
    ],
    "tsa_gate": "FORM_LOCK / FACE_DEPTH_LOCK / ANATOMY_LOCK / SURFACE_DETAIL_LOCK"
}

with open(OUT_DIR / "rangga_spec_v2.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

# ------------------------------------------------------------
# SAVE / EXPORT / PREVIEWS
# ------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "rangga_v2.blend"))

bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "rangga_v2.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"rangga_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*72)
print("RANGGA TSA CHARACTER 001 - V2 ANATOMY LOCK COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: FORM + FACE DEPTH + ANATOMY + SURFACE DETAIL")
print("Eyes: recessed / embedded")
print("Arms: shoulder > upper arm > elbow > forearm > wrist > hand")
print("Legs: thigh > knee > calf > ankle > foot")
print("="*72)
