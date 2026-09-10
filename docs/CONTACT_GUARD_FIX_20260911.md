# Contact guard correction and head restoration (2026-09-11)

## Installed changes

- The contact guard now checks the result AFTER the final allowed repair.
  Previously both the CUDA-graph path and host-driven GPU loop could reject a
  successful last repair using the crossing count measured before that repair.
- Default repair budget: 24, configurable with
  `STRETCH4_CONTACT_GUARD_ITERATIONS` (1-128).
- There are at most N repairs and N+1 checks. The final check does not repair.
- The first eight contact corrections and subsequent local rejection algorithm
  are unchanged. Genuine unresolved intersections still trigger the full safe
  rollback. Collision protection was not disabled.
- Native FEM garment solver iterations remain 64. This is separate from the
  contact guard's 24-repair budget.
- Motion rates remain 90% of the earlier original rates: lift 1.26, arm 0.99,
  wrist 4.5, base linear 0.504, base angular 2.34, linear acceleration 1.08,
  angular acceleration 3.6. Existing environment overrides still take priority.
- Existing tightened compliance thresholds remain unchanged.
- Posterior-head rounding is applied to the visual mesh before the collision
  surface is built. No shirt dimensions, grasp-selection rules, robot models,
  or attachment-release rules were changed in this final correction.

Guard source SHA-256:
`29db8771451749dd349c9e4eeb24194c9da1fc569d76f511f4e5511c34265dde`

## Evidence and limits

The old guard reproduced the exact recorded whole-cloth rollback in all 36
GPU graph runs across three captured failure inputs. Merely adding the final
check resolved the two solver-64 captures. The solver-32 capture required one
additional local rejection. Budgets 24 and 32 resolved all three inputs in all
12 repetitions per input, with finite results and zero remaining intersections.

The full native-FEM tests used one initial checkpoint load, normal robot control
from recorded key intent, the original native attachments, and passive
diagnostic tracing. Cloth positions were not imposed each frame.

| Full-scene run | Head | Motion rates | Guard | Physics steps | Whole rollbacks |
| --- | --- | --- | --- | --- | --- |
| Reproduced failure | Original | 80% | Original 16 | 9760 | 5472 |
| Candidate | Rounded | 90% | Corrected 24 | 9760 | 0 |
| Matched legacy control | Rounded | 90% | Original 16 | 9760 | 0 |

The reproduced failure included 2559 consecutive frozen steps while holding
and 2912 consecutive frozen steps after both grippers were opened. All values
remained finite. This was a full-scene reproduction, not just a guard replay.

The two rounded runs had byte-identical starting checkpoints, collision bodies,
body triangles, cloth triangles, cloth edges and cloth rest points. Both used
the same release frames, 693 and 1713, and the same motion rates.

**Do not attribute the whole-scene improvement exclusively to the guard patch.**
The rounded-head/90%-speed legacy control also passed this particular sequence.
Head rounding removes some of the captured intersections. The final-check
defect is independently demonstrated by the fixed-input GPU comparisons.

These tests establish the reported reproduction and successful corrected
configuration for the tested sequence, not immunity to every possible contact
configuration. Native simulation trajectories were not bitwise identical
across fresh runs even with identical initial checkpoints and key intent.

## Head geometry

- 625 visual vertices changed; none outside the selected head-weight region.
- 773 collision vertices changed, all within the measured head-region bounds.
- Maximum collision-point displacement: approximately 43.99 mm.
- Body and cloth triangle topology remained identical.
- Rounded collision-body SHA-256:
  `7ae4f90eee8a0db8fba20f9982036641ee91db6914a1fe5c5f9da6568fdd0643`.

## Local evidence, not bundled installation assets

Audit root: `/home/seoyul/PhyRC_diagnostics/head_freeze_u2hIuWWo`.

- `goal_v3/traced_replay_v5_20260911_025635/report.json`: full failure.
- `goal_v3/traced_replay_v6_20260911_031300/report.json`: corrected rounded run.
- `goal_v3/traced_replay_v7_20260911_032839/report.json`: matched legacy control.
- `goal_v3/rounded_pair_geometry_and_trace.json`: geometry equality.
- `guard_gpu_v3_baseline/report.json`: exact captured GPU rollback reproduction.
- `guard_gpu_v3_candidate24_fresh/report.json`: corrected GPU regression.
- `goal_v3/rounded_collision_geometry_audit.json`: collision-point differences.
- `goal_v3/final_gui_checkpoint.tar`: latest original GUI/F-slot backup.
- `goal_v3/before_guard_install.tar`: source, runtime, manifest and handoff backup.
- `active_final_gui.json`: final GUI session pointer, runtime configuration and
  source hashes. Consult the actual container/process and session observations
  to establish whether it is still running.

The final diagnostic GUI uses a private copy of the original GUI's slots and
loads its latest backed-up F5 state. The earlier F5 and all original slots remain
in the backup. A checkpoint does not restore Python settings or PhysX internal
solver/contact history; loading one is not a deterministic full-engine replay.

The experimental `goal_v3/raw_pre_failure_seeds` files were NOT used in any
reported full-scene test. Their velocities precede the final 2 m/s production
cap and must not be treated as validated end-of-step checkpoints.

No Git commit, driver installation, Docker daemon restart or GPU reset was
performed for this correction.

