# Random human/chair spawn verification: 2026-09-10

- `./run.sh cpu /scripts/check_random_spawn.py`: 1,000 placements passed
  disk bounds/distribution, -30 to +30 degree yaw coverage, unchanged height, shared
  rigid transformation (including nonuniformly scaled input), reproducible
  seeds, fresh default entropy and checkpoint placement validation.
- `./run.sh smoke`: real GPU main loop passed. All 13 human/chair transformable
  descendants moved together, with maximum transform error below 1e-8 and exactly
  unchanged local mesh points. Sampled placement persisted after initialization.
- Geometry, rounded-head hashes, collision mesh, materials, robot initial poses
  and solver settings exactly match the migration baseline. Human world pose is
  intentionally different; the old full-pose `compare_reports.py` comparison
  therefore does not apply between a random run and the migration baseline.
- Two-robot unloaded motion, gripper toggle, finite cloth and checkpoint
  save/perturb/load passed with zero position error. A different placement's
  checkpoint was rejected without modifying cloth positions.
- Local GUI of the earlier full-turn version showed a second random placement with the whole body rotated and
  seated on the intact chair. Isolated F1/F2 transform snapshots confirmed `P`
  preserves the human/chair placement; Escape closed the session.
- Current +/-30-degree visual-mesh GUI: five independent sampled placements
  produced three positive and two negative yaw angles. All five camera snapshots
  matched and screenshot timing was ready +5.004..5.005 seconds. The fifth
  placement was recaptured with the same seed after another desktop window
  obscured the screenshot. Raw images/gallery remain in ignored
  `output/verification/randomspawn-five-runs/`; compact metadata is in the report.

Evidence: [random spawn GPU report](verification-results/random-spawn.json).
The migration results below describe the earlier fixed-placement version.

---

# Migration verification: 2026-09-10

Status: **installation and teleop smoke verification passed**.

## What was verified

| Check | Result |
|---|---|
| Current teleop source dependency closure | All 16 copied Python files match the original active stage byte-for-byte |
| Derived container image | Built from pinned official Isaac Sim 6.0.1 digest |
| Python environment | Entire `pip freeze` output matches the original image |
| Public assets | Floor JPEG and cloth material USD/BaseColor/Roughness downloaded at pinned revisions; SHA256 checks passed |
| Generated shirt inputs | Both full/cropped USDs match original points exactly, max coordinate difference 0; topology and `phyrc:` metadata match |
| Mannequin input | Mesh coordinates and normalized stage units/up axis match |
| Default cloth material | After stage metadata normalization, exported USD text matches original exactly |
| Repeat installation | Consecutive `prepare` runs passed, including existing container-owned generated files |
| New-project GPU smoke | Real main loop, two-robot motion, gripper toggle, save/perturb/load and finite cloth passed |
| Clean Git-index export | Prepared with no runtime/cache/download folders or original sibling folders; downloads, doctor, shell syntax and GPU smoke passed |
| Original/new/clean scene comparison | Geometry hashes, topology, head, collision body, material, solver and initial poses match |
| Actual local GUI | Scene visually inspected; W moves robot 1; F2/F3 save, F2 loads, Escape closes application |

The clean export was generated with `git archive` from the staged Git tree before
committing, not by copying the original project's runtime or caches. The later
report/documentation additions do not alter the verified runtime. The existing
Docker daemon and official image layers were reused.

## Measured baseline

- One garment, two robots; 15,946 cloth vertices and 31,464 triangles.
- Solver32; density18.321617126 kg/m3, Young25,000 Pa, bend450, thickness10mm and friction0.
- Rounded-head metadata:625 trimmed vertices; visual and collision geometry hashes match the original runtime.
- Human root Y approximately0.45m and original robot initial poses retained.
- Headless checkpoint save/load maximum coordinate error: **0m** in both new-project and clean-export tests.
- GUI W input increased robot1 lift command by0.233333m; robot2 commands remained unchanged. Differential joint motion was0.165381, confirming distinct physical response rather than startup settling alone.
- First new-project smoke took approximately336.5s; clean-export smoke approximately339.8s. GUI initialization also spent several minutes preparing physics tasks before keyboard testing.

## Evidence

- [Original runtime](verification-results/original-smoke.json)
- [New-project runtime](verification-results/new-smoke.json)
- [Clean-export runtime](verification-results/clean-smoke.json)
- [USD geometry comparison](verification-results/asset-comparison.json)
- [GUI keyboard check](verification-results/gui.json)
- [Python package inventory](verification-results/python-freeze.txt)

Full logs, temporary state slots and screenshots remain in ignored local output
locations, not in Git. GUI tests used `/output/gui-verification/states`; original
user slots were not overwritten. `scripts/compare_reports.py` compares two
successful reports using exact geometry hashes and small scalar tolerances.

## Findings corrected during migration

1. The first minimal package omitted `linen_Pumpkin.usd`, which is initialized before the final garment color override. Added its public download and the two textures it actually references, with pinned hashes; no unused normal/displacement textures.
2. Repeated preparation initially attempted to chmod files owned by the container UID from the host. Preparation now adjusts only files owned by the executing UID, and generated files use a group-writable umask. No original project files or user slots were deleted.
3. GitHub device authentication initially expired. A later login succeeded as the requested account and the remote repository was created private.

The copied legacy source retains a few existing trailing-whitespace lines.
A Git whitespace check flags these; they were intentionally not reformatted so
the migrated simulation source remains byte-identical. Shell syntax checks pass.

## Scope and limitations

Test host: Ubuntu22.04.5, Docker29.1.3, RTX5080 16GB, driver580.178.04.
Project image at verification:
`sha256:33b3dabbbdb197adda6a9b1c5ba9b084101223863c1734deabfc77048b0a90c9`.

This is not a fresh OS/driver installation test: Ubuntu, NVIDIA drivers, Docker,
Container Toolkit and cached official image layers already existed on this host.
The README documents their official installation paths, but other hardware and
OS combinations have not been tested here.

The initial gripper toggle did not attach cloth because the fingertips were not
in a pinch fixture. No physical-grasp retention, full dressing, high-load pull,
long-duration stability, recording, remote-desktop or cross-GPU deterministic
trajectory equivalence is certified by this installation smoke test. No physics
or control parameters were reduced to make verification pass.
