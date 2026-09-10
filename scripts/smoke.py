"""Exercise the real teleop main loop, controls and checkpoint API on the GPU.

Uses an isolated state directory, never a user's F1-F5 slots. This is a short
installation smoke test, not a dressing-retention or high-load certification.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

output = Path('/output/verification')
output.mkdir(parents=True, exist_ok=True)
os.environ['STRETCH4_STATE_DIR'] = tempfile.mkdtemp(prefix='smoke_states_', dir=output)
sys.path.insert(0, '/workspace/DexGarmentLab')
import numpy as np
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M
from pxr import Usd, UsdGeom
import omni.usd

report = {'passed': False, 'scope': 'real main-loop startup, unloaded robot motion, gripper toggle, save/load'}
context = {'stop': False}
original_save = M.save_state_slot
original_drive = M.drive_robot
original_running = M.simulation_app.is_running
original_spawn = M.randomize_human_and_chair


def observed_spawn(stage, human_path):
    # Inspect the real posed meshes and all chair/hand-collider descendants.
    roots = [stage.GetPrimAtPath(p) for p in (human_path, '/World/Chair')]
    prims = [p for root in roots if root
             for p in Usd.PrimRange(root, Usd.TraverseInstanceProxies())
             if UsdGeom.Xformable(p)]
    before = {str(p.GetPath()): np.asarray(UsdGeom.Xformable(p)
              .ComputeLocalToWorldTransform(Usd.TimeCode.Default())) for p in prims}
    points = {str(p.GetPath()): np.asarray(UsdGeom.Mesh(p).GetPointsAttr().Get()).copy()
              for p in prims if p.IsA(UsdGeom.Mesh)}
    spawn = original_spawn(stage, human_path)
    assert np.linalg.norm(spawn['offset_m'][:2]) <= 0.10
    assert spawn['offset_m'][2] == 0 and -30 <= spawn['yaw_deg'] <= 30
    after = {str(p.GetPath()): np.asarray(UsdGeom.Xformable(p)
             .ComputeLocalToWorldTransform(Usd.TimeCode.Default())) for p in prims}
    delta = np.linalg.inv(before[human_path]) @ after[human_path]
    error = max(float(np.max(np.abs(before[path] @ delta - after[path])))
                for path in before)
    assert error < 1e-8, f'Human/chair descendants did not move together: {error}'
    assert np.allclose(delta[:3, :3] @ delta[:3, :3].T, np.eye(3), atol=1e-10)
    assert np.isclose(np.linalg.det(delta[:3, :3]), 1.0)
    for path, original in points.items():
        assert np.array_equal(original, UsdGeom.Mesh(stage.GetPrimAtPath(path)).GetPointsAttr().Get())
    assert np.allclose(after[human_path][3, :3] - before[human_path][3, :3], spawn['offset_m'])
    report['human_spawn'] = dict(spawn, checked_descendants=len(prims),
                                rigid_transform_max_error=error, local_mesh_points_unchanged=True)
    return spawn


def array(value):
    return np.asarray(M._to_np(value)).copy()


def geometry_hash(value):
    rounded = np.round(np.asarray(value, dtype=np.float64), 6)
    return hashlib.sha256(rounded.astype('<f8').tobytes()).hexdigest()


def observed_save(key, cloths, rigs):
    result = original_save(key, cloths, rigs)
    if key == 'F1' and 'cloths' not in context:
        assert result, 'Startup checkpoint could not be saved'
        context.update(cloths=cloths, rigs=rigs)
        stage = omni.usd.get_context().get_stage()
        mesh = UsdGeom.Mesh(cloths[0].prim)
        material_path = str(cloths[0].prim.GetPath()).rsplit('/', 2)[0]
        materials = {}
        heads = []
        for prim in stage.Traverse():
            values = {a.GetName(): a.Get() for a in prim.GetAttributes()
                      if a.GetName().startswith(('omniphysics:', 'physxDeformableMaterial:'))
                      and a.Get() is not None}
            if values and prim.GetTypeName() == 'Material':
                materials[str(prim.GetPath())] = values
            info = prim.GetAttribute('phyrc:roundedHeadInfo')
            if info and info.Get():
                heads.append({'info': json.loads(info.Get()),
                              'points_sha256': geometry_hash(UsdGeom.Mesh(prim).GetPointsAttr().Get())})
        body = UsdGeom.Mesh(stage.GetPrimAtPath('/World/Human/CollisionBody'))
        assert body, 'Rounded human collision mesh is missing'
        report['scene'] = {
            'garments': len(cloths), 'robots': len(rigs),
            'vertices': len(mesh.GetPointsAttr().Get()),
            'triangles': len(mesh.GetFaceVertexCountsAttr().Get()),
            'rest_points_sha256': geometry_hash(mesh.GetPointsAttr().Get()),
            'topology_sha256': geometry_hash(mesh.GetFaceVertexIndicesAttr().Get()),
            'collision_points_sha256': geometry_hash(body.GetPointsAttr().Get()),
            'solver_iterations': cloths[0].prim.GetAttribute('physxDeformableBody:solverPositionIterationCount').Get(),
            'materials': materials, 'rounded_heads': heads,
            'robot_initial_positions': [array(r['robot'].get_world_pose()[0]).tolist() for r in rigs],
            'human_transform': np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath('/World/Human'))
                                         .ComputeLocalToWorldTransform(Usd.TimeCode.Default())).tolist(),
        }
        context['initial_joints'] = [array(r['robot'].get_joint_positions()) for r in rigs]
        context['faces'] = [M.garment_face_labels(c.prim, array(c.get_world_positions())[0]) for c in cloths]
        assert report['scene']['vertices'] == 15946
        assert report['scene']['triangles'] == 31464
        assert report['scene']['solver_iterations'] == 32
        assert heads, 'Rounded visual head metadata is missing'
        print('PHYRC-SMOKE: full main-loop initialization reached', flush=True)
    return result


def observed_drive(rig, keymap, held, cloths, dt, frame):
    requested = {keymap['lift_pos']} if frame < 12 else set()
    original_drive(rig, keymap, requested, cloths, dt, frame)
    if rig is not context['rigs'][0]:
        return
    if frame == 13:
        toggle = M.make_gripper_toggle(rig, 'smoke', cloths, context['faces'])
        toggle()
        assert rig['state']['gripper_closed'], 'Gripper close did not reach control state'
        report['grasp_attached_in_initial_pose'] = rig['state'].get('grabbed') is not None
        toggle()
        assert not rig['state']['gripper_closed'], 'Gripper release did not reach control state'
        report['gripper_toggle'] = True
    if frame == 24:
        rigs = context['rigs']
        assert original_save('F2', cloths, rigs), 'Save failed'
        before = [array(c.get_world_positions()) for c in cloths]
        # A checkpoint from another random placement must not modify the scene.
        with np.load(M._state_slot_path('F2')) as saved:
            mismatched = {key: saved[key].copy() for key in saved.files}
        mismatched['placement_human'][3, 0] += 0.01
        np.savez_compressed(M._state_slot_path('F3'), **mismatched)
        assert not M.load_state_slot('F3', cloths, rigs), 'Mismatched placement was accepted'
        assert all(np.array_equal(array(c.get_world_positions()), p) for c, p in zip(cloths, before))
        report['mismatched_placement_rejected'] = True
        for cloth in cloths:
            positions = cloth.get_world_positions().clone()
            positions[..., 0] += 0.001
            cloth.set_world_positions(positions)
        assert M.load_state_slot('F2', cloths, rigs), 'Load failed'
        error = max(float(np.max(np.abs(array(c.get_world_positions()) - p)))
                    for c, p in zip(cloths, before))
        report['save_load_max_position_error_m'] = error
        assert error < 1e-5, f'Checkpoint position mismatch: {error}'
    if frame >= 36:
        movement = [float(np.max(np.abs(array(r['robot'].get_joint_positions()) - p)))
                    for r, p in zip(context['rigs'], context['initial_joints'])]
        assert all(value > 1e-4 for value in movement), f'Robots did not move: {movement}'
        assert all(np.isfinite(array(c.get_world_positions())).all() for c in cloths)
        report.update(passed=True, simulated_control_frames=frame + 1,
                      max_joint_displacement=movement, finite_cloth=True)
        (output / 'smoke.json').write_text(json.dumps(report, indent=2, default=str))
        print('PHYRC-SMOKE-PASS ' + json.dumps(report, default=str), flush=True)
        context['stop'] = True


M.save_state_slot = observed_save
M.randomize_human_and_chair = observed_spawn
M.drive_robot = observed_drive
M.simulation_app.is_running = lambda: not context['stop'] and original_running()
try:
    M.main()
except BaseException as error:
    report['error'] = repr(error)
    (output / 'smoke.json').write_text(json.dumps(report, indent=2, default=str))
    raise
if not report['passed']:
    raise SystemExit('Simulation exited before the smoke test completed')
