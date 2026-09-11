"""Collect a physical F1 pickup demonstration and fit/evaluate an imitation policy.

Privileged cloth coordinates, one active robot, scripted task phases. This is
an initial pickup curriculum, not RGB-D learning or an F1-to-F5 dressing policy.
No checkpoint is loaded during a rollout; only episode resets restore state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, '/project/src/DexGarmentLab')
from Policy.environment import DressingEnv
from Policy.state import array, rotation
from policy_cli import install_failure_handler
install_failure_handler()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--initial-slot', required=True, type=Path)
parser.add_argument('--reference-slot', required=True, type=Path)
parser.add_argument('--output', type=Path, default=Path('/output/grasp-learning'))
parser.add_argument('--probe-only', action='store_true')
parser.add_argument('--dressing-target', type=Path, help='Continue successful pickup toward this stage without loading it')
parser.add_argument('--dressing-controller', choices=('reference','material','thread'), default='material')
parser.add_argument('--orient-cuff', action='store_true', help='Experimental live mouth-normal feedback with the thread controller')
parser.add_argument('--release-after-insertion', action='store_true', help='After verified hand passage, physically open/retreat and check that the sleeve stays on the arm')
parser.add_argument('--grasp-region', choices=('reference','left-cuff','right-cuff'), default='reference')
parser.add_argument('--cuff-point', choices=('corner','upper-middle'), default='corner')
parser.add_argument('--pickup-pitch', type=float, default=0., help='Learn wrist pitch as an extra action when nonzero')
parser.add_argument('--pickup-extension', type=float, default=.3, help='Total arm extension goal in metres')
parser.add_argument('--evaluation-shifts', nargs='+', type=float, default=[0., .01])
parser.add_argument('--epochs', type=int, default=600)
parser.add_argument('--checkpoint', type=Path, help='Evaluate saved weights without collecting or training')
parser.add_argument('--demonstrations', type=Path, help='Reuse a verified real teacher demonstration')
args = parser.parse_args()
if args.epochs < 1:
    parser.error('--epochs must be positive')
if args.probe_only and args.checkpoint:
    parser.error('--probe-only and --checkpoint are mutually exclusive')
if (args.orient_cuff or args.release_after_insertion) and args.dressing_controller!='thread':
    parser.error('Cuff orientation and release probes require --dressing-controller thread')
out = args.output
out.mkdir(parents=True, exist_ok=True)
inputs = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.initial_slot, args.reference_slot)}
report = {'status': 'starting', 'success': False, 'inputs_sha256': inputs,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope': 'robot 0 pickup from F1, measured-state imitation, scripted phase sequencing',
          'physics': 'current production FEM, grasp attachments, guards and friction; no overrides'}
(out/'report.json').write_text(json.dumps(report, indent=2))
(out/'train_grasp_source.py').write_text(Path(__file__).read_text())
previous_exception_hook = sys.excepthook


def record_failure(kind, value, traceback):
    report.update(status='error', success=False, error=f'{kind.__name__}: {value}')
    (out/'report.json').write_text(json.dumps(report, indent=2))
    previous_exception_hook(kind, value, traceback)


sys.excepthook = record_failure
env = DressingEnv(profile='measured_state', initial_slot=args.initial_slot, max_episode_steps=500)
if not env.rigs[0]['arm_lo'] <= args.pickup_extension <= env.rigs[0]['arm_hi']:
    raise ValueError('Pickup extension is outside the current robot joint limits')
import torch  # Isaac must initialize first.
torch.set_num_threads(2)
torch.manual_seed(7)
with np.load(args.reference_slot) as data:
    target_ids = data['r0_grab_idx'].copy()
if args.grasp_region != 'reference':
    from Policy.dressing_task import DressingInspection
    inspector = DressingInspection(env, out)
    calibration={}
    for path in (args.reference_slot,args.dressing_target):
        if path is not None:
            with np.load(path) as data:calibration[str(path)]=inspector.measure(points=data['g0_pos'])
    (out/'cuff_reference_diagnostics_pickup.json').write_text(json.dumps(calibration,indent=2))
    ids = inspector.cuffs[0 if args.grasp_region == 'left-cuff' else 1]
    with np.load(args.initial_slot) as data:
        points = data['g0_pos']
        # Grasp the cuff corner nearest the hem, leaving the rest of the opening free.
        corner = points[ids[np.argmax(points[ids, 1])]]
        if args.cuff_point == 'upper-middle':
            central=ids[np.abs(points[ids,1]-points[ids,1].mean())<.02]
            corner=points[central[np.argmax(points[central,2])]]
        upper = np.where(points[:, 2] >= np.median(points[ids, 2]))[0]
        target_ids = upper[np.argsort(np.linalg.norm(points[upper]-corner, axis=1))[:48]]
    inspector.close()
report['grasp_region'] = args.grasp_region
report['cuff_point'] = args.cuff_point
report['pickup_pitch_rad'] = args.pickup_pitch
report['pickup_extension_m'] = args.pickup_extension
report['target_material_ids'] = target_ids.tolist()


def rollout(name, model=None, shift=0.):
    obs, info = env.reset(seed=7)
    if any(r['grasp_attached'] or r['native_attachment_present'] for r in info['state']['robots']):
        raise ValueError('Pickup episodes must start with both grippers unattached')
    initial = array(env.cloths[0].get_world_positions())[0]
    if len(target_ids) == 0 or target_ids.min() < 0 or target_ids.max() >= len(initial):
        raise ValueError('Reference grasp indices differ from the current cloth topology')
    phase, phase_steps, hold_steps = 0, 0, 0
    samples, traces = [], []
    initial_lift = None
    for step in range(500):
        r = info['state']['robots'][0]
        points = array(env.cloths[0].get_world_positions())[0]
        tip = np.asarray(r['fingertip_midpoint_world'])
        target = points[target_ids].mean(0).astype(float)
        target[0] += shift
        base_rot = rotation(np.array(r['base_pose_world'])[3:])
        base_tilt = float(np.arccos(np.clip(base_rot[2,2],-1,1)))
        state = env.rigs[0]['state']
        attached = bool(r['grasp_attached'] and r['native_attachment_present'])
        target_z = float(initial[target_ids, 2].mean())
        # Raise before advancing into the table; then descend gently into reach.
        if phase <= 1:
            target[2] = target_z + .18
        elif phase <= 3:
            target[2] = target_z + .025
        else:
            target[2] = target_z + .14
        error = target - tip
        local = base_rot.T @ error
        pitch_error=args.pickup_pitch-state['pitch']
        if phase == 0 and abs(error[2]) < .025 and abs(state['arm']-args.pickup_extension) < .015 and abs(pitch_error)<.025:
            phase, phase_steps = 1, 0
        if phase == 1 and np.linalg.norm(error[:2]) < .015:
            phase, phase_steps = 2, 0
        # Use the lowering goal even on the transition from approach: `error`
        # above still refers to the raised goal for that one policy tick.
        if phase == 2 and abs(tip[2] - (target_z + .025)) < .015:
            phase, phase_steps = 3, 0
        if phase == 3 and attached:
            phase, phase_steps = 4, 0
            initial_lift = float(tip[2])
        if phase == 3 and phase_steps > 50 and not attached:
            break
        grab = state.get('grabbed')
        lifted = 0.
        if attached and grab is not None:
            indices = array(grab[1]).astype(int)
            lifted = float(np.median(points[indices, 2] - initial[indices, 2]))
        if phase == 4 and lifted >= .06:
            phase, phase_steps = 5, 0
        from Policy.dressing_task import grasp_health
        health = grasp_health(env)[0]
        healthy = health['attached'] and health['anchor_p95_error_m'] is not None and health['anchor_p95_error_m'] <= .035
        hold_steps = hold_steps + 1 if phase == 5 and attached and lifted >= .06 and healthy and base_tilt<.25 else 0
        # Desired tip error is observed feedback. The phase planner is explicit.
        feature = np.r_[local * 5, (state['arm']-args.pickup_extension)*5, float(attached), np.eye(6)[phase]].astype(np.float32)
        if args.pickup_pitch:feature=np.r_[feature,pitch_error].astype(np.float32)
        expert = np.zeros(6 if args.pickup_pitch else 5, np.float32)
        if phase in (1, 2, 3):
            expert[:2] = np.clip(local[:2]*2/env.M.BASE_LINEAR_RATE, -.25, .25)
        expert[2] = np.clip(error[2]*2/env.M.LIFT_RATE, -.3, .3)
        expert[3] = np.clip((args.pickup_extension-state['arm'])*3/env.M.ARM_RATE, -.3, .3)
        expert[4] = 1 if phase >= 3 else -1
        if args.pickup_pitch:expert[5]=np.clip(pitch_error*3/env.M.WRIST_RATE,-.2,.2)
        if phase == 5:
            expert[:4] = 0
            if args.pickup_pitch:expert[5]=0
        samples.append((feature, expert))
        if model is None:
            chosen = expert
        else:
            with torch.no_grad():
                chosen = model(torch.from_numpy(feature)).numpy()
        action = np.zeros((2, 9), np.float32)
        action[0, [0, 1, 3, 4, 8, 6] if args.pickup_pitch else [0, 1, 3, 4, 8]] = np.clip(chosen, -1, 1)
        # No externally injected grasp, no motion or attachments on robot 1.
        obs, reward, terminated, truncated, info = env.step(action)
        row = {'step': step, 'phase': phase, 'tip': tip.tolist(), 'target': target.tolist(),
               'attached': attached, 'lift_m': lifted, 'hold_steps': hold_steps, 'grasp_health': health, 'base_tilt_rad':base_tilt,
               'error_m': float(np.linalg.norm(error)), 'action': action[0].tolist()}
        traces.append(row)
        if step % 20 == 0 or hold_steps == 20:
            print('GRASP', name, json.dumps(row), flush=True)
            (out/(name+'_progress.json')).write_text(json.dumps(row, indent=2))
        phase_steps += 1
        if hold_steps >= 20 or terminated or truncated:
            break
    final_health=grasp_health(env)[0]
    grab=env.rigs[0]['state'].get('grabbed')
    ids=array(grab[1]).astype(int) if grab is not None else np.array([],int)
    final_points=array(env.cloths[0].get_world_positions())[0]
    final_lift=float(np.median(final_points[ids,2]-initial[ids,2])) if len(ids) else 0.
    final_tilt=float(np.arccos(np.clip(rotation(np.asarray(info['state']['robots'][0]['base_pose_world'])[3:])[2,2],-1,1)))
    result = {'success': hold_steps >= 20 and final_health['attached'] and final_health['anchor_p95_error_m']<=.035 and final_lift>=.06 and final_tilt<.25,
              'final_base_tilt_rad':final_tilt,
              'final_grasp_health':final_health,'final_lift_m':final_lift,'steps': len(traces), 'last_phase': phase,
              'max_lift_m': max((r['lift_m'] for r in traces), default=0),
              'max_hold_steps': max((r['hold_steps'] for r in traces), default=0),
              'ever_attached': any(r['attached'] for r in traces), 'target_shift_m': shift,
              'initial_lift_tip_z': initial_lift}
    (out/(name+'.json')).write_text(json.dumps({'result': result, 'trace': traces}, indent=2))
    np.savez_compressed(out/(name+'_final.npz'), cloth=array(env.cloths[0].get_world_positions()), **obs)
    previous = env.M.STATE_DIR
    try:
        env.M.STATE_DIR = str(out/'states')
        if not env.M.save_state_slot(name.upper(), env.cloths, env.rigs):
            raise RuntimeError('Failed to save the separate rollout checkpoint')
    finally:
        env.M.STATE_DIR = previous
    print('GRASP_RESULT', name, json.dumps(result), flush=True)
    return result, samples


start = time.monotonic()
if args.checkpoint:
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if checkpoint.get('planner_version') not in (3,2 if args.pickup_pitch else 1):
        raise ValueError('Checkpoint uses a different task phase planner; retrain with this script')
    if checkpoint.get('grasp_region','reference') != args.grasp_region or checkpoint.get('pickup_pitch_rad',0.) != args.pickup_pitch:
        raise ValueError('Checkpoint grasp region/pitch differs from the requested curriculum')
    report['checkpoint_cuff_point']=checkpoint.get('cuff_point','corner')
    report['checkpoint_extension_m']=checkpoint.get('pickup_extension_m',.3)
    report['target_transfer']=report['checkpoint_cuff_point']!=args.cuff_point or report['checkpoint_extension_m']!=args.pickup_extension
    model = torch.nn.Sequential(torch.nn.Linear(checkpoint['input_dim'], 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, checkpoint['output_dim']), torch.nn.Tanh())
    if checkpoint['planner_version']==3:
        from Policy.pickup_policy import make_single_pickup_policy
        model=make_single_pickup_policy(bool(args.pickup_pitch))
    model.load_state_dict(checkpoint['model'])
    model.eval()
    evaluations=[]
    for i,shift in enumerate(args.evaluation_shifts):
        evaluation,_=rollout('reloaded_'+str(i),model,shift=shift)
        evaluations.append(evaluation)
    report['evaluations']=evaluations
    report['evaluation']=evaluations[0]
    report['success']=all(e['success'] for e in evaluations)
    report['checkpoint'] = str(args.checkpoint)
elif args.demonstrations:
    with np.load(args.demonstrations) as data:
        if data['features'].shape[1] != (12 if args.pickup_pitch else 11) or data['actions'].shape[1] != (6 if args.pickup_pitch else 5):
            raise ValueError('Demonstration feature/action layout differs')
        samples=list(zip(data['features'].copy(),data['actions'].copy()))
    teacher=json.loads((args.demonstrations.parent/'teacher.json').read_text())['result']
    if not teacher['success']:raise ValueError('Cannot reuse an unsuccessful pickup demonstration')
    report['teacher']=dict(teacher,reused_from=str(args.demonstrations),dataset_sha256=hashlib.sha256(args.demonstrations.read_bytes()).hexdigest())
else:
    teacher, samples = rollout('teacher')
    report['teacher'] = teacher
report['environment'] = {'source_sha256': env._hashes, 'rates': env._runtime,
                         'initial_slot': str(args.initial_slot), 'native_grasp': True}
if not args.probe_only and not args.checkpoint and teacher['success']:
    x = torch.tensor(np.stack([s[0] for s in samples]))
    y = torch.tensor(np.stack([s[1] for s in samples]))
    from Policy.pickup_policy import make_single_pickup_policy
    model=make_single_pickup_policy(bool(args.pickup_pitch))
    optimizer = torch.optim.Adam(model.parameters(), lr=.03)
    before = float(torch.nn.functional.mse_loss(model(x), y).detach())
    for _ in range(args.epochs):
        loss = torch.nn.functional.mse_loss(model(x), y)
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    after = float(torch.nn.functional.mse_loss(model(x), y).detach())
    torch.save({'model': model.state_dict(), 'input_dim': x.shape[1], 'output_dim': y.shape[1],
                'algorithm': 'behavior cloning', 'scripted_phases': True, 'planner_version': 3, 'network_type':'positive_single_pickup',
                'pickup_pitch_rad':args.pickup_pitch,
                'pickup_extension_m':args.pickup_extension,
                'grasp_region': args.grasp_region,
                'cuff_point':args.cuff_point,
                'source_sha256': env._hashes}, out/'policy.pt')
    model.load_state_dict(torch.load(out/'policy.pt', map_location='cpu', weights_only=True)['model'])
    model.eval()
    np.savez_compressed(out/'demonstrations.npz', features=x.numpy(), actions=y.numpy())
    report['training'] = {'samples': len(samples), 'epochs': args.epochs, 'loss_before': before,
                          'loss_after': after, 'evaluation_reloaded_saved_weights': True}
    evaluations=[]
    for i,shift in enumerate(args.evaluation_shifts):
        evaluation,_=rollout('learned_eval_'+str(i),model,shift=shift)
        evaluations.append(evaluation)
    report['evaluations']=evaluations
    report['evaluation']=evaluations[0]
    report['success']=all(e['success'] for e in evaluations)
if args.dressing_target and report.get('success'):
    if args.dressing_controller in ('material','thread'):
        from Policy.material_policy import learn_material_continuation as learn_continuation
    else:
        from Policy.dressing_task import learn_continuation
    options={'thread_arm':True,'orient_cuff':args.orient_cuff,'release_after_insertion':args.release_after_insertion} if args.dressing_controller=='thread' else {}
    report['continuous_dressing'] = learn_continuation(env, out, args.reference_slot, args.dressing_target, rollout, model, active=(0,),**options)
    report['pickup_success'] = report['success']
    report['success'] = report['continuous_dressing'].get('arm_insertion_verified', False)
report.update(status='complete', elapsed_s=time.monotonic()-start)
report['inputs_unchanged'] = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in inputs.items())
(out/'report.json').write_text(json.dumps(report, indent=2))
print('GRASP_REPORT', json.dumps(report), flush=True)
env.close()
