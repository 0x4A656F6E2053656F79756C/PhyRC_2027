"""Offline contract/frame checks; optionally validate a real inspection report."""
import argparse
import copy
import json
from pathlib import Path
import sys

import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'src/DexGarmentLab'))
from Policy.contract import (load_contract, observation_shapes, validate_observation,
                             pack_measured_state, decode_action, resolve_gripper_intent)
from Policy.state import rotation, relative_pose

parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path)
args = parser.parse_args()
contract = load_contract(root/'config/policy_interface.json')


def rejects(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('Invalid input was accepted')


# Configuration changes resize image layouts without touching Python or physics.
changed = copy.deepcopy(contract)
changed['default_dimensions'].update(height=128, width=320)
assert observation_shapes(changed, robots=1, joints=17, profile='actor_rgbd')['rgb'] == (3, 128, 320, 3)
assert observation_shapes(changed, robots=1, joints=17)['joint_position'] == (1, 17)

# Independent, known coordinate example: base +90 Z, world +Y is base +X.
s = np.sqrt(0.5)
base = np.array([1, 2, 3, s, 0, 0, s])
point = np.array([1, 3, 3, 1, 0, 0, 0])
relative = relative_pose(base, point)
assert np.allclose(relative[:3], [1, 0, 0], atol=1e-12)
assert np.allclose(rotation(base[3:]) @ rotation(relative[3:]), np.eye(3), atol=1e-12)
assert np.allclose(relative_pose(base, base), [0, 0, 0, 1, 0, 0, 0], atol=1e-12)
rejects(lambda: rotation([0, 0, 0, 0]))

rates = dict(BASE_LINEAR_RATE=.56, BASE_ANGULAR_RATE=2.6, LIFT_RATE=1.4, ARM_RATE=1.1, WRIST_RATE=5.0)
action = np.zeros((2, 9), dtype=np.float32)
action[0, [1, 3, 8]] = [.5, .25, 1]
decoded = decode_action(action, contract, rates)
assert decoded[0]['velocity_commands']['base_strafe'] == -.28
assert decoded[0]['velocity_commands']['lift_rate'] == .35
assert decoded[0]['gripper_intent'] == 'close'
assert all(v == 0 for v in decoded[1]['velocity_commands'].values())
closed = False
for _ in range(5):
    closed = resolve_gripper_intent(closed, 'close')
assert closed and resolve_gripper_intent(closed, 'hold')
assert not resolve_gripper_intent(closed, 'open')
rejects(lambda: decode_action(np.zeros((18,), np.float32), contract, rates))
rejects(lambda: decode_action(np.ones((2, 9), np.float32)*1.01, contract, rates))
rejects(lambda: decode_action(np.full((2, 9), np.nan, np.float32), contract, rates))

if args.report:
    report = json.loads(args.report.read_text())
    assert report['passed']
    for label, snapshot in report['snapshots'].items():
        packed = pack_measured_state(snapshot, contract)
        r, j = packed['joint_position'].shape
        for robot in snapshot['robots']:
            base = np.array(robot['base_pose_world'])
            for link in robot['links'].values():
                local, world = np.array(link['pose_base']), np.array(link['pose_world'])
                assert np.allclose(base[:3]+rotation(base[3:])@local[:3], world[:3], atol=1e-7)
                assert np.allclose(rotation(base[3:])@rotation(local[3:]), rotation(world[3:]), atol=1e-7)
            assert all(joint['unit'] in ('m', 'rad') for joint in robot['joints'])
        # A missing camera stream must fail an RGB-D profile, not produce dummy images.
        rejects(lambda: validate_observation(packed, contract, robots=r, joints=j, profile='actor_rgbd'))
        invalid = dict(packed, base_pose_world=packed['base_pose_world'][:, :3])
        rejects(lambda: validate_observation(invalid, contract, robots=r, joints=j))
        np.savez_compressed(args.report.parent/(label+'_observation.npz'), **packed)
        print(f'{label}: verified {r} robots, {j} named joints each, actual/FK poses and typed arrays')
    start, end = [report['snapshots'][key] for key in ('startup', 'after_60_ticks')]
    assert abs(end['simulation_time_s']-start['simulation_time_s']-1) < 1e-5
    assert abs(end['physics_dt_s']-1/240) < 1e-12
print('POLICY-CONTRACT-PASS: configurable dimensions, frames, action units/signs, idempotent gripper intent and invalid-input rejection')
