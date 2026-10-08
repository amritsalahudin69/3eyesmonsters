# TSA 3D Monster Canonical Knowledge

## Environment

- Agent: WSL Ubuntu 24.04
- Blender: Windows-native Blender 5.2
- Windows root: `C:\Users\HWI-ADMIN\Downloads\3d\`
- WSL root: `/mnt/c/Users/HWI-ADMIN/Downloads/3d/`
- Windows Blender: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
- WSL Blender path: `/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`

Never assume or install Linux Blender.

## Character Pilot and Visual Truth

Current pilot: **ALIF**. The visual source of truth is accepted Iteration 1 `alif_v1.blend`, resolved to `C:\Users\HWI-ADMIN\alif_output_v1\alif_v1.blend`. Canonical visual references are in `tsa/alif/iteration01/validation/`.

## Visual and Internal Anatomy

**VISIBLE FORM != INTERNAL ANATOMY.** No visible robot joints.

Arm: shoulder → upper arm → elbow → forearm → wrist → hand.

Leg: hip → thigh → knee → shin → ankle → foot.

Alif visual architecture includes `HEAD`, `NECK_BRIDGE`, `TORSO_UNDER`, `BELLY_CORE`, `SUIT_SHELL`, true suit tears, face details, arms/hands, and short legs/feet.

## Coordinate System

Front = `-Y`; up = `+Z`; symmetry = `X=0`.

## Invalidated Historical Chain

Visual audit proved old Iteration 2 structural preparation caused visible geometry displacement/separation. Old Iteration 3 inherited that state. Their former PASS statuses are revoked; neither output is a valid source. Old Iteration 4 is canceled and not trusted. Visual evidence overrides shallow boolean report claims.

## Canonical Derivative Rule

```text
ACCEPTED BLEND → FILE COPY → MODIFY COPY ONLY
```

Do not regenerate/reconstruct a visually accepted character from Python for rigging. The rig adapts to the character; the character does not adapt to the rig. Every derivative must compare its neutral render directly with accepted Iteration 1.

## Proven Clone-Only Rig Foundation

Iteration 2R proved that a 27-bone internal `ALIF_RIG` can be added to a byte-copy of accepted Iteration 1 without changing any pre-existing object transform, parent, origin, mesh geometry, or neutral render. Six direct reference comparisons had zero pixel difference. No binding, weights, IK, constraints, drivers, actions, or keyframes were introduced.

## Proven Alif Knee Topology Limitation

Restart Iteration 3R proved that both canonical `LEG_L_SUIT` and `LEG_R_SUIT` lack vertices in the internal knee blend zone around `Z=0.54 ± 0.06`. Each leg has zero vertices there and a maximum longitudinal topology gap of `0.38`. The accepted arm meshes have usable joint zones, but the current short-leg topology cannot support the required controlled knee deformation without an explicit topology change. Binding was therefore not performed.

## Proven Local Knee Topology Preparation

Restart Iteration 3R-A resolved the knee topology blocker with five symmetric local surface loops at offsets `-0.06`, `-0.03`, `0`, `+0.03`, and `+0.06` from the accepted knee center. Each leg now has 180 knee-band vertices with maximum longitudinal spacing `0.03`. Original vertices remained fixed, new vertices remained on the original polygon surface within `3.34e-8`, and no other mesh, transform, parent, bone, binding, or weight changed. Neutral silhouette remained visually identical.

## Proven Deformation Limitation

Restart Iteration 3R-B proved that deterministic two-influence linear skinning on the accepted 3R-A structure is not sufficient for the required articulation quality. Neutral identity, head independence, manual FK response, topology preservation, and source immutability pass, but elbow 90° exceeds the stretch gate (`p99 ≈ 2.45`) and knee bends fail at 45° (`p01 ≈ 0.196`, `p99 ≈ 3.40`) and 90° (`p99 ≈ 5.83`). Render evidence confirms unacceptable elbow folding/ballooning and knee distortion. This blocked result must not be promoted to an accepted rig source.
