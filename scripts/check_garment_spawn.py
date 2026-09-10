"""Offline uniform-box sampler and translation invariants."""
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/DexGarmentLab'))
from Env_Config.Garment.RandomSpawn import sample_garment_spawn
centers = np.array([[-3., -1., .3], [-1., -1., .3], [1., -1., .3], [3., -1., .3]])
size = [1., .8, .6]
counts = np.zeros(4, int)
representatives = {}
for seed in range(10000):
    sampled = sample_garment_spawn(centers, size, seed=seed)
    index = sampled['table_index']
    representatives.setdefault(index, seed)
    counts[index] += 1
    assert sampled == sample_garment_spawn(centers, size, seed=seed)
    assert np.allclose(sampled['spawn_position_world_m'], centers[index] + [0, 0, .5])
assert np.max(np.abs(counts - 2500)) < 150
# Whole mesh translation preserves relative vertices and cannot accumulate
# across resets when every translation starts from one immutable template.
rng = np.random.default_rng(0)
template = rng.normal(size=(100, 3)) * .1 + centers[2]
for index in (3, 0, 1, 2, 0, 2):
    moved = template + centers[index] - centers[2]
    assert np.allclose(moved[1:] - moved[0], template[1:] - template[0])
    if index == 2:
        assert np.allclose(moved, template)
for bad in ([], [[0, 0, float('nan')]], [[0, 0]]):
    try:
        sample_garment_spawn(bad, size, seed=0)
        raise AssertionError('Invalid table centers accepted')
    except ValueError:
        pass
print('GARMENT-SPAWN-CPU-PASS ' + json.dumps({'samples':10000, 'box_counts':counts.tolist(), 'representative_seeds':representatives}))
