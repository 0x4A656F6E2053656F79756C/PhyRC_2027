"""CPU/USD checks for placement bounds, distribution and preserved assembly."""
import contextlib
import io
import os
import sys

import numpy as np
from pxr import Gf, Usd, UsdGeom

sys.path.insert(0, '/project/src/DexGarmentLab')
from Env_Config.Human.RandomSpawn import randomize_human_and_chair, placement_snapshot, placement_matches
os.environ['STRETCH4_RANDOMIZE'] = '1'


def scene():
    stage = Usd.Stage.CreateInMemory()
    human = UsdGeom.Xform.Define(stage, '/World/Human')
    human.AddTranslateOp().Set(Gf.Vec3d(1.2, 0.45, -0.2))
    human.AddRotateXOp().Set(90)
    human.AddScaleOp().Set(Gf.Vec3f(0.6, 0.46, 0.55))
    UsdGeom.Cube.Define(stage, '/World/Human/Body').AddTranslateOp().Set(Gf.Vec3d(0, 1, 0))
    UsdGeom.Cube.Define(stage, '/World/Chair/Leg').AddTranslateOp().Set(Gf.Vec3d(1.3, 0.55, 0.2))
    return stage


samples = []
with contextlib.redirect_stdout(io.StringIO()):
    for seed in range(1000):
        os.environ['HUMAN_SPAWN_SEED'] = str(seed)
        stage = scene()
        paths = ['/World/Human', '/World/Human/Body', '/World/Chair/Leg']
        def matrices():
            return [np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(p))
                    .ComputeLocalToWorldTransform(Usd.TimeCode.Default())) for p in paths]
        before = matrices()
        result = randomize_human_and_chair(stage, paths[0])
        after = matrices()
        delta = np.linalg.inv(before[0]) @ after[0]
        for old, new in zip(before, after):
            assert np.allclose(old @ delta, new, atol=1e-10)
        assert np.allclose(delta[:3, :3] @ delta[:3, :3].T, np.eye(3), atol=1e-10)
        offset = after[0][3, :3] - before[0][3, :3]
        assert np.linalg.norm(offset[:2]) <= 0.10 + 1e-12 and abs(offset[2]) < 1e-12
        assert np.allclose(offset, result['offset_m'], atol=1e-12)
        assert -30 <= result['yaw_deg'] <= 30
        saved = placement_snapshot(stage)
        assert placement_matches(stage, saved)
        saved['placement_human'][3, 0] += 0.001
        assert not placement_matches(stage, saved)
        assert not placement_matches(stage, {})
        samples.append([*offset[:2], result['yaw_deg']])
    # Fixed seeds reproduce; default launches use independent entropy.
    assert randomize_human_and_chair(scene(), paths[0]) == randomize_human_and_chair(scene(), paths[0])
    del os.environ['HUMAN_SPAWN_SEED']
    assert randomize_human_and_chair(scene(), paths[0]) != randomize_human_and_chair(scene(), paths[0])
samples = np.asarray(samples)
assert np.max(np.abs(samples[:, :2].mean(axis=0))) < 0.006
assert abs(np.mean(np.sum(samples[:, :2] ** 2, axis=1)) - 0.005) < 0.0005
assert np.all(np.histogram(samples[:, 2], bins=4, range=(-30, 30))[0] > 200)
os.environ['STRETCH4_RANDOMIZE'] = '0'
for seed in ('42', '43', 'unused-when-disabled'):
    os.environ['HUMAN_SPAWN_SEED'] = seed
    stage = scene()
    authored = stage.GetRootLayer().ExportToString()
    result = randomize_human_and_chair(stage, '/World/Human')
    assert stage.GetRootLayer().ExportToString() == authored
    assert result['offset_m'] == [0, 0, 0] and result['yaw_deg'] == 0
    assert result['randomized'] is False and result['seed'] is None
print('RANDOM-SPAWN-PASS: 1000 placements; disk/yaw distribution, height, rigid assembly, seeds and slot validation')
