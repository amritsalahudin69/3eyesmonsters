import bpy
import hashlib
import json
import math
import os
import statistics
import struct
import sys
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = r"C:\Users\HWI-ADMIN\Downloads\3d"
ITERATION = os.path.join(ROOT, "tsa", "alif", "restart", "iteration04")
SOURCE = os.path.join(ROOT, "tsa", "alif", "restart", "iteration03B", "alif_deform_v1.blend")
WORKING = os.path.join(ITERATION, "alif_poseproof_v1.blend")
REFERENCE = os.path.join(ROOT, "tsa", "alif", "iteration01", "validation")
VALIDATION = os.path.join(ITERATION, "validation")
LOGS = os.path.join(ITERATION, "logs")
POSES = os.path.join(ITERATION, "poses")
VIEWS = {
    "front": ((0, -8.2, 2.10), (0, 0, 2.0)),
    "three_q_l": ((-6.4, -6.4, 2.35), (0, 0, 2.0)),
    "left": ((-8.2, 0, 2.1), (0, 0, 2.0)),
    "back": ((0, 8.2, 2.1), (0, 0, 2.0)),
    "right": ((8.2, 0, 2.1), (0, 0, 2.0)),
    "three_q_r": ((6.4, -6.4, 2.35), (0, 0, 2.0)),
}
POSE_NAMES = [
    "REST", "READY", "STEP_LEFT", "STEP_RIGHT", "LEAN_LEFT", "LEAN_RIGHT",
    "POINT_LEFT", "POINT_RIGHT", "TURN_LEFT", "TURN_RIGHT", "CROUCH",
    "JUMP_ANTICIPATION", "JUMP_TAKEOFF", "JUMP_APEX", "FALL", "LANDING",
]
LIMBS = ("ARM_L", "ARM_R", "LEG_L_SUIT", "LEG_R_SUIT")
GATE_P01 = 0.25
GATE_P99 = 2.0


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as output:
        json.dump(data, output, indent=2, allow_nan=False)


def percent(values, percentile):
    values = sorted(values)
    at = (len(values) - 1) * percentile
    lower = int(at)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] * (upper - at) + values[upper] * (at - lower)


def world_vertices(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def edge_metric(obj, neutral_lengths):
    points = world_vertices(obj)
    lengths = [
        (points[edge.vertices[0]] - points[edge.vertices[1]]).length
        for edge in obj.data.edges
    ]
    ratios = [
        length / base if base > 1e-12 else 1.0
        for length, base in zip(lengths, neutral_lengths)
    ]
    return {
        "p01": percent(ratios, 0.01),
        "median": statistics.median(ratios),
        "p99": percent(ratios, 0.99),
        "minimum": min(ratios),
        "maximum": max(ratios),
        "non_finite": sum(not math.isfinite(value) for point in points for value in point),
    }


def reset_pose(rig):
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def set_joint(rig, bone_name, axis, degrees):
    reset_pose(rig)
    rig.pose.bones[bone_name].rotation_euler[axis] = math.radians(degrees)
    bpy.context.view_layer.update()


def centroid(obj):
    return sum(world_vertices(obj), Vector()) / len(world_vertices(obj))


def min_surface_distance(left, right):
    left_points = world_vertices(left)
    right_points = world_vertices(right)
    tree = KDTree(len(right_points))
    for index, point in enumerate(right_points):
        tree.insert(point, index)
    tree.balance()
    return min(tree.find(point)[2] for point in left_points)


def place_camera(view_name):
    camera = bpy.data.objects.get("TSA_CAMERA")
    if view_name == "game":
        location, target = ((6.0, 12.5, 6.2), (0.0, 0.0, 1.65))
    else:
        location, target = VIEWS[view_name]
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera


def render(path, view_name):
    place_camera(view_name)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def compare_images(actual_path, reference_path):
    actual = bpy.data.images.load(actual_path, check_existing=False)
    expected = bpy.data.images.load(reference_path, check_existing=False)
    try:
        if tuple(actual.size) != tuple(expected.size):
            return {"pass": False, "reason": "dimensions", "actual": list(actual.size), "reference": list(expected.size)}
        differences = [abs(a - b) for a, b in zip(actual.pixels, expected.pixels)]
        mean = sum(differences) / len(differences)
        maximum = max(differences)
        return {
            "pass": mean <= 0.0005 and maximum <= 0.06,
            "mean_absolute_pixel_difference": mean,
            "maximum_pixel_difference": maximum,
        }
    finally:
        bpy.data.images.remove(actual)
        bpy.data.images.remove(expected)


def snapshot():
    result = {"objects": {}, "bones": {}}
    for obj in bpy.data.objects:
        if obj.type not in {"MESH", "CURVE", "ARMATURE"}:
            continue
        result["objects"][obj.name] = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "matrix_world": [float(value) for row in obj.matrix_world for value in row],
            "vertices": len(obj.data.vertices) if obj.type == "MESH" else None,
            "edges": len(obj.data.edges) if obj.type == "MESH" else None,
            "polygons": len(obj.data.polygons) if obj.type == "MESH" else None,
            "groups": sorted(group.name for group in obj.vertex_groups),
            "modifiers": [(modifier.name, modifier.type) for modifier in obj.modifiers],
        }
        if obj.type == "MESH":
            digest = hashlib.sha256()
            for vertex in obj.data.vertices:
                digest.update(struct.pack("<3f", *vertex.co))
                memberships = sorted(vertex.groups, key=lambda item: item.group)
                digest.update(struct.pack("<I", len(memberships)))
                for membership in memberships:
                    digest.update(struct.pack("<If", membership.group, membership.weight))
            for edge in obj.data.edges:
                digest.update(struct.pack("<2I", *edge.vertices))
            for polygon in obj.data.polygons:
                digest.update(struct.pack("<I", len(polygon.vertices)))
                for index in polygon.vertices:
                    digest.update(struct.pack("<I", index))
            result["objects"][obj.name]["mesh_data_sha256"] = digest.hexdigest()
    for bone in bpy.data.objects["ALIF_RIG"].data.bones:
        result["bones"][bone.name] = {
            "parent": bone.parent.name if bone.parent else None,
            "matrix_local": [float(value) for row in bone.matrix_local for value in row],
            "use_deform": bone.use_deform,
            "use_connect": bone.use_connect,
        }
    return result


def gate_result(metric):
    return metric["non_finite"] == 0 and metric["p01"] >= GATE_P01 and metric["p99"] <= GATE_P99


def explore_direction(rig, bone_name, axis, sign, max_degrees, object_name, limb_name, label):
    side = bone_name[-1] if bone_name.endswith((".L", ".R")) else "L"
    neutral_center = centroid(bpy.data.objects[object_name])
    neutral_metric = edge_metric(bpy.data.objects[limb_name], BASE_EDGES[limb_name]) if limb_name else None
    records = []
    last_safe = 0
    for degrees in range(5, max_degrees + 1, 5):
        set_joint(rig, bone_name, axis, sign * degrees)
        metric = edge_metric(bpy.data.objects[limb_name], BASE_EDGES[limb_name]) if limb_name else None
        center = centroid(bpy.data.objects[object_name])
        record = {
            "angle_degrees": sign * degrees,
            "distal_center_delta": [float(value) for value in center - neutral_center],
        }
        if metric:
            record["deformation"] = metric
            record["metric_gate"] = gate_result(metric)
        if label in {"upper_arm", "thigh"}:
            gap_key = f"{label}_{side}_root"
            gap = min_surface_distance(bpy.data.objects[limb_name], bpy.data.objects["TORSO_UNDER"])
            record["root_gap"] = gap
            record["contact_gate"] = gap <= NEUTRAL_GAPS[gap_key] + (0.12 if label == "upper_arm" else 0.10)
        elif label in {"forearm", "wrist"}:
            gap_key = f"{label}_{side}_distal"
            gap = min_surface_distance(
                bpy.data.objects[limb_name], bpy.data.objects[f"HAND_{side}"]
            )
            record["distal_gap"] = gap
            record["contact_gate"] = gap <= NEUTRAL_GAPS[gap_key] + 0.12
        elif label in {"shin", "foot"}:
            gap_key = f"{label}_{side}_distal"
            gap = min_surface_distance(
                bpy.data.objects[limb_name], bpy.data.objects[f"FOOT_{side}"]
            )
            record["distal_gap"] = gap
            record["contact_gate"] = gap <= NEUTRAL_GAPS[gap_key] + 0.10
        if metric:
            record["safe_gate"] = gate_result(metric) and record.get("contact_gate", True)
        else:
            record["safe_gate"] = record.get("contact_gate", True)
        records.append(record)
        if not record["safe_gate"]:
            break
        last_safe = degrees
    reset_pose(rig)
    return {
        "bone": bone_name,
        "axis": axis,
        "sign": sign,
        "direction_label": label,
        "metric_safe_candidate_degrees": last_safe,
        "records_5_degree_steps": records,
    }


def scan_envelope(rig):
    global BASE_EDGES, NEUTRAL_GAPS
    BASE_EDGES = {
        name: [
            (point_a - point_b).length
            for point_a, point_b in (
                (obj.matrix_world @ obj.data.vertices[edge.vertices[0]].co,
                 obj.matrix_world @ obj.data.vertices[edge.vertices[1]].co)
                for edge in obj.data.edges
            )
        ]
        for name in LIMBS
        for obj in [bpy.data.objects[name]]
    }
    NEUTRAL_GAPS = {}
    for side in ("L", "R"):
        NEUTRAL_GAPS[f"upper_arm_{side}_root"] = min_surface_distance(
            bpy.data.objects[f"ARM_{side}"], bpy.data.objects["TORSO_UNDER"]
        )
        NEUTRAL_GAPS[f"thigh_{side}_root"] = min_surface_distance(
            bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects["TORSO_UNDER"]
        )
        NEUTRAL_GAPS[f"forearm_{side}_distal"] = min_surface_distance(
            bpy.data.objects[f"ARM_{side}"], bpy.data.objects[f"HAND_{side}"]
        )
        NEUTRAL_GAPS[f"wrist_{side}_distal"] = NEUTRAL_GAPS[f"forearm_{side}_distal"]
        NEUTRAL_GAPS[f"shin_{side}_distal"] = min_surface_distance(
            bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects[f"FOOT_{side}"]
        )
        NEUTRAL_GAPS[f"foot_{side}_distal"] = NEUTRAL_GAPS[f"shin_{side}_distal"]
    write_json(os.path.join(LOGS, "neutral_attachment_gaps.json"), NEUTRAL_GAPS)
    scan = {}
    for side in ("L", "R"):
        upper = f"UPPER_ARM.{side}"
        forearm = f"FOREARM.{side}"
        wrist = f"WRIST.{side}"
        thigh = f"THIGH.{side}"
        shin = f"SHIN.{side}"
        foot = f"FOOT.{side}"
        scan[f"UPPER_ARM_{side}_forward_back"] = [
            explore_direction(rig, upper, 0, sign, 60, f"HAND_{side}", f"ARM_{side}", "upper_arm")
            for sign in (-1, 1)
        ]
        scan[f"UPPER_ARM_{side}_outward_inward"] = [
            explore_direction(rig, upper, 2, sign, 60, f"HAND_{side}", f"ARM_{side}", "upper_arm")
            for sign in (-1, 1)
        ]
        scan[f"FOREARM_{side}_flexion"] = [
            explore_direction(rig, forearm, 0, sign, 90, f"HAND_{side}", f"ARM_{side}", "forearm")
            for sign in (-1, 1)
        ]
        scan[f"WRIST_{side}_rotation"] = [
            explore_direction(rig, wrist, 0, sign, 45, f"HAND_{side}", f"ARM_{side}", "wrist")
            for sign in (-1, 1)
        ]
        scan[f"THIGH_{side}_forward_back"] = [
            explore_direction(rig, thigh, 0, sign, 45, f"FOOT_{side}", f"LEG_{side}_SUIT", "thigh")
            for sign in (-1, 1)
        ]
        scan[f"SHIN_{side}_flexion"] = [
            explore_direction(rig, shin, 0, sign, 45, f"FOOT_{side}", f"LEG_{side}_SUIT", "shin")
            for sign in (-1, 1)
        ]
        scan[f"FOOT_{side}_pitch"] = [
            explore_direction(rig, foot, 0, sign, 45, f"FOOT_{side}", f"LEG_{side}_SUIT", "foot")
            for sign in (-1, 1)
        ]
        scan[f"HEAD_{side}_yaw"] = [
            explore_direction(rig, "HEAD", 1, sign, 30, "HEAD", "ARM_L", "head")
            for sign in (-1, 1)
        ]
    return scan


def save_neutral_reference_renders(rig):
    reset_pose(rig)
    comparison = {}
    for view_name in VIEWS:
        filename = f"neutral_{view_name}.png"
        path = os.path.join(VALIDATION, filename)
        render(path, view_name)
        comparison[view_name] = compare_images(
            path, os.path.join(REFERENCE, f"alif_{view_name}.png")
        )
    return comparison


POSE_STATES = {
    "REST": {"rotations": {}, "locations": {}},
    "READY": {
        "rotations": {
            "UPPER_ARM.L": [0, 0, 15], "UPPER_ARM.R": [0, 0, -15],
            "FOREARM.L": [10, 0, 0], "FOREARM.R": [-10, 0, 0],
            "THIGH.L": [0, 0, 0], "THIGH.R": [0, 0, 0],
        },
        "locations": {},
    },
    "STEP_LEFT": {
        "rotations": {
            "UPPER_ARM.L": [20, 0, 0], "UPPER_ARM.R": [-20, 0, 0],
            "THIGH.L": [-20, 0, 0], "THIGH.R": [20, 0, 0],
            "SHIN.L": [5, 0, 0], "FOOT.L": [-5, 0, 0],
        },
        "locations": {},
    },
    "STEP_RIGHT": {
        "rotations": {
            "UPPER_ARM.L": [-20, 0, 0], "UPPER_ARM.R": [20, 0, 0],
            "THIGH.L": [20, 0, 0], "THIGH.R": [-20, 0, 0],
            "SHIN.R": [5, 0, 0], "FOOT.R": [-5, 0, 0],
        },
        "locations": {},
    },
    "LEAN_LEFT": {"rotations": {"COG": [0, 0, 8]}, "locations": {}},
    "LEAN_RIGHT": {"rotations": {"COG": [0, 0, -8]}, "locations": {}},
    "POINT_LEFT": {
        "rotations": {
            "UPPER_ARM.L": [0, 0, 40], "FOREARM.L": [20, 0, 0], "WRIST.L": [5, 0, 0],
            "UPPER_ARM.R": [0, 0, -8], "FOREARM.R": [-10, 0, 0],
        },
        "locations": {},
    },
    "POINT_RIGHT": {
        "rotations": {
            "UPPER_ARM.R": [0, 0, -40], "FOREARM.R": [-20, 0, 0], "WRIST.R": [-5, 0, 0],
            "UPPER_ARM.L": [0, 0, 8], "FOREARM.L": [10, 0, 0],
        },
        "locations": {},
    },
    "TURN_LEFT": {
        "rotations": {"ROOT": [0, -35, 0], "HEAD": [0, -10, 0]},
        "locations": {},
    },
    "TURN_RIGHT": {
        "rotations": {"ROOT": [0, 35, 0], "HEAD": [0, 10, 0]},
        "locations": {},
    },
    "CROUCH": {
        "rotations": {
            "THIGH.L": [-20, 0, 0], "THIGH.R": [-20, 0, 0],
            "SHIN.L": [10, 0, 0], "SHIN.R": [10, 0, 0],
            "FOOT.L": [-10, 0, 0], "FOOT.R": [-10, 0, 0],
        },
        "locations": {"COG": [0, -0.04, 0]},
    },
    "JUMP_ANTICIPATION": {
        "rotations": {
            "THIGH.L": [-20, 0, 0], "THIGH.R": [-20, 0, 0],
            "SHIN.L": [10, 0, 0], "SHIN.R": [10, 0, 0],
            "FOOT.L": [-10, 0, 0], "FOOT.R": [-10, 0, 0],
            "UPPER_ARM.L": [10, 0, 25], "UPPER_ARM.R": [-10, 0, -25],
            "FOREARM.L": [10, 0, 0], "FOREARM.R": [-10, 0, 0],
        },
        "locations": {"COG": [0, -0.04, 0]},
    },
    "JUMP_TAKEOFF": {
        "rotations": {
            "UPPER_ARM.L": [0, 0, 40], "UPPER_ARM.R": [0, 0, -40],
            "FOREARM.L": [0, 0, 10], "FOREARM.R": [0, 0, -10],
            "THIGH.L": [-3, 0, 0], "THIGH.R": [-3, 0, 0],
        },
        "locations": {"COG": [0, 0.05, 0]},
    },
    "JUMP_APEX": {
        "rotations": {
            "UPPER_ARM.L": [0, 0, 40], "UPPER_ARM.R": [0, 0, -40],
            "FOREARM.L": [15, 0, 0], "FOREARM.R": [-15, 0, 0],
            "THIGH.L": [-10, 0, 0], "THIGH.R": [10, 0, 0],
            "SHIN.L": [5, 0, 0], "SHIN.R": [5, 0, 0],
            "FOOT.L": [-10, 0, 0], "FOOT.R": [-10, 0, 0],
        },
        "locations": {"COG": [0, 0.22, 0]},
    },
    "FALL": {
        "rotations": {
            "COG": [0, 0, -5],
            "UPPER_ARM.L": [0, 0, 25], "UPPER_ARM.R": [0, 0, -25],
            "THIGH.L": [-5, 0, 0], "THIGH.R": [5, 0, 0],
            "SHIN.L": [5, 0, 0], "SHIN.R": [5, 0, 0],
        },
        "locations": {"COG": [0, 0.12, 0]},
    },
    "LANDING": {
        "rotations": {
            "THIGH.L": [-20, 0, 0], "THIGH.R": [-20, 0, 0],
            "SHIN.L": [10, 0, 0], "SHIN.R": [10, 0, 0],
            "FOOT.L": [-10, 0, 0], "FOOT.R": [-10, 0, 0],
            "UPPER_ARM.L": [0, 0, 20], "UPPER_ARM.R": [0, 0, -20],
        },
        "locations": {"COG": [0, -0.035, 0]},
    },
}


SAFE_LIMITS = {
    "HEAD": {"axis_1_abs": 30},
    "UPPER_ARM.L": {"axis_0_abs": 25, "axis_2_abs": 45},
    "UPPER_ARM.R": {"axis_0_abs": 25, "axis_2_abs": 45},
    "FOREARM.L": {"axis_0_abs": 45},
    "FOREARM.R": {"axis_0_abs": 45},
    "WRIST.L": {"axis_0_abs": 20},
    "WRIST.R": {"axis_0_abs": 20},
    "THIGH.L": {"axis_0_abs": 20},
    "THIGH.R": {"axis_0_abs": 20},
    "SHIN.L": {"axis_0_abs": 10},
    "SHIN.R": {"axis_0_abs": 10},
    "FOOT.L": {"axis_0_abs": 20},
    "FOOT.R": {"axis_0_abs": 20},
    "ROOT": {"axis_1_abs": 35},
    "COG": {"axis_2_abs": 8, "location_y_abs": 0.22},
}


def apply_state(rig, state):
    reset_pose(rig)
    for bone_name, degrees in state["rotations"].items():
        rig.pose.bones[bone_name].rotation_euler = [math.radians(value) for value in degrees]
    for bone_name, location in state["locations"].items():
        rig.pose.bones[bone_name].location = location
    bpy.context.view_layer.update()


def state_compliance(state):
    issues = []
    for bone_name, rotations in state["rotations"].items():
        limits = SAFE_LIMITS.get(bone_name, {})
        for axis, degrees in enumerate(rotations):
            limit = limits.get(f"axis_{axis}_abs")
            if limit is not None and abs(degrees) > limit + 1e-8:
                issues.append(f"{bone_name}.rotation[{axis}]={degrees} exceeds {limit}")
    for bone_name, location in state["locations"].items():
        limit = SAFE_LIMITS.get(bone_name, {}).get("location_y_abs")
        if limit is not None and abs(location[1]) > limit:
            issues.append(f"{bone_name}.location.y={location[1]} exceeds {limit}")
    return issues


def pose_metrics():
    result = {}
    for side in ("L", "R"):
        arm = edge_metric(bpy.data.objects[f"ARM_{side}"], BASE_EDGES[f"ARM_{side}"])
        leg = edge_metric(bpy.data.objects[f"LEG_{side}_SUIT"], BASE_EDGES[f"LEG_{side}_SUIT"])
        arm_gap = min_surface_distance(bpy.data.objects[f"ARM_{side}"], bpy.data.objects[f"HAND_{side}"])
        leg_gap = min_surface_distance(bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects[f"FOOT_{side}"])
        arm_root_gap = min_surface_distance(bpy.data.objects[f"ARM_{side}"], bpy.data.objects["TORSO_UNDER"])
        leg_root_gap = min_surface_distance(bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects["TORSO_UNDER"])
        arm_contact = (
            arm_gap <= NEUTRAL_GAPS[f"arm_{side}_hand"] + 0.12
            and arm_root_gap <= NEUTRAL_GAPS[f"arm_{side}_root"] + 0.12
        )
        leg_contact = (
            leg_gap <= NEUTRAL_GAPS[f"leg_{side}_foot"] + 0.10
            and leg_root_gap <= NEUTRAL_GAPS[f"leg_{side}_root"] + 0.10
        )
        result[f"arm_{side}"] = {
            **arm, "metric_gate": gate_result(arm), "contact_gate": arm_contact,
            "hand_gap": arm_gap, "root_gap": arm_root_gap,
        }
        result[f"leg_{side}"] = {
            **leg, "metric_gate": gate_result(leg), "contact_gate": leg_contact,
            "foot_gap": leg_gap, "root_gap": leg_root_gap,
        }
    return result


def all_metrics_pass(metrics):
    return all(item["metric_gate"] and item["contact_gate"] for item in metrics.values())


def pose_render_paths(pose_name):
    folder = os.path.join(VALIDATION, pose_name.lower())
    os.makedirs(folder, exist_ok=True)
    paths = {
        "front": os.path.join(folder, "front.png"),
        "three_q": os.path.join(folder, "three_q.png"),
    }
    if pose_name in {"CROUCH", "JUMP_ANTICIPATION", "JUMP_TAKEOFF", "JUMP_APEX", "FALL", "LANDING"}:
        paths["side"] = os.path.join(folder, "side.png")
    if pose_name in {"READY", "STEP_LEFT", "POINT_LEFT", "CROUCH", "JUMP_ANTICIPATION", "JUMP_APEX", "LANDING"}:
        paths["game_camera"] = os.path.join(folder, "game_camera.png")
    return paths


def apply_interpolated_state(rig, start, end, factor):
    rotations = {}
    locations = {}
    for bone_name in set(start["rotations"]) | set(end["rotations"]):
        left = start["rotations"].get(bone_name, [0.0, 0.0, 0.0])
        right = end["rotations"].get(bone_name, [0.0, 0.0, 0.0])
        rotations[bone_name] = [a + (b - a) * factor for a, b in zip(left, right)]
    for bone_name in set(start["locations"]) | set(end["locations"]):
        left = start["locations"].get(bone_name, [0.0, 0.0, 0.0])
        right = end["locations"].get(bone_name, [0.0, 0.0, 0.0])
        locations[bone_name] = [a + (b - a) * factor for a, b in zip(left, right)]
    apply_state(rig, {"rotations": rotations, "locations": locations})
    return {"rotations": rotations, "locations": locations}


def interpolation_checks(rig, chain):
    sequence = []
    for start_name, end_name in zip(chain, chain[1:]):
        for factor in (0.25, 0.5, 0.75):
            state = apply_interpolated_state(
                rig, POSE_STATES[start_name], POSE_STATES[end_name], factor
            )
            envelope = state_compliance(state)
            metrics = pose_metrics()
            sequence.append({
                "from": start_name,
                "to": end_name,
                "factor": factor,
                "envelope_issues": envelope,
                "metrics": metrics,
                "pass": not envelope and all_metrics_pass(metrics),
            })
    reset_pose(rig)
    return sequence


def write_pose_files(rig, source_before, copy_initial):
    all_pose_results = {}
    gameplay_readability = {}
    for pose_name in POSE_NAMES:
        state = POSE_STATES[pose_name]
        apply_state(rig, state)
        issues = state_compliance(state)
        metrics = pose_metrics()
        accepted = not issues and all_metrics_pass(metrics)
        paths = pose_render_paths(pose_name)
        render(paths["front"], "front")
        render(paths["three_q"], "three_q_l")
        if "side" in paths:
            render(paths["side"], "left")
        if "game_camera" in paths:
            render(paths["game_camera"], "game")

        result = {
            "pose": pose_name,
            "bone_rotations_degrees_local_xyz": state["rotations"],
            "bone_locations_local": state["locations"],
            "root_cog_offset": {
                "ROOT": state["locations"].get("ROOT", [0.0, 0.0, 0.0]),
                "COG": state["locations"].get("COG", [0.0, 0.0, 0.0]),
            },
            "safe_envelope_compliance": not issues,
            "envelope_issues": issues,
            "deformation_metrics": metrics,
            "deformation_metrics_pass": all_metrics_pass(metrics),
            "visual_review": "PENDING",
            "render_paths": {
                key: os.path.relpath(path, ITERATION).replace("\\", "/")
                for key, path in paths.items()
            },
            "notes": "Static FK pose only; no Action or keyframe.",
        }
        write_json(os.path.join(POSES, pose_name.lower() + ".json"), result)
        all_pose_results[pose_name] = result
        if "game_camera" in paths:
            gameplay_readability[pose_name] = {
                "render": result["render_paths"]["game_camera"],
                "readable": None,
            }

    step_sequence = interpolation_checks(
        rig, ["REST", "STEP_LEFT", "REST", "STEP_RIGHT", "REST"]
    )
    jump_sequence = interpolation_checks(
        rig, ["REST", "JUMP_ANTICIPATION", "JUMP_TAKEOFF", "JUMP_APEX", "FALL", "LANDING", "REST"]
    )
    return all_pose_results, gameplay_readability, step_sequence, jump_sequence


def build_pose_phase(rig, initial_snapshot, source_before, copy_initial):
    global BASE_EDGES
    BASE_EDGES = {
        name: [
            (obj.matrix_world @ obj.data.vertices[edge.vertices[0]].co
             - obj.matrix_world @ obj.data.vertices[edge.vertices[1]].co).length
            for edge in [*obj.data.edges]
        ]
        for name in LIMBS
        for obj in [bpy.data.objects[name]]
    }
    pose_results, readability, step_sequence, jump_sequence = write_pose_files(
        rig, source_before, copy_initial
    )

    final_neutral = {}
    reset_pose(rig)
    for view_name in VIEWS:
        path = os.path.join(VALIDATION, f"final_neutral_{view_name}.png")
        render(path, view_name)
        final_neutral[view_name] = compare_images(
            path, os.path.join(REFERENCE, f"alif_{view_name}.png")
        )
    final_snapshot = snapshot()
    source_after = sha256(SOURCE)
    actions = len(bpy.data.actions)
    constraints = sum(len(bone.constraints) for bone in rig.pose.bones)
    drivers = sum(len(obj.animation_data.drivers) for obj in bpy.data.objects if obj.animation_data)
    keyframes = sum(
        len(curve.keyframe_points)
        for action in bpy.data.actions
        for curve in action.fcurves
    )
    pose_pass = all(
        item["safe_envelope_compliance"] and item["deformation_metrics_pass"]
        for item in pose_results.values()
    )
    transition_pass = all(item["pass"] for item in step_sequence + jump_sequence)
    status = "PENDING_VISUAL_REVIEW"
    if not pose_pass or not transition_pass or final_snapshot != initial_snapshot or source_before != source_after:
        status = "BLOCKED"
    write_json(os.path.join(ITERATION, "alif_pose_contract.json"), {
        "status": status,
        "source_sha256_before": source_before,
        "working_copy_initial_sha256": copy_initial,
        "poses": {
            name: {
                "definition": "poses/" + name.lower() + ".json",
                "metric_and_envelope_pass": pose_results[name]["safe_envelope_compliance"]
                and pose_results[name]["deformation_metrics_pass"],
                "visual_review": "PENDING",
            }
            for name in POSE_NAMES
        },
        "game_camera_readability": readability,
        "step_sequence": {"checks": step_sequence, "pass": all(item["pass"] for item in step_sequence)},
        "jump_sequence": {"checks": jump_sequence, "pass": all(item["pass"] for item in jump_sequence)},
    })
    write_json(os.path.join(ITERATION, "alif_pose_validation_report.json"), {
        "status": status,
        "poses": pose_results,
        "step_sequence_interpolation": step_sequence,
        "jump_sequence_interpolation": jump_sequence,
        "final_neutral_comparison": final_neutral,
        "all_final_neutral_views_pass": all(item["pass"] for item in final_neutral.values()),
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "working_copy_sha256_initial": copy_initial,
        "actions": actions,
        "keyframes": keyframes,
        "constraints": constraints,
        "drivers": drivers,
        "initial_snapshot_equals_final_snapshot": initial_snapshot == final_snapshot,
        "topology_weights_hierarchy_and_object_transforms_unchanged": initial_snapshot == final_snapshot,
        "visual_review": "PENDING",
    })
    if initial_snapshot != final_snapshot:
        raise RuntimeError("Final neutral rig differs in mesh, weights, hierarchy, or object transforms")
    if source_before != source_after:
        raise RuntimeError("Iteration 3B source hash changed")
    if actions or keyframes or constraints or drivers:
        raise RuntimeError("Animation data, constraints, or drivers appeared")
    camera = bpy.data.objects["TSA_CAMERA"]
    camera.matrix_world = INITIAL_CAMERA_MATRIX
    bpy.context.scene.camera = INITIAL_ACTIVE_CAMERA
    scene = bpy.context.scene
    for name, value in INITIAL_RENDER_SETTINGS.items():
        setattr(scene.render, name, value)
    scene.render.image_settings.file_format = INITIAL_IMAGE_FORMAT
    scene.render.filepath = INITIAL_RENDER_PATH
    scene.render.film_transparent = INITIAL_FILM_TRANSPARENT
    scene.render.engine = INITIAL_RENDER_ENGINE
    if all(item["pass"] for item in final_neutral.values()):
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=WORKING)
    print("ITERATION04_POSE_PHASE", status, "poses", len(pose_results), "step", transition_pass)


def render_scan_candidates(rig, scan):
    candidate_results = {}
    for name, directions in scan.items():
        candidates = [entry for entry in directions if entry["metric_safe_candidate_degrees"] > 0]
        for index, entry in enumerate(candidates):
            set_joint(rig, entry["bone"], entry["axis"], entry["sign"] * entry["metric_safe_candidate_degrees"])
            key = f"{name}_{index}_{entry['metric_safe_candidate_degrees']}deg"
            front = os.path.join(VALIDATION, "envelope", key + "_front.png")
            quarter = os.path.join(VALIDATION, "envelope", key + "_three_q_l.png")
            os.makedirs(os.path.dirname(front), exist_ok=True)
            render(front, "front")
            render(quarter, "three_q_l")
            candidate_results[key] = {
                "bone": entry["bone"],
                "axis": entry["axis"],
                "angle_degrees": entry["sign"] * entry["metric_safe_candidate_degrees"],
                "front": os.path.relpath(front, ITERATION).replace("\\", "/"),
                "three_q_l": os.path.relpath(quarter, ITERATION).replace("\\", "/"),
                "visual_review": "PENDING",
            }
            reset_pose(rig)
    return candidate_results


def main():
    global INITIAL_CAMERA_MATRIX, INITIAL_ACTIVE_CAMERA
    global INITIAL_RENDER_SETTINGS, INITIAL_IMAGE_FORMAT, INITIAL_RENDER_PATH
    global INITIAL_FILM_TRANSPARENT, INITIAL_RENDER_ENGINE
    os.makedirs(VALIDATION, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)
    os.makedirs(POSES, exist_ok=True)
    rig = bpy.data.objects.get("ALIF_RIG")
    if not rig or len(rig.data.bones) != 27:
        raise RuntimeError("Required 27-bone ALIF_RIG is unavailable")
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    phase = arguments[arguments.index("--phase") + 1] if "--phase" in arguments else "discover"
    source_before = sha256(SOURCE)
    current_working = sha256(WORKING)
    if phase == "discover":
        copy_initial = current_working
        if source_before != copy_initial:
            raise RuntimeError("Source and working copy differ before discovery")
    elif phase == "poses":
        source_record = os.path.join(LOGS, "source_before.sha256")
        copy_record = os.path.join(LOGS, "copy_initial.sha256")
        if not os.path.isfile(source_record) or not os.path.isfile(copy_record):
            raise RuntimeError("Initial source/copy hash records are unavailable")
        with open(source_record, encoding="utf-8") as recorded:
            recorded_source = recorded.read().split()[0]
        with open(copy_record, encoding="utf-8") as recorded:
            copy_initial = recorded.read().split()[0]
        if source_before != recorded_source or copy_initial != recorded_source:
            raise RuntimeError("Source no longer matches the verified initial copy")
    else:
        raise RuntimeError("Unknown phase; use --phase discover or --phase poses")
    if len(bpy.data.actions) != 0:
        raise RuntimeError("Source has unexpected Actions; fail closed")
    if sum(len(bone.constraints) for bone in rig.pose.bones) != 0:
        raise RuntimeError("Source has unexpected constraints; fail closed")

    initial_snapshot = snapshot()
    scene = bpy.context.scene
    camera = bpy.data.objects.get("TSA_CAMERA")
    if camera is None:
        raise RuntimeError("TSA_CAMERA is missing")
    INITIAL_CAMERA_MATRIX = camera.matrix_world.copy()
    INITIAL_ACTIVE_CAMERA = scene.camera
    INITIAL_RENDER_SETTINGS = {
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
    }
    INITIAL_IMAGE_FORMAT = scene.render.image_settings.file_format
    INITIAL_RENDER_PATH = scene.render.filepath
    INITIAL_FILM_TRANSPARENT = scene.render.film_transparent
    INITIAL_RENDER_ENGINE = scene.render.engine
    if phase == "discover":
        neutral_comparison = save_neutral_reference_renders(rig)
        if not all(item["pass"] for item in neutral_comparison.values()):
            write_json(os.path.join(LOGS, "iteration04R_blocked.json"), {
                "status": "BLOCKED",
                "blocker": "NEUTRAL_VISUAL_MISMATCH",
                "neutral_comparison": neutral_comparison,
            })
            raise RuntimeError("NEUTRAL_VISUAL_MISMATCH")
        scan = scan_envelope(rig)
        candidate_renders = render_scan_candidates(rig, scan)
        write_json(os.path.join(LOGS, "envelope_scan.json"), {
            "step_degrees": 5,
            "deformation_metric_gates": {"p01_min": GATE_P01, "p99_max": GATE_P99},
            "scan": scan,
            "candidate_renders": candidate_renders,
        })
        write_json(os.path.join(ITERATION, "alif_safe_pose_envelope.json"), {
            "status": "PENDING_VISUAL_REVIEW",
            "source_file": "tsa/alif/restart/iteration03B/alif_deform_v1.blend",
            "working_file": "tsa/alif/restart/iteration04/alif_poseproof_v1.blend",
            "source_sha256_before": source_before,
            "copy_sha256_initial": copy_initial,
            "increment_degrees": 5,
            "metric_gates": {"p01_min": GATE_P01, "p99_max": GATE_P99},
            "scan_log": "logs/envelope_scan.json",
            "candidate_visuals_require_review": list(candidate_renders),
            "safe_ranges": {},
        })
        reset_pose(rig)
        if initial_snapshot != snapshot():
            raise RuntimeError("Object, mesh, hierarchy, transform, or rig architecture changed during validation")
        if source_before != sha256(SOURCE):
            raise RuntimeError("Iteration 3B source hash changed")
        print("ITERATION04_DISCOVERY_COMPLETE", len(scan), len(candidate_renders), source_before)
    elif phase == "poses":
        globals()["NEUTRAL_GAPS"] = {}
        for side in ("L", "R"):
            globals()["NEUTRAL_GAPS"][f"arm_{side}_hand"] = min_surface_distance(
                bpy.data.objects[f"ARM_{side}"], bpy.data.objects[f"HAND_{side}"]
            )
            globals()["NEUTRAL_GAPS"][f"arm_{side}_root"] = min_surface_distance(
                bpy.data.objects[f"ARM_{side}"], bpy.data.objects["TORSO_UNDER"]
            )
            globals()["NEUTRAL_GAPS"][f"leg_{side}_foot"] = min_surface_distance(
                bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects[f"FOOT_{side}"]
            )
            globals()["NEUTRAL_GAPS"][f"leg_{side}_root"] = min_surface_distance(
                bpy.data.objects[f"LEG_{side}_SUIT"], bpy.data.objects["TORSO_UNDER"]
            )
        base_lengths = {
            name: [
                (obj.matrix_world @ obj.data.vertices[edge.vertices[0]].co
                 - obj.matrix_world @ obj.data.vertices[edge.vertices[1]].co).length
                for edge in obj.data.edges
            ]
            for name in LIMBS
            for obj in [bpy.data.objects[name]]
        }
        globals()["BASE_EDGES"] = base_lengths
        build_pose_phase(rig, initial_snapshot, source_before, copy_initial)
    else:
        raise RuntimeError("Unknown phase; use --phase discover or --phase poses")


if __name__ == "__main__":
    main()
