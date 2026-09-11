"""Collect a physical F1 pickup demonstration and fit/evaluate an imitation policy.

Privileged cloth coordinates, two active robots, scripted task phases. This is
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
parser.add_argument('--output', type=Path, default=Path('/output/dual-grasp-learning'))
parser.add_argument('--probe-only', action='store_true')
parser.add_argument('--dressing-target', type=Path, help='Continue successful pickup toward this stage without loading it')
parser.add_argument('--dressing-controller', choices=('reference','material'), default='material')
parser.add_argument('--demonstrations', type=Path, help='Reuse real paired demonstrations and their teacher.json')
parser.add_argument('--evaluation-shifts', nargs='+', type=float, default=[0., .01, -.01])
parser.add_argument('--epochs', type=int, default=600)
parser.add_argument('--checkpoint', type=Path, help='Evaluate saved weights without collecting or training')
args = parser.parse_args()
if args.epochs < 1:
    parser.error('--epochs must be positive')
if args.probe_only and args.checkpoint:
    parser.error('--probe-only and --checkpoint are mutually exclusive')
out = args.output
out.mkdir(parents=True, exist_ok=True)
inputs = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.initial_slot, args.reference_slot)}
report = {'status': 'starting', 'success': False, 'inputs_sha256': inputs,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope': 'two-robot pickup from F1, measured-state imitation, scripted phase sequencing',
          'physics': 'current production FEM, grasp attachments, guards and friction; no overrides'}
(out/'report.json').write_text(json.dumps(report, indent=2))
(out/'train_dual_grasp_source.py').write_text(Path(__file__).read_text())
previous_exception_hook = sys.excepthook


def record_failure(kind, value, traceback):
    report.update(status='error', success=False, error=f'{kind.__name__}: {value}')
    (out/'report.json').write_text(json.dumps(report, indent=2))
    previous_exception_hook(kind, value, traceback)


sys.excepthook = record_failure
env = DressingEnv(profile='measured_state', initial_slot=args.initial_slot, max_episode_steps=600)
import torch  # Isaac must initialize first.
torch.set_num_threads(2)
torch.manual_seed(7)
with np.load(args.reference_slot) as data:
    target_ids = [data[f'r{i}_grab_idx'].copy() for i in range(2)]


def rollout(name, model=None, shift=0.):
    obs, info = env.reset(seed=7)
    if any(r['grasp_attached'] or r['native_attachment_present'] for r in info['state']['robots']):
        raise ValueError('Both robots must start unattached at F1')
    initial = array(env.cloths[0].get_world_positions())[0]
    for ids in target_ids:
        if len(ids) == 0 or ids.min() < 0 or ids.max() >= len(initial):
            raise ValueError('Invalid reference grasp indices')
    initial_z = np.array([initial[ids, 2].mean() for ids in target_ids])
    headings = np.array([-np.pi/2, -3*np.pi/4])
    pitches = np.array([0., .4])
    phase, phase_steps, hold_steps = 0, 0, 0
    samples, traces = [], []
    max_lift = np.zeros(2)
    for step in range(600):
        robots = info['state']['robots']
        points = array(env.cloths[0].get_world_positions())[0]
        tips = np.array([r['fingertip_midpoint_world'] for r in robots])
        targets = np.array([points[ids].mean(0) for ids in target_ids], dtype=float)
        targets[:, 0] += shift
        targets[:, 2] = initial_z + (.18 if phase <= 1 else .025 if phase <= 3 else .14)
        errors = targets-tips
        rotations = [rotation(np.array(r['base_pose_world'])[3:]) for r in robots]
        tilts=[float(np.arccos(np.clip(R[2,2],-1,1))) for R in rotations]
        heading_errors = np.array([(desired-np.arctan2(R[1,0],R[0,0])+np.pi)%(2*np.pi)-np.pi
                                   for desired,R in zip(headings,rotations)])
        states = [r['state'] for r in env.rigs]
        attached = np.array([r['grasp_attached'] and r['native_attachment_present'] for r in robots],dtype=bool)
        lifted = np.zeros(2)
        for i,state in enumerate(states):
            grab=state.get('grabbed')
            if attached[i] and grab is not None:
                ids=array(grab[1]).astype(int)
                lifted[i]=np.median(points[ids,2]-initial[ids,2])
        max_lift=np.maximum(max_lift,lifted)
        if phase == 0 and max(abs(errors[:,2])) < .025 and max(abs(s['arm']-.3) for s in states)<.015 and max(abs(heading_errors))<.035 and max(abs(pitches[i]-states[i]['pitch']) for i in range(2))<.025:
            phase,phase_steps=1,0
        elif phase == 1 and max(np.linalg.norm(errors[:,:2],axis=1))<.015:
            phase,phase_steps=2,0
        elif phase == 2 and max(abs(tips[:,2]-(initial_z+.025)))<.015:
            phase,phase_steps=3,0
        elif phase == 3 and attached.all():
            phase,phase_steps=4,0
        elif phase == 4 and attached.all() and min(lifted)>=.06:
            phase,phase_steps=5,0
        if phase == 3 and phase_steps>60 and not attached.all():
            break
        from Policy.dressing_task import grasp_health
        health=grasp_health(env)
        anchors_ok=all(h['attached'] and h['anchor_p95_error_m'] is not None and h['anchor_p95_error_m']<=.035 for h in health)
        hold_steps=hold_steps+1 if phase==5 and attached.all() and min(lifted)>=.06 and anchors_ok and max(tilts)<.25 else 0
        features,expert=[],np.zeros((2,7),np.float32)
        for i,(R,state) in enumerate(zip(rotations,states)):
            local=R.T@errors[i]
            features.append(np.r_[local*5,(state['arm']-.3)*5,heading_errors[i],pitches[i]-state['pitch'],float(attached[i]),np.eye(6)[phase]])
            if phase in (1,2,3):
                expert[i,:2]=np.clip(local[:2]*2/env.M.BASE_LINEAR_RATE,-.35,.35)
            expert[i,2]=np.clip(heading_errors[i]*2/env.M.BASE_ANGULAR_RATE,-.25,.25)
            expert[i,3]=np.clip(errors[i,2]*2/env.M.LIFT_RATE,-.3,.3)
            expert[i,4]=np.clip((.3-state['arm'])*3/env.M.ARM_RATE,-.3,.3)
            expert[i,5]=np.clip((pitches[i]-state['pitch'])*3/env.M.WRIST_RATE,-.2,.2)
            expert[i,6]=1 if phase>=3 else -1
            if phase==5:
                expert[i,:6]=0
        features=np.array(features,np.float32)
        samples.extend(zip(features.copy(),expert.copy()))
        if model is None:
            chosen=expert
        else:
            with torch.no_grad(): chosen=model(torch.from_numpy(features)).numpy()
        action=np.zeros((2,9),np.float32)
        action[:,[0,1,2,3,4,6,8]]=np.clip(chosen,-1,1)
        obs,_,terminated,truncated,info=env.step(action)
        row={'step':step,'phase':phase,'tips':tips.tolist(),'targets':targets.tolist(),
             'attached':attached.tolist(),'lift_m':lifted.tolist(),'hold_steps':hold_steps,'grasp_health':health,'base_tilt_rad':tilts,
             'errors_m':np.linalg.norm(errors,axis=1).tolist(),'action':action.tolist()}
        traces.append(row)
        if step%30==0 or hold_steps==40:
            print('DUAL_GRASP',name,json.dumps(row),flush=True)
            (out/(name+'_progress.json')).write_text(json.dumps(row,indent=2))
        phase_steps+=1
        if hold_steps>=40 or terminated or truncated: break
    final_health=grasp_health(env)
    final_points=array(env.cloths[0].get_world_positions())[0]
    final_lift=[]
    for rig in env.rigs:
        grab=rig['state'].get('grabbed')
        ids=array(grab[1]).astype(int) if grab is not None else np.array([],int)
        final_lift.append(float(np.median(final_points[ids,2]-initial[ids,2])) if len(ids) else 0.)
    final_tilts=[float(np.arccos(np.clip(rotation(np.asarray(r['base_pose_world'])[3:])[2,2],-1,1))) for r in info['state']['robots']]
    final_ok=all(h['attached'] and h['anchor_p95_error_m']<=.035 and lift>=.06 for h,lift in zip(final_health,final_lift)) and max(final_tilts)<.25
    result={'success':hold_steps>=40 and final_ok,'steps':len(traces),'last_phase':phase,
            'final_grasp_health':final_health,'final_lift_m_each':final_lift,
            'final_base_tilt_rad':final_tilts,
            'max_lift_m_each':max_lift.tolist(),'max_both_hold_steps':max((r['hold_steps'] for r in traces),default=0),
            'both_ever_attached':any(all(r['attached']) for r in traces),'target_shift_m':shift,
            'final_grasps':[r['grasp_attached'] and r['native_attachment_present'] for r in info['state']['robots']]}
    (out/(name+'.json')).write_text(json.dumps({'result':result,'trace':traces},indent=2))
    np.savez_compressed(out/(name+'_final.npz'),cloth=array(env.cloths[0].get_world_positions()),**obs)
    previous=env.M.STATE_DIR
    try:
        env.M.STATE_DIR=str(out/'states')
        if not env.M.save_state_slot(name.upper(),env.cloths,env.rigs): raise RuntimeError('Cannot save private rollout')
    finally: env.M.STATE_DIR=previous
    print('DUAL_GRASP_RESULT',name,json.dumps(result),flush=True)
    return result,samples


start = time.monotonic()
if args.checkpoint:
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if checkpoint.get('planner_version') not in (3, 4):
        raise ValueError('Checkpoint uses a different task phase planner; retrain with this script')
    model = torch.nn.Sequential(torch.nn.Linear(checkpoint['input_dim'], 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 7), torch.nn.Tanh())
    if checkpoint['planner_version'] == 4:
        from Policy.pickup_policy import make_dual_pickup_policy
        model = make_dual_pickup_policy()
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
        samples = list(zip(data['features'].copy(), data['actions'].copy()))
    teacher = json.loads((args.demonstrations.parent/'teacher.json').read_text())['result']
    if not teacher['success']:
        raise ValueError('Only a verified successful physical demonstration may be reused')
    report['teacher'] = dict(teacher, reused_from=str(args.demonstrations),
        dataset_sha256=hashlib.sha256(args.demonstrations.read_bytes()).hexdigest())
else:
    teacher, samples = rollout('teacher')
    report['teacher'] = teacher
report['environment'] = {'source_sha256': env._hashes, 'rates': env._runtime,
                         'initial_slot': str(args.initial_slot), 'native_grasp': True}
if not args.probe_only and not args.checkpoint and teacher['success']:
    x = torch.tensor(np.stack([s[0] for s in samples]))
    y = torch.tensor(np.stack([s[1] for s in samples]))
    from Policy.pickup_policy import make_dual_pickup_policy
    model = make_dual_pickup_policy()
    optimizer = torch.optim.Adam(model.parameters(), lr=.03)
    before = float(torch.nn.functional.mse_loss(model(x), y).detach())
    for _ in range(args.epochs):
        loss = torch.nn.functional.mse_loss(model(x), y)
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    after = float(torch.nn.functional.mse_loss(model(x), y).detach())
    torch.save({'model': model.state_dict(), 'input_dim': x.shape[1], 'output_dim': 7,
                'algorithm': 'behavior cloning', 'scripted_phases': True, 'planner_version': 4, 'network_type': 'positive_axis_policy',
                'source_sha256': env._hashes}, out/'policy.pt')
    model.load_state_dict(torch.load(out/'policy.pt', map_location='cpu', weights_only=True)['model'])
    model.eval()
    np.savez_compressed(out/'demonstrations.npz', features=x.numpy(), actions=y.numpy())
    report['training'] = {'samples': len(samples), 'epochs': args.epochs, 'loss_before': before,
                          'loss_after': after, 'evaluation_reloaded_saved_weights': True}
    evaluations=[]
    for i,shift in enumerate(args.evaluation_shifts):
        result,_=rollout('learned_eval_'+str(i),model,shift=shift)
        evaluations.append(result)
    report['evaluations']=evaluations
    report['evaluation']=evaluations[0]
    report['success']=all(r['success'] for r in evaluations)
if args.dressing_target and report.get('success'):
    if args.dressing_controller == 'material':
        from Policy.material_policy import learn_material_continuation as learn_continuation
    else:
        from Policy.dressing_task import learn_continuation
    report['continuous_dressing'] = learn_continuation(env, out, args.reference_slot, args.dressing_target, rollout, model, active=(0,1))
    report['pickup_success'] = report['success']
    report['success'] = report['continuous_dressing'].get('arm_insertion_verified', False)
report.update(status='complete', elapsed_s=time.monotonic()-start)
report['inputs_unchanged'] = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in inputs.items())
(out/'report.json').write_text(json.dumps(report, indent=2))
print('GRASP_REPORT', json.dumps(report), flush=True)
env.close()
