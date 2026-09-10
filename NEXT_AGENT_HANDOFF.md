# Latest: Native grasp contact and rotation audit

2026-09-10. Follows pushed contact fix `55b9ded` on
`feat/policy-learning-env`. The user clarified that two robots held opposite
ends of the shirt while trying to insert the human arms. The whole hand seemed
to pass through in visual-mesh mode; the user suspects rotation-dependent math.
Treat physical wrist-sphere penetration as a real hypothesis. No exact robot
input sequence or already-pierced state has been captured; F1 stores placement.

- Audited startup order and coordinate conversions: human/chair randomization
  precedes physics initialization and contact-cache construction. Body mesh and
  wrist centers use final world transforms; normals are derived from world
  triangles. Native attachment offsets use actual physics link quaternions.
  No stale pre-randomization transform or position/direction mix-up was found.
- Added `scripts/verify_native_human_contact.py`: two real robot articulations
  with production native cloth attachments and continuous base control pull the
  actual shirt toward the left wrist. Grasp patches and start poses are prepared;
  this is NOT autonomous pickup, sleeve threading, or exact user input replay.
  It verifies actual gripper/attached-node movement and lag, every physics-step
  body intersection, and analytic wrist-sphere/cloth separation at 60Hz.
- Recorded placement (~-26.88 degrees) passed 960 steps / 4 seconds: raw and
  accepted body intersections were zero; minimum sphere gap 5.808mm; maximum
  attachment lag 9.798mm. Both grippers and held cloth moved. There were 36
  control frames within 10mm of the sphere. PhysX handled contact with ZERO
  extra guard corrections; do not misreport these as corrected penetrations.
- Fixed-placement comparison also passed 960 steps: zero body cuts, minimum
  sphere gap 5.714mm, max grasp lag 10.099mm, and 35 frames within 10mm.
  All 960 post callbacks ran; only 883 detailed sweeps were needed because
  broad-phase disjoint bounds legitimately bypass the detailed guard.
- Rotation audit transforms the actual body/sphere triangle mesh and 1,017
  crossing paths together by 0/-30/+30 degrees. All 3,051 paths were blocked;
  max inverse-transform position difference was 0.00264mm. This exercises the
  geometric guard, not a proof of every PhysX FEM trajectory or sleeve insertion.
- No further runtime physics/shape/gripper values were changed. The prior
  interval-face defect is fixed, but the user's precise failure remains
  unreproduced and its sole cause unconfirmed. The next useful reproduction is
  two held shirt sides threading the arms, with the actual failed cloth/robot
  pose or input sequence. Preserve the user's slots while investigating.
- See docs/VERIFICATION.md and docs/verification-results/native-human-contact.json
  for final evidence and commands. Raw traces are in ignored output/verification.
  Preserve unrelated docs/PhyRC_proposals.pdf and the participant checkout.

---

# Previous: Cloth triangle interval contact

2026-09-10. User reported human arms/hands easily piercing the shirt in the
last rotated teleop run, and asked whether arm pose/length, mannequin, garment
or gripper settings had changed. Maintained checkout and branch remain
`/home/seoyul/PhyRC_2027`, `feat/policy-learning-env`; base commit `91107e2`.

- Compared with pre-randomization `104d6b0`: arm pose/length and physical/grasp
  defaults are unchanged. The only changed module-level assignment was the
  checkpoint folder. HandSphereColliders, NativeGrasp, Particle_Garment and
  ContinuousClothControl source bytes are unchanged. Whole human/chair placement
  and the shirt's selected box account for the intended scene differences.
- Read the latest user F1 placement without writing slots: approximately -26.88
  degrees yaw. Live probes found working pre/post callbacks, rotated guard data
  and no residual endpoint cuts in wrist-directed velocity stress, including
  after reset. The user's exact native-grasp input trajectory was not recorded.
- Confirmed a distinct real defect: 8mm triangle motion over a 2mm tip passed
  entirely through its interior between endpoint snapshots. Old node sweeps and
  endpoint edge/face tests accepted it despite three mid-step intersections.
  This defect predates randomization, so do not claim its introduction was caused
  by the random sampler or that it definitively explains the user's entire run.
- `SurfaceContactGuard.py` adds interval vertex/face and edge/edge checks for
  linear per-step motion, with bounded cubic-root solving. Existing local repair
  and final candidate rejection remain in place. No pose, length, proxy size,
  friction, margin or gripper control changes were made to mask the issue.
- Performance matters: run interval tests only after endpoint cuts are repaired;
  reject candidates by swept bounds and Bernstein coefficient bounds first.
  The initial unconditional implementation was far too slow and is not shipped.
  Optimized recorded-scene probe was ~36.5s including startup (earlier ~36.0s).
- `scripts/check_surface_contact.py` validates roots, edge crossings, thin-tip
  tunnelling and permitted tangent/free movement in graph and ordinary paths.
  `scripts/verify_human_contact.py` is a full-shirt velocity stress test, supports
  seeded/fixed scenes and optional read-only human/chair slot placement replay.
  It does not certify loaded native robot grasps. See docs/VERIFICATION.md and
  docs/verification-results/human-contact.json for evidence and reproduction.
- Existing visual fingers are NOT the default physical hands: sphere mode drops
  finger collision triangles in favor of wrist spheres; rendered finger vertices
  extend ~9cm past these proxies. Do not confuse this with collision-proxy
  penetration or silently change the selected hand proxy. The user subsequently
  clarified that the whole hand appeared through the cloth in visual-mesh mode,
  with two robots holding opposite shirt sides while inserting human arms.
  Do not dismiss this as a finger-display issue; see the latest section above.
- Runtime must be prepared after source changes. Current startup/reset toggle
  `--no-randomization` remains available; user data and the separate participant
  checkout were preserved. Untracked docs/PhyRC_proposals.pdf is unrelated.
- Current source was prepared and verified: recorded-pose contact after reset,
  recorded/fixed high-speed stress, analytic GPU controls, teleop/checkpoint
  regression and full RGB-D policy smoke passed. All three 180-step contact
  runs had zero endpoint cuts. Policy repeat cloth error was 1.564mm. Runtime
  guard bytes and measured guard source hashes match the maintained source.

Prior sections below are historical; follow the latest user clarification when
investigating any remaining reported visual/native-grasp penetration.

---

# Previous: Optional fixed placement (randomization disabled)

2026-09-10. User requested an execution argument to restore the placement before
human/chair and garment randomization, followed by handoff update, commit and
push. Maintained checkout: `/home/seoyul/PhyRC_2027`; branch:
`feat/policy-learning-env`, tracking `origin/feat/policy-learning-env`.
This change follows pushed handoff commit `a47b300`. The code, verification and
this handoff are delivered together on the same branch; use `git log -1` for
the delivery commit. No `main` merge is requested.

```bash
cd /home/seoyul/PhyRC_2027
export PHYRC_ACCEPT_EULA=1
./run.sh gui --no-randomization
STRETCH4_SHOW_COLLIDER=0 ./run.sh gui --no-randomization
# Omit the option for the default randomized scene:
./run.sh gui
# Learning scripts use the same switch, immediately after the command:
./run.sh train-demo --no-randomization
./run.sh python --no-randomization /project/your_script.py
```

- `STRETCH4_RANDOMIZE=0` is the equivalent environment setting; default is 1.
  `Env_Config/Randomization.py` shares this switch between both spawn helpers.
  Values other than 0/1 are rejected. The CLI switch overrides an enabled env.
- Disabled mode leaves the authored human/chair transform stack untouched and
  puts the blue shirt on the original third box (zero-based index 2). Explicit
  human/box configuration overrides still apply; shapes and physics are unchanged.
  All learning resets retain this placement regardless of episode seed. Episode
  seed remains recorded, but spawn metadata has `seed=null`, `randomized=false`.
  Randomized mode records `randomized=true` and keeps its previous seed streams.
- Fixed placement does not freeze dynamics or guarantee bitwise GPU FEM repeatability.
  Existing checkpoint placement validation stays enabled. Do not load randomized
  human-placement slots into the fixed scene; the loader will reject them.
- Runtime was prepared from maintained source. Read `docs/VERIFICATION.md` and
  `docs/verification-results/fixed-spawn.json` for current checks and evidence.
  No Docker image rebuild is needed. Edit `src/`, not generated `.runtime`.
- CPU/USD checks and actual fixed-mode teleop/policy smoke passed. The teleop
  scene exactly matches the original baseline including human pose. Policy
  reset seeds 42→43→42 kept the fixed placement; settled cloth errors were
  1.886mm across different seeds and 1.002mm on repeat seed. RGB-D, all action
  channels, termination and checkpoint regression passed.
- Participant checkout `/home/seoyul/PhyRC_2027_participant` remains clean at
  `d4bd2c4`; these later randomization features have not been pulled there.
  Preserve that checkout, user slots and ignored output/caches.
- Unrelated untracked `docs/PhyRC_proposals.pdf` appeared during this task and
  was left untouched; it is not part of the randomization-switch commit.

The following sections are historical. Continue with the user's next patch,
preserving the modular policy API and the current default randomization behavior.

---

# Previous: Random garment box and stability report

2026-09-10. User requested uniform shirt spawn over the four existing boxes,
actual randomization/support verification, an HTML report and a commit.
Maintained checkout: `/home/seoyul/PhyRC_2027`.
Branch: `feat/policy-learning-env`, tracking `origin/feat/policy-learning-env`.
Implementation and report commit `e409213` was pushed to GitHub after validation.
Remote: `git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git`.
The user also requested this handoff refresh to be committed and pushed on the
same branch. No merge into `main` has been requested or performed.

Start from this latest section; the sections marked Previous below are historical
records. Their old branches, paths, pending-commit statements and restrictions do
not override the current state. There is no outstanding implementation request;
continue with the user's next patch. Keep the learning adapter modular because
the user expects further simulation fixes before full dressing training.

- `Env_Config/Garment/RandomSpawn.py` is a pure sampler, shared by teleop startup
  and `Policy/environment.py` reset. Only the blue shirt's translation changes;
  shape, orientation, spawn clearance (0.2m above the tabletop) and physics stay
  unchanged. GUI `P` retains the startup box; learning reset resamples.
- Seed priority at startup: `STRETCH4_GARMENT_SPAWN_SEED`, `HUMAN_SPAWN_SEED`,
  fresh entropy. Learning reset uses its episode seed. Domain separation keeps
  the original human random stream unchanged. `info.garment_spawn` records the
  selected zero-based box index, seed and placement. Observation/action shapes
  remain schema 0.2.0. Reset translates immutable initial world-space cloth
  nodes, never the previous episode's cloth, and clears velocities.
- All four GPU episodes passed 20 seconds at 60Hz, with fixed camera snapshots
  at 1.5/10/20 seconds. Maximum post-2s horizontal centroid drift 0.619mm;
  minimum edge margin 46.14mm; no fall. There is small drift with the existing
  zero-friction setting, so do not claim indefinite or exact zero sliding.
- 10,000 CPU seeds: counts 2521/2452/2549/2478. GPU representative seeds
  2/0/11/1 visit boxes 1/2/3/4; replay seed 2 differed by 1.181mm after settling.
  Local mesh/topology stayed identical. Tests use the actual shared sampler.
- Prepared runtime teleop smoke passed measured startup on box 4, original
  scene fingerprints except human pose, checkpoint restore and mismatch rejection.
  Full policy RGB-D/action/reset smoke also passed (repeat cloth error 0.987mm).
- Isaac VisualCuboid authors already-scaled extent; BBoxCache applies the scale
  again. The smoke validator derives actual cube corners from size plus world
  transform instead. This is a measurement fix, not a geometry/physics patch.
- `docs/verification-results/garment-spawn.html` embeds real rendered images,
  time switching, zoom and plots; browser interaction checks passed. Compact
  JSON includes CPU counts and teleop/policy regression results. Raw GPU PNGs,
  traces and report remain under ignored `output/verification/garment-spawn/`.
  Reproduction commands are in `docs/VERIFICATION.md`.
- Runtime prepared; no image rebuild needed. The separate participant checkout
  `/home/seoyul/PhyRC_2027_participant` is clean at `d4bd2c4`, the earlier
  learning-environment version. It does not yet include garment randomization.
  Preserve this checkout and its generated assets/caches for the user.

## Next-agent operation notes

- Edit maintained `src/DexGarmentLab`, then run `./run.sh prepare` to refresh
  generated `.runtime` for GUI/teleop. Do not edit `.runtime` as the source.
- Current policy API: schema 0.2.0, three configurable RGB-D views (default
  256x256), two robots with float32[2,9] actions, 20Hz policy steps. Read
  `docs/POLICY_INTERFACE.md` before changing sensors, action or reset semantics.
- Default reward is zero, with no validated dressing-success evaluator or force
  sensor. The existing fast training demo is lift behavior cloning only.
- Preserve ignored `output/` user slots and verification artifacts. Run only one
  GPU SimulationApp at a time. CPU/schema checks and GPU support, teleop and
  policy regressions passed for `e409213`; this handoff update changes docs only.
- Evidence entry points: `docs/VERIFICATION.md`,
  `docs/verification-results/garment-spawn.html` and its adjacent JSON. Report
  source metadata records the tested working changes on base `d4bd2c4`; those
  changes were committed as `e409213` afterward.

```bash
cd /home/seoyul/PhyRC_2027
export PHYRC_ACCEPT_EULA=1
./run.sh gui                            # collision visualization
STRETCH4_SHOW_COLLIDER=0 ./run.sh gui    # visual mesh
# After editing maintained simulation source:
./run.sh prepare
./run.sh smoke
./run.sh policy-smoke
```

---

# Previous: RGB-D sensors and Gymnasium learning adapter

2026-09-10. The user authorized the next stage: implement sensors and learning
reset/step, validate and commit; also try quick training from a new GitHub clone.
This supersedes the earlier restriction to specification/read-only inspection.
Branch: `feat/policy-learning-env`, including random-spawn commit `a5c3824`.
Implementation commit: `d152661`, pushed to GitHub. Final verification/documentation
is committed on the same branch. The participant checkout is
`~/PhyRC_2027_participant`; leave it available for the user to run the demo.

Fresh clone build/prepare and 14 GPU doctor checks passed. No project runtime,
asset downloads or caches were copied. Existing host/Docker layers were reused.
`train-demo` passed twice: first run 408.86s including RTX shader compilation,
warm run 109.55s; held-out lift error 0.14688m -> 0.002088m. A 160x96 sensor
smoke passed on the exact clean committed source, including depth freshness,
all action channels, reset and termination. Evidence: participant-clone.json.
The executable source is unchanged by the final verification-only commit.

- Read `docs/POLICY_INTERFACE.md` (schema 0.2.0) and participant quickstart.
  `Policy/environment.py` provides one Isaac/Gymnasium scene per process,
  seedable reset, 20Hz step over existing 60Hz control/240Hz physics, Dict
  observations, float32[2,9] action, episode truncation and evaluator injection.
- Existing teleop setup/contact guards were extracted into shared helpers;
  drive_robot accepts optional continuous rates. Physics/material parameters
  and keyboard behavior remain unchanged. User F1-F5 slots are never used by
  the learning adapter. Change maintained `src/`, then prepare runtime for GUI.
- RGB-D overview and two wrist views default to 256x256; configurable resolution
  and fixed mount extrinsics. The asset camera link has +X up and -Y toward
  fingertips. Replicator explicit delta_time=0 capture awaits fresh annotations;
  three ordinary render updates had returned stale depth and were replaced.
  RGB/depth timestamps must not advance physics. Info includes K, optical poses,
  actual state manifest, source hashes/commit/dirty flag and episode seed.
- Reset detaches callbacks/native grasps, recreates physics views, restores
  initial robot/cloth values, clears controller histories and rebuilds static
  contact guards for the sampled placement. 90 neutral control ticks precede
  reset return; check base speed and open-finger error. Initial cloth restoration
  is exact, but GPU FEM settling is not bitwise reproducible (~2.3mm difference).
- Default reward=0 and no dressing-success termination. Replaceable evaluator
  returns reward, terminated, task_info. Errors invalidate the episode instead
  of silently loading checkpoints. No force/tactile sensor or validated dressing
  evaluator has been introduced.
- `./run.sh policy-smoke` checks actual sensors, metric depth/freshness, all action
  channels, idempotent gripper commands, repeat reset, truncation and evaluator.
  `./run.sh train-demo` collects 64 real lift demonstrations, behavior-clones a
  tiny Torch policy, and evaluates an unseen 22cm goal. Initial trial: error
  14.7cm→2.1mm, ~106s. This is not full dressing or RGB-D learning performance.
- Torch must be imported after SimulationApp startup (Isaac bundles it in an
  extension). Gymnasium 1.2.3 is added to the project image. Build then prepare.
- SimulationApp.close() can immediately terminate Python. Write artifacts first;
  CLI exception handling forwards exit_code=1 to prevent false-success exits.
- CPU/schema checks and real teleop regression passed. See docs/VERIFICATION.md
  and policy-environment.json; final fresh-clone evidence is in
  docs/verification-results/participant-clone.json. No main merge is part of this task.

---

# Previous: Draft policy contract and read-only state inspection

2026-09-10. Random human/chair spawn was committed as `a5c3824` on
`feat/random-human-chair-spawn`. No push was requested/performed.
Current branch `feat/policy-interface-spec` starts from that commit. The new
policy specification/inspection files are left uncommitted for review.

The user explicitly limited this stage to specification, data schema and real
state measurement. Keep it separate from runtime bug fixes. Do not introduce a
learning `reset/step` environment or freeze a flat observation format yet.

- Read `docs/POLICY_INTERFACE.md` and `config/policy_interface.json` (0.1.0-draft).
  Proposed default: three RGB-D views at 256x256 plus named robot state, two
  robots x nine actions, 20Hz policy over 60Hz control/240Hz physics.
  Cameras, success/reward and learning reset/step are explicitly not implemented.
- `Policy/state.py` reads actual PhysX base/link/joint/cloth state; `contract.py`
  validates configurable arrays and decodes action units/signs without dispatch.
  Neither is imported by the normal teleop environment; its source is unchanged
  from `a5c3824`. No dependency/image rebuild or runtime prepare is needed just
  to run the inspector, which reads maintained source via `/project/src`.
- `scripts/inspect_policy_scene.py` runs the normal headless main loop with
  isolated state slots and read-only hooks at startup and after 60 neutral ticks.
  Command: `PHYRC_ACCEPT_EULA=1 HUMAN_SPAWN_SEED=42 ./run.sh python
  /scripts/inspect_policy_scene.py`. Writes under `output/policy-inspection/`.
  It records the sampled seed, schema/source hashes, named joints/limits, actual
  and target states, local/world poses and typed observation NPZ files. It writes
  before SimulationApp.close(), which can fast-exit without executing finally.
- GPU inspection passed: 13 DOFs per robot; exact source-normalized units are
  metres for lift/arm and radians for wrists/finger/wheels. Base movement is a
  bounded root-wrench velocity servo, not direct per-wheel actuation.
  Public base-left action must invert the old base_strafe/right sign.
- Startup F1 is not a settled learning reset: finger q starts near zero while
  its open target is 0.5rad; after 60 ticks (~1 simulated second) q is ~0.4967rad.
  Fingertip origin distance ~0.18758m is not an inner-surface aperture estimate.
  A calibrated grasp/force sensor and dressing success evaluator are absent.
- Offline schema/coordinate/action checks passed, including reconstruction of
  real base-relative poses, wrong-input rejection, resolution/count changes,
  idempotent close intent, and refusing an RGB-D profile without real images.
  Evidence: `docs/verification-results/policy-inspection.json`; host log:
  `/tmp/phyrc-policy-inspection.log`. GUI/GPU inspector sessions are closed.

---

# Previous: Random human/chair placement

2026-09-10. Working branch: `feat/random-human-chair-spawn`, based on `104d6b0`.
GitHub SSH read access was verified with `git ls-remote`; local and remote
`main` both pointed to `104d6b03f78a2284d626d502328bcc1d037027b9` before edits.
The user approved this change for a local Git commit. No push has been requested.

- Default launches sample uniformly inside a 0.10 m XY disk around the existing
  human root (default X=0, Y=0.45), plus a uniform yaw from -30 to +30 degrees
  relative to the original facing direction (narrowed at the user's request).
- `Env_Config/Human/RandomSpawn.py` applies one identical outer rigid transform
  to `/World/Human` and `/World/Chair`, pivoting around the original human root.
  It runs after pose baking, chair fitting, head rounding and collider creation,
  before physics initialization and world-space contact-cache construction.
  Local points, existing transforms, scale, height and human/chair relationship
  are preserved. Do not move randomization ahead of the geometry fitting code.
- Fresh entropy is used each launch; `HUMAN_SPAWN_SEED=<integer>` reproduces a
  placement. The effective seed is logged, including automatically chosen seeds.
  `P` preserves this run's placement.
- Default slots now use `output/states_randomspawn_mesh4` (or
  `states_randomspawn` with refinement disabled). Previous folders are preserved.
  Slots record human/chair world transforms. Loads reject mismatched placement
  or legacy slots without placement data before modifying simulation state.
  Cross-launch reuse requires the same seed/configuration; this avoids loading
  world-space cloth coordinates against a different static contact surface.
- Prepared `.runtime` from maintained source. CPU/USD checks passed for 1,000
  placements, distribution, rigid assembly, seed behavior and slot validation.
  GPU smoke passed with 13 descendants transformed together, exactly unchanged
  mesh points, zero-error checkpoint restoration and mismatched-slot rejection.
  All old scene report fields except the intended human world pose exactly
  match `original-smoke.json`.
- The earlier full-turn version's GUI visually verified the rotated whole body seated on the intact chair;
  isolated F1/F2 matrices confirmed `P` retains both human/chair placements.
  Escape closed the test session. Compact evidence is in
  `docs/verification-results/random-spawn.json`; screenshots and temporary slots
  are under ignored `output/verification/`. Logs:
  `/tmp/phyrc-randomspawn-{prepare,smoke,gui}.log`.
- Current +/-30-degree visual-mesh GUI verification also passed five fresh
  random placements, with yaw -27.667, +11.793, +19.699, +25.442, -18.965 degrees.
  All camera snapshots match, offsets stay within 10 cm, and screenshots were
  captured at ready +5.004..5.005 seconds. Run 5 was recaptured with its exact
  original seed after desktop-window occlusion; this was not a new random draw.
  Local gallery: `output/verification/randomspawn-five-runs/comparison.html`.

---

# Previous: Home-directory working clone and final verification

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
