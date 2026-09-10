# Native two-robot contact and rotation audit: 2026-09-10

The user clarified that both robots were holding opposite shirt sides while
trying to insert the human arms, and the whole hand appeared through the cloth.
A visible/physical finger distinction does not establish the cause of this report.
Code review found that collision caches are constructed after spawn rotation,
body and sphere geometry use final world transforms, and native gripper offsets
use actual robot link quaternions. No rotation-frame mix-up was identified.

`scripts/verify_native_human_contact.py` prepares the unchanged shirt as a vertical
panel in front of the human and two real robot grasps on opposite sides. It then
runs production native attachments and base controllers for four seconds. This
is a loaded grasp/contact test, not autonomous pickup, sleeve insertion, or a
replay of the user's unavailable action sequence. User slots are never loaded
or overwritten; an optional slot supplies only human/chair placement matrices.

The recorded placement (~-26.88 degrees) had zero raw or accepted body cuts in
960 physics substeps. The closest analytic wrist-sphere/cloth surface gap was
5.808mm, with 36 control frames within 10mm. Both actual grippers and attached
cloth moved, with maximum attachment lag 9.798mm. PhysX resolved this contact;
the additional sweep guard needed zero corrections. Gap and lag were sampled
at 60Hz, body triangle intersections at 240Hz. This does not reproduce or rule
out the user's full sleeve-threading failure.

Fixed placement also passed all 960 steps with zero cuts: minimum sphere gap
5.714mm, maximum attachment lag 10.099mm, and 35 frames within 10mm. All
960 post callbacks ran. Its 883 detailed sweeps reflect the legitimate broad-phase
skip when cloth/body bounds are disjoint. The fixed-scene rotation audit below
had a maximum inverse-transform difference of 0.00592mm.

A separate geometric audit rotated the actual body/sphere triangle mesh and
1,017 crossing paths together by 0/-30/+30 degrees. All 3,051 crossings were
blocked. Transforming the corrected points back produced at most 0.00264mm
difference. These are guard-geometry checks, not a rotated PhysX scene replay.

Evidence: [native contact measurements](verification-results/native-human-contact.json).
No runtime parameters or physics implementation changed in this follow-up.

```bash
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_native_human_contact.py --fixed
# Optional read-only recorded human/chair placement:
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_native_human_contact.py --placement-slot /output/states_randomspawn_mesh4/slot_F1.npz
```

---

# Continuous cloth face contact: 2026-09-10

The reported run's F1 placement was read without loading or changing user
cloth/robot slots. Its human yaw was approximately -26.88 degrees. Comparison
with pre-randomization commit `104d6b0` found unchanged arm pose/length settings,
garment physics, hand proxy construction and grasp control. Randomization changes
the shared human/chair placement and the selected garment support box.

A separate, reproducible contact defect was confirmed: an 8mm linear triangle
movement across a 2mm thin tip had zero intersections at both endpoints, three
intersections halfway through, and was entirely accepted by the old guard. Node
rays plus endpoint edge/face tests missed intermediate triangle-interior motion.
The defect also existed in fixed placement; the user's exact grasp trajectory
was not recorded, so this is not proof of the sole cause of that particular run.

- The guard now checks body-vertex/moving-face and body-edge/moving-edge
  intersections over each linear per-step interval. It repairs or rejects an
  unsafe candidate using the existing bounded loop. Garment openings and
  visible geometry are unchanged; no material/friction/margin values were raised.
- GPU controls passed 283 polynomial root cases, crossing/free edge controls,
  and both ordinary and CUDA graph paths at zero yaw, -30/+20 degrees yaw/tilt,
  +30/-20 degrees and -26.88 degrees yaw. Thin-tip crossings were blocked;
  tangential and obstacle-free movements remained available.
- Actual full-shirt stress tests force nodal velocity toward the wrist and
  run production pre/post physics callbacks for 180 steps (0.75 simulated
  seconds). These are contact tests, not a full robot grasp/dressing trial.
  Recorded placement after reset at 1.2m/s, recorded placement at 12m/s stress,
  and fixed placement at 12m/s each had zero endpoint intersections across all
  180 steps, with 135/177/177 guard corrections. Push phases took 6.67/7.76/7.54s.
- Prepared-runtime teleop regression passed with exact original scene
  fingerprints, zero checkpoint restore error and mismatched placement rejection.
  Full 256x256 RGB-D policy regression passed; repeat joint error was zero and
  settled cloth error was 1.564mm. Schema checks and compilation passed.
- Interval work runs only after endpoint repairs, with geometric and polynomial
  bounds rejecting irrelevant candidates. An initial slow implementation was
  replaced before delivery. The optimized recorded-placement run took about
  36.5s including startup, comparable to the earlier 36.0s probe on this host.
- Entirely coplanar motion still uses the existing contact/endpoint checks;
  this is not a proof of all possible FEM trajectories or dressing success.

There is also an existing visual/physical distinction: default `sphere` hand
collision removes finger triangles and uses wrist spheres. Visible finger mesh
vertices extend up to 91.9mm/84.9mm beyond those spheres. This predates
randomization and was not silently resized by this patch. `STRETCH4_SHOW_COLLIDER=1`
displays the actual collision proxy; visual-mesh mode displays the fingers too.
Distinguish these display modes when reproducing apparent finger penetration.

Evidence: [contact controls and live measurements](verification-results/human-contact.json).

```bash
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/check_surface_contact.py
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_human_contact.py --seed 42
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_human_contact.py --fixed --speed 12
# Optional read-only replay of the human/chair placement in a local user slot:
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_human_contact.py --placement-slot /output/states_randomspawn_mesh4/slot_F1.npz --post-reset
```

---

# Optional fixed placement: 2026-09-10

- `./run.sh gui --no-randomization` (equivalently `STRETCH4_RANDOMIZE=0`)
  disables both human/chair and garment placement randomization. The default
  remains randomized. Learning commands accept the same launcher option.
- CPU/USD tests passed 1,000 randomized assemblies and unchanged authored USD
  in disabled mode, even with different seed settings. The garment test passed
  10,000 random samples and fixed original-third-box selection for every seed.
- Prepared-runtime GPU smoke with the disabling option and both spawn seeds
  explicitly set passed. All 13 human/chair descendant transforms remained
  exactly unchanged, and measured cloth positions were over box 3 (index 2).
  All scene fingerprints, including the human pose, matched
  `original-smoke.json` from before randomization. Robot movement, gripper
  toggle, checkpoint restoration and mismatched-placement rejection passed.
- GPU RGB-D policy smoke exercised reset seeds 42→43→42 in fixed mode, checking
  unchanged human/chair transforms and garment placement across different seeds,
  plus the existing sensor/action/reset/termination checks. Settled cloth errors
  were 1.886mm across different seeds and 1.002mm on repeat seed; fixed placement
  does not promise identical FEM settling trajectories.
- Shell syntax, Python compilation and policy contract checks passed. This
  option changes initial placement only; material/solver/shape settings and
  existing explicit human/box configuration overrides remain active.

Evidence: [fixed placement and regression measurements](verification-results/fixed-spawn.json).

```bash
python3 scripts/check_garment_spawn.py
PHYRC_ACCEPT_EULA=1 ./run.sh cpu /scripts/check_random_spawn.py
PHYRC_ACCEPT_EULA=1 HUMAN_SPAWN_SEED=42 STRETCH4_GARMENT_SPAWN_SEED=1 ./run.sh smoke --no-randomization
python3 scripts/compare_reports.py docs/verification-results/original-smoke.json output/verification/smoke.json
PHYRC_ACCEPT_EULA=1 ./run.sh policy-smoke --no-randomization
```

---

# Random garment support: 2026-09-10

- The blue shirt now selects uniformly among the four existing boxes at startup
  and learning reset. The original shape, orientation, height above the selected
  table, human random stream and physical parameters are unchanged.
- CPU sampling over 10,000 seeds selected boxes 1–4 respectively 2521, 2452,
  2549 and 2478 times. Seed replay and whole-mesh translation checks passed.
- Actual GPU resets with seeds 2, 0, 11 and 1 exercised all four boxes for 20
  simulated seconds each, with 1,200 measurements per box. Fixed-camera renders
  at 1.5, 10 and 20 seconds are embedded in the standalone HTML report.
- Every cloth vertex stayed within its selected tabletop XY footprint. Minimum
  edge margin was 46.14mm; minimum height above the tabletop was about 5mm.
  After the initial two seconds, maximum horizontal centroid movement was
  0.619mm and vertical movement was under 0.04mm. No fall occurred in this
  interval. Small drift exists; this is not an infinite-time no-slip guarantee.
- Returning to seed 2 after visiting all boxes restored the same selected box;
  settled cloth differed by at most 1.181mm. Local mesh/topology stayed identical.
- Prepared-runtime teleop regression independently measured startup on box 4
  (seed 1) from live USD cube geometry and PhysX cloth positions. Checkpoint
  restoration error was zero; mismatched human placement was rejected. Scene
  fingerprints matched the original baseline except the randomized human pose.
- Full 256×256 RGB-D policy regression passed all action channels, reset and
  termination. Calibration depths were 0.8999999/1.1999998m; repeated seed
  joint error was zero and cloth error 0.987mm. HTML time switching and image
  enlargement were tested in headless Chrome.

Evidence: [interactive HTML](verification-results/garment-spawn.html),
[compact measurements and regression results](verification-results/garment-spawn.json).
Original PNG frames and 60Hz NPZ traces are in `output/verification/garment-spawn/`.
Reproduce with:

```bash
python3 scripts/check_garment_spawn.py
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_garment_spawn.py
PHYRC_ACCEPT_EULA=1 HUMAN_SPAWN_SEED=42 STRETCH4_GARMENT_SPAWN_SEED=1 ./run.sh smoke
PHYRC_ACCEPT_EULA=1 ./run.sh policy-smoke
python3 scripts/build_garment_spawn_report.py --teleop-report output/verification/smoke.json --policy-report output/policy-smoke/report.json
```

The original zero-friction settings were retained. External disturbances, robot
grasping and longer episodes are outside this support test. Runtime verification
used the working changes on base commit `d4bd2c4`; source hashes are recorded.

---

# Learning environment and RGB-D: 2026-09-10

- GPU integration passed three 256×256 RGB-D cameras and typed Gymnasium observations.
  Moving a camera-aligned calibration cube at frozen physics time produced optical
  depths 0.8999996m and 1.1999998m for expected 0.9m and 1.2m. RGB also refreshed.
  Wrist cameras were visually checked to face the fingertips, with fixed mount extrinsics.
- Every action advances 0.05 simulated seconds. All eight continuous channels,
  gripper close/hold/open, deferred grasp attempt, invalid action rejection,
  time-limit truncation and injected evaluator termination were exercised.
- Reset seeds 42→43→42 reproduced human/chair placement and robot q (max error 0).
  Cloth positions were restored exactly before settling. FEM settling differed by
  2.264mm at most; the test permits 5mm, not bitwise cloth reproducibility.
  Base speed after reset was <=0.002481m/s; finger-open error <=0.000301rad.
- The real teleop main-loop regression passed after runtime preparation, including
  robot motion, gripper toggle, exact checkpoint position restoration and rejection
  of a checkpoint with mismatched human placement. Mesh/material/solver settings
  were not changed by the policy adapter.
- A small real-scene behavior-cloning trial collected 64 transitions and trained
  500 updates. Held-out 22cm lift goal error fell from 0.14688m to 0.00209m in about
  106s including startup. This is a lift calibration demonstration, not a learned
  dressing baseline. The final committed checkout is also tested in a fresh clone.
- CPU schema/frame/action checks, Python compilation and shell syntax checks passed.

- Fresh GitHub clone at `~/PhyRC_2027_participant`, clean source commit `d152661`,
  passed build, independent asset/runtime preparation, all 14 doctor checks and
  actual learning. Cold training took 408.86s (RTX shader compilation confirmed
  in Kit logs); warm rerun took 109.55s. Both reached 0.002088m held-out lift MAE.
- The same committed source also passed full sensor/action/reset checks at
  non-square 160×96 resolution. Expected depth 0.9/1.2m measured
  0.8999999/1.1999998m. Robot q repeated exactly; settled cloth varied by 1.25mm.
  Runtime source hashes matched the maintained checkout. Source trees were clean.

Evidence: [policy environment](verification-results/policy-environment.json),
[fresh participant clone](verification-results/participant-clone.json).
Raw RGB/NPZ/JSON are in `output/policy-smoke/`; training artifacts in
`output/train-demo/`. Full dressing success, force sensing and grasp under load
remain unverified. Gymnasium was pinned to 1.2.3; the Isaac base image is unchanged.

---

# Historical stage: policy specification and read-only inspection (0.1): 2026-09-10

- Actual GPU main loop inspected at startup and after 60 neutral control ticks.
  Both robots expose 13 named joints; base/grasp/fingertip poses, actual joint
  states, control targets, cloth positions/velocities and live limits were read.
  All measured state was finite. Physics dt=1/240s, render dt=1/60s; 60 control
  ticks advanced simulation time by approximately 1s.
- Typed observation arrays were exported and validated against the draft schema.
  CPU checks passed configurable resolution/counts, world/base pose round trips,
  action rate/sign conversion, repeated close intent and invalid-input rejection.
- The inspector reuses the existing main loop, writes isolated F1 slots and does
  not issue policy actions or change physics. The normal teleop source is unchanged.
- RGB-D sensing, a learning reset/step implementation, rewards and full dressing
  success are outside this verification. Current camera manifests contain Kit
  viewport cameras and existing wrist mounting links, not implemented RGB-D streams.

See [policy contract](POLICY_INTERFACE.md) and
[live inspection evidence](verification-results/policy-inspection.json).

---

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
