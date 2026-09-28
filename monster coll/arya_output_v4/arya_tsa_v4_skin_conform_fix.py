
# ARYA - TSA Character Reconstruction V2
# Blender 5.2 LTS
# FORM LOCK rebuild.
# RULE: Arya reuses the proven Rangga body family exactly.
# Only cosmetics/accessories differ: center horn, eyes, tongue/fangs,
# tiger stripes, belly target, club, yellow materials.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "arya_output_v4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.35

# ============================================================
# LOCKED RANGGA FAMILY GEOMETRY
# ============================================================
BODY_W = 2.20
BODY_D = 1.34
BODY_H = 3.10
BODY_Z = 2.05

FRONT_Y = -(BODY_D / 2.0) - 0.055

# Arya palette from the supplied turnaround
YELLOW = (1.00, 0.72, 0.00, 1.0)
YELLOW_SPIKE = (1.00, 0.78, 0.05, 1.0)
BLACK = (0.025, 0.022, 0.020, 1.0)
WHITE = (0.985, 0.985, 0.985, 1.0)
PUPIL = (0.14, 0.075, 0.055, 1.0)
RED = (0.78, 0.035, 0.025, 1.0)
TONGUE_RED = (0.96, 0.13, 0.18, 1.0)
FANG = (0.95, 0.91, 0.80, 1.0)
GROOVE = (0.75, 0.055, 0.060, 1.0)

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

def cone_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64, radius2=0.02):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius, radius2=radius2, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def cylinder_part(name, location, radius, depth, material, region, rotation=(0,0,0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 3
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

def _skin_decal_finish(obj, target, region, offset=0.006):
    """
    TSA V4:
    Skin markings are decals that CONFORM to the body surface.
    They are not thick floating plates.
    """
    shrink = obj.modifiers.new("TSA_SKIN_CONFORM", "SHRINKWRAP")
    shrink.target = target
    shrink.wrap_method = 'NEAREST_SURFACEPOINT'
    shrink.wrap_mode = 'OUTSIDE_SURFACE'
    shrink.offset = offset

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=shrink.name)
    obj.select_set(False)

    # Very small thickness only to make export/render robust.
    solid = obj.modifiers.new("TSA_DECAL_MICRO_THICKNESS", "SOLIDIFY")
    solid.thickness = 0.004
    solid.offset = 0.0
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solid.name)
    obj.select_set(False)

    return mark_region(obj, region)

def flat_poly(name, coords_xz, y, material, region, target):
    # Create a flat jagged decal and shrinkwrap it onto the body.
    verts = [(x, y, z) for (x, z) in coords_xz]
    face = list(range(len(verts)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [face])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return _skin_decal_finish(obj, target, region)

def side_poly(name, coords_yz, x, material, region, target):
    # Same rule for left/right markings: conform to body curvature.
    verts = [(x, y, z) for (y, z) in coords_yz]
    face = list(range(len(verts)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [face])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return _skin_decal_finish(obj, target, region)

clean_scene()

mat_yellow = make_mat("ARYA_YELLOW", YELLOW, 0.24)
mat_spike = make_mat("ARYA_SPIKE_YELLOW", YELLOW_SPIKE, 0.25)
mat_black = make_mat("ARYA_BLACK", BLACK, 0.24)
mat_white = make_mat("ARYA_WHITE", WHITE, 0.18)
mat_pupil = make_mat("ARYA_PUPIL", PUPIL, 0.20)
mat_red = make_mat("ARYA_RED", RED, 0.24)
mat_tongue = make_mat("ARYA_TONGUE", TONGUE_RED, 0.24)
mat_fang = make_mat("ARYA_FANG", FANG, 0.28)
mat_groove = make_mat("ARYA_GROOVE", GROOVE, 0.30)

# ============================================================
# A. EXACT RANGGA FAMILY BASE
# ============================================================
body = rounded_box(
    "BODY", (0,0,BODY_Z), (BODY_W, BODY_D, BODY_H),
    0.28, mat_yellow, "TORSO_HEAD"
)
lower = uv_part(
    "LOWER_VOLUME", (0,0.02,1.03), (1.05,0.63,0.78),
    mat_yellow, "TORSO_LOWER"
)
arm_l = uv_part(
    "ARM.L", (-1.18,-0.01,1.55), (0.34,0.42,0.82),
    mat_yellow, "ARM.L",
    rotation=(0, math.radians(-8), math.radians(-5))
)
arm_r = uv_part(
    "ARM.R", (1.18,-0.01,1.55), (0.34,0.42,0.82),
    mat_yellow, "ARM.R",
    rotation=(0, math.radians(8), math.radians(5))
)
leg_l = rounded_box(
    "LEG.L", (-0.61,0.02,0.43), (0.58,0.74,0.90),
    0.22, mat_yellow, "LEG.L"
)
leg_r = rounded_box(
    "LEG.R", (0.61,0.02,0.43), (0.58,0.74,0.90),
    0.22, mat_yellow, "LEG.R"
)
back_nub = uv_part(
    "BACK_NUB", (0.0,0.73,1.05), (0.17,0.16,0.17),
    mat_yellow, "BACK_DETAIL"
)

# hands
# Character RIGHT hand is on viewer-left (negative X) and must actually grip the club.
hand_l = uv_part("HAND.CLUB", (-1.40,-0.05,1.46), (0.24,0.23,0.27), mat_yellow, "HAND.CLUB")
# Other hand remains relaxed.
hand_r = uv_part("HAND.FREE", (1.20,-0.04,0.92), (0.23,0.23,0.28), mat_yellow, "HAND.FREE")

# ============================================================
# B. SINGLE CENTER HORN - FLUSH BLACK BANDS, NOT FLOATING TORUS
# ============================================================
horn = cone_part(
    "HORN.CENTER", (0,0,3.98), 0.29, 0.82,
    mat_yellow, "HORN.CENTER"
)
# Black band discs overlap the cone and therefore read as painted bands.
band_data = [
    (3.72, 0.26),
    (3.85, 0.22),
    (3.98, 0.18),
    (4.11, 0.14),
]
for i, (z, rad) in enumerate(band_data, 1):
    cylinder_part(
        f"HORN.BAND.{i}", (0,0,z), rad, 0.060,
        mat_black, "HORN_DETAIL"
    )

# ============================================================
# C. FACE - SAME TRIANGULAR EYE LAYOUT AS FAMILY
# ============================================================
eyes = {
    "EYE.TOP": (0.00, 2.92, 0.29),
    "EYE.LEFT": (-0.52, 2.37, 0.30),
    "EYE.RIGHT": (0.52, 2.37, 0.30),
}
for name,(x,z,s) in eyes.items():
    uv_part(name, (x,FRONT_Y,z), (s,0.12,s), mat_white, name)
    uv_part(name+".PUPIL", (x,FRONT_Y-0.125,z), (s*0.36,0.05,s*0.36), mat_pupil, name+".PUPIL")

# ------------------------------------------------------------
# MOUTH ASSEMBLY
# The tongue must originate from a visible mouth cavity.
# Fangs sit on the mouth corners, not directly under the eyes.
# ------------------------------------------------------------
mouth_cavity = rounded_box(
    "MOUTH_CAVITY",
    (0.0, FRONT_Y-0.105, 1.99),
    (1.08, 0.10, 0.25),
    0.085, mat_black, "MOUTH"
)

# fangs at the outer corners of the mouth opening
cone_part(
    "FANG.L", (-0.55, FRONT_Y-0.145, 1.98), 0.095, 0.28,
    mat_fang, "FANG.L", rotation=(math.radians(180),0,0)
)
cone_part(
    "FANG.R", (0.55, FRONT_Y-0.145, 1.98), 0.095, 0.28,
    mat_fang, "FANG.R", rotation=(math.radians(180),0,0)
)

# tongue is a vertical rounded capsule whose TOP is hidden inside the mouth.
tongue = rounded_box(
    "TONGUE",
    (0.0, FRONT_Y-0.175, 1.67),
    (0.46, 0.16, 0.78),
    0.17, mat_tongue, "TONGUE"
)

# central tongue groove
curve_from_points(
    "TONGUE_GROOVE",
    [(0.0,FRONT_Y-0.270,1.96),(0.0,FRONT_Y-0.270,1.48)],
    mat_groove, 0.016, "TONGUE_DETAIL"
)

# ============================================================
# D. BELLY TARGET - CONCENTRIC RINGS, CLOSE TO SURFACE
# ============================================================
for i, radius in enumerate((0.14,0.27,0.40,0.53,0.66), 1):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=0.035,
        location=(0.0, FRONT_Y-0.105, 1.11),
        rotation=(math.radians(90),0,0),
        major_segments=64,
        minor_segments=16
    )
    ring = bpy.context.object
    ring.name = f"BELLY_RING.{i}"
    ring.data.materials.append(mat_black)
    mark_region(ring, "BELLY_TARGET")
# central black disc
cylinder_part(
    "BELLY_CENTER", (0.0, FRONT_Y-0.115, 1.11),
    0.10, 0.045, mat_black, "BELLY_TARGET",
    rotation=(math.radians(90),0,0)
)

# ============================================================
# E. TIGER STRIPES - JAGGED WEDGES, NOT RECTANGULAR BARS
# ============================================================
front_y = FRONT_Y - 0.12

front_stripes = [
    ("STRIPE.FL.TOP", [(-1.02,3.38),(-0.64,3.34),(-0.88,3.19),(-0.52,3.12),(-1.02,3.06)]),
    ("STRIPE.FR.TOP", [(1.02,3.38),(0.64,3.34),(0.88,3.19),(0.52,3.12),(1.02,3.06)]),
    ("STRIPE.FL.MID", [(-1.04,2.62),(-0.68,2.58),(-0.88,2.43),(-0.56,2.36),(-1.04,2.28)]),
    ("STRIPE.FR.MID", [(1.04,2.62),(0.68,2.58),(0.88,2.43),(0.56,2.36),(1.04,2.28)]),
    ("STRIPE.FL.LOW", [(-1.02,1.62),(-0.70,1.58),(-0.90,1.43),(-0.60,1.36),(-1.02,1.28)]),
    ("STRIPE.FR.LOW", [(1.02,1.62),(0.70,1.58),(0.90,1.43),(0.60,1.36),(1.02,1.28)]),
]
for name, coords in front_stripes:
    flat_poly(name, coords, front_y, mat_black, "STRIPE_FRONT", body)

# side stripes on left/right surfaces
side_pattern = [
    ((-0.52,3.12),(-0.18,3.08),(-0.40,2.92),(0.02,2.85),(-0.54,2.79)),
    ((-0.50,2.44),(-0.12,2.40),(-0.36,2.23),(0.04,2.16),(-0.52,2.10)),
    ((-0.48,1.48),(-0.10,1.45),(-0.34,1.30),(0.06,1.22),(-0.50,1.16)),
]
for side, x in (("L",-1.105),("R",1.105)):
    for idx, coords in enumerate(side_pattern,1):
        # mirror Y for the other side only to vary direction subtly
        yz = list(coords)
        side_poly(f"STRIPE.{side}.{idx}", yz, x, mat_black, "STRIPE_SIDE", body)

# back stripes: four jagged marks
back_y = (BODY_D/2.0) + 0.065
back_stripes = [
    ("STRIPE.BACK.L1",[(-1.00,2.72),(-0.64,2.67),(-0.86,2.52),(-0.48,2.46),(-1.00,2.38)]),
    ("STRIPE.BACK.R1",[(1.00,2.72),(0.64,2.67),(0.86,2.52),(0.48,2.46),(1.00,2.38)]),
    ("STRIPE.BACK.L2",[(-0.98,1.48),(-0.62,1.44),(-0.84,1.28),(-0.46,1.22),(-0.98,1.14)]),
    ("STRIPE.BACK.R2",[(0.98,1.48),(0.62,1.44),(0.84,1.28),(0.46,1.22),(0.98,1.14)]),
]
for name, coords in back_stripes:
    flat_poly(name, coords, back_y, mat_black, "STRIPE_BACK", body)

# ============================================================
# F. CLUB - LEFT SIDE, HELD VERTICALLY
# ============================================================
# handle
club_x = -1.50
cylinder_part(
    "CLUB.HANDLE", (club_x,-0.05,1.48),
    0.065, 1.80, mat_red, "CLUB"
)
# bottom knob
uv_part(
    "CLUB.KNOB", (club_x,-0.05,0.56),
    (0.14,0.14,0.11), mat_red, "CLUB"
)
# head
club_head = uv_part(
    "CLUB.HEAD", (club_x,-0.05,2.48),
    (0.31,0.28,0.55), mat_red, "CLUB"
)
# yellow studs on front of club
for idx,(dx,dz) in enumerate(((0.0,0.22),(0.0,-0.17)),1):
    uv_part(
        f"CLUB.STUD.{idx}",
        (club_x, -0.34, 2.48+dz),
        (0.085,0.055,0.085), mat_spike, "CLUB_DETAIL"
    )
# side spikes
cone_part(
    "CLUB.SPIKE.L", (club_x-0.34,-0.05,2.53),
    0.08,0.24,mat_spike,"CLUB_DETAIL",
    rotation=(0,math.radians(-90),0)
)
cone_part(
    "CLUB.SPIKE.R", (club_x+0.34,-0.05,2.53),
    0.08,0.24,mat_spike,"CLUB_DETAIL",
    rotation=(0,math.radians(90),0)
)
cone_part(
    "CLUB.SPIKE.TOP", (club_x,-0.05,3.05),
    0.08,0.24,mat_spike,"CLUB_DETAIL"
)

# ------------------------------------------------------------
# CLUB GRIP
# The handle passes through the character's RIGHT hand.
# Palm + fingers overlap the red handle so the weapon reads as HELD,
# not pasted beside the character.
# ------------------------------------------------------------
uv_part(
    "CLUB.THUMB", (-1.39,-0.19,1.56),
    (0.13,0.11,0.16), mat_yellow, "HAND.CLUB"
)
for idx, z in enumerate((1.56, 1.43, 1.30), start=1):
    uv_part(
        f"CLUB.FINGER.{idx}",
        (-1.51,-0.18,z),
        (0.14,0.10,0.075),
        mat_yellow, "HAND.CLUB"
    )

# ============================================================
# G. SMALL LEG MARK
# ============================================================
# Simple S proxy on character's right leg (viewer left/right depends on view).
bpy.ops.object.text_add(
    location=(0.66, FRONT_Y-0.10, 0.40),
    rotation=(math.radians(90),0,0)
)
leg_mark = bpy.context.object
leg_mark.name = "LEG_MARK"
leg_mark.data.body = "S"
leg_mark.data.align_x = 'CENTER'
leg_mark.data.align_y = 'CENTER'
leg_mark.data.size = 0.25
leg_mark.data.extrude = 0.006
leg_mark.data.materials.append(mat_black)
mark_region(leg_mark,"LEG_DETAIL")

# ============================================================
# LIGHTING / CAMERA
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

add_area("KEY", (-4.5,-5.5,7.5), 780, 5.0)
add_area("FILL", (4.5,-3.0,4.0), 430, 4.0)
add_area("RIM", (0.0,4.5,6.5), 620, 4.0)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.97,0.97,0.97,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.42

bpy.ops.object.camera_add(location=(0,-8,2.1))
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
    "front": ((0,-8.0,2.15),(0,0,2.0)),
    "three_q_l": ((-6.3,-6.3,2.45),(0,0,2.0)),
    "left": ((-8.0,0,2.15),(0,0,2.0)),
    "back": ((0,8.0,2.15),(0,0,2.0)),
    "right": ((8.0,0,2.15),(0,0,2.0)),
    "three_q_r": ((6.3,-6.3,2.45),(0,0,2.0)),
    "top": ((0,0,10.0),(0,0,1.8)),
    "bottom": ((0,0,-7.0),(0,0,1.5)),
}

spec = {
    "character":"ARYA",
    "version":"TSA_CHARACTER_004_V4_SKIN_CONFORM_FIX",
    "source_strategy":"V3 form preserved; tiger-stripe ornaments converted from floating plates to body-conforming skin decals",
    "coordinate_system":{"front_axis":"-Y","up_axis":"+Z","symmetry_plane":"X=0"},
    "locked_rangga_base":{
        "BODY_W":BODY_W,
        "BODY_D":BODY_D,
        "BODY_H":BODY_H,
        "BODY_Z":BODY_Z,
        "lower_volume":[1.05,0.63,0.78],
        "arm_scale":[0.34,0.42,0.82],
        "leg_dimensions":[0.58,0.74,0.90]
    },
    "arya_features":{
        "single_center_horn":True,
        "horn_black_flush_bands":True,
        "three_eyes":True,
        "mouth_corner_fangs":True,
        "visible_mouth_cavity":True,
        "tongue_originates_inside_mouth":True,
        "organic_tongue":True,
        "concentric_belly_target":True,
        "jagged_tiger_stripes":True,
        "character_right_hand_club_grip":True,
        "back_nub":True
    },
    "skin_markings":"shrinkwrapped body-conforming decals",
    "tsa_gate":"STATIC_MODEL_FORM_LOCK"
}

with open(OUT_DIR/"arya_spec_v4.json","w",encoding="utf-8") as f:
    json.dump(spec,f,indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR/"arya_v4.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR/"arya_v4.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name,(loc,target) in views.items():
    point_camera(cam,loc,target)
    scene.render.filepath = str(OUT_DIR/f"arya_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*68)
print("ARYA TSA CHARACTER 004 - V4 SKIN CONFORM FIX COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Gate: STATIC MODEL / FORM LOCK")
print("="*68)
