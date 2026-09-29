import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

blend_file = r"C:\Users\HWI-ADMIN\Downloads\3d\tsa\alif\iteration03\alif_armature_v1.blend"
out_dir = Path(r"C:\Users\HWI-ADMIN\Downloads\3d\tsa\alif\iteration03")
val_dir = out_dir / "validation"

# 1. Create Armature
amt_data = bpy.data.armatures.new("ALIF_RIG_DATA")
amt_obj = bpy.data.objects.new("ALIF_RIG", amt_data)
bpy.context.scene.collection.objects.link(amt_obj)

root_emp = bpy.data.objects.get("ALIF_ROOT")
if root_emp:
    amt_obj.parent = root_emp

bpy.context.view_layer.objects.active = amt_obj
bpy.ops.object.mode_set(mode='EDIT')

bones_def = [
    # Core (7)
    ("ROOT", None, (0, 0, 0), (0, 0, 0.2), False),
    ("COG", "ROOT", (0, 0, 1.58), (0, 0, 1.78), False),
    ("PELVIS", "COG", (0, 0, 1.28), (0, 0, 1.58), True),
    ("SPINE", "PELVIS", (0, 0, 1.58), (0, 0, 2.00), True),
    ("CHEST", "SPINE", (0, 0, 2.00), (0, 0, 2.45), True),
    ("NECK", "CHEST", (0, 0, 2.45), (0, 0, 2.80), True),
    ("HEAD", "NECK", (0, 0, 2.80), (0, 0, 3.50), True),
    
    # Left Arm (5)
    ("SHOULDER.L", "CHEST", (0.30, 0, 2.25), (1.32, 0, 2.25), True),
    ("UPPER_ARM.L", "SHOULDER.L", (1.32, 0, 2.25), (1.32, 0, 1.50), True),
    ("FOREARM.L", "UPPER_ARM.L", (1.32, 0, 1.50), (1.35, 0, 0.95), True),
    ("WRIST.L", "FOREARM.L", (1.35, 0, 0.95), (1.35, 0, 0.76), True),
    ("HAND.L", "WRIST.L", (1.35, 0, 0.76), (1.35, 0, 0.45), True),
    
    # Right Arm (5)
    ("SHOULDER.R", "CHEST", (-0.30, 0, 2.25), (-1.32, 0, 2.25), True),
    ("UPPER_ARM.R", "SHOULDER.R", (-1.32, 0, 2.25), (-1.32, 0, 1.50), True),
    ("FOREARM.R", "UPPER_ARM.R", (-1.32, 0, 1.50), (-1.35, 0, 0.95), True),
    ("WRIST.R", "FOREARM.R", (-1.35, 0, 0.95), (-1.35, 0, 0.76), True),
    ("HAND.R", "WRIST.R", (-1.35, 0, 0.76), (-1.35, 0, 0.45), True),
    
    # Left Leg (5)
    ("HIP.L", "PELVIS", (0.20, 0, 1.28), (0.58, 0, 1.15), True),
    ("THIGH.L", "HIP.L", (0.58, 0, 1.15), (0.58, 0, 0.60), True),
    ("SHIN.L", "THIGH.L", (0.58, 0, 0.60), (0.58, 0, 0.10), True),
    ("ANKLE.L", "SHIN.L", (0.58, 0, 0.10), (0.58, -0.15, -0.10), True),
    ("FOOT.L", "ANKLE.L", (0.58, -0.15, -0.10), (0.58, -0.50, -0.10), True),
    
    # Right Leg (5)
    ("HIP.R", "PELVIS", (-0.20, 0, 1.28), (-0.58, 0, 1.15), True),
    ("THIGH.R", "HIP.R", (-0.58, 0, 1.15), (-0.58, 0, 0.60), True),
    ("SHIN.R", "THIGH.R", (-0.58, 0, 0.60), (-0.58, 0, 0.10), True),
    ("ANKLE.R", "SHIN.R", (-0.58, 0, 0.10), (-0.58, -0.15, -0.10), True),
    ("FOOT.R", "ANKLE.R", (-0.58, -0.15, -0.10), (-0.58, -0.50, -0.10), True)
]

ebones = amt_data.edit_bones

for name, parent, head, tail, def_flag in bones_def:
    b = ebones.new(name)
    b.head = head
    b.tail = tail
    b.use_deform = def_flag
    if parent:
        b.parent = ebones[parent]

bpy.ops.object.mode_set(mode='OBJECT')

# Save rest state
bpy.ops.wm.save_as_mainfile(filepath=blend_file)

# Camera & Render Neutral Views
cam = bpy.data.objects.get("Camera")
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 5.65
bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 1024

def set_cam(loc, rot):
    cam.location = loc
    cam.rotation_euler = rot

views = {
    "front": ((0, -10, 2.0), (math.radians(90), 0, 0)),
    "three_q_l": ((-7.07, -7.07, 2.0), (math.radians(90), 0, math.radians(-45))),
    "left": ((-10, 0, 2.0), (math.radians(90), 0, math.radians(-90))),
    "back": ((0, 10, 2.0), (math.radians(90), 0, math.radians(180))),
    "right": ((10, 0, 2.0), (math.radians(90), 0, math.radians(90))),
    "three_q_r": ((7.07, -7.07, 2.0), (math.radians(90), 0, math.radians(45)))
}

for vname, (loc, rot) in views.items():
    set_cam(loc, rot)
    bpy.context.scene.render.filepath = str(val_dir / f"alif_{vname}.png")
    bpy.ops.render.render(write_still=True)

# Export Contract & Landmarks JSON
landmarks = []
for b in amt_obj.data.bones:
    landmarks.append({
        "name": b.name,
        "head": [round(v, 4) for v in b.head_local],
        "tail": [round(v, 4) for v in b.tail_local],
        "length": round(b.length, 4),
        "parent": b.parent.name if b.parent else None,
        "use_deform": b.use_deform
    })

with open(out_dir / "alif_bone_landmarks.json", "w") as f:
    json.dump(landmarks, f, indent=2)

contract = {
  "character": "ALIF",
  "iteration": 3,
  "rig_version": "ALIF_RIG_V1",
  "coordinate_system": {
    "front": "-Y",
    "up": "+Z",
    "symmetry": "X=0"
  },
  "armature_object": "ALIF_RIG",
  "bone_count": len(amt_obj.data.bones),
  "bones": [b.name for b in amt_obj.data.bones],
  "symmetry_tolerance": {
    "x_max_diff": 0.02,
    "length_max_rel_diff": 0.02
  },
  "visual_joint_geometry": False,
  "mesh_binding": False,
  "armature_modifiers": False,
  "vertex_weights": False,
  "animation": False
}

with open(out_dir / "alif_armature_contract.json", "w") as f:
    json.dump(contract, f, indent=2)

print("ARMATURE_CONTRACT_COMPLETE")
