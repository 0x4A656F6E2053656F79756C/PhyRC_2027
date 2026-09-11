"""CPU USD regression: real instanced robot bindings, isolation, table friction, and rollback."""
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
from Env_Config.Garment.TableClothFriction import configure_table_cloth_friction

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
os.environ['STRETCH4_TABLE_CONTACT_FRICTION'] = '0'
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

# Gripper and table friction configuration
report_gripper = configure_gripper_cloth_friction(stage, .5)
assert len(report_gripper['colliders']) == 8, report_gripper
report_table = configure_table_cloth_friction(stage, .5)
assert len(report_table['colliders']) == 1, report_table

current = read_materials()
changed = {p for p in before if before[p] != current[p]}
expected_changed = set(report_gripper['colliders']) | set(report_table['colliders'])
assert changed == expected_changed, (changed, expected_changed)
assert cloth.GetAttribute('omniphysics:dynamicFriction').Get() == 0

# Human colliders must remain strictly zero friction with min combine
for p in before:
    if '/Human/' in p:
        assert current[p] == [0.0, 0.0, 'min'], (p, current[p])

# Invalid value rejection
for fn in (configure_gripper_cloth_friction, configure_table_cloth_friction):
    for value in (-1, float('nan'), float('inf')):
        try:
            fn(stage, value)
        except ValueError:
            pass
        else:
            raise AssertionError(f'{fn.__name__} allowed invalid value: {value}')

# Rollback to zero
configure_gripper_cloth_friction(stage, 0)
configure_table_cloth_friction(stage, 0)
assert read_materials() == before

# Exercise production defaults
os.environ.pop('STRETCH4_GRIPPER_CONTACT_FRICTION')
os.environ.pop('STRETCH4_TABLE_CONTACT_FRICTION')
zero_scene_friction(stage)
assert read_materials() == current

print(json.dumps({
    'passed': True,
    'finger_colliders': len(report_gripper['colliders']),
    'table_colliders': len(report_table['colliders']),
    'gripper_friction': 0.5,
    'table_friction': 0.5,
    'human_cloth_friction': 0.0,
    'cloth_friction': 0,
    'rollback_passed': True
}, indent=2))
