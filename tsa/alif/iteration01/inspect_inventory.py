import bpy
import json
from pathlib import Path

blend_path = r"C:\Users\HWI-ADMIN\alif_output_v1\alif_v1.blend"
output_json = r"C:\Users\HWI-ADMIN\Downloads\3d\tsa\alif\iteration01\alif_baseline_inventory.json"

target_regions = [
    "HEAD", "NECK_BRIDGE", "TORSO_UNDER", "SUIT_SHELL",
    "ARM_L", "ARM_R", "HAND_L", "HAND_R",
    "LEG_L_SUIT", "LEG_R_SUIT", "FOOT_L", "FOOT_R"
]

inventory = {
    "objects": [],
    "mesh_object_count": 0,
    "armature_count": 0,
    "action_count": len(bpy.data.actions),
    "materials": [m.name for m in bpy.data.materials],
    "tsa_region_objects": {},
    "target_region_transforms": {}
}

for obj in bpy.data.objects:
    obj_info = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "tsa_region": obj.get("tsa_region", None)
    }
    inventory["objects"].append(obj_info)
    
    if obj.type == 'MESH':
        inventory["mesh_object_count"] += 1
    elif obj.type == 'ARMATURE':
        inventory["armature_count"] += 1
        
    region = obj.get("tsa_region")
    if region:
        inventory["tsa_region_objects"][obj.name] = region
        if region in target_regions:
            inventory["target_region_transforms"][region] = {
                "object_name": obj.name,
                "dimensions": [round(v, 4) for v in obj.dimensions],
                "location": [round(v, 4) for v in obj.location],
                "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
                "scale": [round(v, 4) for v in obj.scale]
            }

with open(output_json, 'w') as f:
    json.dump(inventory, f, indent=2)

print("INVENTORY_COMPLETE")
