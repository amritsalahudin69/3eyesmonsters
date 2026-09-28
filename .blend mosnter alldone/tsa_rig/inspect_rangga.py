import bpy

print("=== ALL RANGGA OBJECTS ===")
for obj in sorted(bpy.data.objects, key=lambda x: x.name):
    print(f"'{obj.name}' | Type: {obj.type} | Loc: {[round(c,3) for c in obj.location]} | Parent: {obj.parent.name if obj.parent else 'None'}")
print("=== END ===")
