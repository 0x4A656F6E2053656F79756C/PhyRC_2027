"""Measure the unmodified teleop scene at startup and after 60 neutral ticks.

Run: PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/inspect_policy_scene.py
This is a read-only policy inspection hook, not a reset/step learning env.
The ordinary main loop runs unchanged; F1 writes use an isolated temporary dir.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

output = Path('/output/policy-inspection')
output.mkdir(parents=True, exist_ok=True)
os.environ['STRETCH4_STATE_DIR'] = tempfile.mkdtemp(prefix='states_', dir=output)
os.environ.pop('STRETCH4_LOAD_SLOT', None)
os.environ['STRETCH4_SHOW_COLLIDER'] = '0'
sys.path.insert(0, '/project/src/DexGarmentLab')
import numpy as np
from Policy.state import snapshot
from Policy.contract import load_contract, pack_measured_state
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M

context = {'stop': False, 'ticks': 0}
contract_path = Path('/project/config/policy_interface.json')
contract = load_contract(contract_path)
report = {'passed': False, 'scope': 'read-only live state inspection; startup and 60 neutral control ticks',
          'source_sha256': hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),
          'contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest(), 'snapshots': {}}
original_save, original_record, original_running = M.save_state_slot, M.record_frame, M.simulation_app.is_running
original_spawn = M.randomize_human_and_chair


def spawn(stage, human_path):
    result = original_spawn(stage, human_path)
    report['human_spawn'] = result
    return result


def write_report():
    # SimulationApp.close() may fast-exit the process without Python finally.
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


def measure(label):
    metadata, values = snapshot(M, context['cloths'], context['rigs'])
    assert metadata['all_arrays_finite'], 'Nonfinite live state'
    observation = pack_measured_state(metadata, contract)
    metadata['observation_shapes'] = {key: list(value.shape) for key, value in observation.items()}
    metadata['control_ticks_since_startup'] = context['ticks']
    report['snapshots'][label] = metadata
    np.savez_compressed(output / (label+'.npz'), **values)
    np.savez_compressed(output / (label+'_observation.npz'), **observation)
    write_report()
    print(f'POLICY-INSPECT: {label}: '+json.dumps([
        {'id': r['id'], 'joints': r['joint_count'], 'grasp_xyz': r['links']['grasp_center']['pose_world'][:3],
         'tip_distance_m': r['fingertip_origin_distance_m']} for r in metadata['robots']]), flush=True)


def save(key, cloths, rigs):
    result = original_save(key, cloths, rigs)
    if key == 'F1' and 'cloths' not in context:
        assert result
        context.update(cloths=cloths, rigs=rigs)
        measure('startup')
    return result


def record():
    original_record()
    context['ticks'] += 1
    if context['ticks'] == 60:
        measure('after_60_ticks')
        report['passed'] = True
        context['stop'] = True
        write_report()
        print('POLICY-INSPECTION-PASS '+str(output/'report.json'), flush=True)


M.save_state_slot, M.record_frame = save, record
M.randomize_human_and_chair = spawn
M.simulation_app.is_running = lambda: not context['stop'] and original_running()
try:
    M.main()
finally:
    write_report()
if not report['passed']:
    raise SystemExit('Inspection did not finish')
print('POLICY-INSPECTION-PASS '+str(output/'report.json'), flush=True)
