# Collar-preserving height, placement, and hand collision

The pre-change freeze-fix checkpoint is `6c73e5c`, pushed to
`feat/policy-learning-env`. It retains the enlarged shirt and old wrist spheres.
The following working changes are intentionally separate from that checkpoint.

## Shirt

- `SHIRT_HEIGHT_SCALE=0.8333333333333334` reduces overall raw-Y height by 10/12.
- After the existing uniform/collar resizing, the collar and adjacent vertex ring
  are fixed. Only coordinates below that band are compressed toward it.
- Width, depth, collar shape, and collar area are unchanged by this height edit.
- Existing surface-area mass normalization is recomputed for the new surface.
  This retains mass handling; identical FEM response is not claimed after a
  deliberate rest-shape change.
- `./run.sh prepare` regenerates both full and cropped shirt assets. Existing
  generated files and an already-running GUI do not update merely from editing JSON.

## Placement

Restore only the relevant helpers from historical commit `91107e2`, not its
policy/sensor framework or its older contact guard.

- Human and chair share a rigid offset uniformly sampled in a 10 cm disk and a
  yaw sampled within +/-30 degrees, applied after posing/collider construction
  and before world-space contact data is initialized.
- The blue shirt chooses one of the four unchanged support tables uniformly.
- Robot/table positions, shirt yaw, and dimensions are not randomized.
- `STRETCH4_RANDOMIZE=0` or `./run.sh gui --no-randomization` disables both.
- `HUMAN_SPAWN_SEED` and `STRETCH4_GARMENT_SPAWN_SEED` permit reproducible placement.
- New F-slots include human/chair transforms and a geometry revision. Mismatching
  or pre-change slots are rejected before mutating the scene; old files survive.

## Measured hand mismatch

The actual saved GUI visual points and contact-guard geometry were compared,
not the unposed asset or skeletal joint positions. Reconstruction of the body
including its existing 3 mm collision skin agrees within 1.211e-7 m.

| Hand | Visual vertices outside old sphere | Maximum protrusion |
| --- | ---: | ---: |
| Left | 98.0794% | 91.9213 mm |
| Right | 97.3008% | 84.9095 mm |

The existing spheres fit the cut wrist seam, not the full visible hand. The new
default `fitted` mode builds a closed convex hull from each posed hand and its
forearm cut seam, with 2 mm seam overlap and <=1 mm vertex expansion. This keeps
the original arm length and visible points, while closing gaps between fingers.
It is a smooth mitten-like collision approximation, not independent fingers.

Native convex collision uses a 256-vertex cooking limit and the guard receives
the authored hull faces in world space. Collider visualization displays those
same authored hulls. Legacy `sphere` mode remains available for comparison.

Local measurement artifacts live in
`~/PhyRC_diagnostics/head_freeze_u2hIuWWo/hand_alignment_*_20260911.json`.
The baseline measurement is completed. Any fitted-shape or GUI verification is
reported separately; the freeze checkpoint's native-FEM tests do not automatically
validate this changed geometry. Existing smoke tests were not rewritten.
