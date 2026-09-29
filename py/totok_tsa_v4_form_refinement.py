# TOTOK - TSA Character Reconstruction V4
# Blender 5.2 LTS
# Goal: targeted proportion refinement from the V3 baseline lock.
# Gate: FORM / SILHOUETTE LOCK only. No rig / animation yet.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "totok_output_v4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 896
ORTHO_SCALE = 5.45
FRONT_AXIS = "-Y"
UP_AXIS = "+Z"

# -----------------------------------------------------------------------------
# LOCKED TSA SPEC - derived from the turnaround baseline, not from failed V1/V2.
# -----------------------------------------------------------------------------
SPEC = {
    "character": "TOTOK",
    "version": "TSA_CHARACTER_002_V4_FORM_REFINEMENT",
    "coordinate_system": {
        "front_axis": FRONT_AXIS,
        "up_axis": UP_AXIS,
        "symmetry_plane": "X=0"
    },
    "head": {
        "center": [0.0, 0.0, 2.755],
        "dimensions": [2.04, 1.46, 1.10],
        "bevel": 0.15
    },
    "body_sections": [
        # z, full_width_x, full_depth_y
        [2.20, 1.70, 1.32],
        [1.98, 1.78, 1.38],
        [1.48, 1.82, 1.44],
        [0.92, 1.72, 1.36],
        [0.61, 1.48, 1.18]
    ],
    "bottom_tip": {
        "center": [0.0, 0.0, 0.345],
        "top_radius": 0.43,
        "bottom_radius": 0.035,
        "depth": 0.53
    },
    "roof_slab": {
        "center": [0.0, 0.0, 3.355],
        "dimensions": [2.18, 1.58, 0.11],
        "bevel": 0.030
    },
    "roof": {
        "base_z": 3.405,
        "apex_z": 4.205,
        "half_width": 0.72,
        "half_depth": 0.61,
        "bevel": 0.035
    },
    "halo": {
        "center": [0.0, -0.02, 4.58],
        "major_radius": 0.68,
        "minor_radius": 0.068,
        "tilt_x_deg": 24.0
    },
    "eyes": {
        "white_scale": [0.255, 0.108, 0.255],
        "pupil_scale": [0.105, 0.047, 0.105],
        "centers": {
            "EYE.TOP": [0.00, -0.748, 2.98],
            "EYE.LEFT": [-0.41, -0.765, 2.61],
            "EYE.RIGHT": [0.41, -0.765, 2.61]
        },
        "pupil_front_offset": -0.106,
        "pupil_z_offset": -0.012
    },
    "mouth": {
        "center_z": 2.285,
        "half_width": 0.43,
        "front_y": -0.770
    },
    "tongue": {
        "center": [0.00, -0.815, 1.625],
        "dimensions": [0.48, 0.15, 1.24],
        "bevel": 0.068
    },
    "arms": {
        "left_center": [-1.00, 0.00, 1.53],
        "right_center": [1.00, 0.00, 1.53],
        "scale": [0.225, 0.285, 0.49],
        "left_rot_y_deg": -8.0,
        "right_rot_y_deg": 8.0
    },
    "tail": {
        "points": [
            [-0.70, 0.55, 1.07],
            [-1.12, 0.88, 0.91],
            [-1.48, 0.78, 1.08],
            [-1.42, 0.58, 1.40],
            [-1.18, 0.54, 1.60]
        ],
        "bevel": 0.067,
        "tip_radius": 0.082
    }
}

# -----------------------------------------------------------------------------
# Helpers copied in spirit from the successful Rangga baseline generator.
# -----------------------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def make_mat(name, color, roughness=0.34, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mark_region(obj, region):
    obj["tsa_region"] = region
    return obj


def smooth_object(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True


def apply_bevel(obj, width=0.12, segments=6):
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


def uv_part(name, location, scale, material, region, rotation=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False, bezier=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 18 if bezier else 2
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 6

    if bezier:
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(pts) - 1)
        for bp, p in zip(spline.bezier_points, pts):
            bp.co = p
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
    else:
        spline = curve.splines.new('POLY')
        spline.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            spline.points[i].co = (*p, 1.0)
        spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def make_tapered_body(name, sections, material, region, samples=56, exponent=4.15):
    """Rounded rectangular volume from superellipse cross-sections.

    This avoids the V2 failure where a sphere was used for Totok's torso.
    Each section is (z, width, depth).
    """
    verts = []
    faces = []

    for z, width, depth in sections:
        a = width / 2.0
        b = depth / 2.0
        for i in range(samples):
            t = math.tau * i / samples
            c = math.cos(t)
            s = math.sin(t)
            x = a * math.copysign(abs(c) ** (2.0 / exponent), c)
            y = b * math.copysign(abs(s) ** (2.0 / exponent), s)
            verts.append((x, y, z))

    ring_count = len(sections)
    for r in range(ring_count - 1):
        a0 = r * samples
        a1 = (r + 1) * samples
        for i in range(samples):
            j = (i + 1) % samples
            faces.append((a0 + i, a0 + j, a1 + j, a1 + i))

    # top / bottom caps
    bottom_idx = len(verts)
    verts.append((0.0, 0.0, sections[-1][0]))
    top_idx = len(verts)
    verts.append((0.0, 0.0, sections[0][0]))

    last = (ring_count - 1) * samples
    for i in range(samples):
        j = (i + 1) % samples
        faces.append((bottom_idx, last + j, last + i))
        faces.append((top_idx, i, j))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    smooth_object(obj)

    # Very light subdivision keeps the parameterized silhouette stable.
    sub = obj.modifiers.new("TSA_Subdivision", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    return mark_region(obj, region)


def make_downward_tip(name, center, top_radius, bottom_radius, depth, material, region):
    # Blender's radius1 is the lower end; radius2 is the upper end.
    bpy.ops.mesh.primitive_cone_add(
        vertices=48,
        radius1=bottom_radius,
        radius2=top_radius,
        depth=depth,
        location=center
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)


def make_pyramid(name, spec, material, region):
    hw = spec["half_width"]
    hd = spec["half_depth"]
    bz = spec["base_z"]
    az = spec["apex_z"]
    verts = [
        (-hw, -hd, bz),
        ( hw, -hd, bz),
        ( hw,  hd, bz),
        (-hw,  hd, bz),
        (0.0, 0.0, az)
    ]
    faces = [
        (0, 1, 2, 3),
        (0, 4, 1),
        (1, 4, 2),
        (2, 4, 3),
        (3, 4, 0)
    ]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    apply_bevel(obj, spec["bevel"], 4)
    smooth_object(obj)
    return mark_region(obj, region)


def make_halo(material):
    h = SPEC["halo"]
    bpy.ops.mesh.primitive_torus_add(
        major_radius=h["major_radius"],
        minor_radius=h["minor_radius"],
        major_segments=72,
        minor_segments=20,
        location=h["center"],
        rotation=(math.radians(h["tilt_x_deg"]), 0, 0)
    )
    obj = bpy.context.object
    obj.name = "HALO"
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, "HALO")


def add_area(name, loc, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.data.color = color
    return light


def point_camera(camera, location, target=(0, 0, 2.45)):
    camera.location = location
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------
clean_scene()

BODY = make_mat("TOTOK_BODY", (0.80, 0.765, 0.69, 1.0), roughness=0.38)
ROOF = make_mat("TOTOK_ROOF", (0.84, 0.81, 0.75, 1.0), roughness=0.42)
HALO = make_mat("TOTOK_HALO", (1.00, 0.72, 0.06, 1.0), roughness=0.24)
EYE = make_mat("TOTOK_EYE_WHITE", (0.985, 0.985, 0.985, 1.0), roughness=0.19)
PUPIL = make_mat("TOTOK_PUPIL", (0.13, 0.07, 0.08, 1.0), roughness=0.23)
MOUTH = make_mat("TOTOK_MOUTH", (0.12, 0.07, 0.065, 1.0), roughness=0.38)
TONGUE = make_mat("TOTOK_TONGUE", (0.90, 0.10, 0.10, 1.0), roughness=0.31)

head = rounded_box(
    "HEAD",
    tuple(SPEC["head"]["center"]),
    tuple(SPEC["head"]["dimensions"]),
    SPEC["head"]["bevel"],
    BODY,
    "HEAD"
)

body = make_tapered_body(
    "BODY",
    SPEC["body_sections"],
    BODY,
    "TORSO"
)

tip = make_downward_tip(
    "BOTTOM_TIP",
    tuple(SPEC["bottom_tip"]["center"]),
    SPEC["bottom_tip"]["top_radius"],
    SPEC["bottom_tip"]["bottom_radius"],
    SPEC["bottom_tip"]["depth"],
    BODY,
    "BOTTOM_TIP"
)

roof_slab = rounded_box(
    "ROOF_SLAB",
    tuple(SPEC["roof_slab"]["center"]),
    tuple(SPEC["roof_slab"]["dimensions"]),
    SPEC["roof_slab"]["bevel"],
    ROOF,
    "ROOF_SLAB"
)

roof = make_pyramid("ROOF", SPEC["roof"], ROOF, "ROOF")
halo = make_halo(HALO)

# Eyes: triangular 3-eye layout.
for eye_name, center in SPEC["eyes"]["centers"].items():
    uv_part(
        eye_name,
        tuple(center),
        tuple(SPEC["eyes"]["white_scale"]),
        EYE,
        eye_name
    )
    pupil_center = (
        center[0],
        center[1] + SPEC["eyes"]["pupil_front_offset"],
        center[2] + SPEC["eyes"]["pupil_z_offset"]
    )
    uv_part(
        eye_name + "_PUPIL",
        pupil_center,
        tuple(SPEC["eyes"]["pupil_scale"]),
        PUPIL,
        eye_name + "_PUPIL"
    )

# Mouth slit: small curved line directly above the tongue.
mouth_pts = []
for i in range(34):
    t = i / 33.0
    x = -SPEC["mouth"]["half_width"] + (2.0 * SPEC["mouth"]["half_width"] * t)
    z = SPEC["mouth"]["center_z"] - 0.035 * (1.0 - ((t - 0.5) / 0.5) ** 2)
    mouth_pts.append((x, SPEC["mouth"]["front_y"], z))
curve_from_points("MOUTH", mouth_pts, MOUTH, 0.024, "MOUTH")

# Tongue is a flat rounded strip, not a long cuboid floating beside the model.
tongue = rounded_box(
    "TONGUE",
    tuple(SPEC["tongue"]["center"]),
    tuple(SPEC["tongue"]["dimensions"]),
    SPEC["tongue"]["bevel"],
    TONGUE,
    "TONGUE"
)

# Integrated droopy arms: one smooth volume each, no segmented bead/cylinder chain.
arm_l = uv_part(
    "ARM.L",
    tuple(SPEC["arms"]["left_center"]),
    tuple(SPEC["arms"]["scale"]),
    BODY,
    "ARM.L",
    rotation=(0, math.radians(SPEC["arms"]["left_rot_y_deg"]), math.radians(-7.0))
)
arm_r = uv_part(
    "ARM.R",
    tuple(SPEC["arms"]["right_center"]),
    tuple(SPEC["arms"]["scale"]),
    BODY,
    "ARM.R",
    rotation=(0, math.radians(SPEC["arms"]["right_rot_y_deg"]), math.radians(7.0))
)

# Tail: smooth curved tube from rear-left, visible around the side.
tail_pts = [tuple(p) for p in SPEC["tail"]["points"]]
tail = curve_from_points("TAIL", tail_pts, BODY, SPEC["tail"]["bevel"], "TAIL", bezier=True)
uv_part(
    "TAIL_TIP",
    tail_pts[-1],
    (SPEC["tail"]["tip_radius"],) * 3,
    BODY,
    "TAIL_TIP"
)

# -----------------------------------------------------------------------------
# Lighting / render - same reliable camera strategy as Rangga.
# -----------------------------------------------------------------------------
add_area("KEY", (-4.5, -5.5, 7.5), 1050, 5.0)
add_area("FILL", (4.5, -3.0, 4.0), 650, 4.0)
add_area("RIM", (0.0, 4.5, 6.5), 900, 4.0)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.97, 0.97, 0.97, 1.0)
    bg.inputs["Strength"].default_value = 0.85

bpy.ops.object.camera_add(location=(0, -8, 2.45))
cam = bpy.context.object
cam.name = "TSA_CAMERA"
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
bpy.context.scene.camera = cam

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
    "front": ((0, -8.0, 2.38), (0, 0, 2.32)),
    "three_q_l": ((-6.3, -6.3, 2.58), (0, 0, 2.32)),
    "left": ((-8.0, 0.0, 2.38), (0, 0, 2.32)),
    "back": ((0, 8.0, 2.38), (0, 0, 2.32)),
    "right": ((8.0, 0.0, 2.38), (0, 0, 2.32)),
    "three_q_r": ((6.3, -6.3, 2.58), (0, 0, 2.32)),
    "top": ((0, 0, 10.0), (0, 0, 2.30)),
    "bottom": ((0, 0, -7.0), (0, 0, 2.20)),
}

# Persist reconstruction spec first.
with open(OUT_DIR / "totok_spec_v4.json", "w", encoding="utf-8") as f:
    json.dump(SPEC, f, indent=2)

# Save and export before preview rendering.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "totok_v4.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "totok_v4.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name, (loc, target) in views.items():
    point_camera(cam, loc, target)
    scene.render.filepath = str(OUT_DIR / f"totok_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("=" * 68)
print("TOTOK TSA CHARACTER 002 - STATIC V4 FORM REFINEMENT COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: FORM / SILHOUETTE LOCK only - no rig / animation")
print("=" * 68)
