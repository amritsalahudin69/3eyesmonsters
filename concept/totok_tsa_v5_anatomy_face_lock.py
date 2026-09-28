# TOTOK - TSA Character Reconstruction V5
# Blender 5.2 LTS
# Goal: preserve Totok V4 silhouette while adding the locked TSA face-depth + anatomy standard.
# Gate: FORM LOCK + FACE DEPTH LOCK + ANATOMY LOCK + SURFACE INTEGRATION LOCK
#
# LOCKS:
# - Keep V4 Totok primary proportions: head, tapered body, pointed bottom, roof, halo, tongue, tail.
# - Eyes must sit inside real recessed sockets, not float as sticker-like spheres.
# - Arms must contain shoulder -> upper arm -> elbow -> forearm -> wrist -> palm -> digits.
# - Legs must exist for future walking: thigh -> knee -> calf -> ankle -> foot.
#   They stay compact and tucked under the body so Totok still reads as Totok.
# - Bottom pointed tip remains as Totok's cosmetic silhouette feature.
# - No rig/animation in this gate.

import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path.home() / "totok_output_v5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_RES = 1024
ORTHO_SCALE = 5.45
FRONT_AXIS = "-Y"
UP_AXIS = "+Z"

# -----------------------------------------------------------------------------
# LOCKED V4 BASELINE
# -----------------------------------------------------------------------------
SPEC = {
    "character": "TOTOK",
    "version": "TSA_CHARACTER_002_V5_ANATOMY_FACE_LOCK",
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
        "white_scale": [0.255, 0.120, 0.255],
        "pupil_scale": [0.105, 0.048, 0.105],
        "centers": {
            "EYE.TOP": [0.00, -0.735, 2.98],
            "EYE.LEFT": [-0.41, -0.748, 2.61],
            "EYE.RIGHT": [0.41, -0.748, 2.61]
        },
        "socket_scale": [0.295, 0.185, 0.295],
        "pupil_front_offset": -0.128,
        "pupil_z_offset": -0.012
    },
    "mouth": {
        "center_z": 2.285,
        "half_width": 0.43,
        "front_y": -0.746
    },
    "tongue": {
        "center": [0.00, -0.805, 1.625],
        "dimensions": [0.48, 0.15, 1.24],
        "bevel": 0.068
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
# HELPERS
# -----------------------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for dbs in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(dbs):
            if getattr(block, "users", 0) == 0:
                dbs.remove(block)

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

def apply_modifier(obj, mod_name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod_name)
    obj.select_set(False)

def apply_bevel(obj, width=0.12, segments=6):
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
        segments=segments, ring_count=rings, location=location, rotation=rotation
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
        vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj, region)

def curve_from_points(name, pts, material, bevel_depth, region, cyclic=False, bezier=True):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 16
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
    return mark_region(obj, region)

def boolean_difference(base_obj, cutter_obj):
    mod = base_obj.modifiers.new(name=f"BOOL_{cutter_obj.name}", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter_obj
    apply_modifier(base_obj, mod.name)
    bpy.data.objects.remove(cutter_obj, do_unlink=True)

def make_tapered_body(name, sections, material, region, samples=64, exponent=4.15):
    verts = []
    faces = []
    for z, width, depth in sections:
        a = width/2.0
        b = depth/2.0
        for i in range(samples):
            t = math.tau*i/samples
            c, s = math.cos(t), math.sin(t)
            x = a * math.copysign(abs(c)**(2.0/exponent), c)
            y = b * math.copysign(abs(s)**(2.0/exponent), s)
            verts.append((x,y,z))

    ring_count = len(sections)
    for r in range(ring_count-1):
        a0 = r*samples
        a1 = (r+1)*samples
        for i in range(samples):
            j = (i+1)%samples
            faces.append((a0+i, a0+j, a1+j, a1+i))

    bottom_idx = len(verts)
    verts.append((0,0,sections[-1][0]))
    top_idx = len(verts)
    verts.append((0,0,sections[0][0]))
    last = (ring_count-1)*samples

    for i in range(samples):
        j = (i+1)%samples
        faces.append((bottom_idx,last+j,last+i))
        faces.append((top_idx,i,j))

    mesh = bpy.data.meshes.new(name+"_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    smooth_object(obj)

    sub = obj.modifiers.new("TSA_Subdivision","SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    apply_modifier(obj, sub.name)
    return mark_region(obj, region)

def make_downward_tip(name, center, top_radius, bottom_radius, depth, material, region):
    bpy.ops.mesh.primitive_cone_add(
        vertices=64,
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
        (-hw,-hd,bz),(hw,-hd,bz),(hw,hd,bz),(-hw,hd,bz),(0,0,az)
    ]
    faces = [(0,1,2,3),(0,4,1),(1,4,2),(2,4,3),(3,4,0)]
    mesh = bpy.data.meshes.new(name+"_Mesh")
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
        major_segments=80,
        minor_segments=24,
        location=h["center"],
        rotation=(math.radians(h["tilt_x_deg"]),0,0)
    )
    obj = bpy.context.object
    obj.name = "HALO"
    smooth_object(obj)
    obj.data.materials.append(material)
    return mark_region(obj,"HALO")

def capsule_between(name, a, b, radius, material, region):
    a = Vector(a)
    b = Vector(b)
    v = b-a
    mid = (a+b)*0.5
    obj = cyl_part(name, tuple(mid), radius, v.length, material, region)
    obj.rotation_euler = v.to_track_quat('Z','Y').to_euler()
    uv_part(name+"_A_CAP", tuple(a), (radius,radius,radius), material, region)
    uv_part(name+"_B_CAP", tuple(b), (radius,radius,radius), material, region)
    return obj

def build_hand(name, side, wrist, material):
    x,y,z = wrist
    palm = uv_part(
        name+"_PALM",
        (x, y-0.015, z-0.22),
        (0.17,0.16,0.21),
        material,
        "HAND"
    )
    # thumb
    uv_part(
        name+"_THUMB",
        (x + side*0.14, y-0.02, z-0.20),
        (0.07,0.09,0.10),
        material,
        "THUMB"
    )
    # three tiny digits, downward-oriented
    for i, dx in enumerate([-0.075,0.0,0.075]):
        uv_part(
            f"{name}_DIGIT_{i}",
            (x + dx, y-0.03, z-0.39),
            (0.055,0.075,0.105),
            material,
            "FINGER"
        )
    return palm

def build_foot(name, side, material):
    # compact but real leg chain; largely tucked beneath the robe/body.
    hip = (side*0.42, 0.03, 0.64)
    knee = (side*0.43, 0.00, 0.42)
    ankle = (side*0.43,-0.03,0.22)

    capsule_between(name+"_THIGH", hip, knee, 0.15, material, "THIGH")
    uv_part(name+"_KNEE", knee, (0.15,0.16,0.14), material, "KNEE")
    capsule_between(name+"_CALF", knee, ankle, 0.125, material, "CALF")
    uv_part(name+"_ANKLE", ankle, (0.11,0.12,0.095), material, "ANKLE")

    foot = uv_part(
        name+"_FOOT",
        (side*0.43,-0.16,0.10),
        (0.22,0.30,0.13),
        material,
        "FOOT"
    )
    # toe points forward (-Y)
    uv_part(
        name+"_TOE",
        (side*0.43,-0.29,0.09),
        (0.19,0.15,0.10),
        material,
        "TOE"
    )
    return foot

# -----------------------------------------------------------------------------
# BUILD
# -----------------------------------------------------------------------------
clean_scene()

BODY = make_mat("TOTOK_BODY", (0.80,0.765,0.69,1.0), roughness=0.38)
ROOF = make_mat("TOTOK_ROOF", (0.84,0.81,0.75,1.0), roughness=0.42)
HALO = make_mat("TOTOK_HALO", (1.00,0.72,0.06,1.0), roughness=0.24)
EYE = make_mat("TOTOK_EYE_WHITE", (0.985,0.985,0.985,1.0), roughness=0.19)
PUPIL = make_mat("TOTOK_PUPIL", (0.13,0.07,0.08,1.0), roughness=0.23)
SOCKET = make_mat("TOTOK_SOCKET", (0.66,0.62,0.56,1.0), roughness=0.48)
MOUTH = make_mat("TOTOK_MOUTH", (0.12,0.07,0.065,1.0), roughness=0.38)
TONGUE = make_mat("TOTOK_TONGUE", (0.90,0.10,0.10,1.0), roughness=0.31)

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

# -----------------------------------------------------------------------------
# FACE DEPTH LOCK
# -----------------------------------------------------------------------------
for eye_name, center in SPEC["eyes"]["centers"].items():
    ex, ey, ez = center
    sx, sy, sz = SPEC["eyes"]["socket_scale"]

    # Actual head recess.
    cutter = uv_part(
        eye_name+"_SOCKET_CUTTER",
        (ex, ey+0.015, ez),
        (sx,sy,sz),
        SOCKET,
        "CUTTER"
    )
    boolean_difference(head, cutter)

    # Socket back wall / bowl.
    uv_part(
        eye_name+"_SOCKET",
        (ex, ey+0.075, ez),
        (sx*0.92,0.075,sz*0.92),
        SOCKET,
        "EYE_SOCKET"
    )

    # White eye is partially embedded in the socket.
    uv_part(
        eye_name+"_WHITE",
        (ex, ey-0.014, ez),
        tuple(SPEC["eyes"]["white_scale"]),
        EYE,
        eye_name
    )

    pupil_center = (
        ex,
        ey + SPEC["eyes"]["pupil_front_offset"],
        ez + SPEC["eyes"]["pupil_z_offset"]
    )
    uv_part(
        eye_name+"_PUPIL",
        pupil_center,
        tuple(SPEC["eyes"]["pupil_scale"]),
        PUPIL,
        eye_name+"_PUPIL"
    )

# mouth slit
mouth_pts = []
for i in range(40):
    t = i/39.0
    x = -SPEC["mouth"]["half_width"] + 2.0*SPEC["mouth"]["half_width"]*t
    z = SPEC["mouth"]["center_z"] - 0.035*(1.0 - ((t-0.5)/0.5)**2)
    mouth_pts.append((x,SPEC["mouth"]["front_y"],z))
curve_from_points("MOUTH", mouth_pts, MOUTH, 0.020, "MOUTH")

# tongue remains Totok's signature long flat tongue, tucked under the mouth
tongue = rounded_box(
    "TONGUE",
    tuple(SPEC["tongue"]["center"]),
    tuple(SPEC["tongue"]["dimensions"]),
    SPEC["tongue"]["bevel"],
    TONGUE,
    "TONGUE"
)

# -----------------------------------------------------------------------------
# ARMS - TSA ANATOMY LOCK
# -----------------------------------------------------------------------------
def build_arm(side):
    tag = "L" if side < 0 else "R"
    shoulder = (side*0.91, 0.00, 1.82)
    elbow    = (side*1.04,-0.005,1.48)
    wrist    = (side*1.00,-0.015,1.19)

    uv_part(f"SHOULDER_{tag}", shoulder, (0.22,0.26,0.24), BODY, f"SHOULDER.{tag}")
    capsule_between(f"UPPER_ARM_{tag}", shoulder, elbow, 0.17, BODY, f"UPPER_ARM.{tag}")
    uv_part(f"ELBOW_{tag}", elbow, (0.175,0.19,0.17), BODY, f"ELBOW.{tag}")
    capsule_between(f"FOREARM_{tag}", elbow, wrist, 0.145, BODY, f"FOREARM.{tag}")
    uv_part(f"WRIST_{tag}", wrist, (0.12,0.13,0.11), BODY, f"WRIST.{tag}")
    build_hand(f"HAND_{tag}", side, wrist, BODY)

build_arm(-1)
build_arm(1)

# -----------------------------------------------------------------------------
# LEGS - TSA ANATOMY LOCK
# -----------------------------------------------------------------------------
build_foot("LEG_L", -1, BODY)
build_foot("LEG_R", 1, BODY)

# -----------------------------------------------------------------------------
# TAIL
# -----------------------------------------------------------------------------
tail_pts = [tuple(p) for p in SPEC["tail"]["points"]]
curve_from_points(
    "TAIL",
    tail_pts,
    BODY,
    SPEC["tail"]["bevel"],
    "TAIL",
    bezier=True
)
uv_part(
    "TAIL_TIP",
    tail_pts[-1],
    (SPEC["tail"]["tip_radius"],)*3,
    BODY,
    "TAIL_TIP"
)

# -----------------------------------------------------------------------------
# LIGHTING / CAMERA
# -----------------------------------------------------------------------------
def add_area(name, loc, energy, size, color=(1,1,1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.data.color = color
    return light

def point_camera(camera, location, target=(0,0,2.32)):
    camera.location = location
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()

add_area("KEY", (-4.5,-5.5,7.5), 1050, 5.0)
add_area("FILL", (4.5,-3.0,4.0), 650, 4.0)
add_area("RIM", (0.0,4.5,6.5), 900, 4.0)

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.97,0.97,0.97,1.0)
    bg.inputs["Strength"].default_value = 0.85

bpy.ops.object.camera_add(location=(0,-8,2.45))
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
    "front": ((0,-8.0,2.38),(0,0,2.32)),
    "three_q_l": ((-6.3,-6.3,2.58),(0,0,2.32)),
    "left": ((-8.0,0.0,2.38),(0,0,2.32)),
    "back": ((0,8.0,2.38),(0,0,2.32)),
    "right": ((8.0,0.0,2.38),(0,0,2.32)),
    "three_q_r": ((6.3,-6.3,2.58),(0,0,2.32)),
    "top": ((0,0,10.0),(0,0,2.30)),
    "bottom": ((0,0,-7.0),(0,0,1.85))
}

# -----------------------------------------------------------------------------
# SPEC / TSA LOCK
# -----------------------------------------------------------------------------
SPEC["tsa_locks"] = {
    "preserve_v4_primary_form": True,
    "eye_depth_rule": "Three eyes are seated inside real head recesses with socket depth; no sticker/floating-eye treatment.",
    "arm_anatomy_rule": "Each arm has shoulder, upper arm, elbow, forearm, wrist, palm and simplified digits.",
    "leg_anatomy_rule": "Each leg has thigh, knee, calf, ankle, foot and toe direction, even though Totok keeps compact hidden/tucked proportions.",
    "bottom_tip_rule": "The central pointed lower tip remains as Totok's cosmetic silhouette feature and is separate from the two anatomical legs.",
    "rig_gate": "No rig or animation until all-angle form and anatomy are approved."
}
SPEC["tsa_gate"] = "FORM_LOCK / FACE_DEPTH_LOCK / ANATOMY_LOCK / SURFACE_INTEGRATION_LOCK"

with open(OUT_DIR / "totok_spec_v5.json","w",encoding="utf-8") as f:
    json.dump(SPEC,f,indent=2)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "totok_v5.blend"))

bpy.ops.export_scene.gltf(
    filepath=str(OUT_DIR / "totok_v5.glb"),
    export_format='GLB',
    export_apply=True,
    export_animations=False
)

for view_name,(loc,target) in views.items():
    point_camera(cam,loc,target)
    scene.render.filepath = str(OUT_DIR / f"totok_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print("="*72)
print("TOTOK TSA CHARACTER 002 - V5 ANATOMY + FACE LOCK COMPLETE")
print(f"OUTPUT: {OUT_DIR}")
print("Preserved: V4 head/body/tip/roof/halo/tongue/tail")
print("Added: recessed eye sockets + full compact arm/leg anatomy")
print("Gate: FORM + FACE DEPTH + ANATOMY + SURFACE INTEGRATION")
print("="*72)
