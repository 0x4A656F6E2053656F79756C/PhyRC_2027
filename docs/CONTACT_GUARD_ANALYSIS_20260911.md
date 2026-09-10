# Contact-guard exit analysis and 90% motion rates

Date: 2026-09-11 (KST).

## Scope and current runtime

The user requested changing the earlier 20% motion slowdown to a 10%
slowdown, and analysis of persistent cloth fallback and F-slot settings.

Source and matching runtime defaults now use 90% of the original motion
rates, rather than 80%. This is a 12.5% increase relative to the preceding
80% defaults. Base acceleration was adjusted proportionally as before.

| Setting | New default |
| --- | ---: |
| LIFT_RATE | 1.26 |
| ARM_RATE | 0.99 |
| WRIST_RATE | 4.5 |
| BASE_LINEAR_RATE | 0.504 |
| BASE_ANGULAR_RATE | 2.34 |
| BASE_LINEAR_ACCEL | 1.08 |
| BASE_ANGULAR_ACCEL | 3.6 |

GARMENT_SOLVER_ITERATIONS remains 64. The tightened compliance thresholds
remain 0.315/0.45 and 0.495/0.72. Environment overrides retain precedence.

The active GUI was NOT restarted or hot-patched. It still uses its
startup 80% defaults. Loading an F-slot does not reload Python constants.
The new 90% defaults require a new process. No execution test of the 90%
defaults was performed. No guard, geometry, material, driver, container
installation, or F-slot file was changed. No commit or push was made.

## Evidence and correction to the earlier explanation

Evidence root on this workstation:
`/home/seoyul/PhyRC_diagnostics/head_freeze_u2hIuWWo`.

Examined full per-iteration captures:

- `live_failure_20260911_013102/event_0001_fallback_onset`, step 6149,
  solver 64, robot 2 holding.
- `live_failure_20260911_013102/event_0004_user_marker`, step 7341,
  solver 64, both grippers released.
- `live_failure_20260911_012120/event_0001_fallback_onset`, step 3873,
  solver 32, robot 2 holding.

The summary `cut_count` is a count BEFORE that iteration's repair, not a
count of residual intersections AFTER its repair. The earlier statement
that five crossings remained after all 16 repairs was therefore too strong.

The source confirms this exit-condition defect in both implementations:

1. `_GpuSweep._iteration` counts crossings, then performs `_repair`.
2. `_advance_iteration` reads the unchanged, pre-repair count.
3. On attempt 16, any positive pre-repair count sets `fallback = 1`.
4. `_fallback` discards the entire result and zeros every cloth velocity.
5. There is no intersection check of the last repaired result before this
   fallback. The host-driven `for attempt in range(16)` / `else` path has
   the same missing final check.

Consequently, success on repair 16 is indistinguishable from failure at
the exit condition. This is distinct from PhysX FEM solver iterations.

## Independent geometry analysis

CPU-only NumPy/SciPy analysis used the captured body and cloth topology,
full start/candidate arrays, and intermediate arrays after each repair.
No SimulationApp was started and the interactive scene was not changed.

| Capture | Recorded count before repair 16 | Independent count before repair 16 | Independent count after repair 16 |
| --- | ---: | ---: | ---: |
| Solver 64 onset | 5 | 5 | 0 |
| Solver 64, released | 5 | 5 | 0 |
| Solver 32 onset | 9 | 9 | 2 |

Counts in the independent columns are unique intersecting cloth edges
plus unique intersecting body edges. They are not a count of distinct
physical contact points. All three starting surfaces had zero detected
edge/face intersections in this independent check.

Continuing the captured local-rejection process, rather than restarting
FEM, gave the following bounded, independent results:

- Solver 64 onset: check 17 already clear; 44 blocked nodes, 15,902 other
  nodes retain their locally repaired displacement.
- Solver 64 released: check 17 already clear; 42 blocked nodes, 15,904
  other nodes retain their locally repaired displacement.
- Solver 32 onset: two crossings at check 17; one more local rejection
  expands the blocked set from 48 to 50 nodes; check 18 is clear.

This supports a missing-final-check problem in the two solver-64
snapshots and insufficient local-rejection budget in the solver-32
snapshot. It does NOT establish successful continued dressing after a
patch, or guarantee the same thresholds for all poses.

The independent detector uses float64 segment/triangle tests, enumerates
intersections, and uses a normalized endpoint epsilon. Production Warp
uses float32 nearest-ray-hit queries and an absolute 1e-6 meter endpoint
epsilon. The matching last pre-repair counts are useful cross-checks,
not proof of bit-identical detectors. The final repaired positions still
need rechecking with the production GPU detector before a release fix.

Detailed numeric output is saved outside the repository at:
`contact_exit_analysis_20260911_90pct.json` under the evidence root.
The exploratory `MOTION` output's `candidate_mm` label was incorrect:
its values were meters. Subsequent explicit `_MM` output multiplied by
1000. The JSON records displacement values in meters.

## Why local repair reaches the limit

The first eight attempts perform contact displacement and node sweeps;
the next eight return cumulatively blocked nodes to their start positions.
Moving individual nodes back changes adjacent edges and triangles, so
locally rejecting motion can create new crossings at the boundary between
reverted and unreverted nodes. The blocked region then expands.

Recorded examples show this is not merely an unexecuted protection loop:

- Solver 64 onset: counts before attempts 9-16 are
  `18,16,21,17,17,7,9,5`; blocked nodes expand from 17 to 44.
- Solver 32 onset: counts before attempts 9-16 are
  `11,11,32,31,27,8,8,9`; blocked nodes expand from 14 to 48.
- In the solver-32 first eight attempts, the correction approaches
  numerical stagnation while the intersection count stays at 11.

The final entire-cloth fallback discards progress outside that small
blocked region as well. Only cloth state is reverted; robot state and
targets are not transactionally reverted with it. Repeated rejection can
therefore separate the moving gripper from the cloth after PhysX has
computed its attachment response.

## Speed, repetition, and rollback depth

On the solver-64 failure step, recorded robot-2 grasp displacement from
the preceding physics step was approximately 0.0954 mm. The preceding
11 displacements ranged up to 3.87 mm per step. On the solver-32 failure
step it was approximately 2.89 mm. These are actual grasp displacements,
not the command-rate defaults.

The cloth candidate entering the guard differed from its start by up to
80.8 mm in the solver-64 onset and 78.9 mm after release. These candidate
displacements are not a measurement of robot speed or of unmodified FEM
motion alone. Stored deformation, solver response, and preceding contact
processing can also contribute.

After both grips are released, the local failure persists with only
micrometer-scale robot displacement. Slowing the robot may reduce the
chance of entering difficult contact configurations, but continuing
robot commands are not necessary to sustain this recorded failure.
Its initiating cause is not established by the speed observation alone.

The fallback returns exactly one physics step's cloth start and zeroes
velocity. It is not a return to an older stable checkpoint. A geometrically
non-intersecting start can still produce a new conflicting candidate due
to its deformation/contact response. Repeating the same rollback can
therefore keep the cloth stuck even without a grip.

The onset and released captures do NOT have globally identical starting
arrays: their largest coordinate difference is approximately 18.55 mm.
Do not claim that every intervening step was fully frozen from the very
first fallback. The recorder confirms sustained episodes rather than
requiring fallback on every intermediate physics step.

Simply multiplying a backward displacement is not a safe recovery rule.
It can create new intersections and attachment inconsistency. An older
checkpoint would need matching robot pose/velocity/targets and attachment
state, followed by revalidation. Existing F-slots are not complete PhysX
solver-history snapshots.

## Parameter and patch recommendation (not applied)

1. Add a final intersection recheck after the last repair, before declaring
   fallback. Do not accept residual intersections merely to unfreeze cloth.
2. Make the guard budget configurable and compare 16/24/32 with early
   termination. The independent 17/18-check results justify this test,
   not a universal guarantee. The current 16 and 8 limits are hard-coded,
   not controlled by GARMENT_SOLVER_ITERATIONS.
3. If real residual crossings remain, evaluate smaller physical steps or
   validated adaptive candidate reduction, and couple failure handling to
   robot commands/targets so cloth-only rollback does not grow the anchor
   error. Keep this separate from the narrow exit-condition fix.
4. Use a jointly consistent older-state recovery only as a bounded last
   resort, rather than an arbitrary larger cloth-only displacement.

Increasing FEM iterations or reducing step size can improve deformable
solver convergence generally, but does not fix this custom guard's exit
condition. NVIDIA's primary documentation for the underlying solver is
[PhysX deformable surfaces](https://nvidia-omniverse.github.io/PhysX/physx/5.7.0/docs/DeformableSurface.html).

## F-slot settings versus saved dynamic state

`save_state_slot` / `load_state_slot` in
`src/DexGarmentLab/Env_StandAlone/Teleop_TShirt_Stretch4_Env.py` save and
restore cloth positions/velocities, robot pose and joint state, controller
position targets, gripper state, grasp node indices/offsets, and camera.
The startup fixture's NPZ fields were inspected as well.

They do NOT restore solver iteration counts, motion-rate constants,
compliance thresholds, material parameters, or cloth rest shape. Loading
a slot saved under solver 32 into a GUI started with solver 64 does not
reset the solver to 32. Likewise it does not revert a new speed default.

However, saved cloth and joint velocities are restored, while base
velocities and command ramps are deliberately zeroed. Loading is not a
fully static start. Old poses, deformation, and grasp offsets can produce
different transients under a new material, rest shape, or control law.

Load clears the guard cache, native attachments, and compliance/base-drive
history, restores states, and rebuilds attachments with synchronized FK.
It does not restore complete contact/solver internals, so loading a frozen
NPZ need not reproduce a live freeze.

The loader rejects a saved shirt with detected human intersections and
skips incompatible array shapes. Equal vertex counts do NOT certify that
an older save is semantically compatible with a changed rest shape or
vertex ordering. Such compatibility needs more than the current shape
checks. This is a residual risk, not evidence that old solver settings
were silently loaded in the present incident.
