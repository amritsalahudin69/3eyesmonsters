# LUKMAN - TSA Character Reconstruction V2
# Blender 5.2 LTS
# Goal: keep Lukman's face and body language, but rebuild only the arms/hands and legs/feet
# so anatomy follows the TSA lock: shoulder -> upper arm -> elbow -> forearm -> wrist -> hand,
# and hip/thigh -> knee -> calf -> ankle -> foot.
# Face/body/crest/belly/zipper stay in Lukman's established form.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "lukman_output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.55

# ------------------------------------------------------------
# FAMILY BASELINE LOCK
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

FRONT_Y = -(BODY_D / 2.0) - 0.055

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


def mark_region(obj, region):
    obj["tsa_region"] = region
    return obj


def smooth_object(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True


def apply_modifier(obj, mod_name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_name)
    obj.select_set(False)


def apply_bevel(obj, width=0.18, segments=8):
    mod = obj.modifiers.new("TSA_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    apply_modifier(obj, mod.name)


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
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


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
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def cyl_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
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


def create_jagged_crest(name, y_half=0.61):
    profile = [
        (-1.02, 3.48),
        (-0.88, 3.85),
        (-0.66, 3.72),
        (-0.48, 4.12),
        (-0.30, 3.97),
        ( 0.02, 4.35),
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
    faces.append(list(range(n)))
    faces.append(list(range(n, 2*n))[::-1])
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
    apply_modifier(obj, bevel.name)
    smooth_object(obj)
    return mark_region(obj, "HEAD_CREST")


def add_eye(name, x, z, size):
    uv_part(name, (x, FRONT_Y, z), (size, 0.12, size), mat_white, name)
    uv_part(name + ".PUPIL", (x, FRONT_Y - 0.13, z - 0.005), (size*0.34, 0.05, size*0.34), mat_pupil, name + ".PUPIL")


def build_hand_with_claws(side, wrist, palm_center, tag):
    # proper wrist + palm volume
    uv_part(f"HAND.{tag}.PALM", palm_center, (0.20, 0.15, 0.24), mat_green, f"HAND.{tag}")
    uv_part(f"HAND.{tag}.WRISTPAD", wrist, (0.11, 0.11, 0.10), mat_green, f"WRIST.{tag}")
    # subtle finger/knuckle masses to avoid oval-only limb ending
    for idx, dz in enumerate([0.10, 0.00, -0.10], start=1):
        uv_part(
            f"HAND.{tag}.DIGIT.{idx}",
            (palm_center[0] + side * 0.02, palm_center[1] - 0.01, palm_center[2] + dz),
            (0.08, 0.06, 0.08),
            mat_green,
            f"DIGIT.{tag}",
        )
    # Lukman claws stay as claws, but now attached to hand/palm zone
    claw_base_x = palm_center[0] + side * 0.18
    for idx, z in enumerate([palm_center[2] + 0.12, palm_center[2], palm_center[2] - 0.12], start=1):
        cone_part(
            f"CLAW.{tag}.{idx}",
            (claw_base_x + side * 0.14, palm_center[1], z),
            0.08,
            0.42,
            mat_spike,
            f"CLAW.{tag}",
            rotation=(0, math.radians(-90 if side < 0 else 90), 0),
            vertices=48,
            radius2=0.01,
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
# 1. CORE BODY / FAMILY SHAPE - PRESERVED
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
uv_part("BACK_NUB", (0.0, 0.73, 0.95), (0.18, 0.16, 0.18), mat_green_dark, "BACK_DETAIL")

# ============================================================
# 2. FACE FORM LOCK - PRESERVED
# ============================================================
add_eye("EYE.TOP", 0.00, 2.90, 0.29)
add_eye("EYE.LEFT", -0.52, 2.34, 0.30)
add_eye("EYE.RIGHT", 0.52, 2.34, 0.30)

mouth_z = 1.98
curve_from_points(
    "MOUTH.SEAM",
    [(-0.58, FRONT_Y - 0.10, mouth_z), (0.58, FRONT_Y - 0.10, mouth_z)],
    mat_black,
    0.018,
    "MOUTH"
)

for i, x in enumerate([-0.50,-0.39,-0.28,-0.17,-0.06,0.06,0.17,0.28,0.39,0.50], start=1):
    curve_from_points(
        f"MOUTH.STITCH.{i}",
        [(x, FRONT_Y - 0.115, mouth_z - 0.065), (x, FRONT_Y - 0.115, mouth_z + 0.065)],
        mat_black,
        0.015,
        "MOUTH_STITCH"
    )

# ============================================================
# 3. BELLY / ZIPPER / LOGO - PRESERVED
# ============================================================
uv_part("BELLY_PATCH", (0.0, FRONT_Y - 0.015, 1.12), (0.74, 0.10, 0.72), mat_yellow, "BELLY_PATCH")

zip_y = FRONT_Y - 0.145
curve_from_points("ZIPPER.CENTER", [(0.0, zip_y, 1.75), (0.0, zip_y, 1.10)], mat_black, 0.026, "ZIPPER")
for i, z in enumerate([1.70,1.60,1.50,1.40,1.30,1.20], start=1):
    direction = -1 if i % 2 == 0 else 1
    curve_from_points(
        f"ZIPPER.TOOTH.{i}",
        [(-0.095, zip_y, z + 0.025*direction), (0.095, zip_y, z - 0.025*direction)],
        mat_black,
        0.022,
        "ZIPPER"
    )

rounded_box("ZIPPER.SLIDER", (0.0, zip_y - 0.015, 1.08), (0.26, 0.11, 0.22), 0.06, mat_orange, "ZIPPER_PULL")
curve_from_points(
    "ZIPPER.PULL_LOOP",
    [(-0.14, zip_y - 0.025, 1.02), (-0.18, zip_y - 0.025, 0.78), (-0.13, zip_y - 0.025, 0.57),
     (0.13, zip_y - 0.025, 0.57), (0.18, zip_y - 0.025, 0.78), (0.14, zip_y - 0.025, 1.02)],
    mat_orange,
    0.055,
    "ZIPPER_PULL",
    cyclic=True,
)

logo_y = FRONT_Y - 0.14
for row, z in enumerate((1.64, 1.56), start=1):
    pts = []
    for i in range(30):
        t = i/29
        x = -0.70 + 0.38*t
        zz = z + 0.035*math.sin(t*math.pi*4)
        pts.append((x, logo_y, zz))
    curve_from_points(f"LOGO.BLACK.{row}", pts, mat_black, 0.024, "BELLY_LOGO")
curve_from_points("LOGO.RED_ACCENT", [(-0.74, logo_y, 1.64),(-0.69, logo_y, 1.69),(-0.64, logo_y, 1.66)], mat_red, 0.026, "BELLY_LOGO")

# ============================================================
# 4. TSA ANATOMY REBUILD - ONLY ARMS/HANDS + LEGS/FEET CHANGED
# ============================================================
def build_arm(side):
    tag = "L" if side < 0 else "R"
    shoulder = (side * 1.08, 0.00, 1.96)
    elbow = (side * 1.23, 0.00, 1.46)
    wrist = (side * 1.18, -0.01, 1.00)
    palm = (side * 1.22, -0.01, 0.77)

    uv_part(f"SHOULDER.{tag}", shoulder, (0.24, 0.28, 0.28), mat_green, f"SHOULDER.{tag}")
    capsule_between(f"UPPER_ARM.{tag}", shoulder, elbow, 0.18, mat_green, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW.{tag}", elbow, (0.18, 0.18, 0.18), mat_green, f"ELBOW.{tag}")
    capsule_between(f"FOREARM.{tag}", elbow, wrist, 0.16, mat_green, f"FOREARM.{tag}")
    uv_part(f"WRIST.{tag}", wrist, (0.11, 0.11, 0.10), mat_green, f"WRIST.{tag}")
    build_hand_with_claws(side, wrist, palm, tag)


def build_leg(side):
    tag = "L" if side < 0 else "R"
    hip = (side * 0.56, 0.03, 0.82)
    knee = (side * 0.58, 0.02, 0.50)
    ankle = (side * 0.58, -0.02, 0.22)

    capsule_between(f"THIGH.{tag}", hip, knee, 0.21, mat_green, f"THIGH.{tag}")
    uv_part(f"KNEE.{tag}", knee, (0.19, 0.19, 0.17), mat_green, f"KNEE.{tag}")
    capsule_between(f"CALF.{tag}", knee, ankle, 0.17, mat_green, f"CALF.{tag}")
    uv_part(f"ANKLE.{tag}", ankle, (0.14, 0.15, 0.10), mat_green, f"ANKLE.{tag}")
    uv_part(f"FOOT.{tag}", (side * 0.58, -0.14, 0.08), (0.23, 0.30, 0.15), mat_green, f"FOOT.{tag}")
    uv_part(f"TOE.{tag}", (side * 0.58, -0.28, 0.08), (0.19, 0.12, 0.10), mat_green, f"TOE.{tag}")


build_arm(-1)
build_arm(1)
build_leg(-1)
build_leg(1)

# ============================================================
# 5. LIGHTING / CAMERA
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
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.96,0.96,0.96,1.0)
    bg.inputs["Strength"].default_value = 0.75

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
    "version": "TSA_CHARACTER_007_V2_ANATOMY_LOCK_KEEP_FACE_BODY",
    "source_strategy": "Preserve Lukman face/body/crest/belly/zipper, rebuild only arm-hand and leg-foot anatomy per TSA baseline.",
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
        "face": True,
        "body": True,
        "jagged_top_crest": True,
        "stitched_mouth": True,
        "yellow_belly_patch": True,
        "vertical_zipper": True,
        "orange_puller": True,
        "three_claws_each_side": True,
        "back_nub": True,
    },
    "rebuild_only": {
        "shoulder_upperarm_elbow_forearm_wrist_hand": True,
        "thigh_knee_calf_ankle_foot": True,
    },
    "tsa_gate": "STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR / "lukman_spec_v2.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "lukman_v2.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "lukman_v2.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc,target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"lukman_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*60)
print("LUKMAN TSA CHARACTER 007 - V2 ANATOMY LOCK KEEP FACE BODY COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("="*60)
