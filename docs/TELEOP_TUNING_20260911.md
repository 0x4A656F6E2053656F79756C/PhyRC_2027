> Update: motion rates now use 90% of the original defaults, not the 80% recorded below. See CONTACT_GUARD_ANALYSIS_20260911.md. Solver 64 and tightened compliance remain unchanged. The running diagnostic GUI has not been restarted.

# Teleop tuning, 2026-09-11

User-requested tuning during the intermittent cloth-freeze investigation.
This changes defaults in the maintained source and its runtime copies. Geometry
remains in the pre-head-edit configuration; this is no longer a byte-identical
pre-head source restoration. Existing environment overrides still take priority.

| Setting | Previous | New |
| --- | --- | --- |
| GARMENT_SOLVER_ITERATIONS | 32 | 64 |
| LIFT_RATE | 1.4 | 1.12 |
| ARM_RATE | 1.1 | 0.88 |
| WRIST_RATE | 5.0 | 4.0 |
| BASE_LINEAR_RATE | 0.56 | 0.448 |
| BASE_ANGULAR_RATE | 2.6 | 2.08 |
| BASE_LINEAR_ACCEL | 1.2 | 0.96 |
| BASE_ANGULAR_ACCEL | 4.0 | 3.2 |
| COMPLIANCE_START | 0.35 | 0.315 |
| COMPLIANCE_END | 0.50 | 0.45 |
| COMPLIANCE_LOCAL_START | 0.55 | 0.495 |
| COMPLIANCE_LOCAL | 0.80 | 0.72 |

Command rates and base acceleration limits are reduced by 20%. Scaling both
base rates and accelerations preserves their nominal ramp duration. The higher
solver count can additionally reduce wall-clock simulation throughput; it is
not a promise of exactly 20% slower perceived motion.

Strain-control thresholds are reduced by 10%, retaining the directional filter,
growth prediction and anti-windup formulas. Earlier reviewed motion presets had
the same rates as the previous defaults. This is an explicit new tuning, not a
claim to have recovered the exact session the user remembers.

Native attachment, cloth material, collision guard, physics frequency and
collision subiterations are unchanged. Lower thresholds can engage control
restriction earlier but do not fix the observed cloth-only full rollback or
guarantee a hard stop at every blocked contact. Continue recording/reproduction.

The previous code and recording are preserved outside the repository at:

`/home/seoyul/PhyRC_backups/20260911_012920_before_solver64_slow_tight/`

- `project-source-before.tar.gz`: source/config/scripts and the two runtime files.
- `live-recording.tar`: the complete earlier diagnostic recording directory.
- `live-before-tuning.npz`: the latest explicitly captured compatible state.
- `gui-before.log`: previous GUI log.

The detailed first failed-step recording is retained at
`/home/seoyul/PhyRC_diagnostics/head_freeze_u2hIuWWo/live_failure_20260911_012120/`.
The restarted diagnostic GUI uses a separate recording directory and its
pre-incident startup fixture, leaving the captured frozen states untouched.
No commit or push is part of this tuning request.
