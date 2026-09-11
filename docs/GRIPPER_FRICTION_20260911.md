# Gripper friction and preserved dressing stages — 2026-09-11

## Preserved user stages

Live container `happy_cori` was running the current geometry. A desktop capture
showed the mannequin wearing the blue shirt, with the grippers released.
F1–F5 were copied and SHA-256 verified in:

`/home/seoyul/PhyRC_backups/dressing_stages_20260911_155147/`

Each NPZ is read-only and independent of the GUI slot directory. Future F-key
saves and slot clearing do not affect these copies. `manifest.json` records
source paths, timestamps, sizes and hashes. `gui.png` records the observed scene.
All five NPZ files passed ZIP CRC checks; cloth positions were finite and all
used revision `20260911_neckfixed_shortheight_handfit_v1`, 15946 vertices.

| Stage | Robot 1 grasp | Robot 2 grasp |
| --- | --- | --- |
| F1 | none | none |
| F2 | held | held |
| F3 | none | held |
| F4 | none | held |
| F5 | none | none |

These are user-recorded states, not a measured motion replay or a universal
freeze regression. Copy preserved slots to a separate writable directory when
needed; never use the archive itself as `STRETCH4_STATE_DIR`. Startup overwrites
F1. Placement and geometry validation still apply. The original session's human
and chair placement must match when loading the slots.

## Friction change

The local historical `scripts/patch_slippery_cloth.py` in the original
`~/Documents/PhyRC_6.0.1/isaac-upgrade-docker` project explicitly changes
`GARMENT_FRICTION` from 0.2 to 0.0. We reused **0.2**, not the older 0.5/25 values.
This is the historical cloth coefficient; no separate historical finger-specific
coefficient was found.

The zero-scene pass is retained, followed by a finger material override:

- Eight enabled finger/fingertip colliders across the two robots: static/dynamic
  coefficient 0.2, rigid friction combine `max`.
- Cloth deformable material: dynamic coefficient 0.
- Human body and fitted hands: coefficient 0, combine `min`.
- Other rigid materials, grasp attachments, collision filtering and guard logic
  are unchanged. Finger materials govern their other permitted contacts too.

For rigid/FEM contact the rigid material's combine rule applies, so the requested
cloth/finger coefficient is max(0, 0.2) = 0.2. Cloth/human remains zero. The FEM
solver uses dynamic friction; authored static coefficients are not independently
simulated. See [NVIDIA material friction combine documentation](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/110.0/dev_guide/deformables/deformable_bodies.html#material-friction-combine-modes).

## Verification and rollback

`scripts/check_gripper_friction.py` runs a CPU USD test using the actual instanced
robot asset twice, plus human/table fixtures and a deformable material. It checks
all eight effective finger bindings, unchanged 52 other collider materials,
unchanged cloth friction, invalid coefficient rejection, reapplication and exact
zero-friction restoration. It passed. Run with GUI closed using
`./run.sh cpu /scripts/check_gripper_friction.py` and the usual EULA environment.

The current GUI received the same function through Script Editor, without a
restart or loading any F-slot. Only eight effective finger material bindings
changed; all live human bindings and the cloth coefficient were checked. Its
pre-change full state is `output/friction_trial_20260911/before_live/slot_LIVE.npz`.
Source/runtime copies are synchronized. There was no second GPU SimulationApp.

The initial session-only buttons were removed at the user's clarification:
rollback is a code change, and no extra GUI windows should be created. The
production source and runtime never included the panel. The local scripts that
created it have been retired; historical copies remain only in external backups.
The Script Editor extension was disabled before normal application shutdown.

For code rollback, change the environment fallback from `'0.2'` to `'0'` in
`Env_Config/Garment/ZeroSceneFriction.py` at the call to
`configure_gripper_cloth_friction`, then synchronize source to runtime. This
restores zero/min finger materials while preserving the geometry changes and
the zero cloth/human friction. The independent friction commit is `83dd0ec`;
geometry is in `007e7cd`. No rollback has been applied: the default remains 0.2.

For a subsequent launch, restore with:

```bash
STRETCH4_GRIPPER_CONTACT_FRICTION=0 ./run.sh gui
```

The GUI was closed normally at the user’s request. A force/slip or dressing replay after enabling friction
has not been performed; effective bindings are verified, not grip strength.
`docs/verification-results/gripper-friction-live-20260911.json` records the live
binding check. Full logs, source rollback archive and F-slots remain local.

## Shutdown checkpoint

The exact closing state was saved separately, without changing the stage slots:
`/home/seoyul/PhyRC_backups/gui_shutdown_20260911_160840/shutdown_state.npz`.
The output copy is `output/friction_trial_20260911/shutdown/slot_LIVE.npz`.
All five active F-slots and their preserved copies still match their original
SHA-256 hashes. Container `happy_cori` exited and was removed by its `--rm`
launcher. No GUI was relaunched.
