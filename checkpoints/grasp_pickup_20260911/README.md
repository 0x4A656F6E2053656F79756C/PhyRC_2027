# First pickup policy

Experimental behavior-cloning policy: one robot starts from F1, picks up the
shirt, raises the grasped region and holds it. It uses privileged measured
coordinates plus scripted phase transitions. Native attachments remain enabled.
It is not an RL, RGB-D, dual-arm or complete dressing policy.

`policy.pt` contains PyTorch state dictionaries and metadata only; use
`torch.load(..., weights_only=True)`. Architecture: 11 → 64 → 64 → 5, tanh.
The exact feature/action mapping and planner version are in `scripts/train_grasp.py`.

183 demonstration transitions, 600 optimizer steps. Reloaded-weight evaluations
succeeded at the original target and with a 1 cm target shift: maximum grasped
region lift 9.12 cm and 9.20 cm, retaining at least 6 cm for one simulated second.
These are two narrow tests, not an estimated general success rate. `report.json`
contains source/input hashes and metrics. Full traces/data are local under
`output/grasp_learning_v2/`; original F1–F5 are independently backed up.

Evaluate this saved policy after preparing the runtime and supplying the preserved
stages described in `docs/GRASP_LEARNING_20260911.md`:

```bash
./run.sh train-single-grasp --no-randomization \
  --initial-slot /output/stage_review_20260911_161340/states/slot_F1.npz \
  --reference-slot /output/stage_review_20260911_161340/states/slot_F2.npz \
  --checkpoint /project/checkpoints/grasp_pickup_20260911/policy.pt \
  --output /output/grasp_reloaded
```
