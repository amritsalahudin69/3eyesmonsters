# TSA 3D Monster — Current State

## Current Pilot

**ALIF**

## Iteration Status

- Iteration 1: **PASS / TRUSTED** — canonical visual baseline accepted.
- Old Iteration 2: **INVALID** — visual displacement/separation versus Iteration 1.
- Old Iteration 3: **INVALID** — derived from invalid Iteration 2.
- Old Iteration 4: **CANCELED / NOT USED**.
- Iteration 2R: **PASS** — clone-only internal armature; all pre-existing transforms, parents, origins, mesh geometry, and six neutral renders remained identical.
- Iteration 3R: **BLOCKED — TOPOLOGY_LIMITATION** — both canonical leg meshes have zero vertices in the knee blend zone and a `0.38` longitudinal topology gap. The gate stopped before binding; the Iteration 3R copy remains byte-identical to Iteration 2R.
- Iteration 3R-A: **PASS** — symmetric local knee topology added only to `LEG_L_SUIT` and `LEG_R_SUIT`; knee-band spacing is now `0.03`, original vertices and canonical silhouette remain preserved, and no binding was performed.
- Iteration 3R-B: **BLOCKED — DEFORMATION_QUALITY_LIMIT** — deterministic manual binding preserves the neutral visual master and enables FK response, but elbow 90° and knee 45°/90° fail the edge-deformation gate. Elbow 90° reaches `p99 ≈ 2.45`; knee 45° reaches `p01 ≈ 0.196` and `p99 ≈ 3.40`; knee 90° reaches `p99 ≈ 5.83`. Render evidence also shows unacceptable elbow folding/ballooning and knee distortion. No topology was changed in 3R-B.
- Restart Iteration 4R: **BLOCKED — BASIC_JUMP_POSE_LIMIT** — neutral copy and static FK proofs were validated without mesh, weight, or armature-architecture edits. Numeric deformation and interpolation checks pass, but visual review shows CROUCH and JUMP_ANTICIPATION do not read clearly as a compressed/loading pose within the conservative knee envelope (SHIN flexion capped at 10°; 15° fails the supporting p01 gate). The safe envelope remains provisional where visual range coverage is incomplete. No Actions, keyframes, IK, constraints, or exports were created.

## Canonical Sources

- Input: `C:\Users\HWI-ADMIN\alif_output_v1\alif_v1.blend`
- WSL input: `/mnt/c/Users/HWI-ADMIN/alif_output_v1/alif_v1.blend`
- Visual references: `tsa/alif/iteration01/validation/`

## Current Trusted Artifact

`tsa/alif/restart/iteration03A/alif_topology_v1.blend`

## Current Blocker / Next Allowed Action

Iteration 4R remains blocked at `BASIC_JUMP_POSE_LIMIT`. Do not advance to Iteration 5R. The Iteration 4 working copy is a neutral proof artifact only; Iteration 3R-B remains blocked and is not promoted as a trusted source. Any further pose work must first resolve the crouch/jump-anticipation readability blocker within validated deformation limits.

## Current Rules

No reconstruction; unapproved topology changes; origin/mesh/hierarchy changes; automatic weights; robot joints; motion; IK; constraints; drivers; actions; keyframes; or use of invalid old Iteration 2/3 assets. Do not treat the blocked 3R-B derivative as an accepted source.
