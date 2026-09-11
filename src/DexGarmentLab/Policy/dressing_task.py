"""Continuous dressing trial helpers; no checkpoint loading or forced grasps."""
from copy import deepcopy
import json
import numpy as np
from .state import array, rotation


def grasp_health(env):
    """Measure real FEM attachment-anchor error, not just the close command."""
    points=array(env.cloths[0].get_world_positions())[0]
    result=[]
    for rig in env.rigs:
        state=rig['state']; grab=state.get('grabbed')
        local=state.get('_native_local_offsets'); mask=state.get('_grab_anchor_mask')
        root=rig['robot'].prim_path.rsplit('/',1)[0]
        if grab is None or local is None or mask is None or not env.stage.GetPrimAtPath(root+'/ClothGraspAttachment'):
            result.append({'attached':False,'anchor_p95_error_m':None});continue
        tf=array(rig['robot']._articulation_view._physics_view.get_link_transforms())[0,rig['grasp_link_idx']]
        R=rotation(np.r_[tf[6],tf[3:6]])
        mask=array(mask).astype(bool);ids=array(grab[1]).astype(int)[mask]
        expected=tf[:3]+np.asarray(local)[mask]@R.T
        error=np.linalg.norm(points[ids]-expected,axis=1)
        result.append({'attached':True,'anchor_count':len(ids),'anchor_p95_error_m':float(np.quantile(error,.95))})
    return result


class DressingInspection:
    def __init__(self, env, output):
        from pxr import Gf, Usd, UsdGeom, UsdSkel
        import torch
        from Env_Config.Garment.SurfaceContactGuard import SurfaceContactGuard
        self.env, self.output, self.sensors = env, output, None
        mesh, local, counts, indices, hands, _ = env.M._hand_vertex_sets(env.stage, '/World/Human', .948514)
        xf = UsdGeom.Xformable(env.stage.GetPrimAtPath('/World/Human')).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        points = np.asarray([xf.Transform(Gf.Vec3d(*p)) for p in local])
        joints = UsdSkel.BindingAPI(mesh).GetJointsAttr().Get()
        if not joints:
            skeleton = next((UsdSkel.Skeleton(p) for p in Usd.PrimRange(env.stage.GetPrimAtPath('/World/Human'))
                             if p.IsA(UsdSkel.Skeleton)), None)
            if skeleton is None:
                raise ValueError('Cannot locate human skeleton for sleeve inspection')
            joints = skeleton.GetJointsAttr().Get()
        names = [str(j) for j in joints]
        ji = np.asarray(mesh.GetAttribute('primvars:skel:jointIndices').Get()).reshape(len(local), -1)
        jw = np.asarray(mesh.GetAttribute('primvars:skel:jointWeights').Get()).reshape(ji.shape)
        dominant = ji[np.arange(len(local)), jw.argmax(1)]
        self.arms = []
        for side, ids in hands.items():
            forearm_ids = np.where(np.isin(dominant, [i for i,n in enumerate(names) if n.endswith(side+'_elbow')]))[0]
            if not len(forearm_ids):
                raise ValueError('Cannot locate posed forearm: '+side)
            hand = points[ids].mean(0)
            forearm_points = points[forearm_ids]
            centre = forearm_points.mean(0)
            direction = hand-centre
            along = (forearm_points-centre)@direction
            # The centre is already outside deeply inserted F4 cuffs. Use the
            # proximal forearm surface band near the elbow as the segment start.
            proximal = forearm_points[along <= np.quantile(along, .15)].mean(0)
            self.arms.append((proximal, hand))
        self.arms.sort(key=lambda p: p[1][0])
        if len(self.arms) != 2:
            raise ValueError('Expected two posed arms')
        htri, offset = [], 0
        for count in counts:
            face = indices[offset:offset+count]
            htri.extend([[face[0],face[j],face[j+1]] for j in range(1,count-1)])
            offset += count
        self.guard = SurfaceContactGuard(points, np.asarray(htri), device='cuda:0', use_graph=False)
        tri = np.array(UsdGeom.Mesh(env.cloths[0].prim).GetFaceVertexIndicesAttr().Get()).reshape(-1,3)
        edges, ec = np.unique(np.sort(np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]])),axis=1),axis=0,return_counts=True)
        self.tri_t = torch.as_tensor(tri,dtype=torch.int32,device='cuda:0')
        self.edges_t = torch.as_tensor(edges,dtype=torch.int32,device='cuda:0')
        adjacency = {}
        for a,b in edges[ec==1]:
            adjacency.setdefault(int(a),[]).append(int(b)); adjacency.setdefault(int(b),[]).append(int(a))
        if any(len(v)!=2 for v in adjacency.values()):
            raise ValueError('Expected simple garment boundary loops')
        loops, unseen = [],set(adjacency)
        while unseen:
            loop,previous,current=[],None,min(unseen)
            while current not in loop:
                loop.append(current)
                nxt=next(v for v in adjacency[current] if v!=previous)
                previous,current=current,nxt
            unseen.difference_update(loop); loops.append(np.array(loop))
        self.cuffs=[v for v in loops if len(v)==80]
        if len(self.cuffs)!=2:
            raise ValueError('Expected current shirt sleeve topology')
        # Stable material identities assigned from original folded shirt X order.
        with np.load(env.initial_slot) as saved:
            self.cuffs.sort(key=lambda ids:saved['g0_pos'][ids,0].mean())
        self.inner=[]
        for ids in self.cuffs:
            near=tri[np.isin(tri,ids).any(1)]
            self.inner.append(np.setdiff1d(np.unique(near),ids))

    def measure(self, full=False, points=None):
        p=array(self.env.cloths[0].get_world_positions())[0] if points is None else np.asarray(points)
        results=[]
        for ids,inner,(forearm,hand) in zip(self.cuffs,self.inner,self.arms):
            loop=p[ids]; centre=loop.mean(0)
            _,sv,axes=np.linalg.svd(loop-centre,full_matrices=False)
            normal=axes[2]
            if np.dot(normal,centre-p[inner].mean(0))<0: normal=-normal
            a,b=np.dot(forearm-centre,normal),np.dot(hand-centre,normal)
            t=float(-a/(b-a)) if abs(b-a)>1e-8 else -1.
            crossing=forearm+t*(hand-forearm)
            polygon=(loop-centre)@axes[:2].T; point=(crossing-centre)@axes[:2].T
            inside=False
            for u,v in zip(polygon,np.roll(polygon,-1,axis=0)):
                if (u[1]>point[1]) != (v[1]>point[1]):
                    hit=(v[0]-u[0])*(point[1]-u[1])/(v[1]-u[1])+u[0]
                    if point[0]<hit: inside=not inside
            ratio=float(sv[2]/max(sv[1],1e-8))
            through=bool(a<-.005 and b>.01 and 0<t<1 and inside and ratio<.6)
            results.append({'forearm_to_hand_crosses_cuff':through,'forearm_signed_m':float(a),
                            'hand_signed_m':float(b),'crossing_inside':inside,'plane_ratio':ratio,
                            'cuff_normal_world':normal.tolist(),
                            'cuff_centre':centre.tolist(),'hand_centre':hand.tolist(),
                            'forearm_centre':forearm.tolist()})
        result={'arms':results,'both_cross_cuffs':all(r['forearm_to_hand_crosses_cuff'] for r in results)}
        if full:
            result['visual_intersections']=int(self.guard.count_intersections(self.env.M._to_t(p),self.edges_t,self.tri_t))
        return result

    def capture(self,name):
        from .sensors import RGBDSensors
        from PIL import Image
        if self.sensors is None:
            config=deepcopy(self.env.contract); config['default_dimensions'].update(width=640,height=480)
            config['cameras']=[dict(id='dressing_'+view,mount='world',eye_world_m=eye,
                target_world_m=[0,.12,1.08],clip_m=[.05,10],horizontal_fov_deg=52)
                for view,eye in [('front',[0,-2.2,1.45]),('left',[-2.2,.1,1.45]),('above',[0,-.2,3.1])]]
            config['cameras'].append(dict(id='dressing_scene',mount='world',
                eye_world_m=[-3.2,-3.6,2.7],target_world_m=[-.5,-.5,.8],
                clip_m=[.05,10],horizontal_fov_deg=65))
            self.sensors=RGBDSensors(self.env.stage,self.env.world,self.env.rigs,config)
        values,_=self.sensors.capture()
        for i,view in enumerate(('front','left','above','scene')):
            Image.fromarray(values['rgb'][i]).save(self.output/f'{name}_{view}.png')

    def close(self):
        if self.sensors: self.sensors.close()


def goal_action(env, info, goal, active=(0,1)):
    """Bounded reference tracking proposal through ordinary 20 Hz actions."""
    features,action=[],np.zeros((2,9),np.float32)
    for i,robot in enumerate(info['state']['robots']):
        pose=np.asarray(robot['base_pose_world']); R=rotation(pose[3:]); G=rotation(goal[f'r{i}_root_quat'])
        if int(goal.get(f'r{i}_grab_ci', -1)) >= 0 and f'r{i}_grab_off' in goal:
            ci=int(goal[f'r{i}_grab_ci']);ids=goal[f'r{i}_grab_idx'].astype(int)
            desired=np.median(goal[f'g{ci}_pos'][ids]-goal[f'r{i}_grab_off'],axis=0)
            current=array(env.M._grasp_link_pos(env.rigs[i])).reshape(3)
            delta=R.T@(desired-current)
        else:
            delta=R.T@(goal[f'r{i}_root_pos']-pose[:3])
        heading=(np.arctan2(G[1,0],G[0,0])-np.arctan2(R[1,0],R[0,0])+np.pi)%(2*np.pi)-np.pi
        ctl=goal[f'r{i}_ctl'][:5]-np.array([env.rigs[i]['state'][k] for k in ('lift','arm','yaw','pitch','roll')])
        error=np.r_[delta[:2],heading,ctl]
        features.append(np.r_[error*np.array([5,5,1,5,5,1,1,1]),float(robot['grasp_attached'])])
        if i in active:
            rates=np.array([env.M.BASE_LINEAR_RATE]*2+[env.M.BASE_ANGULAR_RATE,env.M.LIFT_RATE,env.M.ARM_RATE]+[env.M.WRIST_RATE]*3)
            action[i,:8]=np.clip(1.5*error/rates,-.3,.3)
            action[i,8]=1
    return np.asarray(features,np.float32),action


def run_goal_phase(env, goal_path, inspection, name, policy=None, active=(0,1), steps=240):
    """Continue the live pickup state. Reading a goal never restores its state."""
    import torch
    with np.load(goal_path) as saved:
        goal={k:saved[k].copy() for k in saved.files}
    if str(goal['scene_geometry_revision'])!=env.M._STATE_GEOMETRY_REVISION or not env.M.placement_matches(env.stage,goal):
        raise ValueError('Goal belongs to another geometry or placement')
    if env._done:
        raise RuntimeError('Continuous phase requires an active episode; no reset is allowed')
    env.max_episode_steps=env._step_id+steps+1
    _,info=env._observe()
    if not all(info['state']['robots'][i]['grasp_attached'] and info['state']['robots'][i]['native_attachment_present'] for i in active):
        raise RuntimeError('Required live grasps missing; insertion must not start')
    initial_time=float(env.world.current_time)
    initial_load_count=getattr(env,'_slot_load_count',0)
    trace,samples=[],[]
    for step in range(steps):
        features,teacher=goal_action(env,info,goal,active)
        samples.extend((features[i].copy(),teacher[i].copy()) for i in active)
        if policy is None:
            action=teacher
        else:
            with torch.no_grad(): action=policy(torch.from_numpy(features)).numpy()
            for i in range(2):
                if i not in active: action[i]=0
        _,_,terminated,truncated,info=env.step(np.asarray(action,np.float32))
        attached=[bool(r['grasp_attached'] and r['native_attachment_present']) for r in info['state']['robots']]
        health=grasp_health(env)
        row=dict(step=step,attached=attached,grasp_health=health,**inspection.measure())
        trace.append(row)
        if step%30==0:
            print('CONTINUOUS_DRESSING',name,json.dumps(row),flush=True)
            (inspection.output/(name+'_progress.json')).write_text(json.dumps(row,indent=2))
        if (not all(attached[i] for i in active)
                or any(health[i]['anchor_p95_error_m'] is None or health[i]['anchor_p95_error_m']>.06 for i in active)
                or terminated or truncated): break
    result=dict(steps=len(trace),initial_sim_time_s=initial_time,final_sim_time_s=float(env.world.current_time),
                checkpoint_loads_during_phase=getattr(env,'_slot_load_count',0)-initial_load_count,
                episode_id=env._episode,final_grasps=attached,grasp_health=health,
                required_grasps_healthy=all(attached[i] and health[i]['anchor_p95_error_m'] is not None and health[i]['anchor_p95_error_m']<=.035 for i in active),
                translation_target='saved grasp centres when available, otherwise base pose',
                **inspection.measure(full=True))
    if result['checkpoint_loads_during_phase']:
        raise RuntimeError('A state was restored during a continuous dressing phase')
    (inspection.output/(name+'.json')).write_text(json.dumps({'result':result,'trace':trace},indent=2))
    previous=env.M.STATE_DIR
    try:
        env.M.STATE_DIR=str(inspection.output/'states')
        if not env.M.save_state_slot(name.upper(),env.cloths,env.rigs): raise RuntimeError('Cannot save phase result')
    finally: env.M.STATE_DIR=previous
    inspection.capture(name)
    print('CONTINUOUS_DRESSING_RESULT',name,json.dumps(result),flush=True)
    return result,samples


def learn_continuation(env, output, carry_path, insertion_path, pickup_rollout, pickup_model, active=(0,1)):
    """Collect an actual continuation, then evaluate a fresh continuous policy episode."""
    import torch
    inspection=DressingInspection(env,output)
    result={'active_robots':list(active),'starts_from_live_successful_pickup':True,
            'arm_insertion_verified':False}
    inspection.capture('actual_pickup_before_carry')
    result['teacher_carry'],first=run_goal_phase(env,carry_path,inspection,'teacher_carry',active=active,steps=260)
    if not result['teacher_carry']['required_grasps_healthy']:
        result['stopped_reason']='grasp lost during carry'; inspection.close(); return result
    result['teacher_insertion'],second=run_goal_phase(env,insertion_path,inspection,'teacher_insertion',active=active,steps=180)
    if not any(a['forearm_to_hand_crosses_cuff'] for a in result['teacher_insertion']['arms']):
        result['stopped_reason']='Neither sleeve crossed a hand; failed dressing demonstration is not cloned'
        inspection.close();return result
    samples=first+second
    x=torch.tensor(np.stack([s[0] for s in samples])); y=torch.tensor(np.stack([s[1] for s in samples]))
    policy=torch.nn.Sequential(torch.nn.Linear(9,64),torch.nn.Tanh(),torch.nn.Linear(64,64),torch.nn.Tanh(),torch.nn.Linear(64,9),torch.nn.Tanh())
    optimizer=torch.optim.Adam(policy.parameters(),lr=.003)
    before=float(torch.nn.functional.mse_loss(policy(x),y).detach())
    for _ in range(800):
        loss=torch.nn.functional.mse_loss(policy(x),y);optimizer.zero_grad();loss.backward();optimizer.step()
    torch.save({'model':policy.state_dict(),'input_dim':9,'output_dim':9,'algorithm':'behavior cloning',
                'task':'continuous carry and insertion proposal','active_robots':list(active)},output/'continuation_policy.pt')
    policy.load_state_dict(torch.load(output/'continuation_policy.pt',map_location='cpu',weights_only=True)['model']);policy.eval()
    result['training']={'samples':len(samples),'loss_before':before,'loss_after':float(loss.detach())}
    np.savez_compressed(output/'continuation_demonstrations.npz',features=x.numpy(),actions=y.numpy())
    # This is a NEW full episode from F1, not restoration of a held/inserted state.
    result['fresh_pickup'],_=pickup_rollout('continuous_policy_pickup',pickup_model)
    if not result['fresh_pickup']['success']:
        result['stopped_reason']='fresh pickup failed; insertion not started';inspection.close();return result
    result['learned_carry'],_=run_goal_phase(env,carry_path,inspection,'learned_carry',policy,active,260)
    if result['learned_carry']['required_grasps_healthy']:
        result['learned_insertion'],_=run_goal_phase(env,insertion_path,inspection,'learned_insertion',policy,active,180)
    else:
        result['stopped_reason']='learned carry lost a required grasp'
    inspection.close()
    return result
