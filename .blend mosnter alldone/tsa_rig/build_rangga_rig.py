import bpy
import mathutils

def build_rig():
    print("=== STARTING RIG BUILD FOR RANGGA ===")
    
    # Ensure operating on rangga_v2.blend without modifying original file
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    
    # 1. Create Armature Object
    arm_data = bpy.data.armatures.new("TSA_RIG")
    arm_obj = bpy.data.objects.new("TSA_RIG", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    
    # Set Metadata Custom Properties on Armature object
    arm_obj["tsa_rig_version"] = "TSA_RIG_CONTRACT_V1"
    arm_obj["tsa_front_axis"] = "-Y"
    arm_obj["tsa_up_axis"] = "+Z"
    arm_obj["tsa_symmetry_plane"] = "X=0"
    arm_obj["tsa_character"] = "RANGGA"
    arm_obj["tsa_rig_role"] = "HUMANOID_BASELINE"
    arm_obj["tsa_motion_ready"] = True
    arm_obj["tsa_animation_present"] = False

    # Also set on armature data block
    arm_data["tsa_rig_version"] = "TSA_RIG_CONTRACT_V1"

    # Activate armature object
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Bone Definitions (head, tail, parent_name, is_deform)
    bone_defs = [
        # Spine / Core Chain
        ("ROOT", [0, 0, 0], [0, 0, 0.2], None, True),
        ("COG", [0, 0, 1.03], [0, 0, 1.25], "ROOT", True),
        ("PELVIS", [0, 0, 0.9], [0, 0, 0.7], "COG", True),
        ("SPINE", [0, 0, 1.03], [0, 0, 1.6], "COG", True),
        ("CHEST", [0, 0, 1.6], [0, 0, 2.15], "SPINE", True),
        ("NECK", [0, 0, 2.15], [0, 0, 2.5], "CHEST", True),
        ("HEAD", [0, 0, 2.5], [0, 0, 3.8], "NECK", True),

        # Left Arm
        ("SHOULDER.L", [-0.5, 0.0, 2.15], [-1.17, -0.01, 2.15], "CHEST", True),
        ("UPPER_ARM.L", [-1.17, -0.01, 2.15], [-1.31, -0.02, 1.62], "SHOULDER.L", True),
        ("FOREARM.L", [-1.31, -0.02, 1.62], [-1.26, -0.04, 1.18], "UPPER_ARM.L", True),
        ("WRIST.L", [-1.26, -0.04, 1.18], [-1.24, -0.05, 0.95], "FOREARM.L", True),
        ("HAND.L", [-1.24, -0.05, 0.95], [-1.24, -0.05, 0.75], "WRIST.L", True),

        # Right Arm (Symmetric)
        ("SHOULDER.R", [0.5, 0.0, 2.15], [1.17, -0.01, 2.15], "CHEST", True),
        ("UPPER_ARM.R", [1.17, -0.01, 2.15], [1.31, -0.02, 1.62], "SHOULDER.R", True),
        ("FOREARM.R", [1.31, -0.02, 1.62], [1.26, -0.04, 1.18], "UPPER_ARM.R", True),
        ("WRIST.R", [1.26, -0.04, 1.18], [1.24, -0.05, 0.95], "FOREARM.R", True),
        ("HAND.R", [1.24, -0.05, 0.95], [1.24, -0.05, 0.75], "WRIST.R", True),

        # Left Leg
        ("THIGH.L", [-0.565, 0.015, 0.8], [-0.57, 0.01, 0.5], "PELVIS", True),
        ("SHIN.L", [-0.57, 0.01, 0.5], [-0.57, -0.04, 0.22], "THIGH.L", True),
        ("ANKLE.L", [-0.57, -0.04, 0.22], [-0.57, -0.15, 0.08], "SHIN.L", True),
        ("FOOT.L", [-0.57, -0.15, 0.08], [-0.57, -0.45, 0.05], "ANKLE.L", True),

        # Right Leg (Symmetric)
        ("THIGH.R", [0.565, 0.015, 0.8], [0.57, 0.01, 0.5], "PELVIS", True),
        ("SHIN.R", [0.57, 0.01, 0.5], [0.57, -0.04, 0.22], "THIGH.R", True),
        ("ANKLE.R", [0.57, -0.04, 0.22], [0.57, -0.15, 0.08], "SHIN.R", True),
        ("FOOT.R", [0.57, -0.15, 0.08], [0.57, -0.45, 0.05], "ANKLE.R", True),

        # Helper / IK Target Bones
        ("HAND_IK.L", [-1.24, -0.05, 0.75], [-1.24, -0.05, 0.55], "ROOT", False),
        ("HAND_IK.R", [1.24, -0.05, 0.75], [1.24, -0.05, 0.55], "ROOT", False),
        ("ELBOW_POLE.L", [-1.31, 1.0, 1.62], [-1.31, 1.2, 1.62], "CHEST", False),
        ("ELBOW_POLE.R", [1.31, 1.0, 1.62], [1.31, 1.2, 1.62], "CHEST", False),
        ("FOOT_IK.L", [-0.57, -0.15, 0.08], [-0.57, -0.15, 0.28], "ROOT", False),
        ("FOOT_IK.R", [0.57, -0.15, 0.08], [0.57, -0.15, 0.28], "ROOT", False),
        ("KNEE_POLE.L", [-0.57, -1.0, 0.5], [-0.57, -1.2, 0.5], "FOOT_IK.L", False),
        ("KNEE_POLE.R", [0.57, -1.0, 0.5], [0.57, -1.2, 0.5], "FOOT_IK.R", False),
    ]

    edit_bones = arm_data.edit_bones

    for name, head, tail, parent_name, is_deform in bone_defs:
        b = edit_bones.new(name)
        b.head = mathutils.Vector(head)
        b.tail = mathutils.Vector(tail)
        b.use_deform = is_deform

    for name, head, tail, parent_name, is_deform in bone_defs:
        if parent_name:
            edit_bones[name].parent = edit_bones[parent_name]

    bpy.ops.object.mode_set(mode='POSE')

    # Add IK constraints
    pose_bones = arm_obj.pose.bones

    # Arm IK Left
    ik_arm_l = pose_bones["FOREARM.L"].constraints.new(type='IK')
    ik_arm_l.target = arm_obj
    ik_arm_l.subtarget = "HAND_IK.L"
    ik_arm_l.pole_target = arm_obj
    ik_arm_l.pole_subtarget = "ELBOW_POLE.L"
    ik_arm_l.chain_count = 2

    # Arm IK Right
    ik_arm_r = pose_bones["FOREARM.R"].constraints.new(type='IK')
    ik_arm_r.target = arm_obj
    ik_arm_r.subtarget = "HAND_IK.R"
    ik_arm_r.pole_target = arm_obj
    ik_arm_r.pole_subtarget = "ELBOW_POLE.R"
    ik_arm_r.chain_count = 2

    # Leg IK Left
    ik_leg_l = pose_bones["SHIN.L"].constraints.new(type='IK')
    ik_leg_l.target = arm_obj
    ik_leg_l.subtarget = "FOOT_IK.L"
    ik_leg_l.pole_target = arm_obj
    ik_leg_l.pole_subtarget = "KNEE_POLE.L"
    ik_leg_l.chain_count = 2

    # Leg IK Right
    ik_leg_r = pose_bones["SHIN.R"].constraints.new(type='IK')
    ik_leg_r.target = arm_obj
    ik_leg_r.subtarget = "FOOT_IK.R"
    ik_leg_r.pole_target = arm_obj
    ik_leg_r.pole_subtarget = "KNEE_POLE.R"
    ik_leg_r.chain_count = 2

    bpy.ops.object.mode_set(mode='OBJECT')

    # Object-to-Bone Parent Mapping
    parent_map = {
        # Head / Face
        "EYE.LEFT_LENS": "HEAD",
        "EYE.LEFT_SOCKET": "HEAD",
        "EYE.LEFT_SPIRAL": "HEAD",
        "EYE.RIGHT_LENS": "HEAD",
        "EYE.RIGHT_SOCKET": "HEAD",
        "EYE.RIGHT_SPIRAL": "HEAD",
        "EYE.TOP_LENS": "HEAD",
        "EYE.TOP_SOCKET": "HEAD",
        "EYE.TOP_SPIRAL": "HEAD",
        "MOUTH_GROOVE": "HEAD",
        "HORN_BASE_L": "HEAD",
        "HORN_BASE_R": "HEAD",
        "HORN_L": "HEAD",
        "HORN_R": "HEAD",

        # Torso / Body accessories
        "BODY_SPIRAL": "CHEST",
        "BACK_NUB": "SPINE",
        "LOWER_VOLUME": "PELVIS",

        # Left Arm
        "SHOULDER_L": "SHOULDER.L",
        "UPPER_ARM_L": "UPPER_ARM.L",
        "UPPER_ARM_L_A_CAP": "UPPER_ARM.L",
        "UPPER_ARM_L_B_CAP": "UPPER_ARM.L",
        "ELBOW_L": "FOREARM.L",
        "FOREARM_L": "FOREARM.L",
        "FOREARM_L_A_CAP": "FOREARM.L",
        "FOREARM_L_B_CAP": "FOREARM.L",
        "WRIST_L": "WRIST.L",
        "HAND_L_WRIST_PAD": "WRIST.L",
        "HAND_L_PALM": "HAND.L",
        "HAND_L_FINGER_0": "HAND.L",
        "HAND_L_FINGER_1": "HAND.L",
        "HAND_L_FINGER_2": "HAND.L",
        "HAND_L_THUMB": "HAND.L",

        # Right Arm
        "SHOULDER_R": "SHOULDER.R",
        "UPPER_ARM_R": "UPPER_ARM.R",
        "UPPER_ARM_R_A_CAP": "UPPER_ARM.R",
        "UPPER_ARM_R_B_CAP": "UPPER_ARM.R",
        "ELBOW_R": "FOREARM.R",
        "FOREARM_R": "FOREARM.R",
        "FOREARM_R_A_CAP": "FOREARM.R",
        "FOREARM_R_B_CAP": "FOREARM.R",
        "WRIST_R": "WRIST.R",
        "HAND_R_WRIST_PAD": "WRIST.R",
        "HAND_R_PALM": "HAND.R",
        "HAND_R_FINGER_0": "HAND.R",
        "HAND_R_FINGER_1": "HAND.R",
        "HAND_R_FINGER_2": "HAND.R",
        "HAND_R_THUMB": "HAND.R",

        # Left Leg
        "THIGH_L": "THIGH.L",
        "THIGH_L_A_CAP": "THIGH.L",
        "THIGH_L_B_CAP": "THIGH.L",
        "KNEE_L": "SHIN.L",
        "CALF_L": "SHIN.L",
        "CALF_L_A_CAP": "SHIN.L",
        "CALF_L_B_CAP": "SHIN.L",
        "ANKLE_L": "ANKLE.L",
        "FOOT_L": "FOOT.L",
        "TOE_L": "FOOT.L",

        # Right Leg
        "THIGH_R": "THIGH.R",
        "THIGH_R_A_CAP": "THIGH.R",
        "THIGH_R_B_CAP": "THIGH.R",
        "KNEE_R": "SHIN.R",
        "CALF_R": "SHIN.R",
        "CALF_R_A_CAP": "SHIN.R",
        "CALF_R_B_CAP": "SHIN.R",
        "ANKLE_R": "ANKLE.R",
        "FOOT_R": "FOOT.R",
        "TOE_R": "FOOT.R",
    }

    for obj_name, bone_name in parent_map.items():
        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]
            matrix_world = obj.matrix_world.copy()
            obj.parent = arm_obj
            obj.parent_type = 'BONE'
            obj.parent_bone = bone_name
            obj.matrix_world = matrix_world

    # Handle BODY_CORE mesh deformation skinning
    if "BODY_CORE" in bpy.data.objects:
        body_core = bpy.data.objects["BODY_CORE"]
        # Skin BODY_CORE via vertex weights to PELVIS, SPINE, CHEST, NECK, HEAD
        # Group vertices by Z height
        vgroups = {
            "HEAD": body_core.vertex_groups.new(name="HEAD"),
            "NECK": body_core.vertex_groups.new(name="NECK"),
            "CHEST": body_core.vertex_groups.new(name="CHEST"),
            "SPINE": body_core.vertex_groups.new(name="SPINE"),
            "PELVIS": body_core.vertex_groups.new(name="PELVIS"),
        }
        
        for v in body_core.data.vertices:
            w_coord = body_core.matrix_world @ v.co
            z = w_coord.z
            if z >= 2.4:
                vgroups["HEAD"].add([v.index], 1.0, 'REPLACE')
            elif z >= 2.0:
                vgroups["NECK"].add([v.index], 1.0, 'REPLACE')
            elif z >= 1.6:
                vgroups["CHEST"].add([v.index], 1.0, 'REPLACE')
            elif z >= 1.0:
                vgroups["SPINE"].add([v.index], 1.0, 'REPLACE')
            else:
                vgroups["PELVIS"].add([v.index], 1.0, 'REPLACE')
                
        mod = body_core.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = arm_obj

    # Save to NEW file: rangga_rig_v1.blend
    bpy.ops.wm.save_as_mainfile(filepath="rangga_rig_v1.blend")
    print("=== RIG BUILD COMPLETED: rangga_rig_v1.blend ===")

if __name__ == "__main__":
    build_rig()
