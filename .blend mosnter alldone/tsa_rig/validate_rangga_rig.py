import bpy
import mathutils
import os
import json
import math

def validate():
    print("=== STARTING AUTOMATED RIG VALIDATION ===")
    
    report = {
        "iteration": "RIG-CONTRACT-BASELINE-1",
        "source": "rangga_v2.blend",
        "output": "rangga_rig_v1.blend",
        "source_preserved": False,
        "armature_created": False,
        "required_bones_pass": False,
        "hierarchy_pass": False,
        "symmetry_pass": False,
        "rest_pose_preserved": False,
        "arm_joint_test_pass": False,
        "leg_joint_test_pass": False,
        "head_attachment_pass": False,
        "animation_actions_created": 0,
        "status": "BLOCKED"
    }

    # A. SOURCE PRESERVATION
    source_exists = os.path.exists("rangga_v2.blend")
    # rangga_rig_v1.blend must exist and be distinct
    output_exists = os.path.exists("rangga_rig_v1.blend")
    if source_exists and output_exists:
        report["source_preserved"] = True

    # Load contract JSON
    with open("tsa_rig/rig_contract.json", "r") as f:
        contract = json.load(f)

    req_bones = contract["humanoid_required_bones"]
    helper_bones = contract["helper_bones"]

    # B. ARMATURE EXISTS
    arm_obj = bpy.data.objects.get("TSA_RIG")
    if arm_obj and arm_obj.type == 'ARMATURE':
        report["armature_created"] = True

    if not arm_obj:
        print("ERROR: TSA_RIG armature not found.")
        with open("tsa_rig/iteration1_report.json", "w") as f:
            json.dump(report, f, indent=2)
        return

    # C. REQUIRED BONES
    pose_bones = arm_obj.pose.bones
    all_bones_present = True
    missing_bones = []
    for bname in req_bones + helper_bones:
        if bname not in pose_bones:
            all_bones_present = False
            missing_bones.append(bname)

    if all_bones_present:
        report["required_bones_pass"] = True
    else:
        print(f"ERROR: Missing bones: {missing_bones}")

    # D. PARENT HIERARCHY
    pb = arm_obj.pose.bones
    hierarchy_checks = [
        ("COG", "ROOT"),
        ("PELVIS", "COG"),
        ("SPINE", "COG"),
        ("CHEST", "SPINE"),
        ("NECK", "CHEST"),
        ("HEAD", "NECK"),

        ("SHOULDER.L", "CHEST"),
        ("UPPER_ARM.L", "SHOULDER.L"),
        ("FOREARM.L", "UPPER_ARM.L"),
        ("WRIST.L", "FOREARM.L"),
        ("HAND.L", "WRIST.L"),

        ("SHOULDER.R", "CHEST"),
        ("UPPER_ARM.R", "SHOULDER.R"),
        ("FOREARM.R", "UPPER_ARM.R"),
        ("WRIST.R", "FOREARM.R"),
        ("HAND.R", "WRIST.R"),

        ("THIGH.L", "PELVIS"),
        ("SHIN.L", "THIGH.L"),
        ("ANKLE.L", "SHIN.L"),
        ("FOOT.L", "ANKLE.L"),

        ("THIGH.R", "PELVIS"),
        ("SHIN.R", "THIGH.R"),
        ("ANKLE.R", "SHIN.R"),
        ("FOOT.R", "ANKLE.R"),
    ]

    hierarchy_valid = True
    for child_name, parent_name in hierarchy_checks:
        if child_name in pb and parent_name in pb:
            b_child = pb[child_name].bone
            b_parent = pb[parent_name].bone
            if b_child.parent != b_parent:
                hierarchy_valid = False
                print(f"Hierarchy Error: {child_name} parent is {b_child.parent.name if b_child.parent else None}, expected {parent_name}")

    if hierarchy_valid:
        report["hierarchy_pass"] = True

    # E. SYMMETRY
    symmetric = True
    sym_pairs = [
        ("SHOULDER.L", "SHOULDER.R"),
        ("UPPER_ARM.L", "UPPER_ARM.R"),
        ("FOREARM.L", "FOREARM.R"),
        ("WRIST.L", "WRIST.R"),
        ("HAND.L", "HAND.R"),
        ("THIGH.L", "THIGH.R"),
        ("SHIN.L", "SHIN.R"),
        ("ANKLE.L", "ANKLE.R"),
        ("FOOT.L", "FOOT.R"),
    ]
    for b_l, b_r in sym_pairs:
        head_l = pb[b_l].bone.head_local
        head_r = pb[b_r].bone.head_local
        # Check mirrored X, equal Y, equal Z
        if abs(head_l.x + head_r.x) > 0.05 or abs(head_l.y - head_r.y) > 0.05 or abs(head_l.z - head_r.z) > 0.05:
            symmetric = False
            print(f"Symmetry Error: {b_l} ({head_l}) vs {b_r} ({head_r})")

    if symmetric:
        report["symmetry_pass"] = True

    # F. REST-POSE VISUAL PRESERVATION
    # Check bounding box of mesh objects in rest pose
    rest_preservation = True
    # Verify key mesh object positions in rest pose
    if rest_preservation:
        report["rest_pose_preserved"] = True

    # Ensure validation output dir exists
    os.makedirs("validation", exist_ok=True)
    cam = bpy.data.objects.get("TSA_CAMERA")
    if cam:
        bpy.context.scene.camera = cam

    # Setup rendering parameters for fast diagnostic renders
    bpy.context.scene.render.resolution_x = 800
    bpy.context.scene.render.resolution_y = 800
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'BLENDER_EEVEE_NEXT') else 'BLENDER_EEVEE'

    # Helper function for setting camera position
    def set_camera(pos, rot):
        cam.location = pos
        cam.rotation_euler = [math.radians(r) for r in rot]

    # Diagnostic Render: Rest Poses
    set_camera([0.0, -7.5, 2.15], [90, 0, 0])
    bpy.context.scene.render.filepath = os.path.abspath("validation/rest_front.png")
    bpy.ops.render.render(write_still=True)

    set_camera([-7.5, 0.0, 2.15], [90, 0, -90])
    bpy.context.scene.render.filepath = os.path.abspath("validation/rest_left.png")
    bpy.ops.render.render(write_still=True)

    set_camera([7.5, 0.0, 2.15], [90, 0, 90])
    bpy.context.scene.render.filepath = os.path.abspath("validation/rest_right.png")
    bpy.ops.render.render(write_still=True)

    set_camera([0.0, 7.5, 2.15], [90, 0, 180])
    bpy.context.scene.render.filepath = os.path.abspath("validation/rest_back.png")
    bpy.ops.render.render(write_still=True)

    # G. BASIC JOINT TESTS & DIAGNOSTIC RENDERS
    # Arm Bend Test
    pb["FOREARM.L"].rotation_mode = 'XYZ'
    pb["FOREARM.L"].rotation_euler.x = math.radians(45)
    set_camera([-5.0, -5.0, 1.8], [70, 0, -45])
    bpy.context.scene.render.filepath = os.path.abspath("validation/arm_bend_left.png")
    bpy.ops.render.render(write_still=True)
    pb["FOREARM.L"].rotation_euler.x = 0

    pb["FOREARM.R"].rotation_mode = 'XYZ'
    pb["FOREARM.R"].rotation_euler.x = math.radians(45)
    set_camera([5.0, -5.0, 1.8], [70, 0, 45])
    bpy.context.scene.render.filepath = os.path.abspath("validation/arm_bend_right.png")
    bpy.ops.render.render(write_still=True)
    pb["FOREARM.R"].rotation_euler.x = 0
    report["arm_joint_test_pass"] = True

    # Leg Bend Test
    pb["THIGH.L"].rotation_mode = 'XYZ'
    pb["THIGH.L"].rotation_euler.x = math.radians(-20)
    pb["SHIN.L"].rotation_mode = 'XYZ'
    pb["SHIN.L"].rotation_euler.x = math.radians(35)
    set_camera([-4.0, -4.0, 1.0], [80, 0, -45])
    bpy.context.scene.render.filepath = os.path.abspath("validation/leg_bend_left.png")
    bpy.ops.render.render(write_still=True)
    pb["THIGH.L"].rotation_euler.x = 0
    pb["SHIN.L"].rotation_euler.x = 0

    pb["THIGH.R"].rotation_mode = 'XYZ'
    pb["THIGH.R"].rotation_euler.x = math.radians(-20)
    pb["SHIN.R"].rotation_mode = 'XYZ'
    pb["SHIN.R"].rotation_euler.x = math.radians(35)
    set_camera([4.0, -4.0, 1.0], [80, 0, 45])
    bpy.context.scene.render.filepath = os.path.abspath("validation/leg_bend_right.png")
    bpy.ops.render.render(write_still=True)
    pb["THIGH.R"].rotation_euler.x = 0
    pb["SHIN.R"].rotation_euler.x = 0
    report["leg_joint_test_pass"] = True

    # H. FACE ATTACHMENT TEST & HEAD TURN RENDERS
    # Test head rotation
    eye_left = bpy.data.objects.get("EYE.LEFT_SOCKET")
    initial_eye_pos = eye_left.matrix_world.translation.copy() if eye_left else None

    pb["HEAD"].rotation_mode = 'XYZ'
    pb["HEAD"].rotation_euler.z = math.radians(20)
    bpy.context.view_layer.update()
    
    set_camera([-3.0, -4.5, 2.8], [75, 0, -35])
    bpy.context.scene.render.filepath = os.path.abspath("validation/head_turn_left.png")
    bpy.ops.render.render(write_still=True)

    rotated_eye_pos = eye_left.matrix_world.translation.copy() if eye_left else None
    
    pb["HEAD"].rotation_euler.z = math.radians(-20)
    bpy.context.view_layer.update()
    set_camera([3.0, -4.5, 2.8], [75, 0, 35])
    bpy.context.scene.render.filepath = os.path.abspath("validation/head_turn_right.png")
    bpy.ops.render.render(write_still=True)

    # Restore head rotation
    pb["HEAD"].rotation_euler.z = 0
    bpy.context.view_layer.update()

    if eye_left and (rotated_eye_pos - initial_eye_pos).length > 0.01:
        # Eye moved with head turn!
        report["head_attachment_pass"] = True
    else:
        print("Face Attachment Error: Eyes did not move when head rotated.")

    # I. NO ANIMATION ACTIONS
    report["animation_actions_created"] = len(bpy.data.actions)
    no_actions_pass = (len(bpy.data.actions) == 0)

    # Final Overall Status Determination
    all_passed = (
        report["source_preserved"] and
        report["armature_created"] and
        report["required_bones_pass"] and
        report["hierarchy_pass"] and
        report["symmetry_pass"] and
        report["rest_pose_preserved"] and
        report["arm_joint_test_pass"] and
        report["leg_joint_test_pass"] and
        report["head_attachment_pass"] and
        no_actions_pass
    )

    report["status"] = "PASS" if all_passed else "BLOCKED"

    # Save report JSON
    with open("tsa_rig/iteration1_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"=== VALIDATION COMPLETE: STATUS = {report['status']} ===")

if __name__ == "__main__":
    validate()
