# Policy learning and continuous dressing trials — 2026-09-11

**Current outcome:** both-robot pickup/lift is verified. Stable final arm insertion
with both robots or the one-robot fallback has not been achieved. The best
one-arm trial held a healthy geometric crossing for 2.35 seconds while moving,
but failed the final hold and did not reproduce reliably.

## Preserved baseline

GitHub tag `pre-grasp-learning-20260911` points to `d1c4552`, before learning
restoration. Inspect it without replacing current work:

```bash
git fetch origin --tags
git worktree add ../PhyRC_2027_pre_learning pre-grasp-learning-20260911
```

Prepare that checkout using its README. Original F1–F5 files, manifest and
archive are protected outside this project at:

`/home/seoyul/PhyRC_backups/dressing_stages_20260911_155147/`

[The hash manifest](verification-results/preserved-stages-20260911.json) records
all five files. Future F-key writes cannot overwrite this separate archive.
The snapshots are local, not included in GitHub. They predate friction changes;
restoring poses does not restore PhysX internal history or promise bitwise FEM
replay. Keep the archive independently backed up.

## Implemented scope

The Gymnasium environment, measured-state/RGB-D interface and historical lift
calibration example were restored from `e409213`. Only shared initialization
and optional numerical commands were extracted from the maintained teleop code;
keyboard callers retain their original path. See [POLICY_INTERFACE.md](POLICY_INTERFACE.md).

Current geometry, FEM64, contact guards and motion rates remain unchanged.
Gripper friction is 0.2; cloth/mannequin friction remains zero. Pickups use the
existing physical pinch eligibility and native FEM attachments, not externally
injected grasps. This is privileged-state behavior cloning with scripted phases,
not RL, a vision policy, or a completed F1–F5 dressing policy.

The maintained `train-grasp` command controls BOTH robots. Their phases are
raise, approach, lower, close, lift and hold. Both must actually attach before
lifting. Success requires each grabbed region to rise at least 6 cm relative
to the settled episode start, with both maintaining it for 2 seconds. Native
anchor p95 error must stay within 3.5 cm and active robots must stay upright
(tilt <0.25 rad). Final post-action state is checked too. A close command alone
never counts as a grasp.

The version-4 dual policy learns six positive axis gains plus a phase-dependent
gripper head from 650 real paired transitions. Zero tracking error produces
exactly zero continuous motion. This fixes the unwanted axis biases observed
in the initial dense network. The one-robot structured policy uses four or five
positive gains and the same explicit phase principle.

## Verified pickup checkpoints

| Checkpoint | Scope | Observed result |
|---|---|---|
| `checkpoints/grasp_pickup_20260911/` | Historical restored single hem pickup, MLP planner 1 | Original and +1 cm targets: 9.12/9.20 cm maximum lift, 1-second hold |
| `checkpoints/dual_pickup_20260911/` | Two-robot structured pickup, dual planner 4 | Repeated original-target pickups: about 9.2/9.8 cm, shared 2-second hold; +1 cm and −1 cm retests both passed |
| `checkpoints/cuff_pickup_20260911/` | One-robot structured cuff pickup, single planner 3 | Cuff corner: 8.8 cm, 1-second hold; same policy also acquired upper-middle cuff with longer commanded reach |

These are limited tests in the preserved scene, not a general success-rate
estimate. Each checkpoint directory contains weights and measured results.
Full datasets, traces, screenshots and separately named saved states are local
under `output/`. Failed attempts are retained.

## Continuous dressing verification

A continuation begins from the ACTUAL successful pickup, with no F2/F3/F4
restore between phases. Only a new full evaluation episode resets to F1.
Reports record episode IDs, monotonically advancing simulation time and zero
checkpoint loads during every carry/insertion phase.

`Policy/dressing_task.py` measures real native-anchor errors and anatomically
matched sleeve-cuff crossings. The arm segment starts near the elbow, using
the proximal 15% band of the posed forearm mesh, and ends at the hand centre.
The previous forearm-centre endpoint falsely rejected deeply inserted F4 cuffs.
The corrected diagnostic passes both known F4 sleeves and rejects F2.

Insertion requires the arm segment to cross the cuff plane inside its boundary,
with outward hand orientation and a planarity check. Current material trials
require 40 consecutive valid steps (2 seconds), healthy grasp, upright robot,
and zero independent visual-mesh edge/face intersections. Rendered front, side,
overhead and wide scene views are inspected before claiming success. Robot
pose agreement or cloth draped outside an arm is insufficient.

The material controller fits current native local anchors to saved garment
material coordinates, accounting for a newly acquired pinch orientation.
Damped IK uses real PhysX Jacobians and ordinary velocity actions. Shared path
progress pauses when a robot lags; base-heading/arm posture guidance avoids
unnecessary base motion into the mannequin. Arrival, grasp-health and upright
checks gate later phases. The requested raise is 1.25 m, within pitched-wrist
reach. The reference route reads F2, optional F3 and F4 garment goals.

The one-robot `thread` variant keeps the acquired cuff orientation after carry
and translates the open cuff along the measured anatomical arm axis. It uses
the current cuff geometry rather than imposing the failed F3 wrist rotation.
The revised variant first physically centres the cuff 16 cm ahead of the hand,
using up to three live feedback corrections. The current variant tracks the
measured cuff centre throughout insertion at 3 cm/s, with no lateral offset.
Its target is 65% along the elbow-to-hand segment. It retains the original
crossing and attachment-health thresholds; these are controller goals, not
changes to contact physics.
After 40 healthy crossing steps and a zero-intersection check, the latest
controller fixes the achieved gripper pose for 60 additional steps (3 seconds),
rather than continuing to force the cuff toward a deeper reference endpoint.
Only a successful physical continuation is used to fit task-space gains, then
a fresh F1 pickup and learned continuation are evaluated.

## Attempts retained

| Local directory | Outcome |
|---|---|
| `dual_grasp_probe_v1` | Flat second wrist missed the grasp; lift blocked |
| `dual_grasp_learning_v1` | Dense policy passed original/+1 cm but failed −1 cm approach; continuation blocked |
| `dual_continuous_v2` | Structured dual pickup passed; inspection joint-order inheritance error then stopped continuation |
| `dual_continuous_v3` | Both grasps retained through live F2/F3 motion; zero final visual intersections, but neither sleeve inserted |
| `dual_material_v1` | Both lifted; carry failed and robot 1 tipped over. One transient cuff crossing was not counted |
| `single_cuff_v1` | Flat-wrist cuff corner pickup failed at table contact |
| `single_cuff_v2` | Pitched-wrist physical teacher succeeded; dense learned policy stalled in preparation |
| `single_cuff_v3` | Structured cuff pickup succeeded; live carry/insertion reached gripper goals with healthy grasp but draped outside the arm |
| `single_cuff_v4` | Upper-middle cuff approach was blocked by the table with 0.30 m extension |
| `single_thread_v4` | Repeated F1 pickup/carry/alignment passed, but native anchor error exceeded 6 cm during hand entry; stopped before the success-hold gate, no stable insertion policy learned |
| `single_thread_v3` | Direct cuff feedback achieved 47 consecutive healthy crossing steps (2.35 s); hand passage visible. Further driving raised anchor error around the 3.5 cm limit; final hold failed, so no successful policy was claimed |
| `single_thread_v2` | Physical centring succeeded. Gripper path completed with healthy grasp, but the free cuff lagged and passed below/outside the forearm; all three reviewed views reject insertion |
| `single_thread_v1` | Fresh pickup and live carry succeeded, but the freely swinging cuff was misaligned; insertion was correctly blocked |
| `single_cuff_v5` | 0.42 m extension enabled actual upper-middle pickup. Opening projection increased from 0.00325 to 0.01114 m². Carry succeeded, but F3 motion exceeded 6 cm anchor error; insertion blocked |

The independent F2-reset prototype in `sleeve_learning_v1` was stopped after the
user clarified the continuous task. It is diagnostic only and never counts as
F1 pickup-to-insertion success.

## Run and reproduce

Close other Isaac sessions first. Prepare assets as described in the README;
install the restored dependency and synchronize source without regenerating
geometry when the current assets are already prepared:

```bash
export PHYRC_ACCEPT_EULA=1
./run.sh build
cp -a src/DexGarmentLab/. .runtime/DexGarmentLab/
./run.sh train-grasp --no-randomization \
  --initial-slot /output/stage_review_20260911_161340/states/slot_F1.npz \
  --reference-slot /output/stage_review_20260911_161340/states/slot_F2.npz \
  --checkpoint /project/checkpoints/dual_pickup_20260911/policy.pt \
  --output /output/dual_pickup_new
```

Default reload tests use the original target and ±1 cm offsets. To train anew,
omit `--checkpoint`; `--demonstrations` can reuse a verified real teacher dataset.
Use a fresh output directory. The upper-middle one-robot fallback is:

```bash
./run.sh train-single-grasp --no-randomization \
  --initial-slot /output/stage_review_20260911_161340/states/slot_F1.npz \
  --reference-slot /output/stage_review_20260911_161340/states/slot_F2.npz \
  --grasp-region left-cuff --cuff-point upper-middle \
  --pickup-pitch .4 --pickup-extension .42 \
  --checkpoint /project/checkpoints/cuff_pickup_20260911/policy.pt \
  --evaluation-shifts 0 --dressing-controller thread \
  --dressing-target /output/stage_review_20260911_161340/states/slot_F4.npz \
  --output /output/single_thread_new
```

Target transfer is explicitly recorded: these gain weights were trained at the
cuff corner with 0.30 m extension. No model feature or physical parameter is
silently substituted. `--dressing-controller material` selects reference material
waypoints; `reference` retains the earlier robot-pose proposal for comparison.

`./run.sh train-demo` remains only the historical lift-calibration example.
`policy-smoke --resolution 128 128 --output /output/policy_smoke_new` tests real
RGB-D freshness/depth, action semantics, resets and episode termination.
The CPU schema check is `python3 scripts/check_policy_contract.py`.
Structured-policy regression checks also verify exact zero motion at zero error,
signed 1 cm responses without unrelated-axis drift, and phase gates.

## Validation results

The full restored GPU environment smoke passed at 128×128. See
[smoke measurements](verification-results/policy-smoke-20260911.json).
`python3 scripts/check_pickup_policy.py` (with PyTorch installed) checks the
shipped structured weights without starting a simulator. Its
[CPU result](verification-results/pickup-policy-invariants-20260911.json) passed.
The schema checker, Python compilation, shell syntax and whitespace checks also
passed. Physical evaluation remains separate from these interface checks.

Representative reviewed views: [v2 outside-arm failure](verification-results/single-thread-v2-outside-arm.png)
and [v3 hand passage with unstable final grasp](verification-results/single-thread-v3-unstable-grasp.png).
Full numeric trial summaries are in [the continuous-dressing evidence](verification-results/continuous-dressing-20260911.json).

The revised dual policy also passed fresh +1 cm and −1 cm physical pickup
evaluations: final lifts 9.07/9.80 cm and 9.25/9.80 cm, respectively, with
both grasps healthy and a shared 2-second hold. These are five recorded tests
including three nominal repeats, not an arbitrary-scene success-rate estimate.
