"""Real GPU box support test: four seeded resets, 20 simulated seconds each.

Run via ./run.sh python /scripts/verify_garment_spawn.py. Produces measured
trajectories and equal-time renders; the HTML builder runs separately on host.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, '/project/src/DexGarmentLab')
import numpy as np
from Policy.environment import DressingEnv
from Policy.state import array
from policy_cli import install_failure_handler
install_failure_handler()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seconds', type=int, default=20)
args = parser.parse_args()
if args.seconds < 10:
    parser.error('Use at least 10 simulated seconds')
output = Path('/output/verification/garment-spawn')
output.mkdir(parents=True, exist_ok=True)
report = {'passed': False, 'status': 'running', 'episodes': []}
def save():
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
save()
# Initial launch must also use the sampler, not only the policy reset path.
os.environ['STRETCH4_GARMENT_SPAWN_SEED'] = '2'
os.environ['HUMAN_SPAWN_SEED'] = '42'
start = time.monotonic()
env = DressingEnv(profile='measured_state', max_episode_steps=args.seconds*20+1)
from Env_Config.Garment.RandomSpawn import sample_garment_spawn
from Policy.sensors import RGBDSensors
from pxr import UsdGeom
from PIL import Image
initial_spawn = deepcopy(env.backend.garment_spawn)
assert initial_spawn['table_index'] == 0
initial = array(env.cloths[0].get_world_positions())[0]
assert np.linalg.norm(initial.mean(0)[:2] - np.array(initial_spawn['table_center_world_m'])[:2]) < .1
mesh = UsdGeom.Mesh(env.cloths[0].prim)
local_points = np.array(mesh.GetPointsAttr().Get()).copy()
topology = np.array(mesh.GetFaceVertexIndicesAttr().Get()).copy()
config = deepcopy(env.contract)
config['default_dimensions'].update(width=960, height=540)
config['cameras'] = [dict(config['cameras'][0], id='box_verification',
                          eye_world_m=[0,-6,5.5], target_world_m=[0,-.9,.4])]
sensor = RGBDSensors(env.stage, env.world, env.rigs, config)
report.update(initial_launch=initial_spawn, seconds_per_episode=args.seconds,
              capture_times_since_restore_s=[1.5, 10, args.seconds],
              thresholds={'post_2s_centroid_drift_m':.01, 'minimum_xy_edge_clearance_m':0,
                          'minimum_height_above_table_m':-.01, 'post_2s_vertical_centroid_drift_m':.01},
              camera=config['cameras'][0], source_commit=env._source_commit,
              source_sha256=env._hashes, garment_local_points_sha256=hashlib.sha256(local_points.tobytes()).hexdigest(),
              topology_sha256=hashlib.sha256(topology.tobytes()).hexdigest())
original_tick = env._tick
trace = []
active = {'enabled': False, 'ticks':0}

def measure_tick(decoded):
    original_tick(decoded)
    if not active['enabled']:
        return
    active['ticks'] += 1
    points = array(env.cloths[0].get_world_positions())[0]
    if not np.isfinite(points).all():
        raise RuntimeError('Nonfinite cloth state')
    trace.append([active['ticks']/60, *points.mean(0).tolist(), *points.min(0).tolist(), *points.max(0).tolist()])
env._tick = measure_tick


def capture(label):
    values, cameras = sensor.capture()
    name = f'box_{env.garment_spawn["table_index"]+1}_{label}.png'
    Image.fromarray(values['rgb'][0]).save(output/name)
    return name

# These are first-found seeds from the same uniform sampler, not box overrides.
seeds = [2, 0, 11, 1]
reference = None
for expected, seed in enumerate(seeds):
    trace.clear()
    active.update(enabled=True, ticks=0)
    obs, info = env.reset(seed=seed)
    assert env.garment_spawn['table_index'] == expected
    assert env.garment_spawn == sample_garment_spawn(env.backend.garment_table_centers, env.M.BOX_SIZE, seed=seed)
    assert info['reset_settling']['cloth_restore_max_abs_m'] <= 1e-7
    reset_metrics = info['reset_settling']
    if expected == 0:
        reference = array(env.cloths[0].get_world_positions())
    pictures = {'1.5': capture('01_5s')}
    zero = np.zeros(env.action_space.shape, np.float32)
    for step in range(round((args.seconds-1.5)*20)):
        obs, reward, terminated, truncated, info = env.step(zero)
        assert not terminated and not truncated
        t = 1.5 + (step+1)*.05
        if np.isclose(t, 10): pictures['10'] = capture('10s')
        if np.isclose(t, args.seconds): pictures[str(args.seconds)] = capture('end')
    active['enabled'] = False
    data = np.asarray(trace)
    np.savez_compressed(output/f'box_{expected+1}_trace.npz', samples=data)
    center = np.array(env.garment_spawn['table_center_world_m'])
    size = np.array(env.garment_spawn['table_size_m'])
    low, high = center[:2]-size[:2]/2, center[:2]+size[:2]/2
    # All cloth vertices, not just the centroid, must remain supported.
    edge = np.minimum(data[:,4:6]-low, high-data[:,7:9]).min(axis=1)
    height = data[:,6] - (center[2]+size[2]/2)
    late = data[data[:,0] >= 2-1e-8]
    xy_drift = np.linalg.norm(late[:,1:3]-late[0,1:3], axis=1)
    z_drift = np.abs(late[:,3]-late[0,3])
    passed = bool(edge.min() >= 0 and height.min() >= -.01 and xy_drift.max() <= .01 and z_drift.max() <= .01)
    episode = {'seed':seed, 'spawn':deepcopy(env.garment_spawn), 'pictures':pictures,
               'samples':len(data), 'duration_s':float(data[-1,0]),
               'minimum_xy_edge_clearance_m':float(edge.min()), 'minimum_height_above_table_m':float(height.min()),
               'post_2s_centroid_drift_m':float(xy_drift.max()), 'post_2s_vertical_centroid_drift_m':float(z_drift.max()),
               'final_centroid_world_m':data[-1,1:4].tolist(), 'reset_settling':reset_metrics,
               'passed':passed}
    report['episodes'].append(episode)
    save()
    print('GARMENT-BOX-RESULT '+json.dumps(episode), flush=True)
    # Keep measuring other boxes even if one fails; overall failure stays visible.

# Return to the first seed after visiting all boxes: no cumulative translation.
obs, info = env.reset(seed=2)
repeat_error = float(np.abs(array(env.cloths[0].get_world_positions())-reference).max())
assert env.garment_spawn == initial_spawn
assert repeat_error < .005
assert np.array_equal(local_points, mesh.GetPointsAttr().Get())
assert np.array_equal(topology, mesh.GetFaceVertexIndicesAttr().Get())
report.update(repeat_seed_cloth_max_abs_m=repeat_error, local_mesh_and_topology_unchanged=True,
              elapsed_wall_s=time.monotonic()-start, status='complete',
              passed=all(row['passed'] for row in report['episodes']))
save()
print('GARMENT-SPAWN-GPU '+str(report['passed']), flush=True)
if not report['passed']:
    raise RuntimeError('Garment support/drift check failed; see the per-box report')
sensor.close()
env.close()
