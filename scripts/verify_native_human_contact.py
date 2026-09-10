"""Measure real native robot grasps while pulling a shirt toward the left wrist.

This prepares two grasps instead of testing pickup or replaying user controls.
The original shirt is rigidly repositioned in front of the unchanged human;
production gripper attachments, base actuators, FEM and contact remain active.
No user checkpoint is loaded or overwritten (optional placement is read only).
"""
import json
import argparse
import hashlib
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, '/project/src/DexGarmentLab')
from policy_cli import install_failure_handler
install_failure_handler()
parser = argparse.ArgumentParser()
parser.add_argument('--fixed', action='store_true')
parser.add_argument('--seed', type=int, default=42)
parser.add_argument('--placement-slot', type=Path)
parser.add_argument('--output', type=Path, default=Path('/output/verification/native-human-contact.json'))
args = parser.parse_args()
if args.fixed and args.placement_slot:
    parser.error('Choose a fixed scene or recorded placement, not both')
os.environ['HUMAN_SPAWN_SEED'] = str(args.seed)
if args.fixed:
    os.environ['STRETCH4_RANDOMIZE'] = '0'
os.environ['STRETCH4_HEADLESS'] = '1'
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({'passed':False,'status':'running'}))
started = time.monotonic()
import numpy as np
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M
from pxr import Gf, Usd, UsdGeom
import torch

saved = {}
if args.placement_slot:
    with np.load(args.placement_slot, allow_pickle=False) as data:
        saved = {name: data['placement_'+name.lower()].copy() for name in ('Human','Chair')}
def placement(stage, human_path):
    for name in ('Human', 'Chair'):
        xf = UsdGeom.Xformable(stage.GetPrimAtPath('/World/' + name))
        before = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        target = Gf.Matrix4d(saved[name].tolist())
        ops = xf.GetOrderedXformOps()
        op = xf.AddTransformOp(opSuffix='randomSpawn')
        op.Set(before.GetInverse() * target)
        xf.SetXformOpOrder([op, *ops], xf.GetResetXformStack())
    return {'recorded_placement': True}
if saved:
    M.randomize_human_and_chair = placement
env = M.TeleopTShirtStretch4_Env()
cloths, faces, post = M.initialize_manipulation(env)
from Env_Config.Human.HandSphereColliders import sphere_world_geometry
from Env_Config.Garment.NativeGrasp import update_native_grasp, current_grasp_offsets
center, radius = sphere_world_geometry(env.stage.GetPrimAtPath('/World/Human/HandSphere_left'))
guard=M._BODY_GEOM['sweep']; gc=cloths[0]
rigs=(env.rig,env.rig2)
# Rigidly orient the shirt as a vertical panel in front of the body.
p=gc.get_world_positions()[0].clone()
xf=UsdGeom.Xformable(env.stage.GetPrimAtPath('/World/Human')).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
x=np.array(xf.TransformDir(Gf.Vec3d(1,0,0)));x/=np.linalg.norm(x)
inward=np.array(xf.TransformDir(Gf.Vec3d(0,1,0)));inward/=np.linalg.norm(inward)
z=np.array([0.,0.,1.])
rel=(p-p.mean(0)).cpu().numpy()
q=center+rel[:,0,None]*x+rel[:,1,None]*z-rel[:,2,None]*inward
body=guard.mesh.points.numpy()
front=np.min(body[(body[:,2]>.7)&(body[:,2]<1.6)]@inward)
q+=inward*(front-.06-np.max(q@inward))
q=torch.as_tensor(q,device=p.device,dtype=p.dtype)
patches=[]
for sign in (-1,1):
    target=q.mean(0)+torch.tensor(sign*.28*x+.20*z,device=p.device,dtype=p.dtype)
    patches.append(torch.argsort(torch.linalg.norm(q-target,dim=1))[:48])
heading=np.arctan2(inward[1],inward[0])
for rig,ids in zip(rigs,patches):
    robot=rig['robot']; pos,quat=robot.get_world_pose()
    robot.set_world_pose(position=pos,orientation=M._to_t(np.array([np.cos(heading/2),0,0,np.sin(heading/2)])))
    joints=robot.get_joint_positions().clone(); joints[rig['lift_idx']]=.7
    robot.set_joint_positions(joints); robot.set_joint_velocities(torch.zeros_like(joints))
    rig['state']['lift']=.7
    M.drive_robot(rig,M.ROBOT1_KEYMAP,set(),cloths,1/60,0)
for _ in range(4):env.world.step(render=False)
for rig,ids in zip(rigs,patches):
    robot=rig['robot']; pos,quat=robot.get_world_pose()
    desired=q[ids].mean(0).cpu().numpy()
    grip=M._grasp_link_pos(rig)
    # Keep wheels on the ground; tune lift to the prepared patch height.
    rig['state']['lift'] += float(desired[2]-grip[2])
    joints=robot.get_joint_positions().clone(); joints[rig['lift_idx']]=rig['state']['lift']
    robot.set_joint_positions(joints)
    shifted=pos.clone(); shifted[:2] += M._to_t(desired[:2]-grip[:2])
    robot.set_world_pose(position=shifted,orientation=quat)
    M.drive_robot(rig,M.ROBOT1_KEYMAP,set(),cloths,1/60,0)
for _ in range(4):env.world.step(render=False)
gc.set_world_positions(q[None]);gc.set_velocities(torch.zeros_like(q[None]))
M.begin_cloth_motion(cloths)
assert guard.count_intersections(q,gc._contact_edges,gc._contact_triangles)==0
for rig,ids in zip(rigs,patches):
    grip=M._to_t(M._grasp_link_pos(rig))
    rig['state']['grabbed']=(0,ids,q[ids]-grip)
    rig['state']['gripper_closed']=True
    update_native_grasp(rig,cloths,M.GRAB_ANCHOR_COUNT)
    print('PREPARED-GRASP',rig['robot'].prim_path,'grip',grip,'patch',q[ids].mean(0),flush=True)
# Flush attachment USD edits through the same application used by GUI.
M.simulation_app.update()
initial_grips=np.array([M._grasp_link_pos(r) for r in rigs])
initial_anchors=[gc.get_world_positions()[0,ids[r['state']['_grab_anchor_mask']]].clone() for r,ids in zip(rigs,patches)]
counts={'sweeps':0,'corrections':0,'post_callbacks':0,'audited_substeps':0}
original=guard.sweep
original_post=M.cloth_post_step
def measured_post(*args):
    counts['post_callbacks'] += 1
    return original_post(*args)
M.cloth_post_step=measured_post
raw_cuts=[]
def measured(start,target,velocity,*a,**kw):
    counts['sweeps']+=1
    raw_cuts.append(guard.count_intersections(target,gc._contact_edges,gc._contact_triangles))
    result=original(start,target,velocity,*a,**kw)
    counts['corrections']+=int(bool(torch.any(torch.abs(result[0]-target)>1e-6)))
    return result
guard.sweep=measured
traces=[]
commands={k:0. for k in ('base_fwd','base_strafe','base_turn','lift_rate','arm_rate','yaw_rate','pitch_rate','roll_rate')}
commands['base_fwd']=.18
def surface_distance(current):
    t=current[gc._contact_triangles.long()]; a,b,c=t.unbind(1)
    pt=torch.tensor(center,device=p.device,dtype=p.dtype)
    ab=b-a;ac=c-a;ap=pt-a
    n=torch.linalg.cross(ab,ac);n2=(n*n).sum(1).clamp_min(1e-20)
    proj=pt-n*((ap*n).sum(1)/n2)[:,None]
    v=proj-a
    aa=(ab*ab).sum(1);bb=(ac*ac).sum(1);cross=(ab*ac).sum(1)
    av=(ab*v).sum(1);bv=(ac*v).sum(1);den=(aa*bb-cross*cross).clamp_min(1e-20)
    u=(bb*av-cross*bv)/den;w=(aa*bv-cross*av)/den
    dist=torch.where((u>=0)&(w>=0)&(u+w<=1),((pt-proj)**2).sum(1),torch.inf)
    for e,f in ((a,b),(b,c),(c,a)):
        d=f-e;t=((pt-e)*d).sum(1)/(d*d).sum(1).clamp_min(1e-20)
        closest=e+t.clamp(0,1)[:,None]*d
        dist=torch.minimum(dist,((closest-pt)**2).sum(1))
    return float(torch.sqrt(dist.min()))-radius
for frame in range(240):
    for rig in rigs:M.drive_robot(rig,M.ROBOT1_KEYMAP,set(),cloths,1/60,frame,commands=commands)
    for _ in range(4):
        env.world.step(render=False)
        current=gc.get_world_positions()[0]
        cuts=guard.count_intersections(current,gc._contact_edges,gc._contact_triangles)
        counts['audited_substeps'] += 1
        if cuts: raise RuntimeError('Accepted cloth/body cuts: '+str(cuts))
    grips=np.array([M._grasp_link_pos(r) for r in rigs]);lags=[];travel=[]
    for r,ids,initial in zip(rigs,patches,initial_anchors):
        mask=r['state']['_grab_anchor_mask']; actual=current[ids[mask]]
        target=M._to_t(M._grasp_link_pos(r))+current_grasp_offsets(r)[mask]
        lags.append(float(torch.linalg.norm(actual-target,dim=1).max()))
        travel.append(float(((actual-initial)*torch.as_tensor(inward,device=p.device)).sum(1).mean()))
    row={'frame':frame,'grip_advance_m':((grips-initial_grips)@inward).tolist(),'anchor_advance_m':travel,'anchor_lag_max_m':lags,'sphere_surface_gap_m':surface_distance(current),'corrections':counts['corrections']}
    traces.append(row)
    if frame%30==0:print('NATIVE-PULL',row,flush=True)
# Metamorphic test: rotate the same actual body mesh AND crossing paths.
# Check that changing world axes does not make these crossings pass through.
from Env_Config.Garment.SurfaceContactGuard import SurfaceContactGuard
vertices = guard.mesh.points.numpy()
triangles = guard.mesh.indices.numpy().reshape(-1, 3)
selected = triangles[::20]
centroids = vertices[selected].mean(1)
normals = np.cross(vertices[selected[:, 1]] - vertices[selected[:, 0]],
                   vertices[selected[:, 2]] - vertices[selected[:, 0]])
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
origin = vertices.mean(0)
reference = None
rotation_checks = []
for yaw in (0., -30., 30.):
    angle = np.radians(yaw)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.],
                         [np.sin(angle), np.cos(angle), 0.], [0., 0., 1.]])
    posed = (vertices - origin) @ rotation.T + origin
    contact = SurfaceContactGuard(posed, triangles, guard.device)
    start = torch.as_tensor((centroids + normals * .025 - origin) @ rotation.T + origin,
                            dtype=torch.float32, device=p.device)
    target = torch.as_tensor((centroids - normals * .025 - origin) @ rotation.T + origin,
                             dtype=torch.float32, device=p.device)
    safe, _ = contact.sweep(start, target, torch.zeros_like(start))
    progress = ((safe - start) * (target - start)).sum(1) / ((target - start)**2).sum(1)
    returned = (safe.cpu().numpy() - origin) @ rotation + origin
    if reference is None:
        reference = returned
    rotation_checks.append({
        'additional_yaw_deg': yaw,
        'rays': len(selected),
        'unblocked_crossings': int((progress > .99).sum()),
        'max_inverse_rotation_error_m': float(np.linalg.norm(returned - reference, axis=1).max()),
    })
print('ROTATION-CHECKS', rotation_checks, flush=True)
gaps = [row['sphere_surface_gap_m'] for row in traces]
max_lag = max(max(row['anchor_lag_max_m']) for row in traces)
contact_frames = sum(gap < .010 for gap in gaps)
checks = {
    'two_real_grasps_moved': min(traces[-1]['grip_advance_m']) > .08,
    'cloth_followed_both_grasps': min(traces[-1]['anchor_advance_m']) > .08,
    'attachment_lag_under_30mm': max_lag < .030,
    # The scene uses 5mm rest and 8mm contact offsets. Contact need not
    # intersect geometry or require the additional guard to correct anything.
    'wrist_contact_exercised': contact_frames >= 12,
    'no_sphere_surface_penetration': min(gaps) >= -.0001,
    # The broad phase legitimately skips detailed sweeps outside body bounds.
    'all_960_substeps_audited': counts['audited_substeps'] == counts['post_callbacks'] == 960,
    'rotation_crossings_blocked': all(row['unblocked_crossings'] == 0 for row in rotation_checks),
    'no_accepted_body_cuts': True,  # Asserted after every physics substep.
}
report = {
    'passed': all(checks.values()),
    'kind': 'prepared two real robot native grasps; controlled forward pull',
    'exact_user_input_replay': False,
    'physics_steps': 960,
    'duration_sim_s': 960 * env.world.get_physics_dt(),
    'surface_gap_sample_hz': 60,
    'sphere_center': center.tolist(),
    'sphere_radius_m': radius,
    'minimum_sphere_surface_gap_m': min(gaps),
    'contact_frames_within_10mm': contact_frames,
    'maximum_anchor_lag_m': max_lag,
    'counts': counts,
    'raw_max_intersections': max(raw_cuts, default=0),
    'accepted_max_intersections': 0,
    'checks': checks,
    'rotation_checks': rotation_checks,
    'config': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
    'human_world': np.asarray(xf).tolist(),
    'source_sha256': {},
    'elapsed_wall_s': time.monotonic() - started,
    'trace': traces,
}
for module in (M, sys.modules[type(guard).__module__],
               sys.modules[update_native_grasp.__module__]):
    path = Path(module.__file__)
    report['source_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
args.output.write_text(json.dumps(report, indent=2) + '\n')
print('NATIVE-CONTACT-RESULT', {k: v for k, v in report.items() if k != 'trace'}, flush=True)
if not report['passed']:
    raise RuntimeError('Native contact verification failed; inspect ' + str(args.output))
M.simulation_app.close()
