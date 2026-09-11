# Two-robot pickup policy

Planner version 4, structured PyTorch policy with six positive learned axis gains
and a learned gripper head. Both robots start unattached at F1. Scripted phases
coordinate their approach, close, lift and hold. It uses measured cloth state and
the existing native attachments. This is behavior cloning, not RL or a complete
dressing policy.

Weights were fit to 650 actual paired transitions. `evaluations.json` records
reloaded-weight tests: each robot must lift its grasped cloth region at least
6 cm and both must retain it for 2 seconds with healthy native anchors.
Full datasets/traces are local under `output/`; original F1–F5 are independently
protected. This checkpoint alone does not contain those user states.

```bash
./run.sh train-grasp --no-randomization \
  --initial-slot /output/stage_review_20260911_161340/states/slot_F1.npz \
  --reference-slot /output/stage_review_20260911_161340/states/slot_F2.npz \
  --checkpoint /project/checkpoints/dual_pickup_20260911/policy.pt \
  --output /output/dual_pickup_reloaded
```

Use a fresh output directory. The default reload evaluation tests the original
target and ±1 cm offsets. Every individual attempt checks BOTH grasps. Finite
tests do not guarantee success in arbitrary scenes. See
`docs/GRASP_LEARNING_20260911.md` for continuous dressing attempts and limits.

The shipped weights passed all five recorded physical evaluations: three
nominal repeats, +1 cm and −1 cm. Offset final lifts were 9.07/9.80 cm and
9.25/9.80 cm, with both native grasps healthy and a shared 2-second hold.
