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

## Canonical Sources

- Input: `C:\Users\HWI-ADMIN\alif_output_v1\alif_v1.blend`
- WSL input: `/mnt/c/Users/HWI-ADMIN/alif_output_v1/alif_v1.blend`
- Visual references: `tsa/alif/iteration01/validation/`

## Current Trusted Artifact

`tsa/alif/restart/iteration03A/alif_topology_v1.blend`

## Current Blocker / Next Allowed Action

Iteration 3R-B remains blocked. Next action requires an explicitly approved corrective iteration for elbow/knee deformation architecture; Iteration 4R is not allowed.

## Current Rules

No reconstruction; unapproved topology changes; origin/mesh/hierarchy changes; automatic weights; robot joints; motion; IK; constraints; drivers; actions; keyframes; or use of invalid old Iteration 2/3 assets. Do not treat the blocked 3R-B derivative as an accepted source.
