import bpy
import json
import math
from pathlib import Path

blend_file = r"C:\Users\HWI-ADMIN\Downloads\3d\tsa\alif\iteration02\alif_rigready_v1.blend"
out_dir = Path(r"C:\Users\HWI-ADMIN\Downloads\3d\tsa\alif\iteration02")
val_dir = out_dir / "validation"

# 1. Build hierarchy
def create_empty(name, parent=None, location=(0,0,0)):
    emp = bpy.data.objects.get(name) or bpy.data.objects.new(name, None)
    if emp.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(emp)
    emp.empty_display_type = 'PLAIN_AXES'
    emp.empty_display_size = 0.5
    emp.location = location
    if parent:
        emp.parent = parent
    return emp

root = create_empty("ALIF_ROOT")
head_region = create_empty("HEAD_CTRL_REGION", parent=root, location=(0, 0, 3.06))
torso_region = create_empty("TORSO_CTRL_REGION", parent=root, location=(0, 0, 1.58))
arm_l_region = create_empty("ARM_L_REGION", parent=root, location=(1.32, 0, 1.72))
arm_r_region = create_empty("ARM_R_REGION", parent=root, location=(-1.32, 0, 1.72))
leg_l_region = create_empty("LEG_L_REGION", parent=root, location=(0.58, 0, 0.62))
leg_r_region = create_empty("LEG_R_REGION", parent=root, location=(-0.58, 0, 0.62))

for obj in bpy.data.objects:
    if obj.name in ["ALIF_ROOT", "HEAD_CTRL_REGION", "TORSO_CTRL_REGION", "ARM_L_REGION", "ARM_R_REGION", "LEG_L_REGION", "LEG_R_REGION"]:
        continue
    
    name = obj.name
    reg = obj.get("tsa_region", "")
    
    # Classification rules
    if reg in ["HEAD", "EYE_L", "EYE_R", "PUPIL_L", "PUPIL_R", "BOLT_L", "BOLT_R", "STITCH_HEAD"] or "HEAD" in name or "EYE" in name or "BOLT" in name or "STITCH" in name or "EAR" in name or "MOUTH" in name or "TEETH" in name or "NECK_BRIDGE" in name:
        obj.parent = head_region
        obj.matrix_parent_inverse = head_region.matrix_world.inverted()
    elif reg in ["ARM_L", "HAND_L"] or "ARM_L" in name or "HAND_L" in name or "SLEEVE_L" in name:
        obj.parent = arm_l_region
        obj.matrix_parent_inverse = arm_l_region.matrix_world.inverted()
    elif reg in ["ARM_R", "HAND_R"] or "ARM_R" in name or "HAND_R" in name or "SLEEVE_R" in name:
        obj.parent = arm_r_region
        obj.matrix_parent_inverse = arm_r_region.matrix_world.inverted()
    elif reg in ["LEG_L_SUIT", "FOOT_L"] or "LEG_L" in name or "FOOT_L" in name or "SHOE_L" in name:
        obj.parent = leg_l_region
        obj.matrix_parent_inverse = leg_l_region.matrix_world.inverted()
    elif reg in ["LEG_R_SUIT", "FOOT_R"] or "LEG_R" in name or "FOOT_R" in name or "SHOE_R" in name:
        obj.parent = leg_r_region
        obj.matrix_parent_inverse = leg_r_region.matrix_world.inverted()
    else: # Default Torso & Clothing
        obj.parent = torso_region
        obj.matrix_parent_inverse = torso_region.matrix_world.inverted()

# Save rest state
bpy.ops.wm.save_as_mainfile(filepath=blend_file)

# Function to setup camera & render
cam = bpy.data.objects.get("Camera")
if not cam:
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

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
    "three_q_r": ((7.07, -7.07, 2.0), (math.radians(90), 0, math.radians(45))),
    "top": ((0, 0, 12.0), (0, 0, 0)),
    "bottom": ((0, 0, -8.0), (math.radians(180), 0, 0))
}

# 2. Render Neutral Views
for vname, (loc, rot) in views.items():
    set_cam(loc, rot)
    bpy.context.scene.render.filepath = str(val_dir / f"alif_{vname}.png")
    bpy.ops.render.render(write_still=True)

# 3. Head Test +15 deg
set_cam(*views["front"])
head_region.rotation_euler.z = math.radians(15)
bpy.context.scene.render.filepath = str(val_dir / "head_test_plus15_front.png")
bpy.ops.render.render(write_still=True)

set_cam(*views["three_q_l"])
bpy.context.scene.render.filepath = str(val_dir / "head_test_plus15_34.png")
bpy.ops.render.render(write_still=True)

# Head Test -15 deg
set_cam(*views["front"])
head_region.rotation_euler.z = math.radians(-15)
bpy.context.scene.render.filepath = str(val_dir / "head_test_minus15_front.png")
bpy.ops.render.render(write_still=True)

head_region.rotation_euler.z = 0

# 4. Limb Region Pivot Proof
arm_l_region.rotation_euler.y = math.radians(-10)
arm_r_region.rotation_euler.y = math.radians(10)
leg_l_region.rotation_euler.x = math.radians(8)
leg_r_region.rotation_euler.x = math.radians(-8)

set_cam(*views["front"])
bpy.context.scene.render.filepath = str(val_dir / "region_pivot_front.png")
bpy.ops.render.render(write_still=True)

set_cam(*views["three_q_l"])
bpy.context.scene.render.filepath = str(val_dir / "region_pivot_34.png")
bpy.ops.render.render(write_still=True)

# Reset back to neutral rest pose
arm_l_region.rotation_euler.y = 0
arm_r_region.rotation_euler.y = 0
leg_l_region.rotation_euler.x = 0
leg_r_region.rotation_euler.x = 0

bpy.ops.wm.save_as_mainfile(filepath=blend_file)

# 5. Inventory output
inv = {
    "objects": [],
    "mesh_object_count": 0,
    "armature_count": len([o for o in bpy.data.objects if o.type == 'ARMATURE']),
    "action_count": len(bpy.data.actions),
    "materials": [m.name for m in bpy.data.materials],
    "semantic_regions": ["ALIF_ROOT", "HEAD_CTRL_REGION", "TORSO_CTRL_REGION", "ARM_L_REGION", "ARM_R_REGION", "LEG_L_REGION", "LEG_R_REGION"]
}

for obj in bpy.data.objects:
    inv["objects"].append({
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "location": [round(v, 4) for v in obj.location],
        "rotation": [round(v, 4) for v in obj.rotation_euler],
        "scale": [round(v, 4) for v in obj.scale],
        "tsa_region": obj.get("tsa_region", None)
    })
    if obj.type == 'MESH':
        inv["mesh_object_count"] += 1

with open(out_dir / "alif_rigready_inventory.json", "w") as f:
    json.dump(inv, f, indent=2)

print("RIGREADY_PREPARATION_COMPLETE")
