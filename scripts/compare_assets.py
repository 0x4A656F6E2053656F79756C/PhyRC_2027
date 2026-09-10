"""Compare generated USD geometry with an explicitly mounted migration baseline."""
import json
from pathlib import Path
import sys
import numpy as np
from pxr import Usd, UsdGeom

baseline = Path(sys.argv[1])
current = Path('/workspace/DexGarmentLab')
result = {}
for relative in [
    'Assets/Garment/Tops/Modelink/t_shirt.usd',
    'Assets/Garment/Tops/Modelink/t_shirt_short.usd',
    'Assets/Human/Mesh/manikin_exports/female2_c4-c5.usd',
]:
    stages = [Usd.Stage.Open(str(root / relative)) for root in (baseline, current)]
    meshes = [{str(p.GetPath()): UsdGeom.Mesh(p) for p in s.Traverse() if p.IsA(UsdGeom.Mesh)}
              for s in stages]
    assert meshes[0].keys() == meshes[1].keys(), relative
    maximum = 0.0
    for path, old in meshes[0].items():
        new = meshes[1][path]
        for attribute in ['faceVertexCounts', 'faceVertexIndices']:
            assert np.array_equal(old.GetPrim().GetAttribute(attribute).Get(),
                                  new.GetPrim().GetAttribute(attribute).Get()), (relative, path, attribute)
        a = np.asarray(old.GetPointsAttr().Get(), dtype=float)
        b = np.asarray(new.GetPointsAttr().Get(), dtype=float)
        assert a.shape == b.shape
        maximum = max(maximum, float(np.max(np.abs(a - b))))
        for attr in old.GetPrim().GetAttributes():
            if attr.GetName().startswith('phyrc:'):
                assert attr.Get() == new.GetPrim().GetAttribute(attr.GetName()).Get(), attr.GetName()
    assert maximum < 1e-7, (relative, maximum)
    assert UsdGeom.GetStageUpAxis(stages[0]) == UsdGeom.GetStageUpAxis(stages[1])
    assert UsdGeom.GetStageMetersPerUnit(stages[0]) == UsdGeom.GetStageMetersPerUnit(stages[1])
    result[relative] = {'max_vertex_difference_m': maximum, 'meshes': len(meshes[0]), 'passed': True}
Path('/output/verification').mkdir(parents=True, exist_ok=True)
Path('/output/verification/asset_comparison.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
