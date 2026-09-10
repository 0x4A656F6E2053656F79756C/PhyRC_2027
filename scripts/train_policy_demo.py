"""Small real-scene behavior-cloning example; NOT a dressing success baseline.

Collect feedback-controller demonstrations, optimize a neural policy, then
compare untrained/trained closed-loop rollouts at a held-out lift target.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, '/project/src/DexGarmentLab')
import numpy as np
from Policy.environment import DressingEnv
from policy_cli import install_failure_handler
install_failure_handler()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seed', type=int, default=7)
parser.add_argument('--epochs', type=int, default=500)
parser.add_argument('--output', type=Path, default=Path('/output/train-demo'))
args = parser.parse_args()
if args.epochs < 1:
    parser.error('--epochs must be positive')
args.output.mkdir(parents=True, exist_ok=True)
(args.output/'report.json').write_text(json.dumps({'passed': False, 'status': 'running'}))
start = time.monotonic()
env = DressingEnv(profile='measured_state', max_episode_steps=32)
import torch  # Isaac registers its bundled Torch during SimulationApp startup.
torch.set_num_threads(1)
torch.manual_seed(args.seed)
policy = torch.nn.Sequential(torch.nn.Linear(2, 32), torch.nn.Tanh(), torch.nn.Linear(32, 1), torch.nn.Tanh())
initial_weights = {k: v.clone() for k, v in policy.state_dict().items()}


run_manifest = {}


def features(obs, goal, lift_index):
    # Named state fields, not a frozen flatten-all observation layout.
    return np.array([goal - obs['joint_position'][0, lift_index], goal - obs['controller_target'][0, 0]], np.float32)


def rollout(goal, *, expert=False, seed=123):
    obs, info = env.reset(seed=seed)
    joint_names = [j['name'] for j in info['state']['robots'][0]['joints']]
    lift_index = joint_names.index('lift_joint')
    lift_rate = info['state']['runtime_control_parameters']['LIFT_RATE']
    run_manifest.update(source_commit=info['source_commit'], source_sha256=info['source_sha256'], source_is_dirty=info['source_is_dirty'])
    trace = []
    for step in range(32):
        x = features(obs, goal, lift_index)
        if expert:
            a = float(np.clip(4 * x[1] / lift_rate, -.35, .35))
        else:
            with torch.no_grad():
                a = float(policy(torch.from_numpy(x)).item())
        action = np.zeros((2, 9), np.float32)
        action[0, 3] = a
        obs, _, terminated, truncated, info = env.step(action)
        trace.append([*x.tolist(), a, float(obs['joint_position'][0, lift_index]), goal])
        if terminated or truncated:
            break
    return np.asarray(trace, np.float32)


# A held-out goal is evaluated with identical placement before/after training.
untrained = rollout(.22)
print('TRAIN-DEMO untrained rollout complete', flush=True)
data = np.concatenate([rollout(goal, expert=True, seed=args.seed+i) for i, goal in enumerate((.12, .30))])
x, y = torch.from_numpy(data[:, :2]), torch.from_numpy(data[:, 2:3])
optimizer = torch.optim.Adam(policy.parameters(), lr=.01)
loss_before = float(torch.nn.functional.mse_loss(policy(x), y).detach())
for _ in range(args.epochs):
    loss = torch.nn.functional.mse_loss(policy(x), y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
loss_after = float(torch.nn.functional.mse_loss(policy(x), y).detach())
trained = rollout(.22)
untrained_error = float(np.abs(untrained[-8:, 3]-.22).mean())
trained_error = float(np.abs(trained[-8:, 3]-.22).mean())
report = {'task': 'robot_0 lift calibration; behavior cloning, not full dressing',
          'source_commit': run_manifest['source_commit'], 'source_is_dirty': run_manifest['source_is_dirty'], 'source_sha256': run_manifest['source_sha256'],
          'seed': args.seed, 'demonstration_transitions': len(data), 'epochs': args.epochs,
          'loss_before': loss_before, 'loss_after': loss_after, 'held_out_goal_m': .22,
          'untrained_final_window_mae_m': untrained_error, 'trained_final_window_mae_m': trained_error,
          'elapsed_wall_s': time.monotonic()-start,
          'passed': loss_after < loss_before and trained_error < untrained_error and trained_error < .03}
torch.save({'state_dict': policy.state_dict(), 'initial_state_dict': initial_weights,
            'inputs': ['goal_minus_measured_lift_m', 'goal_minus_commanded_lift_m'],
            'output': 'robot_0_normalized_lift_velocity', 'schema_version': env.contract['schema_version']}, args.output/'policy.pt')
np.savez_compressed(args.output/'trajectories.npz', demonstrations=data, untrained=untrained, trained=trained)
(args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print('TRAIN-DEMO ' + json.dumps(report), flush=True)
# Write result before SimulationApp.close(), whose fast shutdown can exit Python.
if not report['passed']:
    raise RuntimeError('Training demo failed its improvement/accuracy checks; see report.json')
env.close()
