import bpy

for name in ['BODY_CORE', 'LOWER_VOLUME']:
    obj = bpy.data.objects[name]
    print(f"--- {name} ---")
    print(f"Vert count: {len(obj.data.vertices)}")
    print(f"Vertex groups: {[v.name for v in obj.vertex_groups]}")
    print(f"Modifiers: {[m.name for m in obj.modifiers]}")

