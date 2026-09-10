"""GPU integration checks. Artifacts are saved before Isaac's fast shutdown."""
import argparse
import json
import sys
from pathlib import Path
import time
sys.path.insert(0, '/project/src/DexGarmentLab')
import numpy as np
from Policy.environment import DressingEnv
from policy_cli import install_failure_handler
install_failure_handler()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--resolution', nargs=2, type=int, default=[256, 256], metavar=('WIDTH', 'HEIGHT'))
args = parser.parse_args()
output = Path('/output/policy-smoke')
output.mkdir(exist_ok=True)
(output/'report.json').write_text(json.dumps({'passed': False, 'status': 'running'}))
start = time.monotonic()
env = DressingEnv(max_episode_steps=8, resolution=tuple(args.resolution))
cx, cy = args.resolution[0] // 2, args.resolution[1] // 2
obs, info = env.reset(seed=42)
assert env.observation_space.contains(obs)
print('POLICY reset ready', flush=True)
report = {'passed': False, 'initial': info}
for i in range(3):
    from PIL import Image
    Image.fromarray(obs['rgb'][i]).save(output / f'camera_{i}.png')
    assert obs['depth_valid'][i].mean() > .01, (i, 'empty depth')
    assert obs['rgb'][i].std() > 2, (i, 'empty rgb')
np.savez_compressed(output/'reset.npz', **obs)
first_matrix = info['state']['static']
first_q = obs['joint_position'].copy()
first_cloth = [c.get_world_positions().clone() for c in env.cloths]
first_rgb = obs['rgb'].copy()
first_t = float(obs['simulation_time_s'])
for invalid in (np.zeros((2, 8), np.float32), np.full((2, 9), np.nan, np.float32), np.ones((2, 9), np.float64)):
    try:
        env.step(invalid)
        raise AssertionError('Invalid action accepted')
    except ValueError:
        pass
assert float(env.world.current_time) == first_t
# Independent metric-depth check using a camera-aligned 20 cm test cube.
from pxr import UsdGeom, Gf
cube = UsdGeom.Cube.Define(env.stage, '/World/PolicyDepthProbe')
cube.CreateSizeAttr(.2)
cube.CreateDisplayColorAttr([(1, 0, 0)])
optical = np.array(info['cameras'][0]['world_from_optical_column_vectors'])
probe_pose = optical.copy()
probe_pose[:3, 3] += optical[:3, 2]
op = cube.AddTransformOp()
op.Set(Gf.Matrix4d(probe_pose.T.tolist()))
probe, _ = env.sensors.capture()
center = float(probe['depth'][0, cy, cx, 0])
assert abs(center - .9) < .015, center
# Changing geometry at the same physics timestamp must refresh RGB AND depth.
probe_pose[:3, 3] += optical[:3, 2] * .3
op.Set(Gf.Matrix4d(probe_pose.T.tolist()))
probe2, _ = env.sensors.capture()
center2 = float(probe2['depth'][0, cy, cx, 0])
assert abs(center2 - 1.2) < .015, center2
assert np.mean(np.abs(probe['rgb'].astype(float)-probe2['rgb'].astype(float))) > .01
assert float(env.world.current_time) == first_t
report['depth_probe_m'] = [center, center2]
env.stage.RemovePrim('/World/PolicyDepthProbe')
act = np.zeros((2,9), np.float32)
act[0,3] = .25
act[0,8] = 1
for step in range(8):
    nxt, reward, terminated, truncated, info = env.step(act)
    assert env.observation_space.contains(nxt)
    assert not terminated and truncated == (step == 7)
    assert nxt['gripper_close_command'][0,0] and not nxt['gripper_close_command'][1,0]
    assert np.isclose(float(nxt['simulation_time_s']) - first_t, (step+1)*.05, atol=1e-6)
assert nxt['controller_target'][0,0] > .13 and nxt['controller_target'][1,0] == 0
assert nxt['joint_position'][0,3] - first_q[0,3] > .03
report['lift_delta_m'] = float(nxt['joint_position'][0,3] - first_q[0,3])
report['after_action'] = info
assert np.mean(np.abs(nxt['rgb'][1].astype(float)-first_rgb[1].astype(float))) > .1
np.savez_compressed(output/'after_action.npz', **nxt)
try:
    env.step(act)
    raise AssertionError('Step after truncation accepted')
except RuntimeError:
    pass
obs2, info2 = env.reset(seed=43)
if info['human_spawn']['randomized']:
    assert info2['state']['static'] != first_matrix
else:
    assert info2['state']['static'] == first_matrix
    for reset_info in (info, info2):
        assert reset_info['human_spawn']['offset_m'] == [0, 0, 0]
        assert reset_info['human_spawn']['yaw_deg'] == 0
        assert reset_info['garment_spawn']['table_index'] == 2
        assert reset_info['garment_spawn']['randomized'] is False
    assert info2['garment_spawn'] == info['garment_spawn']
    fixed_error = max(float((c.get_world_positions()-first).abs().max())
                      for c, first in zip(env.cloths, first_cloth))
    assert fixed_error < .005
    report['different_seed_fixed_cloth_max_abs_m'] = fixed_error
obs3, info3 = env.reset(seed=42)
assert info3['state']['static'] == first_matrix
assert not obs3['gripper_close_command'].any()
report['repeat_seed_q_max_abs'] = float(np.max(np.abs(obs3['joint_position']-first_q)))
assert report['repeat_seed_q_max_abs'] < 1e-5
report['repeat_seed_cloth_max_abs'] = max(float((c.get_world_positions()-first).abs().max()) for c, first in zip(env.cloths, first_cloth))
print('POLICY repeated reset cloth max error', report['repeat_seed_cloth_max_abs'], flush=True)
# FEM settling is numerically sensitive even on one GPU. Require a bounded
# 5 mm restart envelope, while checking the pre-settle restore separately.
assert info3['reset_settling']['cloth_restore_max_abs_m'] <= 1e-7
assert report['repeat_seed_cloth_max_abs'] < .005
# Exercise every continuous channel and deferred, idempotent close/open.
env.max_episode_steps = 60
action = np.zeros((2,9), np.float32)
action[0, [0,1,2,4,5,6,7]] = [.15,.12,.10,.12,.08,-.08,.08]
action[0,8] = 1
for _ in range(32):
    motion, _, _, _, mi = env.step(action)
assert not env.rigs[0]['state'].get('pending_grab')
assert motion['gripper_close_command'][0,0]
assert np.linalg.norm(motion['base_pose_world'][0,:2]-obs3['base_pose_world'][0,:2]) > .02
for column in (1,2,3,4):
    assert abs(motion['controller_target'][0,column]) > .05
assert np.max(np.abs(motion['controller_target'][1,:5])) == 0
release = np.zeros((2,9), np.float32)
release[0,8] = -1
for _ in range(20):
    opened, _, _, _, _ = env.step(release)
    assert not opened['gripper_close_command'][0,0]
assert env.rigs[0]['state'].get('grabbed') is None
assert abs(opened['joint_position'][0,11] - env.M.GRIPPER_OPEN) < .03, opened['joint_position'][0,11:13]
report['multi_axis_state'] = mi
# Task evaluator termination is distinct from a time limit.
env.evaluator = lambda prev, action, nxt, info: (1., True, {'success_evaluated': True, 'success': True})
_, reward, terminated, truncated, info = env.step(np.zeros((2,9), np.float32))
assert reward == 1 and terminated and not truncated
assert info['termination_reason'] == 'task_evaluator' and info['success_evaluated']
report.update(passed=True, elapsed_wall_s=time.monotonic()-start, reset_repeat=info3)
(output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
print('POLICY-SMOKE-PASS ' + str(output/'report.json'), flush=True)
env.close()
