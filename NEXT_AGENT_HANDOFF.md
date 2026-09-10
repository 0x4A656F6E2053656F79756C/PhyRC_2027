# Latest: environment-aware setup and safe re-cloning

2026-09-10. The user chose to keep this handoff in Git. It is maintenance
documentation, not an installation/runtime dependency.

- README now starts with an existing-environment decision table. Keep supported working OS/driver/Docker installations; resolve only missing or failing components. Non-reference driver versions are not automatically rejected.
- `scripts/doctor.py` replaces the former information-only shell block. Results are PASS/MISSING/FAIL/CHECK with README anchors; exit codes0/1/2 mean prechecks passed, missing/problem, additional checks needed.
- `./run.sh doctor` never installs packages, pulls images, modifies host configuration or restarts Docker. `--json` prints structured results without creating a report file.
- `--gpu` requires explicit NVIDIA license acceptance and an existing local project image. It runs a time-limited NVML probe in a uniquely named temporary container and cleans up only that container. This is not a Vulkan/PhysX compatibility certificate; use smoke for that.
- The current release still targets x86_64 Linux with documented Ubuntu22.04/24.04 support. Other Linux releases are CHECK, native Windows/macOS and other architectures FAIL for this launcher. RTX/VRAM matching is only a preliminary screen, not a GPU model/performance certificate.
- The user wants to verify restoration from GitHub. The existing working folder and ignored user data will be preserved; a separate GitHub clone at `~/Documents/PhyRC_2027_clone_check` is used rather than deleting the current repository first. Final clone verification results will be recorded after execution.
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
