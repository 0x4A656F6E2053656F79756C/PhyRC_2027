"""CPU USD regression: real instanced robot bindings, isolation, and rollback."""
import json
import os
import sys
from pathlib import Path
schema_roots = list(Path("/isaac-sim/extscache").glob("omni.usd.schema.physx-*"))
lib_paths = os.environ.get('LD_LIBRARY_PATH', '').split(':')
missing = [str(p / 'bin') for p in schema_roots if str(p / 'bin') not in lib_paths]
if missing:
    os.environ['LD_LIBRARY_PATH'] = ':'.join(missing + lib_paths)
    os.execv(sys.executable, [sys.executable, *sys.argv])
for schema_root in schema_roots:
    sys.path.insert(0, str(schema_root))
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Plug
for schema in Path("/isaac-sim/extscache").glob("omni.usd.schema.physx-*/plugins/**/plugInfo.json"):
    Plug.Registry().RegisterPlugins(str(schema))
sys.path.insert(0, '/project/src/DexGarmentLab')
from Env_Config.Garment.ZeroSceneFriction import zero_scene_friction
from Env_Config.Garment.GripperClothFriction import configure_gripper_cloth_friction
stage = Usd.Stage.CreateInMemory()
for name in ('Stretch4', 'Stretch4_2'):
    stage.DefinePrim('/World/' + name).GetReferences().AddReference(
        '/project/assets/custom/robots/stretch_4/stretch_4.usd', '/stretch')
for name in ('Human/CollisionBody', 'Human/HandHull_left', 'Human/HandHull_right', 'Table'):
    prim = UsdGeom.Cube.Define(stage, '/World/' + name).GetPrim()
    UsdPhysics.CollisionAPI.Apply(prim)
cloth = UsdShade.Material.Define(stage, '/World/ClothMaterial').GetPrim()
cloth.ApplyAPI('OmniPhysicsBaseMaterialAPI')
cloth.ApplyAPI('OmniPhysicsDeformableMaterialAPI')
cloth.GetAttribute('omniphysics:dynamicFriction').Set(.7)
os.environ['STRETCH4_HUMAN_CONTACT_FRICTION'] = '0'
os.environ['STRETCH4_GRIPPER_CONTACT_FRICTION'] = '0'
zero_scene_friction(stage)
def read_materials():
    out = {}
    for p in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        if not p.HasAPI(UsdPhysics.CollisionAPI):
            continue
        m, _ = UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial('physics')
        if m:
            a = UsdPhysics.MaterialAPI(m.GetPrim())
            out[str(p.GetPath())] = [a.GetStaticFrictionAttr().Get(), a.GetDynamicFrictionAttr().Get(),
                PhysxSchema.PhysxMaterialAPI(m.GetPrim()).GetFrictionCombineModeAttr().Get()]
    return out
before = read_materials()
report = configure_gripper_cloth_friction(stage, .2)
assert len(report['colliders']) == 8, report
current = read_materials()
changed = {p for p in before if before[p] != current[p]}
assert changed == set(report['colliders']), changed
assert cloth.GetAttribute('omniphysics:dynamicFriction').Get() == 0
assert all(current[p] == before[p] for p in before if '/Human/' in p or p == '/World/Table')
for value in (-1, float('nan'), float('inf')):
    try:
        configure_gripper_cloth_friction(stage, value)
    except ValueError:
        pass
    else:
        raise AssertionError(value)
configure_gripper_cloth_friction(stage, 0)
assert read_materials() == before
# Exercise production defaults and repeated application as well.
os.environ.pop('STRETCH4_GRIPPER_CONTACT_FRICTION')
zero_scene_friction(stage)
assert read_materials() == current
print(json.dumps({'passed': True, 'finger_colliders': len(changed),
                  'nonfinger_colliders_unchanged': len(before) - len(changed),
                  'cloth_friction': 0, 'rollback_passed': True}, indent=2))
