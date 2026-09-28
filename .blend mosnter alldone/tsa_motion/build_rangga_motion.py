import bpy
import mathutils
import math

def create_motion_baseline():
    print("=== STARTING RANGGA MOTION BASELINE BUILD ===")
    
    # 1. Verify source rig exists
    arm_obj = bpy.data.objects.get("TSA_RIG")
    if not arm_obj or arm_obj.type != 'ARMATURE':
        raise Exception("TSA_RIG armature object not found in scene.")
        
    if arm_obj.get("tsa_rig_version") != "TSA_RIG_CONTRACT_V1":
        raise Exception("Armature does not meet TSA_RIG_CONTRACT_V1 metadata contract.")

    pb = arm_obj.pose.bones
    
    # Helper to insert keyframe on pose bone
    def keyframe_bone(action, bone_name, frame, loc=None, rot_euler=None):
        if bone_name not in pb:
            return
        pbone = pb[bone_name]
        pbone.rotation_mode = 'XYZ'
        
        if loc is not None:
            pbone.location = mathutils.Vector(loc)
            pbone.keyframe_insert(data_path="location", frame=frame)
            
        if rot_euler is not None:
            pbone.rotation_euler = mathutils.Euler([math.radians(r) for r in rot_euler], 'XYZ')
            pbone.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Clear existing animation data or actions
    if arm_obj.animation_data:
        arm_obj.animation_data.action = None

    # Define Actions specs
    actions_spec = {
        "idle_loop": (1, 48),
        "walk_cycle": (1, 24),
        "run_cycle": (1, 16),
        "point_hold": (1, 32),
        "turn_left_90": (1, 20),
        "turn_right_90": (1, 20)
    }

    # ----------------------------------------------------
    # BUILD ACTION 1: idle_loop (1..48)
    # ----------------------------------------------------
    act_idle = bpy.data.actions.new(name="idle_loop")
    act_idle.use_fake_user = True
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = act_idle

    # Reset rest pose
    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 & 48 (Neutral)
    for f in [1, 48]:
        keyframe_bone(act_idle, "COG", f, loc=(0, 0, 0), rot_euler=(0, 0, 0))
        keyframe_bone(act_idle, "CHEST", f, rot_euler=(0, 0, 0))
        keyframe_bone(act_idle, "HEAD", f, rot_euler=(0, 0, 0))
        keyframe_bone(act_idle, "HAND_IK.L", f, loc=(0, 0, 0))
        keyframe_bone(act_idle, "HAND_IK.R", f, loc=(0, 0, 0))

    # Frame 13 (Inhale / rise)
    keyframe_bone(act_idle, "COG", 13, loc=(0, 0, 0.025), rot_euler=(0, 0, 0))
    keyframe_bone(act_idle, "CHEST", 13, rot_euler=(-2, 0, 0))
    keyframe_bone(act_idle, "HEAD", 13, rot_euler=(1, 0, 0))
    keyframe_bone(act_idle, "HAND_IK.L", 13, loc=(0, 0, 0.015))
    keyframe_bone(act_idle, "HAND_IK.R", 13, loc=(0, 0, 0.015))

    # Frame 25 (Neutral crossing)
    keyframe_bone(act_idle, "COG", 25, loc=(0, 0, 0), rot_euler=(0, 0, 0))
    keyframe_bone(act_idle, "CHEST", 25, rot_euler=(0, 0, 0))
    keyframe_bone(act_idle, "HEAD", 25, rot_euler=(0, 0, 0))

    # Frame 37 (Exhale / lower)
    keyframe_bone(act_idle, "COG", 37, loc=(0, 0, -0.018), rot_euler=(0, 0, 0))
    keyframe_bone(act_idle, "CHEST", 37, rot_euler=(1.5, 0, 0))
    keyframe_bone(act_idle, "HEAD", 37, rot_euler=(-1, 0, 0))
    keyframe_bone(act_idle, "HAND_IK.L", 37, loc=(0, 0, -0.01))
    keyframe_bone(act_idle, "HAND_IK.R", 37, loc=(0, 0, -0.01))


    # ----------------------------------------------------
    # BUILD ACTION 2: walk_cycle (1..24, In-Place)
    # ----------------------------------------------------
    act_walk = bpy.data.actions.new(name="walk_cycle")
    act_walk.use_fake_user = True
    arm_obj.animation_data.action = act_walk

    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 & 24 (Left Contact)
    for f in [1, 24]:
        keyframe_bone(act_walk, "COG", f, loc=(0, 0, -0.02), rot_euler=(0, 0, 3))
        keyframe_bone(act_walk, "FOOT_IK.L", f, loc=(0, -0.28, 0.0))
        keyframe_bone(act_walk, "FOOT_IK.R", f, loc=(0, 0.22, 0.0))
        keyframe_bone(act_walk, "HAND_IK.L", f, loc=(0, 0.18, 0.05))
        keyframe_bone(act_walk, "HAND_IK.R", f, loc=(0, -0.18, 0.05))
        keyframe_bone(act_walk, "CHEST", f, rot_euler=(0, 0, -3))

    # Frame 4 (Down)
    keyframe_bone(act_walk, "COG", 4, loc=(0, 0, -0.05), rot_euler=(0, 0, 1))
    keyframe_bone(act_walk, "FOOT_IK.L", 4, loc=(0, -0.14, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.R", 4, loc=(0, 0.28, 0.05))

    # Frame 7 (Passing)
    keyframe_bone(act_walk, "COG", 7, loc=(0, 0, 0.01), rot_euler=(0, 0, 0))
    keyframe_bone(act_walk, "FOOT_IK.L", 7, loc=(0, 0.0, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.R", 7, loc=(0, 0.05, 0.12))
    keyframe_bone(act_walk, "HAND_IK.L", 7, loc=(0, 0.0, 0.0))
    keyframe_bone(act_walk, "HAND_IK.R", 7, loc=(0, 0.0, 0.0))

    # Frame 10 (Up)
    keyframe_bone(act_walk, "COG", 10, loc=(0, 0, 0.03), rot_euler=(0, 0, -2))
    keyframe_bone(act_walk, "FOOT_IK.L", 10, loc=(0, 0.14, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.R", 10, loc=(0, -0.15, 0.08))

    # Frame 13 (Right Contact)
    keyframe_bone(act_walk, "COG", 13, loc=(0, 0, -0.02), rot_euler=(0, 0, -3))
    keyframe_bone(act_walk, "FOOT_IK.L", 13, loc=(0, 0.22, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.R", 13, loc=(0, -0.28, 0.0))
    keyframe_bone(act_walk, "HAND_IK.L", 13, loc=(0, -0.18, 0.05))
    keyframe_bone(act_walk, "HAND_IK.R", 13, loc=(0, 0.18, 0.05))
    keyframe_bone(act_walk, "CHEST", 13, rot_euler=(0, 0, 3))

    # Frame 16 (Down)
    keyframe_bone(act_walk, "COG", 16, loc=(0, 0, -0.05), rot_euler=(0, 0, -1))
    keyframe_bone(act_walk, "FOOT_IK.R", 16, loc=(0, -0.14, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.L", 16, loc=(0, 0.28, 0.05))

    # Frame 19 (Passing)
    keyframe_bone(act_walk, "COG", 19, loc=(0, 0, 0.01), rot_euler=(0, 0, 0))
    keyframe_bone(act_walk, "FOOT_IK.R", 19, loc=(0, 0.0, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.L", 19, loc=(0, 0.05, 0.12))
    keyframe_bone(act_walk, "HAND_IK.L", 19, loc=(0, 0.0, 0.0))
    keyframe_bone(act_walk, "HAND_IK.R", 19, loc=(0, 0.0, 0.0))

    # Frame 22 (Up)
    keyframe_bone(act_walk, "COG", 22, loc=(0, 0, 0.03), rot_euler=(0, 0, 2))
    keyframe_bone(act_walk, "FOOT_IK.R", 22, loc=(0, 0.14, 0.0))
    keyframe_bone(act_walk, "FOOT_IK.L", 22, loc=(0, -0.15, 0.08))


    # ----------------------------------------------------
    # BUILD ACTION 3: run_cycle (1..16, In-Place)
    # ----------------------------------------------------
    act_run = bpy.data.actions.new(name="run_cycle")
    act_run.use_fake_user = True
    arm_obj.animation_data.action = act_run

    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 & 16 (Left Contact)
    for f in [1, 16]:
        keyframe_bone(act_run, "COG", f, loc=(0, 0, -0.04), rot_euler=(8, 0, 4))
        keyframe_bone(act_run, "FOOT_IK.L", f, loc=(0, -0.38, 0.0))
        keyframe_bone(act_run, "FOOT_IK.R", f, loc=(0, 0.32, 0.1))
        keyframe_bone(act_run, "HAND_IK.L", f, loc=(0, 0.28, 0.15))
        keyframe_bone(act_run, "HAND_IK.R", f, loc=(0, -0.32, 0.2))
        keyframe_bone(act_run, "CHEST", f, rot_euler=(0, 0, -4))

    # Frame 5 (Airborne Phase 1)
    keyframe_bone(act_run, "COG", 5, loc=(0, 0, 0.09), rot_euler=(6, 0, 0))
    keyframe_bone(act_run, "FOOT_IK.L", 5, loc=(0, -0.08, 0.16))
    keyframe_bone(act_run, "FOOT_IK.R", 5, loc=(0, 0.08, 0.24))

    # Frame 9 (Right Contact)
    keyframe_bone(act_run, "COG", 9, loc=(0, 0, -0.04), rot_euler=(8, 0, -4))
    keyframe_bone(act_run, "FOOT_IK.L", 9, loc=(0, 0.32, 0.1))
    keyframe_bone(act_run, "FOOT_IK.R", 9, loc=(0, -0.38, 0.0))
    keyframe_bone(act_run, "HAND_IK.L", 9, loc=(0, -0.32, 0.2))
    keyframe_bone(act_run, "HAND_IK.R", 9, loc=(0, 0.28, 0.15))
    keyframe_bone(act_run, "CHEST", 9, rot_euler=(0, 0, 4))

    # Frame 13 (Airborne Phase 2)
    keyframe_bone(act_run, "COG", 13, loc=(0, 0, 0.09), rot_euler=(6, 0, 0))
    keyframe_bone(act_run, "FOOT_IK.R", 13, loc=(0, -0.08, 0.16))
    keyframe_bone(act_run, "FOOT_IK.L", 13, loc=(0, 0.08, 0.24))


    # ----------------------------------------------------
    # BUILD ACTION 4: point_hold (1..32)
    # ----------------------------------------------------
    act_point = bpy.data.actions.new(name="point_hold")
    act_point.use_fake_user = True
    arm_obj.animation_data.action = act_point

    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 (Neutral)
    keyframe_bone(act_point, "HAND_IK.R", 1, loc=(0, 0, 0))
    keyframe_bone(act_point, "CHEST", 1, rot_euler=(0, 0, 0))
    keyframe_bone(act_point, "HEAD", 1, rot_euler=(0, 0, 0))

    # Frame 8 (Arm Lifting)
    keyframe_bone(act_point, "HAND_IK.R", 8, loc=(0, -0.25, 0.35))
    keyframe_bone(act_point, "CHEST", 8, rot_euler=(0, 0, -4))

    # Frame 16 (Point established)
    keyframe_bone(act_point, "HAND_IK.R", 16, loc=(0, -0.55, 0.65))
    keyframe_bone(act_point, "UPPER_ARM.R", 16, rot_euler=(-65, 0, 10))
    keyframe_bone(act_point, "FOREARM.R", 16, rot_euler=(15, 0, 0))
    keyframe_bone(act_point, "CHEST", 16, rot_euler=(0, 0, -10))
    keyframe_bone(act_point, "HEAD", 16, rot_euler=(0, 0, -12))

    # Frame 24 & 32 (Stable Hold)
    for f in [24, 32]:
        keyframe_bone(act_point, "HAND_IK.R", f, loc=(0, -0.55, 0.65))
        keyframe_bone(act_point, "UPPER_ARM.R", f, rot_euler=(-65, 0, 10))
        keyframe_bone(act_point, "FOREARM.R", f, rot_euler=(15, 0, 0))
        keyframe_bone(act_point, "CHEST", f, rot_euler=(0, 0, -10))
        keyframe_bone(act_point, "HEAD", f, rot_euler=(0, 0, -12))


    # ----------------------------------------------------
    # BUILD ACTION 5: turn_left_90 (1..20)
    # ----------------------------------------------------
    act_tl = bpy.data.actions.new(name="turn_left_90")
    act_tl.use_fake_user = True
    arm_obj.animation_data.action = act_tl

    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 (Front)
    keyframe_bone(act_tl, "ROOT", 1, rot_euler=(0, 0, 0))
    keyframe_bone(act_tl, "HEAD", 1, rot_euler=(0, 0, 0))
    keyframe_bone(act_tl, "CHEST", 1, rot_euler=(0, 0, 0))

    # Frame 4 (Head initiates)
    keyframe_bone(act_tl, "HEAD", 4, rot_euler=(0, 0, 22))

    # Frame 8 (Chest follows)
    keyframe_bone(act_tl, "HEAD", 8, rot_euler=(0, 0, 35))
    keyframe_bone(act_tl, "CHEST", 8, rot_euler=(0, 0, 30))
    keyframe_bone(act_tl, "FOOT_IK.R", 8, loc=(0, -0.05, 0.12), rot_euler=(0, 0, 25))

    # Frame 12 (ROOT & Pelvis turn)
    keyframe_bone(act_tl, "ROOT", 12, rot_euler=(0, 0, 60))
    keyframe_bone(act_tl, "CHEST", 12, rot_euler=(0, 0, 15))
    keyframe_bone(act_tl, "FOOT_IK.L", 12, loc=(0, 0.05, 0.1), rot_euler=(0, 0, 30))

    # Frame 16 (Settling)
    keyframe_bone(act_tl, "ROOT", 16, rot_euler=(0, 0, 85))
    keyframe_bone(act_tl, "HEAD", 16, rot_euler=(0, 0, 5))

    # Frame 20 (Full 90° turn)
    keyframe_bone(act_tl, "ROOT", 20, rot_euler=(0, 0, 90))
    keyframe_bone(act_tl, "HEAD", 20, rot_euler=(0, 0, 0))
    keyframe_bone(act_tl, "CHEST", 20, rot_euler=(0, 0, 0))
    keyframe_bone(act_tl, "FOOT_IK.L", 20, loc=(0, 0, 0), rot_euler=(0, 0, 0))
    keyframe_bone(act_tl, "FOOT_IK.R", 20, loc=(0, 0, 0), rot_euler=(0, 0, 0))


    # ----------------------------------------------------
    # BUILD ACTION 6: turn_right_90 (1..20)
    # ----------------------------------------------------
    act_tr = bpy.data.actions.new(name="turn_right_90")
    act_tr.use_fake_user = True
    arm_obj.animation_data.action = act_tr

    for pbone in pb:
        pbone.location = (0, 0, 0)
        pbone.rotation_euler = (0, 0, 0)

    # Frame 1 (Front)
    keyframe_bone(act_tr, "ROOT", 1, rot_euler=(0, 0, 0))
    keyframe_bone(act_tr, "HEAD", 1, rot_euler=(0, 0, 0))
    keyframe_bone(act_tr, "CHEST", 1, rot_euler=(0, 0, 0))

    # Frame 4 (Head initiates)
    keyframe_bone(act_tr, "HEAD", 4, rot_euler=(0, 0, -22))

    # Frame 8 (Chest follows)
    keyframe_bone(act_tr, "HEAD", 8, rot_euler=(0, 0, -35))
    keyframe_bone(act_tr, "CHEST", 8, rot_euler=(0, 0, -30))
    keyframe_bone(act_tr, "FOOT_IK.L", 8, loc=(0, -0.05, 0.12), rot_euler=(0, 0, -25))

    # Frame 12 (ROOT & Pelvis turn)
    keyframe_bone(act_tr, "ROOT", 12, rot_euler=(0, 0, -60))
    keyframe_bone(act_tr, "CHEST", 12, rot_euler=(0, 0, -15))
    keyframe_bone(act_tr, "FOOT_IK.R", 12, loc=(0, 0.05, 0.1), rot_euler=(0, 0, -30))

    # Frame 16 (Settling)
    keyframe_bone(act_tr, "ROOT", 16, rot_euler=(0, 0, -85))
    keyframe_bone(act_tr, "HEAD", 16, rot_euler=(0, 0, -5))

    # Frame 20 (Full 90° turn)
    keyframe_bone(act_tr, "ROOT", 20, rot_euler=(0, 0, -90))
    keyframe_bone(act_tr, "HEAD", 20, rot_euler=(0, 0, 0))
    keyframe_bone(act_tr, "CHEST", 20, rot_euler=(0, 0, 0))
    keyframe_bone(act_tr, "FOOT_IK.L", 20, loc=(0, 0, 0), rot_euler=(0, 0, 0))
    keyframe_bone(act_tr, "FOOT_IK.R", 20, loc=(0, 0, 0), rot_euler=(0, 0, 0))


    # Set default active action back to idle_loop
    arm_obj.animation_data.action = act_idle

    # Create Camera Presets
    cams_spec = {
        "CAM_FRONT": ([0.0, -7.5, 2.15], [90, 0, 0]),
        "CAM_LEFT": ([-7.5, 0.0, 2.15], [90, 0, -90]),
        "CAM_RIGHT": ([7.5, 0.0, 2.15], [90, 0, 90]),
        "CAM_BACK": ([0.0, 7.5, 2.15], [90, 0, 180]),
        "CAM_3Q_LEFT": ([-5.3, -5.3, 2.15], [90, 0, -45]),
        "CAM_3Q_RIGHT": ([5.3, -5.3, 2.15], [90, 0, 45]),
    }

    for cam_name, (loc, rot) in cams_spec.items():
        if cam_name not in bpy.data.objects:
            c_data = bpy.data.cameras.new(cam_name)
            c_obj = bpy.data.objects.new(cam_name, c_data)
            bpy.context.collection.objects.link(c_obj)
        else:
            c_obj = bpy.data.objects[cam_name]
        c_obj.location = mathutils.Vector(loc)
        c_obj.rotation_euler = mathutils.Euler([math.radians(r) for r in rot], 'XYZ')

    # Save to NEW output file: rangga_motion_v1.blend
    bpy.ops.wm.save_as_mainfile(filepath="rangga_motion_v1.blend")
    print("=== MOTION BASELINE BUILD COMPLETED: rangga_motion_v1.blend ===")

if __name__ == "__main__":
    create_motion_baseline()
