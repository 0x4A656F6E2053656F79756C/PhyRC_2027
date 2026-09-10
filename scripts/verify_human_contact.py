"""Probe the real posed surface and force a full shirt toward the wrist.

Optional placement replay reads only the human/chair transforms from a slot;
it never loads or overwrites user cloth/robot state. This is a velocity-driven
contact stress test, not a validated native robot grasp or dressing trial.
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
parser.add_argument('--speed', type=float, default=1.2)
parser.add_argument('--post-reset', action='store_true')
parser.add_argument('--fixed', action='store_true')
parser.add_argument('--seed', type=int, default=42)
parser.add_argument('--placement-slot', type=Path)
parser.add_argument('--output', type=Path, default=Path('/output/verification/human-contact.json'))
args = parser.parse_args()
if not 0 < args.speed <= 12:
    parser.error('Speed must be in (0,12] m/s')
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
import omni.physx
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
if args.post_reset:
    env.reset()
    M.simulation_app.update()
    for rig in (env.rig, env.rig2):
        rig['robot'].initialize()
        M.stretch4_tuning(rig, restore=True)
    for cloth in cloths:
        cloth.initialize()
guard = M._BODY_GEOM['sweep']
points = guard.mesh.points.numpy()
triangles = guard.mesh.indices.numpy().reshape(-1, 3)
centers = points[triangles].mean(1)
normals = np.cross(points[triangles[:,1]]-points[triangles[:,0]], points[triangles[:,2]]-points[triangles[:,0]])
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
query = omni.physx.get_physx_scene_query_interface()
rows = []
for i in range(0, len(triangles), 20):
    c, n = centers[i], normals[i]
    hits = []
    for sign in (-1, 1):
        hit = query.raycast_closest(tuple(map(float,c+sign*n*.025)), tuple(map(float,-sign*n)), .05)
        hits.append({k: (list(v) if k in ('position','normal') else v) for k,v in hit.items()})
    rows.append({'face': i, 'center': c.tolist(), 'hits': hits})
# Every normal crossing must be stopped by the independent swept mesh guard.
ids = np.arange(0, len(triangles), 20)
start = torch.as_tensor(centers[ids]+normals[ids]*.025, device=guard.device).contiguous()
target = torch.as_tensor(centers[ids]-normals[ids]*.025, device=guard.device).contiguous()
safe, _ = guard.sweep(start, target, torch.zeros_like(start))
advance = ((safe-start)*(target-start)).sum(1) / ((target-start)**2).sum(1)
report = {'passed':False, 'human_world': np.asarray(UsdGeom.Xformable(env.stage.GetPrimAtPath('/World/Human')).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).tolist(), 'faces': len(triangles),
          'sample_count':len(ids), 'node_sweep_uncorrected': int((advance>.99).sum()),
          'rays':rows}
from Env_Config.Human.HandSphereColliders import sphere_world_geometry
root_transform = UsdGeom.Xformable(env.stage.GetPrimAtPath(env.human.prim_path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
scale = np.linalg.norm(root_transform.TransformDir(Gf.Vec3d(1,0,0)))
mesh, hp, _, _, hands, _ = M._hand_vertex_sets(env.stage, env.human.prim_path, scale)
coverage = {}
for side, indices in hands.items():
    c, radius = sphere_world_geometry(env.stage.GetPrimAtPath(f'/World/Human/HandSphere_{side}'))
    hand_points = np.array([root_transform.Transform(Gf.Vec3d(*map(float,p))) for p in hp[indices]])
    outside = np.linalg.norm(hand_points-c,axis=1)-radius
    coverage[side] = {'visible_hand_vertices':len(indices),'outside_sphere_vertices':int((outside>0).sum()),'max_outside_m':float(outside.max())}
report['visible_hand_coverage'] = coverage
print('VISIBLE-HAND-COVERAGE',coverage,flush=True)
args.output.write_text(json.dumps(report, indent=2))
print('ROTATED-CONTACT-PROBE', {k:v for k,v in report.items() if k!='rays'}, flush=True)
# Exercise the actual FEM step and production pre/post callbacks at the wrist.
root_xf = UsdGeom.Xformable(env.stage.GetPrimAtPath('/World/Human')).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
x = np.array(root_xf.TransformDir(Gf.Vec3d(1,0,0))); x /= np.linalg.norm(x)
inward = np.array(root_xf.TransformDir(Gf.Vec3d(0,1,0))); inward /= np.linalg.norm(inward)
z = np.array([0.,0.,1.])
center, radius = sphere_world_geometry(env.stage.GetPrimAtPath('/World/Human/HandSphere_left'))
gc = cloths[0]
p = gc.get_world_positions()[0].cpu().numpy()
relative = p-p.mean(0)
# Original shirt lies in XY; map it rigidly to the vertical XZ plane.
q = center + relative[:,0,None]*x + relative[:,1,None]*z - relative[:,2,None]*inward
front = np.min(points[(points[:,2]>.7) & (points[:,2]<1.6)] @ inward)
q += inward*(front-.06-np.max(q@inward))
q = torch.as_tensor(q, dtype=torch.float32, device=guard.device)
M.begin_cloth_motion(cloths)
assert guard.count_intersections(q, gc._contact_edges, gc._contact_triangles) == 0
gc.set_world_positions(q[None])
gc.set_velocities(torch.zeros_like(q[None]))
calls = {'pre':0,'post':0,'sweeps':0,'corrections':0}
pre, post_fn, sweep = M.cloth_pre_step, M.cloth_post_step, guard.sweep
def counted_pre(*a):
    calls['pre'] += 1
    return pre(*a)
def counted_post(*a):
    calls['post'] += 1
    return post_fn(*a)
def counted_sweep(start, target, velocity, *a, **kw):
    calls['sweeps'] += 1
    result = sweep(start, target, velocity, *a, **kw)
    calls['corrections'] += int(bool(torch.any(torch.abs(result[0]-target)>1e-6)))
    return result
M.cloth_pre_step, M.cloth_post_step, guard.sweep = counted_pre, counted_post, counted_sweep
crossings = []
push_started = time.monotonic()
for step in range(180):
    velocity = torch.as_tensor(inward*args.speed, dtype=torch.float32, device=guard.device)
    gc.set_velocities(velocity.expand_as(q)[None].contiguous())
    env.world.step(render=False)
    current = gc.get_world_positions()[0]
    cut = guard.count_intersections(current, gc._contact_edges, gc._contact_triangles)
    crossings.append(cut)
    if step%30 == 0:
        print('WRIST-STEP',step,'cuts',cut,'calls',calls, 'travel',float(((current-q)*torch.as_tensor(inward,device=q.device)).sum(1).mean()),flush=True)
report['wrist_push'] = dict(calls=calls, max_intersections=max(crossings), intersections=crossings,
                           elapsed_wall_s=time.monotonic()-push_started,
                           duration_sim_s=180*env.world.get_physics_dt())
args.output.write_text(json.dumps(report, indent=2))
print('WRIST-PUSH-RESULT',report['wrist_push'],flush=True)
# A thin tip may cross a triangle interior between two endpoint snapshots.
from Env_Config.Garment.SurfaceContactGuard import SurfaceContactGuard
tip = np.array([[0,0,.001],[-.001,-.001,-.001],[.001,-.001,-.001],[0,.001,-.001]],dtype=np.float32)
tip_tri = np.array([[0,1,2],[0,2,3],[0,3,1],[1,3,2]],dtype=np.int32)
tiny = SurfaceContactGuard(tip,tip_tri,guard.device)
sheet = torch.tensor([[-.02,-.02,.004],[.02,-.02,.004],[0,.02,.004]],device=guard.device)
end_sheet = sheet.clone(); end_sheet[:,2] = -.004
et = torch.tensor([[0,1],[1,2],[2,0]],dtype=torch.int32,device=guard.device)
ft = torch.tensor([[0,1,2]],dtype=torch.int32,device=guard.device)
result,_ = tiny.sweep(sheet,end_sheet,torch.zeros_like(sheet),et,ft)
test = {'start_cuts':tiny.count_intersections(sheet,et,ft),
        'mid_cuts':tiny.count_intersections((sheet+end_sheet)/2,et,ft),
        'end_cuts':tiny.count_intersections(end_sheet,et,ft),
        'accepted_all_the_way':bool(torch.allclose(result,end_sheet))}
report['thin_tip_swept_face'] = test
report.update(config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
              source_guard_sha256=hashlib.sha256(Path(sys.modules[SurfaceContactGuard.__module__].__file__).read_bytes()).hexdigest(),
              elapsed_wall_s=time.monotonic()-started)
report['passed'] = bool(report['node_sweep_uncorrected']==0 and max(crossings)==0
                         and calls['pre']==180 and calls['post']==180 and calls['corrections']>0
                         and not test['accepted_all_the_way'])
args.output.write_text(json.dumps(report, indent=2)+'\n')
print('THIN-TIP-SWEPT-FACE',test,flush=True)
if not report['passed']:
    raise RuntimeError('Human contact verification failed; inspect the report')
print('HUMAN-CONTACT-PASS',args.output,flush=True)
M.simulation_app.close()
