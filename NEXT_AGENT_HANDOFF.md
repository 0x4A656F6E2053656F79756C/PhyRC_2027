# Latest: Home-directory working clone and final verification

2026-09-10. The maintained working checkout is now `~/PhyRC_2027`.
Use this checkout for future source/configuration changes and Git commits.

- At the user's explicit request, deleted `~/Documents/PhyRC_2027` and `~/Documents/PhyRC_2027_clone_check` completely. Both had clean tracked working trees and no unpushed commits before deletion; local and remote `main` matched `0f8780a447f5f55aa2d1629a7aa492d0e6d467ad`.
- Preserved the original `~/Documents/PhyRC_6.0.1` tree, including its source, user states and backups. No Docker images or host tools were removed.
- Cloned the private GitHub repository over SSH into `~/PhyRC_2027` from commit `0f8780a`. No downloaded assets, generated runtime, output or project caches were copied from an older checkout.
- `PHYRC_ACCEPT_EULA=1 ./run.sh build` and `prepare` succeeded. The existing host OS, NVIDIA driver, Docker installation and cached image layers were reused; this was not a fresh-OS installation test.
- `doctor --gpu --json` returned exit 0 with all 14 checks PASS. Actual GPU smoke also passed two-robot unloaded motion, gripper toggle and checkpoint save/perturb/load.
- `compare_reports.py` matched the new smoke scene against `docs/verification-results/original-smoke.json`, including geometry hashes, material, rounded head, poses and solver settings.
- A real local GUI session initialized with collider visualization enabled. Screenshot inspection confirmed the shirt/yellow hem, textured floor, chair, robots and rounded head were visible. F2/F3 saved isolated test slots; holding W changed robot 1's lift command by 0.2333333333 m while robot 2's controls stayed unchanged. Differential joint motion was 0.1653811955, confirming actual selective motion rather than common startup settling. The F2 load key was sent and Escape closed the application normally; the exact numerical restore round-trip was verified by smoke.
- Test artifacts are under `output/verification/` and `output/gui-verification/`; temporary host logs use `/tmp/phyrc2027-home-*.log` and the doctor report is `/tmp/phyrc2027-home-doctor.json`. These generated artifacts are ignored by Git. A compact result record is committed as `docs/verification-results/home-clone.json`.
- Runtime source and physical configuration were not changed during this move. Verification does not establish full dressing-task success or grasp retention under load.

Older `Documents/PhyRC_2027` paths below describe historical working/verification
copies, not the current checkout. The two deleted folders must not be used as
the source for future work. Launch from the maintained checkout:

```bash
cd ~/PhyRC_2027
export PHYRC_ACCEPT_EULA=1
./run.sh gui
```

---

# Previous: environment-aware setup and safe re-cloning

2026-09-10. The user chose to keep this handoff in Git. It is maintenance
documentation, not an installation/runtime dependency.

- README now starts with an existing-environment decision table. Keep supported working OS/driver/Docker installations; resolve only missing or failing components. Non-reference driver versions are not automatically rejected.
- `scripts/doctor.py` replaces the former information-only shell block. Results are PASS/MISSING/FAIL/CHECK with README anchors; exit codes0/1/2 mean prechecks passed, missing/problem, additional checks needed.
- `./run.sh doctor` never installs packages, pulls images, modifies host configuration or restarts Docker. `--json` prints structured results without creating a report file.
- `--gpu` requires explicit NVIDIA license acceptance and an existing local project image. It runs a time-limited NVML probe in a uniquely named temporary container and cleans up only that container. This is not a Vulkan/PhysX compatibility certificate; use smoke for that.
- The current release still targets x86_64 Linux with documented Ubuntu22.04/24.04 support. Other Linux releases are CHECK, native Windows/macOS and other architectures FAIL for this launcher. RTX/VRAM matching is only a preliminary screen, not a GPU model/performance certificate.
- GitHub restoration verification PASSED using a real SSH clone of commit `bf234d3` into `~/Documents/PhyRC_2027_clone_check`. The existing working folders and ignored user data were preserved, not deleted. The later handoff-only commit does not change the tested runtime or doctor implementation.
- The fresh clone initially returned doctor exit1 for missing downloaded assets/prepared runtime, with the unrequested GPU probe marked CHECK. After `build` and `prepare`, `doctor --gpu --json` returned exit0 with every check PASS. No original asset-download, cache or generated runtime directories were copied into the clone.
- The cloned repository's actual GPU smoke passed two-robot unloaded motion, gripper toggle and checkpoint save/perturb/load. `compare_reports.py` confirmed its scene fingerprints match the committed original baseline. The existing host OS/driver/Docker and Docker image layers were reused; this is not a fresh-OS test. GUI input was not retested in this follow-up; the earlier GUI validation remains documented below.
- Doctor scenario checks passed for supported/other OS versions, unsupported platform/architecture, missing tools, refusing GPU execution without EULA consent, and cleaning up the uniquely named GPU probe after timeout. The existing-host real GPU precheck also passed.
- Follow-up artifacts: clone `output/verification/smoke.json`; host logs `/tmp/phyrc2027-github-clone-{build,prepare,smoke}.log`; doctor before/after JSON under `/tmp/phyrc2027-clone-doctor-{before,after}.json`. These temporary reports are not runtime dependencies and are not added to Git.
- A folder deletion does not delete GitHub or Docker's external image store. It DOES delete ignored slots/videos and uncommitted files in that folder. Review those separately and confirm pushed commits before removing a working copy.

The migration baseline and physical runtime below remain unchanged.

---

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
