"""Compare scene fingerprints from two successful installation smoke runs."""
import json
import math
from pathlib import Path
import sys


def compare(a, b, path='scene'):
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), path
        for key in a:
            compare(a[key], b[key], f'{path}.{key}')
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for index, (old, new) in enumerate(zip(a, b)):
            compare(old, new, f'{path}[{index}]')
    elif isinstance(a, (float, int)) and not isinstance(a, bool):
        assert math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-6), (path, a, b)
    else:
        assert a == b, (path, a, b)


baseline, current = [json.loads(Path(path).read_text()) for path in sys.argv[1:3]]
assert baseline['passed'] and current['passed'], 'Both runtime tests must pass first'
compare(baseline['scene'], current['scene'])
print('PHYRC-SCENE-COMPARISON-PASS: geometry hashes, material, head, poses and solver match')
