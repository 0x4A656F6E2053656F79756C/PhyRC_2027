"""Material-aware continuous motion through the production velocity interface.

Saved garment coordinates are geometric goals, never restored states. A rigid
fit accounts for the newly acquired grasp's actual local attachment frame.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from .state import array, rotation
from .dressing_task import DressingInspection, grasp_health


def live_poses(env):
    result=[]
    for rig in env.rigs:
        tf=array(rig['robot']._articulation_view._physics_view.get_link_transforms())[0,rig['grasp_link_idx']]
        result.append((tf[:3].astype(float), rotation(np.r_[tf[6],tf[3:6]])))
    return result


def material_goals(env, path, active):
    with np.load(path) as data:
        if str(data['scene_geometry_revision'])!=env.M._STATE_GEOMETRY_REVISION or not env.M.placement_matches(env.stage,data):
            raise ValueError('Material goal geometry/placement mismatch')
        goals=live_poses(env);fits=[];preferred=[]
        for i in range(2):
            B=rotation(data[f'r{i}_root_quat'])
            preferred.append((float(np.arctan2(B[1,0],B[0,0])),float(data[f'r{i}_ctl'][1])))
        for i in active:
            state=env.rigs[i]['state'];grab=state.get('grabbed')
            if grab is None:raise RuntimeError('Cannot fit a missing live grasp')
            mask=array(state['_grab_anchor_mask']).astype(bool)
            local=np.asarray(state['_native_local_offsets'])[mask]
            desired=data[f'g{grab[0]}_pos'][array(grab[1]).astype(int)[mask]]
            a,b=local.mean(0),desired.mean(0)
            U,_,Vh=np.linalg.svd((local-a).T@(desired-b))
            fix=np.eye(3);fix[2,2]=np.linalg.det(Vh.T@U.T)
            R=Vh.T@fix@U.T;position=b-R@a
            fit=float(np.sqrt(np.mean(np.sum((local@R.T+position-desired)**2,axis=1))))
            goals[i]=(position,R);fits.append({'robot':i,'anchor_rigid_fit_rmse_m':fit})
    return goals,fits,preferred


def velocity_action(env, poses, goals, policy=None, active=(0,1), preferred=None):
    """Damped task-space IK, including mobile-base and summed extension motion."""
    action=np.zeros((2,9),np.float32);samples=[];errors=[]
    for i in active:
        rig=env.rigs[i];p,R=poses[i];target,T=goals[i]
        error=np.r_[target-p,Rotation.from_matrix(T@R.T).as_rotvec()]
        twist=np.clip(error*np.array([1.5]*3+[1.2]*3),[-.12]*3+[-.3]*3,[.12]*3+[.3]*3)
        samples.append((error.astype(np.float32),twist.astype(np.float32)))
        if policy is not None:
            import torch
            with torch.no_grad():twist=policy(torch.tensor(error,dtype=torch.float32)).numpy()
        robot=rig['robot'];base=array(robot.get_world_pose()[0]);B=rotation(array(robot.get_world_pose()[1]))
        raw=array(robot._articulation_view.get_jacobians())[0]
        if raw.shape[2]!=len(robot.dof_names)+6:
            raise ValueError('Expected floating-base PhysX Jacobian')
        J=raw[rig['grasp_link_idx']]
        A=np.zeros((6,8));A[:3,0]=B[:,0];A[:3,1]=B[:,1]
        A[:3,2]=np.cross([0,0,1],p-base);A[5,2]=1
        A[:,3]=J[:,rig['lift_idx']+6]
        A[:,4]=J[:,np.asarray(rig['arm_joint_idx'])+6].sum(1)/4
        for j,key in enumerate(('yaw_idx','pitch_idx','roll_idx'),5):A[:,j]=J[:,rig[key]+6]
        rates=np.array([env.M.BASE_LINEAR_RATE]*2+[env.M.BASE_ANGULAR_RATE,env.M.LIFT_RATE,env.M.ARM_RATE]+[env.M.WRIST_RATE]*3)
        A*=rates
        # Constrain joints already at a limit; the backend still enforces limits.
        for j,axis in enumerate(('lift','arm','yaw','pitch','roll'),3):
            value=rig['state'][axis]
            if value<=rig[axis+'_lo']+1e-4 or value>=rig[axis+'_hi']-1e-4:
                trial=A.T@np.linalg.solve(A@A.T+.0025*np.eye(6),twist)
                if (value<=rig[axis+'_lo']+1e-4 and trial[j]<0) or (value>=rig[axis+'_hi']-1e-4 and trial[j]>0):A[:,j]=0
        inverse=A.T@np.linalg.solve(A@A.T+.0025*np.eye(6),np.eye(6))
        command=inverse@twist
        if preferred is not None:
            heading,extension=preferred[i]
            error_heading=(heading-np.arctan2(B[1,0],B[0,0])+np.pi)%(2*np.pi)-np.pi
            posture=np.zeros(8)
            posture[2]=1.5*error_heading/rates[2]
            posture[4]=1.5*(extension-rig['state']['arm'])/rates[4]
            command+=(np.eye(8)-inverse@A)@posture
        command*=min(1.,.3/max(np.abs(command).max(),1e-8))
        action[i,:8]=command;action[i,8]=1
        errors.append({'robot':i,'position_error_m':float(np.linalg.norm(error[:3])),
                       'orientation_error_rad':float(np.linalg.norm(error[3:]))})
    return action,samples,errors


def phase(env, inspection, name, goals, active, steps, policy=None, preferred=None, cuff_target=None, cuff_normal_target=None, release_after_insertion=False):
    if env._done or not all(grasp_health(env)[i]['attached'] for i in active):
        raise RuntimeError('Material phase requires an active episode with all required live grasps')
    starts=live_poses(env);rotations=[Slerp([0,1],Rotation.from_matrix(np.stack([R,T])))
                                   for (_,R),(_,T) in zip(starts,goals)]
    distance=max(np.linalg.norm(goals[i][0]-starts[i][0]) for i in active)
    cuff_start=None
    if cuff_target is not None:
        cuff, target_centre=cuff_target
        cuff_start=array(env.cloths[0].get_world_positions())[0,inspection.cuffs[cuff]].mean(0)
        distance=float(np.linalg.norm(target_centre-cuff_start))
    angle=max(np.linalg.norm(Rotation.from_matrix(goals[i][1]@starts[i][1].T).as_rotvec()) for i in active)
    travel_steps=max(1,int(max(distance/(.03 if cuff_target is not None else .10),angle/.25)/.05))
    steps=max(steps,travel_steps+160)
    start_posture=[]
    for rig in env.rigs:
        B=rotation(array(rig['robot'].get_world_pose()[1]))
        start_posture.append((np.arctan2(B[1,0],B[0,0]),rig['state']['arm']))
    env.max_episode_steps=env._step_id+steps+1
    load_count=env._slot_load_count;t0=float(env.world.current_time);trace=[];samples=[];stable=0
    alpha=0.;errors=[];success_hold_poses=None;success_hold_start=None
    release_commanded=False;release_start=None;release_direction=None
    for step in range(steps):
        if success_hold_poses is None and (not errors or max(e['position_error_m'] for e in errors)<(.025 if cuff_target is not None else .12)):
            alpha=min(1.,alpha+1/travel_steps)
        moving=[((1-alpha)*p+alpha*q,s(alpha).as_matrix()) for (p,_),(q,_),s in zip(starts,goals,rotations)]
        if cuff_target is not None and success_hold_poses is None:
            # Deformation changes the cuff-to-gripper offset. Servo the observed
            # material opening itself, using the same ordinary velocity policy.
            i=active[0];poses=live_poses(env)
            current_centre=array(env.cloths[0].get_world_positions())[0,inspection.cuffs[cuff]].mean(0)
            desired_centre=(1-alpha)*cuff_start+alpha*target_centre
            moving[i]=(poses[i][0]+desired_centre-current_centre,moving[i][1])
            if cuff_normal_target is not None:
                mouth=inspection.measure()['arms'][cuff]
                normal=np.asarray(mouth['cuff_normal_world'])
                cross=np.cross(normal,cuff_normal_target)
                sine=np.linalg.norm(cross);cosine=np.clip(np.dot(normal,cuff_normal_target),-1.,1.)
                if sine<1e-8 and cosine<0:
                    cross=np.cross(normal,[1.,0,0]);sine=np.linalg.norm(cross)
                    if sine<1e-8:cross=np.cross(normal,[0,1.,0]);sine=np.linalg.norm(cross)
                turn=cross/max(sine,1e-8)*min(.25,.25*np.arccos(cosine))
                # A folded mouth has an unreliable fitted normal; hold the
                # measured wrist until its surface becomes planar again.
                if mouth['plane_ratio']>=.6:turn=np.zeros(3)
                moving[i]=(moving[i][0],Rotation.from_rotvec(turn).as_matrix()@poses[i][1])
        if success_hold_poses is not None:
            moving=success_hold_poses
            if release_commanded and step-success_hold_start>=12:
                moving=list(success_hold_poses);i=active[0]
                moving[i]=(release_start+.06*release_direction,moving[i][1])
        posture=None if preferred is None else [(h+alpha*((g-h+np.pi)%(2*np.pi)-np.pi),a+alpha*(b-a))
                                                for (h,a),(g,b) in zip(start_posture,preferred)]
        action,pairs,errors=velocity_action(env,live_poses(env),moving,policy,active,posture);samples+=pairs
        release_active=release_commanded
        if release_active:
            for i in active:action[i,8]=-1
        _,_,terminated,truncated,info=env.step(action)
        health=grasp_health(env);measure=inspection.measure()
        healthy=all(health[i]['attached'] and health[i]['anchor_p95_error_m'] is not None and health[i]['anchor_p95_error_m']<=.035 for i in active)
        # For a one-robot fallback, either anatomically matched sleeve is useful.
        through=measure['both_cross_cuffs'] if len(active)==2 else any(a['forearm_to_hand_crosses_cuff'] for a in measure['arms'])
        expected_gripper_state=all(not health[i]['attached'] for i in active) if release_active else healthy
        stable=stable+1 if through and expected_gripper_state else 0
        tilts=[float(np.arccos(np.clip(rotation(array(r['robot'].get_world_pose()[1]))[2,2],-1,1))) for r in env.rigs]
        upright=all(tilts[i]<.25 for i in active)
        if name.endswith('_insertion') and success_hold_poses is None and stable>=40 and upright:
            if inspection.measure(full=True)['visual_intersections']==0:
                success_hold_poses=live_poses(env);success_hold_start=step
                if release_after_insertion:
                    if len(active)!=1:raise ValueError('Release/retreat probe is a one-arm fallback')
                    i=active[0];release_start=success_hold_poses[i][0].copy()
                    arm_index=cuff_target[0] if cuff_target is not None else next(j for j,a in enumerate(measure['arms']) if a['forearm_to_hand_crosses_cuff'])
                    proximal,hand=inspection.arms[arm_index]
                    release_direction=(hand-proximal)/np.linalg.norm(hand-proximal)
                    release_commanded=True
        row=dict(step=step,path_fraction=alpha,errors=errors,grasp_health=health,base_tilt_rad=tilts,
                 stable_insertion_steps=stable,**measure);trace.append(row)
        row['holding_verified_insertion']=success_hold_poses is not None
        row['expected_grippers_released']=release_active
        row['required_gripper_state_satisfied']=expected_gripper_state
        if cuff_target is not None:
            row['desired_cuff_centre']=desired_centre.tolist()
            row['measured_cuff_centre']=measure['arms'][cuff]['cuff_centre']
        if cuff_normal_target is not None:
            row['cuff_normal_alignment']=float(np.dot(measure['arms'][cuff]['cuff_normal_world'],cuff_normal_target))
        if step%40==0:
            print('MATERIAL_DRESSING',name,json.dumps(row),flush=True)
            (inspection.output/(name+'_progress.json')).write_text(json.dumps(row,indent=2))
        safe_gripper_state=expected_gripper_state if release_active else all(health[i]['attached'] and health[i]['anchor_p95_error_m'] is not None and health[i]['anchor_p95_error_m']<=.06 for i in active)
        if not upright or not safe_gripper_state or terminated or truncated:break
        if success_hold_poses is not None:
            if step-success_hold_start>=(80 if release_commanded else 60):break
            continue
        settling=80 if name.endswith('_insertion') else 40
        normal_ready=cuff_normal_target is None or (row['cuff_normal_alignment']>=.75 and measure['arms'][cuff]['plane_ratio']<.6)
        if alpha==1 and healthy and normal_ready and max(e['position_error_m'] for e in errors)<.025 and max(e['orientation_error_rad'] for e in errors)<.12 and step>=travel_steps+settling:break
    result=dict(steps=len(trace),initial_sim_time_s=t0,final_sim_time_s=float(env.world.current_time),episode_id=env._episode,
                checkpoint_loads_during_phase=env._slot_load_count-load_count,required_grasps_healthy=healthy,
                grasp_health=health,errors=errors,base_tilt_rad=tilts,robots_upright=upright,
                stable_insertion_steps=stable,**inspection.measure(full=True))
    result['stopped_at_verified_insertion']=success_hold_poses is not None
    result['release_commanded']=release_commanded
    result['required_gripper_state_satisfied']=expected_gripper_state
    result['post_insertion_steps']=0 if success_hold_start is None else len(trace)-1-success_hold_start
    result['stationary_insertion_hold_steps']=0 if release_commanded else result['post_insertion_steps']
    result['insertion_candidate']=bool(upright and stable>=40 and result['visual_intersections']==0
        and (not name.endswith('_insertion') or result['post_insertion_steps']>=(80 if release_commanded else 60)))
    if release_commanded:
        result['grippers_released']=all(not health[i]['attached'] for i in active)
        result['retreat_along_arm_m']=float(np.dot(live_poses(env)[active[0]][0]-release_start,release_direction))
        result['insertion_candidate']=bool(result['insertion_candidate'] and result['grippers_released'] and result['retreat_along_arm_m']>=.04)
    result['target_reached']=bool(alpha>=1-1e-8 and max(e['position_error_m'] for e in errors)<.04
                                  and max(e['orientation_error_rad'] for e in errors)<.18)
    if cuff_target is not None:
        result['cuff_target_centre']=target_centre.tolist()
        result['cuff_centre_error_m']=float(np.linalg.norm(np.asarray(result['arms'][cuff]['cuff_centre'])-target_centre))
        result['target_reached']=bool(result['target_reached'] and result['cuff_centre_error_m']<.025)
    if cuff_normal_target is not None:
        result['cuff_normal_alignment']=float(np.dot(result['arms'][cuff]['cuff_normal_world'],cuff_normal_target))
        result['target_reached']=bool(result['target_reached'] and result['cuff_normal_alignment']>=.75)
    if result['checkpoint_loads_during_phase']:raise RuntimeError('State restore inside continuous phase')
    (inspection.output/(name+'.json')).write_text(json.dumps({'result':result,'trace':trace},indent=2))
    old=env.M.STATE_DIR
    try:
        env.M.STATE_DIR=str(inspection.output/'states')
        if not env.M.save_state_slot(name.upper(),env.cloths,env.rigs):raise RuntimeError('Cannot save private result')
    finally:env.M.STATE_DIR=old
    inspection.capture(name)
    print('MATERIAL_DRESSING_RESULT',name,json.dumps(result),flush=True)
    return result,samples


def learn_material_continuation(env, output, carry_path, insertion_path, pickup_rollout, pickup_model, active=(0,1), thread_arm=False, orient_cuff=False, release_after_insertion=False):
    import torch
    inspection=DressingInspection(env,output);result={'active_robots':list(active),'starts_from_live_successful_pickup':True,'arm_insertion_verified':False}
    if thread_arm and len(active)!=1:raise ValueError('Arm-axis threading is a one-robot fallback')
    result['thread_arm']=thread_arm
    if orient_cuff and not thread_arm:raise ValueError('Cuff orientation control requires arm-axis threading')
    result['orient_cuff']=orient_cuff
    if release_after_insertion and (not thread_arm or len(active)!=1):raise ValueError('Release probe requires one-robot arm-axis threading')
    result['release_after_insertion']=release_after_insertion
    source=Path(__file__).read_bytes()
    result['controller_source_sha256']=hashlib.sha256(source).hexdigest()
    env._hashes['material_policy.py']=result['controller_source_sha256']
    (output/'material_policy_source.py').write_bytes(source)
    inspection.capture('material_start')
    path_stages=[('carry',carry_path)]
    intermediate=Path(insertion_path).with_name('slot_F3.npz')
    if not thread_arm and Path(insertion_path).name=='slot_F4.npz' and intermediate.is_file():
        path_stages.append(('preinsert',intermediate))
    path_stages.append(('insertion',insertion_path))
    result['reference_files_sha256']={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for _,p in path_stages}
    calibration={}
    for _,path in path_stages:
        with np.load(path) as d:calibration[str(path)]=inspection.measure(points=d['g0_pos'])
    (output/'cuff_reference_diagnostics.json').write_text(json.dumps(calibration,indent=2))
    def episode(prefix, policy=None):
        records={};samples=[]
        goals=live_poses(env)
        for i in active:goals[i]=(np.r_[goals[i][0][:2],1.25],goals[i][1])
        records['raise'],pairs=phase(env,inspection,prefix+'_raise',goals,active,180,policy);samples+=pairs
        if not records['raise']['required_grasps_healthy'] or not records['raise']['robots_upright']:return records,samples
        for name,path in path_stages:
            if thread_arm and name=='insertion':
                poses=live_poses(env);points=array(env.cloths[0].get_world_positions())[0];i=active[0]
                cuff=min(range(2),key=lambda j:np.linalg.norm(points[inspection.cuffs[j]].mean(0)-poses[i][0]))
                proximal,hand=inspection.arms[cuff];axis=hand-proximal
                # A single live pinch leaves the mouth free to swing. Physically
                # centre it ahead of the hand before judging insertion alignment.
                # This is ordinary motion in this episode, never a state restore.
                direction=axis/np.linalg.norm(axis)
                # An offset can place the arm outside a strongly tilted mouth.
                # Track the anatomical axis and let the original contacts act.
                lateral=np.zeros(3)
                alignment_centre=hand+.16*direction+lateral
                orientation=poses[i][1].copy()
                preferred=[]
                for rig in env.rigs:
                    B=rotation(array(rig['robot'].get_world_pose()[1]))
                    preferred.append((float(np.arctan2(B[1,0],B[0,0])),rig['state']['arm']))
                aligned=False
                for attempt in range(3):
                    poses=live_poses(env);points=array(env.cloths[0].get_world_positions())[0]
                    centre=points[inspection.cuffs[cuff]].mean(0)
                    goals=poses.copy();goals[i]=(poses[i][0]+alignment_centre-centre,orientation)
                    key='align_'+str(attempt)
                    records[key],pairs=phase(env,inspection,prefix+'_'+key,goals,active,400 if orient_cuff else 140,policy,preferred,
                                            cuff_target=(cuff,alignment_centre),cuff_normal_target=direction if orient_cuff else None);samples+=pairs
                    if not records[key]['required_grasps_healthy'] or not records[key]['robots_upright'] or not records[key]['target_reached']:
                        return records,samples
                    measured=inspection.measure()['arms'][cuff]
                    denominator=measured['hand_signed_m']-measured['forearm_signed_m']
                    if denominator>.01 and measured['crossing_inside']:
                        aligned=True;break
                if not aligned:
                    records['insertion']={'insertion_candidate':False,'stopped_reason':'Live cuff still misaligned after three physical centring attempts'}
                    break
                poses=live_poses(env);points=array(env.cloths[0].get_world_positions())[0]
                centre=points[inspection.cuffs[cuff]].mean(0)
                initial_fraction=-measured['forearm_signed_m']/denominator
                # Keep the acquired orientation and slide the opening along the
                # actual arm axis. This avoids the failed F3 wrist rotation.
                target_centre=proximal+.65*axis+lateral
                goals=poses.copy();goals[i]=(poses[i][0]+target_centre-centre,orientation)
                (output/(prefix+'_thread_plan.json')).write_text(json.dumps({'cuff':cuff,
                    'initial_arm_axis_fraction':float(initial_fraction),'target_arm_axis_fraction':.65,
                    'lateral_gripper_clearance_offset_m':lateral.tolist(),'alignment_centre':alignment_centre.tolist(),
                    'initial_cuff_centre':centre.tolist(),'target_cuff_centre':target_centre.tolist(),
                    'translation_m':(target_centre-centre).tolist(),'gripper_orientation':'maintained'},indent=2))
                records[name],pairs=phase(env,inspection,prefix+'_'+name,goals,active,260,policy,preferred,
                                         cuff_target=(cuff,target_centre),cuff_normal_target=direction if orient_cuff else None,
                                         release_after_insertion=release_after_insertion);samples+=pairs
                break
            goals,fit,preferred=material_goals(env,path,active)
            (output/(prefix+'_'+name+'_goal_fit.json')).write_text(json.dumps({'fits':fit,'positions':[p.tolist() for p,R in goals],'rotations':[R.tolist() for p,R in goals]},indent=2))
            records[name],pairs=phase(env,inspection,prefix+'_'+name,goals,active,240,policy,preferred);samples+=pairs
            if not records[name]['required_grasps_healthy'] or not records[name]['robots_upright'] or not records[name]['target_reached']:break
        return records,samples
    result['teacher'],samples=episode('material_teacher')
    final=result['teacher'].get('insertion',{})
    if not final.get('insertion_candidate'):
        result['stopped_reason']='No stable geometrically verified insertion; failed dressing demonstration is not cloned'
        inspection.close();return result
    class MotionPolicy(torch.nn.Module):
        def __init__(self):
            super().__init__();self.log_gain=torch.nn.Parameter(torch.zeros(6));self.register_buffer('limit',torch.tensor([.12]*3+[.3]*3))
        def forward(self,x):return torch.clamp(x*self.log_gain.exp(),-self.limit,self.limit)
    x=torch.tensor(np.stack([a for a,b in samples]));y=torch.tensor(np.stack([b for a,b in samples]));policy=MotionPolicy()
    optimizer=torch.optim.Adam(policy.parameters(),lr=.03)
    for _ in range(400):
        loss=torch.nn.functional.mse_loss(policy(x),y);optimizer.zero_grad();loss.backward();optimizer.step()
    torch.save({'model':policy.state_dict(),'algorithm':'behavior cloning','network_type':'positive_task_space_gain','input_dim':6},output/'material_policy.pt')
    policy.load_state_dict(torch.load(output/'material_policy.pt',weights_only=True)['model']);policy.eval()
    np.savez_compressed(output/'material_demonstrations.npz',features=x.numpy(),actions=y.numpy())
    result['training']={'samples':len(samples),'loss':float(loss.detach())}
    result['fresh_pickup'],_=pickup_rollout('material_policy_pickup',pickup_model)
    if result['fresh_pickup']['success']:
        result['learned'],_=episode('material_learned',policy)
        result['insertion_candidate']=result['learned'].get('insertion',{}).get('insertion_candidate',False)
    inspection.close();return result
