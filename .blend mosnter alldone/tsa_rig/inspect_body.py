import bpy
import mathutils

for name in ['BODY_CORE', 'LOWER_VOLUME', 'BODY_SPIRAL', 'BACK_NUB']:
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        world_bbox = [list(obj.matrix_world @ mathutils.Vector(c)) for c in obj.bound_box]
        min_z = min(c[2] for c in world_bbox)
        max_z = max(c[2] for c in world_bbox)
        print(f"{name}: Z[{min_z:.3f}, {max_z:.3f}]")

