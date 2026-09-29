# RANGGA - TSA Character Reconstruction V1
# Blender 4.x
# Goal: static canonical model from front/side/back/top/bottom turnaround baseline.
# Gate: MODEL STATIC only. No rig / animation yet.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "rangga_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RENDER_RES = 768
ORTHO_SCALE = 5.2
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05
BLACK = (0.015, 0.012, 0.012, 1.0)
BLACK_SOFT = (0.035, 0.030, 0.030, 1.0)
RED = (0.85, 0.035, 0.025, 1.0)
MOUTH = (0.06, 0.055, 0.055, 1.0)

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def make_mat(name, color, roughness=0.32, metallic=0.0):
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

def apply_bevel(obj, width=0.18, segments=6):
    mod = obj.modifiers.new("TSA_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)

def rounded_box(name, location, dimensions, bevel, material, region):
    bpy.ops.mesh.primitive_cube_add(location=location)
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

def cone_part(name, location, radius, depth, material, region, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=radius, radius2=0.025, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 2
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 5
    spline = curve.splines.new('POLY')
    spline.points.add(len(pts)-1)
    for i, p in enumerate(pts):
        spline.points[i].co = (*p, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def spiral(name, center_x, center_z, y, radius, turns, material, bevel, region, phase=0.0):
    pts = []
    steps = 150
    for i in range(steps):
        t = i / (steps - 1)
        ang = phase + t * turns * math.tau
        r = radius * (0.10 + 0.90 * t)
        x = center_x + r * math.cos(ang)
        z = center_z + r * math.sin(ang)
        pts.append((x, y, z))
    return curve_from_points(name, pts, material, bevel, region)

clean_scene()
mat_black = make_mat("RANGGA_BLACK", BLACK, roughness=0.26)
mat_black_soft = make_mat("RANGGA_EYE", BLACK_SOFT, roughness=0.22)
mat_red = make_mat("RANGGA_RED", RED, roughness=0.25)
mat_mouth = make_mat("RANGGA_MOUTH", MOUTH, roughness=0.30)

body = rounded_box("BODY", (0, 0, BODY_Z), (BODY_W, BODY_D, BODY_H), 0.28, mat_black, "TORSO_HEAD")
lower = uv_part("LOWER_VOLUME", (0, 0.02, 1.03), (1.05, 0.63, 0.78), mat_black, "TORSO_LOWER")
arm_l = uv_part("ARM.L", (-1.18, -0.01, 1.55), (0.34, 0.42, 0.82), mat_black, "ARM.L", rotation=(0, math.radians(-8), math.radians(-5)))
arm_r = uv_part("ARM.R", (1.18, -0.01, 1.55), (0.34, 0.42, 0.82), mat_black, "ARM.R", rotation=(0, math.radians(8), math.radians(5)))
leg_l = rounded_box("LEG.L", (-0.61, 0.02, 0.43), (0.58, 0.74, 0.90), 0.22, mat_black, "LEG.L")
leg_r = rounded_box("LEG.R", (0.61, 0.02, 0.43), (0.58, 0.74, 0.90), 0.22, mat_black, "LEG.R")
horn_l = cone_part("HORN.L", (-0.88, 0.00, 3.82), 0.22, 0.64, mat_black, "HORN.L", rotation=(0, math.radians(-14), 0))
horn_r = cone_part("HORN.R", (0.88, 0.00, 3.82), 0.22, 0.64, mat_black, "HORN.R", rotation=(0, math.radians(14), 0))
tail_nub = uv_part("BACK_NUB", (0.0, 0.73, 1.05), (0.17, 0.16, 0.17), mat_black, "BACK_DETAIL")

FRONT_Y = -(BODY_D / 2.0) - 0.055
eye_specs = {"EYE.TOP": (0.00, 2.90, 0.30), "EYE.LEFT": (-0.53, 2.33, 0.30), "EYE.RIGHT": (0.53, 2.33, 0.30)}
for name, (x, z, s) in eye_specs.items():
    uv_part(name, (x, FRONT_Y, z), (s, 0.12, s), mat_black_soft, name)
    spiral(name + "_SPIRAL", x, z, FRONT_Y - 0.125, s * 0.70, 2.55, mat_red, 0.032, name + "_DETAIL", phase=math.radians(25))

mouth_pts = []
for i in range(40):
    t = i / 39
    x = -0.48 + 0.96 * t
    z = 1.85 - 0.045 * (1.0 - ((t - 0.5) / 0.5) ** 2)
    mouth_pts.append((x, FRONT_Y - 0.10, z))
curve_from_points("MOUTH", mouth_pts, mat_mouth, 0.025, "MOUTH")
spiral("BODY_SPIRAL", 0.0, 1.22, FRONT_Y - 0.085, 0.57, 2.15, mat_red, 0.055, "TORSO_DETAIL", phase=math.radians(18))

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
    "character": "RANGGA",
    "version": "TSA_CHARACTER_001_V1",
    "coordinate_system": {"front_axis": "-Y", "up_axis": "+Z", "symmetry_plane": "X=0"},
    "dimensions": {"body_width": BODY_W, "body_depth": BODY_D, "body_height": BODY_H, "body_center_z": BODY_Z},
    "landmarks": {
        "eye_top": [0.00, float(FRONT_Y), 2.90],
        "eye_left": [-0.53, float(FRONT_Y), 2.33],
        "eye_right": [0.53, float(FRONT_Y), 2.33],
        "mouth_center": [0.00, float(FRONT_Y), 1.85],
        "belly_spiral_center": [0.00, float(FRONT_Y), 1.22],
        "horn_left": [-0.88, 0.0, 3.82],
        "horn_right": [0.88, 0.0, 3.82]
    },
    "semantic_regions": ["TORSO_HEAD", "TORSO_LOWER", "ARM.L", "ARM.R", "LEG.L", "LEG.R", "HORN.L", "HORN.R", "EYE.TOP", "EYE.LEFT", "EYE.RIGHT", "MOUTH", "TORSO_DETAIL", "BACK_DETAIL"],
    "tsa_gate": "STATIC_MODEL_V1"
}
with open(OUT_DIR / "rangga_spec.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

blend_path = OUT_DIR / "rangga_v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

glb_path = OUT_DIR / "rangga_v1.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format='GLB', export_apply=True, export_animations=False)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"rangga_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 60)
print("RANGGA TSA CHARACTER 001 - STATIC V1 COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Created: rangga_v1.blend, rangga_v1.glb, rangga_spec.json + 8 preview PNGs")
print("=" * 60)
