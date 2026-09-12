"""CPU geometry and session lifecycle tests for teleop/policy evaluation."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.evaluation_geometry import boundary_loops, capped_mesh, inside_mesh, cuff_crossing, GarmentGeometry
from Policy.evaluation_live import EvaluationSession, IsaacMeasurements


def tube():
    angle = np.arange(32) * 2 * np.pi / 32
    points = np.array([[x, .2 * np.cos(a), .2 * np.sin(a)] for x in (0, 1) for a in angle])
    faces = []
    for a in range(32):
        b = (a + 1) % 32
        faces.extend([[a, b, b + 32], [a, b + 32, a + 32]])
    faces = np.asarray(faces)
    return points, faces, boundary_loops(faces)


class GeometryTests(unittest.TestCase):
    def test_short_sleeves_and_collar_require_exposed_hands_and_head(self):
        p, f, loops = tube()
        # Three isolated tubes exercise known sleeve/collar crossings without
        # depending on a learned policy or authored garment vertex numbers.
        body = p[:, [1, 2, 0]] + [0, 3, 0]
        points = np.vstack((p, p + [0, 1, 0], body))
        faces = np.vstack((f, f + 64, f + 128))
        geometry = GarmentGeometry.__new__(GarmentGeometry)
        geometry.faces, geometry.loops = faces, boundary_loops(faces)
        geometry.cuffs = [np.arange(32, 64), np.arange(96, 128)]
        geometry.inner = [np.arange(32), np.arange(64, 96)]
        geometry.collar, geometry.collar_inner = np.arange(160, 192), np.arange(128, 160)
        geometry.coverage_samples = 40
        arm = np.array([[.2, 0, 0], [1.5, 0, 0], [2.5, 0, 0], [2.7, 0, 0]])
        arms = dict(left=arm, right=arm + [0, 1, 0])
        neck = np.array([[0, 3, .2], [0, 3, .9], [0, 3, 1.3]])
        head = np.array([[0, 3, 1.1], [.05, 3, 1.2]])
        wrists, coverage, report = geometry.measure(points, arms, neck, head)
        self.assertTrue(report['dressing_complete'])
        self.assertLess(coverage['left'], .4)  # A short sleeve is enough.
        self.assertTrue(all(wrists.values()))
        # Collar caught on the face, wrong opening, or hand still inside.
        self.assertFalse(geometry.measure(points, arms, neck, head - [0, 0, .3])[2]['dressing_complete'])
        self.assertFalse(geometry.measure(points, arms, neck + [.4, 0, 0], head)[2]['dressing_complete'])
        short_hand = arm.copy(); short_hand[2:] = [[.7, 0, 0], [.8, 0, 0]]
        self.assertFalse(geometry.measure(points, dict(left=short_hand, right=arms['right']), neck, head)[2]['dressing_complete'])

    def test_virtual_caps_containment_and_rigid_invariance(self):
        points, faces, loops = tube()
        closed, triangles = capped_mesh(points, faces, loops)
        queries = np.array([[.5, 0, 0], [1.2, 0, 0], [.5, .3, 0], [-.2, 0, 0]])
        np.testing.assert_equal(inside_mesh(queries, closed, triangles), [True, False, False, False])
        rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        np.testing.assert_equal(inside_mesh(queries @ rotation + 7, closed @ rotation + 7, triangles),
                                [True, False, False, False])
        self.assertEqual(len(boundary_loops(triangles)), 0)

    def test_cuff_requires_polygon_crossing_not_nearness(self):
        points, _, _ = tube()
        chain = np.array([[.2, 0, 0], [.8, 0, 0], [1.3, 0, 0], [1.5, 0, 0]])
        self.assertAlmostEqual(cuff_crossing(points[32:], points[:32], chain), .8)
        self.assertIsNone(cuff_crossing(points[32:], points[:32], chain + [0, .3, 0]))
        self.assertIsNone(cuff_crossing(points[32:] * [1, 0, 0], points[:32], chain))
        self.assertIsNotNone(cuff_crossing(points[32:], points[:32], chain[::-1]))

    def test_known_arm_length_coverage_and_wrist_entry(self):
        points, faces, loops = tube()
        # A synthetic sleeve isolates the numeric primitive from shirt labels.
        geometry = GarmentGeometry.__new__(GarmentGeometry)
        geometry.faces, geometry.loops = faces, loops
        geometry.cuffs, geometry.inner = [np.arange(32, 64)], [np.arange(32)]
        geometry.coverage_samples = 40
        chain = np.array([[.2, 0, 0], [.8, 0, 0], [1.3, 0, 0], [1.5, 0, 0]])
        wrists, coverage, _ = geometry.measure(points, {'left': chain})
        self.assertTrue(wrists['left'])
        self.assertAlmostEqual(coverage['left'], 29 / 40)
        wrists, coverage, _ = geometry.measure(points, {'left': chain + [0, .3, 0]})
        self.assertFalse(wrists['left'])
        self.assertEqual(coverage['left'], 0)
        # Two arms in a single sleeve must not count as two dressed sleeves.
        wrists, coverage, _ = geometry.measure(points, {'left': chain, 'right': chain})
        self.assertFalse(any(wrists.values()))
        self.assertEqual(sum(coverage.values()), 0)


class FakeMeasurements:
    def contact(self, points):
        return True

    def __init__(self, *args):
        self.metadata = {'measurement_version': 'test'}
        self.calls = 0
        self.interrupt_at = None

    def physical_sample(self):
        self.calls += 1
        return None, [self.calls != self.interrupt_at, False], False, [True, False]

    def measure(self, physical=None):
        _, holding, clear, lifted = physical if physical else (None, [True, False], False, [True, False])
        return {'gripper_holding': holding, 'garment_lifted_clear': clear,
                'gripper_lifted': lifted, 'dressing_complete': False,
                'wrist_in_sleeve': {'left': False, 'right': False},
                'garment_beyond_shoulder': {'left': False, 'right': False},
                'arm_coverage': {'left': 0.0, 'right': 0.0}}


class SessionTests(unittest.TestCase):
    def test_precontact_pickup_is_kept_and_clock_uses_first_physics_contact(self):
        class Delayed(FakeMeasurements):
            def contact(self, points):
                return self.calls == 1001  # Only tick 1000, between 20Hz samples.
        with tempfile.TemporaryDirectory() as output:
            session = self.make_session(output)
            session.start(measurements=Delayed())
            for _ in range(1480):
                session._physics_step(1 / 240)
            result = session.finish()['result']
            self.assertEqual(result['raw_points'], 5)
            self.assertEqual(result['first_contact_tick'], 1000)
            self.assertEqual(result['task_time_s'], 2)
            self.assertEqual(result['final_score'], 2.5)
            from Policy.evaluation import evaluate_episode
            rescored = evaluate_episode(session.trace)
            self.assertEqual(rescored['task_time_s'], result['task_time_s'])
            self.assertEqual(rescored['final_score'], result['final_score'])

    def test_no_contact_session_saves_raw_points_but_no_rate(self):
        class NoContact(FakeMeasurements):
            def contact(self, points):
                return False
        with tempfile.TemporaryDirectory() as output:
            session = self.make_session(output)
            session.start(measurements=NoContact())
            for _ in range(721):
                session._physics_step(1 / 240)
            report = session.finish()
            self.assertTrue(report['valid'])
            self.assertEqual(report['result']['raw_points'], 5)
            self.assertIsNone(report['result']['final_score'])
            self.assertEqual(report['result']['score_status'], 'no_contact')

    @patch('Policy.dressing_task.grasp_health')
    def test_actual_anchor_rise_qualifies_even_when_hem_touches_table(self, health):
        initial = np.array([[0, 0, .5], [.02, 0, .5], [0, .02, .5],
                            [.2, 0, .5], [.22, 0, .5], [.2, .02, .5]])
        points = initial.copy()
        measurement = IsaacMeasurements.__new__(IsaacMeasurements)
        measurement.pickup_references = {}
        measurement.cloths = [SimpleNamespace(get_world_positions=lambda: points[None])]
        state = {'grabbed': (0, np.arange(3), None), '_grab_anchor_mask': np.ones(3, bool)}
        measurement.rigs = [{'state': state}, {'state': {}}]
        measurement.stage = None
        measurement.geometry = SimpleNamespace(faces=np.array([[0, 1, 2], [3, 4, 5]]))
        measurement.table_centres = np.array([[0, 0, .25]])
        measurement.table_size = np.array([1, 1, .5])
        measurement.clearance_m, measurement.max_anchor_error_m, measurement.pickup_rise_m = .01, .035, .05
        health.return_value = [dict(attached=True, anchor_count=3, anchor_p95_error_m=.001), dict(attached=False)]
        self.assertEqual(measurement.physical_sample()[3], [False, False])
        points[:3, 2] += .1
        _, holding, clear, lifted = measurement.physical_sample()
        self.assertEqual(holding, [True, False])
        self.assertFalse(clear)
        self.assertEqual(lifted, [True, False])
        points[:3, 2] = initial[:3, 2] + .02
        self.assertEqual(measurement.physical_sample()[3], [False, False])

    def make_session(self, output):
        physics = SimpleNamespace(subscribe_physics_on_step_events=lambda **kwargs: object())
        world = SimpleNamespace(get_physics_dt=lambda: 1 / 240,
                                _physics_context=SimpleNamespace(_physics_sim_interface=physics))
        return EvaluationSession(SimpleNamespace(world=world), [], [], None, output)

    @patch('Policy.evaluation_live.IsaacMeasurements', FakeMeasurements)
    def test_pickup_physics_interruptions_and_final_partial_interval(self):
        with tempfile.TemporaryDirectory() as output:
            session = self.make_session(output)
            session.start()
            for _ in range(720):
                session._physics_step(1 / 240)
            result = session.finish()
            self.assertEqual(result['result']['raw_points'], 5)
            self.assertAlmostEqual(result['result']['task_time_s'], 3)
            session.start()
            # A single 240 Hz interruption BETWEEN 20 Hz geometry samples.
            session.measurements.interrupt_at = 365
            for _ in range(725):
                session._physics_step(1 / 240)
            result = session.finish()
            self.assertTrue(result['valid'])
            self.assertEqual(result['result']['raw_points'], 0)
            self.assertAlmostEqual(result['result']['task_time_s'], 725 / 240)

    @patch('Policy.evaluation_live.IsaacMeasurements', FakeMeasurements)
    def test_reset_load_zero_duration_and_measurement_error_are_invalid(self):
        with tempfile.TemporaryDirectory() as output:
            session = self.make_session(output)
            for reason in ('checkpoint_load', 'scene_reset', 'policy_exception'):
                session.start()
                session._physics_step(1 / 240)
                result = session.finish(reason=reason, valid=False, take_final=False)
                self.assertFalse(result['valid'])
                self.assertIsNone(result['result'])
            session.start()
            self.assertFalse(session.finish()['valid'])
            session.start()
            session._physics_step(.1)  # Changed physics rate is an error.
            self.assertFalse(session.active)
            self.assertFalse(session.last_report['valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
