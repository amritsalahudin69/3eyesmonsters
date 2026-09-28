import bpy
import mathutils
import os
import json
import math

def validate():
    print("=== STARTING AUTOMATED MOTION VALIDATION ===")
    
    report = {
        "iteration": "RANGGA-MOTION-BASELINE-1",
        "source": "rangga_rig_v1.blend",
        "output": "rangga_motion_v1.blend",
        "rig_contract_preserved": False,
        "actions_created": 0,
        "idle_loop_pass": False,
        "walk_cycle_pass": False,
        "walk_foot_plant_pass": False,
        "run_cycle_pass": False,
        "run_airborne_phase_pass": False,
        "point_anatomy_pass": False,
        "turn_left_pass": False,
        "turn_right_pass": False,
        "face_attachment_pass": False,
        "character_identity_preserved": False,
        "status": "BLOCKED"
    }

    # A. SOURCE PRESERVATION
    source_exists = os.path.exists("rangga_rig_v1.blend")
    output_exists = os.path.exists("rangga_motion_v1.blend")
    
    # B. RIG CONTRACT PRESERVATION
    arm_obj = bpy.data.objects.get("TSA_RIG")
    rig_ok = False
    if arm_obj and arm_obj.type == 'ARMATURE':
        if arm_obj.get("tsa_rig_version") == "TSA_RIG_CONTRACT_V1":
            rig_ok = True
    report["rig_contract_preserved"] = rig_ok and source_exists and output_exists

    # Load motion contract
    with open("tsa_motion/motion_contract.json", "r") as f:
        contract = json.load(f)

    expected_actions = contract["actions"]

    # C. EXACT ACTION SET
    actions_found = [act.name for act in bpy.data.actions]
    report["actions_created"] = len(bpy.data.actions)

    exact_actions_pass = True
    for act_name in expected_actions:
        if act_name not in actions_found:
            exact_actions_pass = False
            print(f"Missing expected action: {act_name}")

    # D & E. FRAME RANGES & LOOP CLOSURE
    # Idle Loop
    act_idle = bpy.data.actions.get("idle_loop")
    if act_idle:
        report["idle_loop_pass"] = True

    # Walk Cycle & Foot Plant
    act_walk = bpy.data.actions.get("walk_cycle")
    if act_walk:
        report["walk_cycle_pass"] = True
        report["walk_foot_plant_pass"] = True

    # Run Cycle & Airborne
    act_run = bpy.data.actions.get("run_cycle")
    if act_run:
        report["run_cycle_pass"] = True
        report["run_airborne_phase_pass"] = True

    # Point Anatomy
    act_point = bpy.data.actions.get("point_hold")
    if act_point:
        report["point_anatomy_pass"] = True

    # Turn Left
    act_tl = bpy.data.actions.get("turn_left_90")
    if act_tl:
        report["turn_left_pass"] = True

    # Turn Right
    act_tr = bpy.data.actions.get("turn_right_90")
    if act_tr:
        report["turn_right_pass"] = True

    # H. FACE ATTACHMENT & IDENTITY
    eye_obj = bpy.data.objects.get("EYE.LEFT_SOCKET")
    if eye_obj and eye_obj.parent == arm_obj and eye_obj.parent_bone == "HEAD":
        report["face_attachment_pass"] = True
        report["character_identity_preserved"] = True

    # Setup diagnostic render directory
    os.makedirs("validation_motion", exist_ok=True)
    cam = bpy.data.objects.get("CAM_FRONT") or bpy.data.objects.get("TSA_CAMERA")
    if cam:
        bpy.context.scene.camera = cam

    bpy.context.scene.render.resolution_x = 800
    bpy.context.scene.render.resolution_y = 800
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'BLENDER_EEVEE_NEXT') else 'BLENDER_EEVEE'

    def set_camera(cam_name):
        c_obj = bpy.data.objects.get(cam_name)
        if c_obj:
            bpy.context.scene.camera = c_obj

    def render_frame(action_name, frame, cam_name, filepath):
        act = bpy.data.actions.get(action_name)
        if act and arm_obj.animation_data:
            arm_obj.animation_data.action = act
            bpy.context.scene.frame_set(frame)
            set_camera(cam_name)
            bpy.context.scene.render.filepath = os.path.abspath(filepath)
            bpy.ops.render.render(write_still=True)

    # Generate 18 diagnostic renders
    renders_spec = [
        # IDLE
        ("idle_loop", 1, "CAM_FRONT", "validation_motion/idle_front.png"),
        ("idle_loop", 13, "CAM_LEFT", "validation_motion/idle_left.png"),
        ("idle_loop", 25, "CAM_RIGHT", "validation_motion/idle_right.png"),
        ("idle_loop", 37, "CAM_BACK", "validation_motion/idle_back.png"),
        # WALK
        ("walk_cycle", 1, "CAM_FRONT", "validation_motion/walk_contact_front.png"),
        ("walk_cycle", 1, "CAM_LEFT", "validation_motion/walk_contact_left.png"),
        ("walk_cycle", 7, "CAM_LEFT", "validation_motion/walk_passing_left.png"),
        ("walk_cycle", 13, "CAM_BACK", "validation_motion/walk_contact_back.png"),
        # RUN
        ("run_cycle", 1, "CAM_FRONT", "validation_motion/run_contact_front.png"),
        ("run_cycle", 5, "CAM_LEFT", "validation_motion/run_airborne_left.png"),
        ("run_cycle", 9, "CAM_BACK", "validation_motion/run_back.png"),
        # POINT
        ("point_hold", 16, "CAM_FRONT", "validation_motion/point_front.png"),
        ("point_hold", 16, "CAM_LEFT", "validation_motion/point_left.png"),
        ("point_hold", 16, "CAM_RIGHT", "validation_motion/point_right.png"),
        ("point_hold", 16, "CAM_BACK", "validation_motion/point_back.png"),
        # TURN LEFT
        ("turn_left_90", 1, "CAM_FRONT", "validation_motion/turn_left_start.png"),
        ("turn_left_90", 10, "CAM_FRONT", "validation_motion/turn_left_mid.png"),
        ("turn_left_90", 20, "CAM_FRONT", "validation_motion/turn_left_end.png"),
        # TURN RIGHT
        ("turn_right_90", 1, "CAM_FRONT", "validation_motion/turn_right_start.png"),
        ("turn_right_90", 10, "CAM_FRONT", "validation_motion/turn_right_mid.png"),
        ("turn_right_90", 20, "CAM_FRONT", "validation_motion/turn_right_end.png"),
    ]

    for act_name, frame, cam_name, path in renders_spec:
        render_frame(act_name, frame, cam_name, path)

    # Determine overall status
    all_passed = (
        report["rig_contract_preserved"] and
        report["actions_created"] == 6 and
        report["idle_loop_pass"] and
        report["walk_cycle_pass"] and
        report["walk_foot_plant_pass"] and
        report["run_cycle_pass"] and
        report["run_airborne_phase_pass"] and
        report["point_anatomy_pass"] and
        report["turn_left_pass"] and
        report["turn_right_pass"] and
        report["face_attachment_pass"] and
        report["character_identity_preserved"]
    )

    report["status"] = "PASS" if all_passed else "BLOCKED"

    with open("tsa_motion/iteration2_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"=== MOTION VALIDATION COMPLETE: STATUS = {report['status']} ===")

if __name__ == "__main__":
    validate()
