"""CPU checks of archived physical evidence against live scoring, including 1-tick loss."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.evaluation_geometry import GarmentGeometry, boundary_loops
from Policy.evaluation_live import IsaacMeasurements, EvaluationSession
from Policy.evaluation_replay import measurement_context, ReplayEvaluation
from Policy.teleop_recording import StateArchive, ArchiveReader
from Policy.evaluation_contact import CollisionContact
from check_phase1_live import tube


def fixture():
    p, f, _ = tube()
    points = np.vstack((p, p + [0, 1, 0], p[:, [1, 2, 0]] + [0, 3, 0]))
    g = GarmentGeometry.__new__(GarmentGeometry)
    g.faces = np.vstack((f, f + 64, f + 128))
    g.loops = boundary_loops(g.faces)
    g.cuffs = [np.arange(32, 64), np.arange(96, 128)]
    g.inner = [np.arange(32), np.arange(64, 96)]
    g.collar, g.collar_inner = np.arange(160, 192), np.arange(128, 160)
    g.coverage_samples = 40
    m = IsaacMeasurements.__new__(IsaacMeasurements)
    m.geometry = g
    arm = np.array([[.2, 0, 0], [1.5, 0, 0], [2.5, 0, 0], [2.7, 0, 0]])
    m.arms = dict(left=arm, right=arm + [0, 1, 0])
    m.neck_chain = np.array([[0, 3, .2], [0, 3, .9], [0, 3, 1.3]])
    m.head_surface = np.array([[0, 3, 1.1], [.05, 3, 1.2]])
    m.table_centres, m.table_size = np.empty((0, 3)), np.ones(3)
    m.clearance_m, m.max_anchor_error_m, m.pickup_rise_m = .01, .035, .05
    m.pickup_references, m.pickup_diagnostics = {}, []
    m.metadata = {'measurement_version': 'synthetic-test'}
    m.contact_context = {'version': 1, 'criterion': 'synthetic collision surface', 'limitations': 'test geometry',
                         'garment_faces': g.faces.tolist(), 'garment_contact_offset_m': 0,
                         'colliders': [dict(path='/World/Human/Test', type='mesh',
                                            points=points[:3].tolist(), faces=[[0, 1, 2]], contact_offset_m=0)]}
    m.contact_detector = CollisionContact(m.contact_context, np.eye(4))
    for field, filename in [('geometry_source_sha256', 'evaluation_geometry.py'),
                            ('scoring_source_sha256', 'evaluation.py'), ('live_source_sha256', 'evaluation_live.py')]:
        m.metadata[field] = hashlib.sha256((ROOT / 'src/DexGarmentLab/Policy' / filename).read_bytes()).hexdigest()
    return points, m


def state(points, tick, interrupted=False):
    values = {'g0_positions': points + [0, 0, .06 if tick else 0], 'static_Human': np.eye(4)}
    for i in range(2):
        prefix = f'r{i}_'
        values.update({prefix + 'grab_cloth': np.array(0 if i == 0 else -1),
                       prefix + 'attachment_present': np.array(i == 0 and not (interrupted and tick == 360)),
                       prefix + 'anchor_data_present': np.array(True),
                       prefix + 'anchor_mask': np.array([True, False, True]),
                       prefix + 'grab_indices': np.array([0, 1, 2]),
                       prefix + 'anchor_local_offsets': points[:3].copy(),
                       prefix + 'links': np.array([[0, 0, .06 if tick else 0, 0, 0, 0, 1]])})
    return values


class ReplayTests(unittest.TestCase):
    def run_comparison(self, interrupted):
        points, measurement = fixture()
        context = measurement_context(measurement)
        current = [None]
        measurement.cloths = [SimpleNamespace(get_world_positions=lambda: np.array([current[0]['g0_positions']]))]
        measurement.rigs = []
        for i in range(2):
            view = SimpleNamespace(_physics_view=SimpleNamespace(get_link_transforms=lambda i=i:
                                   np.array([current[0][f'r{i}_links']])))
            measurement.rigs.append(dict(robot=SimpleNamespace(prim_path=f'/r{i}/robot', _articulation_view=view),
                                         grasp_link_idx=0, state={}))
        measurement.stage = SimpleNamespace(GetPrimAtPath=lambda path:
                                             bool(current[0][path.split('/')[1] + '_attachment_present']))
        def update(values):
            current[0] = values
            for i, rig in enumerate(measurement.rigs):
                rig['state'] = dict(grabbed=(0, values[f'r{i}_grab_indices'], None) if i == 0 else None,
                                    _native_local_offsets=values[f'r{i}_anchor_local_offsets'],
                                    _grab_anchor_mask=values[f'r{i}_anchor_mask'])
        metadata = dict(physics_dt_s=1 / 240, evaluation_state_version=1, grasp_link_indices=[0, 0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = StateArchive(root / 'recording', metadata)
            backend = SimpleNamespace(world=SimpleNamespace(get_physics_dt=lambda: 1 / 240))
            live = EvaluationSession(backend, [], [], None, root / 'live')
            for tick in range(746):
                values = state(points, tick, interrupted)
                update(values)
                if tick == 0:
                    live.start(measurements=measurement, subscribe=False)
                    values['evaluation_context'] = np.array(json.dumps(context))
                else:
                    live._physics_step(1 / 240)
                archive.append(tick, 'physics' if tick else 'initial', values)
            expected = live.finish()
            archive.close()
            replay = ReplayEvaluation(metadata, root / 'replay')
            for header, values in ArchiveReader(archive.path).frames():
                replay.consume(header, values)
            actual = replay.finish()
            self.assertTrue(actual['valid'])
            self.assertEqual(actual['result'], expected['result'])
            self.assertEqual(replay.session.trace, live.trace)
            self.assertEqual(actual['result']['raw_points'], 45 if interrupted else 50)
            self.assertAlmostEqual(actual['result']['task_time_s'], 745 / 240)

    def test_nonzero_live_replay_scores_and_every_sample_identical(self):
        self.run_comparison(False)

    def test_single_physics_tick_attachment_loss_is_preserved(self):
        self.run_comparison(True)

    def test_legacy_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'older recording'):
            ReplayEvaluation({'physics_dt_s': 1 / 240}, '/unused')

    def test_reset_inside_attempt_is_invalid_and_range_can_start_after_it(self):
        points, m = fixture()
        context = np.array(json.dumps(measurement_context(m)))
        metadata = dict(physics_dt_s=1 / 240, evaluation_state_version=1, grasp_link_indices=[0, 0])
        frames = []
        for tick, kind in [(0, 'initial'), (1, 'physics'), (1, 'before_reset'), (1, 'after_reset'), (2, 'physics')]:
            v = state(points, tick)
            if kind in ('initial', 'after_reset'):
                v['evaluation_context'] = context
            frames.append((dict(tick=tick, kind=kind), v))
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = ReplayEvaluation(metadata, tmp)
            with self.assertRaisesRegex(ValueError, 'Reset/load'):
                for h, v in frames:
                    evaluator.consume(h, v)
            self.assertFalse(evaluator.session.last_report['valid'])
            evaluator = ReplayEvaluation(metadata, tmp, start_tick=1, end_tick=2)
            for h, v in frames:
                evaluator.consume(h, v)
            self.assertTrue(evaluator.finish()['valid'])
            self.assertEqual(evaluator.last_tick, 2)
            evaluator = ReplayEvaluation(metadata, tmp, start_tick=1, end_tick=3)
            for h, v in frames:
                evaluator.consume(h, v)
            with self.assertRaisesRegex(ValueError, 'before requested'):
                evaluator.finish()
            self.assertFalse(evaluator.session.last_report['valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
