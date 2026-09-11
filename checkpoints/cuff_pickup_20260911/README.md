# One-robot cuff pickup policy

The user-authorized fallback picks a sleeve corner with robot 0; robot 1 is idle.
A 241-transition real demonstration trained a structured policy with five
positive learned gains and a phase-dependent gripper head. Inputs include
measured cloth position and a scripted phase. Wrist pitch is 0.4 rad. Native
attachments and production contact settings remain unchanged.

Reloaded weights picked up from F1 and held a measured 8.8 cm lift for 1 second.
`evaluation.json` contains the actual attachment and lift measurements. This
checkpoint verifies pickup only; continuous insertion results are documented
separately in `docs/GRASP_LEARNING_20260911.md`. It is not RL or a vision policy.

```bash
./run.sh train-single-grasp --no-randomization \
  --initial-slot /output/stage_review_20260911_161340/states/slot_F1.npz \
  --reference-slot /output/stage_review_20260911_161340/states/slot_F2.npz \
  --grasp-region left-cuff --pickup-pitch .4 \
  --checkpoint /project/checkpoints/cuff_pickup_20260911/policy.pt \
  --evaluation-shifts 0 --output /output/cuff_pickup_reloaded
```

The same structured gains also passed upper-middle cuff pickup with a 0.42 m
extension target in `single_cuff_v5` and `single_thread_v1` (about 8.75 cm lift).
These targets differ from the training demonstration; use `--cuff-point
upper-middle --pickup-extension .42` and keep `--pickup-pitch .4`. The runner
records this target transfer explicitly. This does not establish insertion.
