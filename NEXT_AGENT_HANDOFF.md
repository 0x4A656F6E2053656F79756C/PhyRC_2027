# Latest handoff: contact guard correction installed, 2026-09-11

This section supersedes the historical notes below, especially statements that
head rounding is rolled back or that no full-scene reproduction exists.

- Project: `/home/seoyul/PhyRC_2027`; original Documents project remains separate.
- Native FEM garment solver: 64. Motion defaults: 90% of the original rates.
- Posterior head is rounded in both visual geometry and derived collision mesh.
- Source and runtime now contain the tested contact-guard correction: final
  post-repair recheck, default 24 repairs, optional
  `STRETCH4_CONTACT_GUARD_ITERATIONS` from 1 to 128.
- Collision protection and genuine unresolved-contact fallback remain enabled.
- Full native-FEM replay reproduced the original persistent freeze, including
  persistence after both grippers opened. Rounded-head/90%-speed tests completed
  9760 physics steps without a whole rollback, for both corrected and legacy
  guards. Do not claim the full-scene difference is solely due to the guard fix.
- The final-check defect and its correction were independently verified on
  exact captured failure inputs on the GPU.
- Details and evidence paths: `docs/CONTACT_GUARD_FIX_20260911.md`.
- Audit root: `/home/seoyul/PhyRC_diagnostics/head_freeze_u2hIuWWo`.
- Original GUI was backed up through `event_0008_user_marker`, physics step
  131196, then its recorder was flushed and container stopped. Backups:
  `goal_v3/final_gui_checkpoint.tar` and `goal_v3/before_guard_install.tar`.
- Final GUI launcher: `launch_final_gui_v4.sh` under the audit root. Container:
  `phyrc-audit-final`. Session pointer: `active_final_gui.json`. Verify the real
  process, `runtime_config.json`, `self_test.json` and observations before
  claiming it is running; a pointer file alone is not proof.
- Final GUI uses private slot copies and the latest backed-up original GUI F5.
  Earlier slot contents remain in the backup; project output slots are untouched.
- Hardware investigation found container-specific NVIDIA device-access loss
  consistent with a later systemd reload, not proof of a new GPU hardware fault
  or the cause of the earlier freeze. No host driver/Docker reinstall was done.
- Do not use `goal_v3/raw_pre_failure_seeds`: experimental, unused, missing the
  final production velocity cap. See its `DO_NOT_USE.md`; regeneration approval
  is still pending and is not needed for the already completed valid replays.
- No commit or push was made for this correction. Preserve unrelated files,
  including `docs/PhyRC_proposals.pdf`.

---

# Historical handoff below (may describe superseded state)

# Current investigation: intermittent cloth freeze, cause not established

2026-09-11. The user requested investigation of apparent cloth detachment and
freezing that can recover without input. The pre-head rollback below remains
active; no additional production physics/control changes were made.

- Audit evidence and scripts: `~/PhyRC_diagnostics/head_freeze_u2hIuWWo/`.
  Read its `FINDINGS.md` before drawing conclusions from previous smoke tests.
- Preserved audit-start output and a user-approved live snapshot. The snapshot
  reported both robots holding 256 vertices; its timing relative to spontaneous
  recovery is unknown. The user's original F-slots were preserved.
- Original-image/full-original-stage and migrated-image/Home-stage GPU replays
  used the same pre-head main, shirt geometry and fixtures. Both executed the
  protection callbacks, and both showed transient centimeter-scale grip errors
  without missing attachment prims. The exact prolonged freeze was not reproduced.
- Both opposed-lift/wait replays completed with 5,760 pre/post/sweep calls and no
  full-cloth rollback. Their trajectories and correction counts differed; no
  repeat-control study was completed to attribute that difference.
- Earlier global-rollback speculation is NOT a confirmed root cause. F-slot
  loading clears guard caches and rebuilds attachments, so it does not preserve
  all internal simulator history needed to reproduce a transient lock.
- A passive diagnostic GUI is launched with `launch_observer.sh`, original image
  `phyrc-stretch4:isaac-6.0.1`, read-only Home runtime, container `phyrc-audit-live`.
  It restores the captured live snapshot, uses isolated slots, samples errors
  before/after guarding and can save up to eight separate event snapshots.
  Query whether it is still running before any GPU launch.
- A bare-variable forwarding compatibility difference in run.sh was identified
  but not changed: some original FEEL aliases need a STRETCH4_ prefix in the new
  launcher. Neither observed GUI had such overrides. It is not the established
  cause of the current incident.
- No complete recovery or stability certification is claimed. Investigation
  files and the worktree have not been committed or pushed during this audit.

---

# Previous: diagnostic restoration to immediately before the head edit

2026-09-10. The user requested a rollback for investigation, not a physics fix.
The active maintenance checkout remains `~/PhyRC_2027`. This section supersedes
all physical-state and verification claims below.

- Restored the exact archived teleop main, resize_shirt.py, make_wearable_shirt.py and both generated Modelink USDs from the snapshot immediately before the combined head-rounding/height-restoration request.
- Removed the head-rounding helper from source and generated runtime. The original posterior head shape is therefore restored, including its known protrusion.
- Removed SHIRT_HEIGHT_SCALE from geometry.json. The shirt retains the earlier uniform 1.2 enlargement and collar-area correction; the later Y-only 10/12 transform is no longer applied. The original archived generator recomputes its pre-head mass metadata when prepare is explicitly run.
- Native grasp, contact guards, robot control, physics rates and solver settings were not edited. The standalone migration launcher remains in place, rather than installing the incompatible original-project launcher.
- Complete pre-rollback project/Git/runtime files, excluding disposable caches and separately preserved output, are in `~/PhyRC_backups/20260910_234215_before_pre_head_restore/current-project-with-git-runtime.tar.gz`. The previous output directory was moved intact to `output-current/` in that same backup directory. The rollback input archive is also copied there as `pre-head-source-assets.tar.gz`.
- Copied the historical F1-F4 slots to `output/states_large20_neck20_near1m_mesh4/`. F1 is automatically overwritten at GUI startup; the historical originals remain preserved outside this checkout. The historical LIVE is copied separately to `output/pre_head_reference/live_before.npz`; it was not automatically loaded or substituted for an F-slot.
- The original `~/Documents/PhyRC_6.0.1` files and currently running GUI `youthful_lederberg` were left untouched. That existing GUI still runs the post-head-edit original source; close it before launching the restored Home checkout. Do not run two GPU SimulationApps at once.
- No preparation, simulation, syntax checks or verification were run after restoration. Existing smoke assertions and scene baselines require the post-head rounded geometry and do not certify this diagnostic rollback. Tests were intentionally not modified.
- Changes are left uncommitted and unpushed for the user's comparison. Git history and the unrelated untracked proposal PDF are preserved. The source checksum manifest describes the restored inputs, not a passing runtime test.

Launch only after closing the existing original-project GUI:

```bash
cd ~/PhyRC_2027
export PHYRC_ACCEPT_EULA=1
./run.sh gui
```

---

# Historical migration record (post-head-edit baseline, not current physics)

# PhyRC_2027 maintenance handoff

2026-09-10: minimal standalone migration and installation/teleop verification
completed. This repository, rather than the old patch pipeline, is the maintained
working source going forward.

## Repository and operation

- GitHub: https://github.com/0x4A656F6E2053656F79756C/PhyRC_2027, private, branch `main`, SSH origin.
- Local folder: `~/Documents/PhyRC_2027`. Git identity uses the user's existing global configuration.
- Authenticated GitHub CLI: `~/.local/bin/gh`. Credentials are in the OS keyring, never this repository.
- Read README.md for fresh-machine installation and teleop; read THIRD_PARTY.md before any public redistribution.
- Commands: `export PHYRC_ACCEPT_EULA=1`, then `./run.sh build`, `./run.sh prepare`, `./run.sh smoke`, `./run.sh gui`.
- Only one GPU SimulationApp at a time. Verification GUI was closed with Escape.
- Source edits belong in `src/DexGarmentLab`, not generated `.runtime`. Do not reapply old `patch_stage.py` onto these already-patched files.

## What is included

Sixteen current runtime Python files, the three original geometry-generation
helpers, the compatibility shim, container/launcher/downloader code, and four
indispensable local asset files (robot USD, Modelink source USD, female USD and
its JPEG). Exact public downloads for those custom inputs were not established.

The floor JPEG and linen material USD/BaseColor/Roughness are downloaded from
pinned public revisions and checksum-checked. Isaac Sim and Python libraries are
installed from external sources. No old caches, trained policies, datasets,
backup archives or user F1-F5 slots are committed. Submodules are intentionally
absent: the executed teleop was an extensively modified local snapshot, not an
unmodified upstream checkout with a known matching commit.

## Latest simulation configuration

- Isaac Sim6.0.1 native surface FEM; physics240Hz, render/control60Hz, TGS, solver32, collision updates4/iterations4.
- One blue shirt/yellow hem, four tables, two Stretch4 robots.
- Sleeve reach .375 and straight T rest sleeves; global resize1.2 followed by height10/12, keeping the widened X/Z dimensions.
- The height restoration also changes the collar shape; do not describe the final collar as still exactly +20% area.
- Cloth15946 vertices/31464 triangles after refinement; density18.3216174, mass approximately129.763g, thickness10mm, Young25000, bend450.
- Human Y.45 and chair follow, total1m move toward tables. Arm spread10 degrees per side, elevation input20.
- RoundHead runs before CollisionBody creation;625 vertices trimmed. Both visual and collision meshes retain the rounded posterior skull.
- Control rates, safety guards, native grasp and contact settings are unchanged from the original active source.
- Default slots: `output/states_shortheight_roundhead_mesh4`. F1 is overwritten with initial state each launch. Older-geometry slots are not compatible merely because node counts match.

## Verification and preservation

See docs/VERIFICATION.md and its JSON evidence. Original/new/clean-export scene
fingerprints match. Two-robot unloaded movement, gripper toggle, zero-error
checkpoint save/load and actual GUI keyboard control passed. First initialization
can spend about5-6minutes cooking physics/rendering resources; this is documented
in README, not hidden by distributing old caches.

Original source and user slots remain under
`~/Documents/PhyRC_6.0.1/isaac-upgrade-docker`. Do not overwrite or remove them.
Local migration logs are `/tmp/phyrc2027-*.log`; full diagnostics/screenshots are
under this repository's ignored `output/` directory. Clean export used
`/tmp/phyrc2027-clean-Xgk02A`, which is not a runtime dependency.

Known scope limits: same existing host/driver/Docker infrastructure, not a fresh
OS installation; no loaded-grasp retention, high-load dressing or cross-GPU
trajectory certificate. Preserve these distinctions in future reports. Existing
legacy whitespace/comments were retained to preserve source byte identity.

## Future changes

Use a feature branch, edit maintained source/configuration, prepare with GUI
closed, run smoke and GUI checks, and commit only the intended source/docs.
Keep generated assets, cached downloads and private user states out of Git.
Changing geometry/physics requires a new slot namespace and appropriate
regression tests. Confirm custom asset redistribution rights before making the
repository public.
# 2026-09-11: geometry/randomization changes BEFORE checkpoint

This checkpoint preserves the verified contact-freeze fix before the next
shirt-height, placement-randomization, and hand-collider changes.

- SurfaceContactGuard now checks the geometry AFTER its final permitted repair;
  default budget is 24 repairs plus a final check. Unresolved crossings still
  trigger safe rollback. Native FEM solver iterations are independently 64.
- Robot command rates are 90% of the original rates; tighter compliance limits
  remain enabled. Rounded visual and collision head geometry is restored.
- The recorded native-FEM sequence reproduced persistent freeze with the original
  head/80%/legacy guard. Rounded head/90%/corrected guard passed the same sequence;
  rounded head/90%/legacy guard also passed. Do not attribute the complete scene
  improvement solely to the guard change. Exact failed-input GPU replay separately
  demonstrates the guard defect and correction. See docs/CONTACT_GUARD_FIX_20260911.md.
- The final diagnostic GUI uses container phyrc-audit-final. The prior problematic
  F5 pose was reloaded successfully at 2026-09-11 05:41:07 KST (load epoch 2).
  This checkpoint was saved after both grippers opened. F5 restores poses, not
  historical solver settings or complete internal PhysX contact history.
- Local recordings/backups are under ~/PhyRC_diagnostics/head_freeze_u2hIuWWo/;
  they are not required installation assets and are not included in Git.
- Shirt height is still the enlarged value at this checkpoint. The requested
  10/12 height reduction with unchanged collar geometry, placement randomization,
  and visual-hand collider alignment are the NEXT changes, not verified here.
