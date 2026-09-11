#!/usr/bin/env python3
"""CPU regression checks for the shipped structured pickup policies.

Requires PyTorch, but does not start Isaac or perform a physical success test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/DexGarmentLab"))

import torch
from Policy.pickup_policy import make_dual_pickup_policy, make_single_pickup_policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [
        ("dual", "dual_pickup_20260911", make_dual_pickup_policy(), 13, 7, 6, [0, 1, 2, 3, 4, 5]),
        ("cuff", "cuff_pickup_20260911", make_single_pickup_policy(True), 12, 5, 4, [0, 1, 2, 3, 5]),
    ]
    results = []
    for name, directory, model, width, phase_start, grip, motion in cases:
        path = ROOT / "checkpoints" / directory / "policy.pt"
        data = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(data["model"])
        model.eval()
        x = torch.zeros(6, width)
        x[torch.arange(6), phase_start + torch.arange(6)] = 1
        with torch.no_grad():
            y = model(x)
        assert torch.count_nonzero(y[:, motion]) == 0, (name, "zero-error drift", y)
        assert (y[:3, grip] < -.5).all() and (y[3:, grip] > .5).all(), (name, "gripper phase", y)
        for sign in (-1, 1):
            trial = x[1].clone()
            trial[0] = sign * .05  # Position errors are normalized by 5.
            with torch.no_grad():
                action = model(trial)
            assert sign * action[0] > 0, (name, "wrong tracking direction")
            assert torch.count_nonzero(action[[i for i in motion if i != 0]]) == 0, (name, "cross-axis drift")
        for phase in (0, 5):
            trial = x[phase].clone()
            trial[:2] = .3
            with torch.no_grad():
                action = model(trial)
            assert torch.count_nonzero(action[:2]) == 0, (name, "phase gate")
        results.append({
            "policy": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "zero_error_zero_motion": True,
            "signed_1cm_response_without_other_axis_motion": True, "phase_gates": True,
        })
    report = {"passed": True, "scope": "CPU policy invariants; not physical task success", "results": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
