"""v7 regressions: routed sleeve material, binary upper coverage and hand exit."""
from copy import deepcopy
import unittest
import numpy as np
from check_overall_quality import quality_trace
from check_phase1_live import tube
from Policy.evaluation import evaluate_episode, evaluate_submissions
from Policy.evaluation_geometry import GarmentGeometry, boundary_loops, segment_in_mesh, capped_mesh


def samples():
    result = quality_trace()
    for s in result:
        s.update(upper_arm_sleeve_covered=dict(left=True, right=True),
                 hand_out_of_sleeve=dict(left=True, right=True))
    return result


def garment():
    # Connected torso tube x=0..1 and sleeve tube x=1..2, same material mesh.
    p, f, _ = tube()
    points = np.vstack((p, p[32:] + [1, 0, 0]))
    faces = np.vstack((f, f + 32))
    g = GarmentGeometry.__new__(GarmentGeometry)
    g.faces, g.loops = faces, boundary_loops(faces)
    g.cuffs, g.inner = [np.arange(64, 96)], [np.arange(32, 64)]
    g.coverage_samples = 40
    g.set_sleeve_regions([list(range(len(f), len(faces)))])
    return points, g


class SleeveTests(unittest.TestCase):
    def test_success_selection_uses_completion_not_total_points(self):
        s = samples()
        for row in s:
            row['gripper_holding'] = row['gripper_lifted'] = [False, False]
        r = evaluate_episode(s)
        self.assertEqual(r['raw_points'], 45)
        self.assertTrue(r['success_evaluated'])
        self.assertTrue(r['success'])
        s = samples()
        for row in s:
            row['hand_out_of_sleeve'] = dict(left=row['time_s'] < 1, right=row['time_s'] < 1)
            row['neck_out'] = row['front_facing'] = row['time_s'] >= 1
        r = evaluate_episode(s)
        self.assertEqual(r['raw_points'], 50)
        self.assertFalse(r['success'])

    def test_full_points_and_binary_coverage_ignores_all_fractions(self):
        s = samples()
        for row in s:
            row['upper_arm_coverage'] = dict(left=0, right=0)
            row['arm_coverage'] = dict(left=0, right=0)
        r = evaluate_episode(s)
        self.assertEqual(r['raw_points'], 50)
        self.assertEqual(r['scoring_revision'], 'sleeve-cover-hand-exit-v7')
        self.assertNotIn('upper_arm_full_credit_fraction', r['score_items']['overall_dressing'])
        for row in s: row['upper_arm_sleeve_covered']['right'] = False
        self.assertEqual(evaluate_episode(s)['overall_dressing_points'], 25)

    def test_wrist_entry_does_not_score_until_hand_exits_and_order_is_temporal(self):
        s = samples()
        for row in s:
            row['hand_out_of_sleeve'] = dict(left=row['time_s'] >= 2, right=row['time_s'] >= 1)
        before = evaluate_episode(s[:20])
        self.assertEqual(before['breakdown']['first_sleeve'], 0)
        self.assertEqual(before['breakdown']['second_sleeve'], 0)
        self.assertFalse(before['success'])
        r = evaluate_episode(s)
        self.assertEqual(r['first_arm'], 'right')
        self.assertEqual(r['milestone_times_s']['first_sleeve'], 1)
        self.assertEqual(r['milestone_times_s']['second_sleeve'], 2)

    def test_routing_required_and_points_latched(self):
        s = samples()
        for row in s: row['wrist_in_sleeve']['left'] = False
        r = evaluate_episode(s)
        self.assertEqual(r['breakdown']['left_upper_arm'], 0)
        self.assertEqual(r['breakdown']['second_sleeve'], 0)
        s = samples()
        for row in s[1:]:
            row['upper_arm_sleeve_covered'] = dict(left=False, right=False)
            row['hand_out_of_sleeve'] = dict(left=False, right=False)
        r = evaluate_episode(s)
        self.assertEqual(r['breakdown']['left_upper_arm'], 5)
        self.assertEqual(r['breakdown']['second_sleeve'], 5)

    def test_torso_enclosure_not_sleeve_coverage_and_tiny_sleeve_overlap_counts(self):
        p, g = garment()
        chain = np.array([[.2, 0, 0], [.8, 0, 0], [2.5, 0, 0], [2.7, 0, 0]])
        d = g.measure(p, dict(left=chain))[2]['left']
        self.assertEqual(d['upper_arm_coverage'], 1)
        self.assertTrue(d['hand_out'])
        self.assertFalse(d['upper_arm_sleeve_covered'])
        chain[1, 0] = 1.0001
        d = g.measure(p, dict(left=chain))[2]['left']
        self.assertTrue(d['upper_arm_sleeve_covered'])
        # Merely touch sleeve root without entering its volume.
        v, f = capped_mesh(p, g.faces[g.sleeve_regions[0]], g.sleeve_loops[0])
        self.assertFalse(segment_in_mesh(np.array([[.2, 0, 0], [1., 0, 0]]), v, f))
        # Even routing cannot rely on a 40-point coverage probe hitting the cloth.
        short = np.array([[1.9999, 0, 0], [2.4, 0, 0], [2.5, 0, 0], [2.7, 0, 0]])
        w, _, d = g.measure(p, dict(left=short))
        self.assertTrue(w['left'])
        self.assertTrue(d['left']['upper_arm_sleeve_covered'])

    def test_geometry_requires_wrist_and_hand_outside_cuff(self):
        p, g = garment()
        chain = np.array([[.2, 0, 0], [1.5, 0, 0], [1.9, 0, 0], [2.1, 0, 0]])
        w, _, d = g.measure(p, dict(left=chain))
        self.assertTrue(w['left'])
        self.assertFalse(d['left']['hand_out'])
        chain[2:, 0] += .3
        self.assertTrue(g.measure(p, dict(left=chain))[2]['left']['hand_out'])
        d = g.measure(p, dict(left=chain, right=chain))[2]
        for side in ('left', 'right'):
            self.assertFalse(d[side]['hand_out'])
            self.assertFalse(d[side]['upper_arm_sleeve_covered'])

    def test_no_contact_ranking_and_schema_validation(self):
        s = samples()
        for row in s:
            row['first_contact_time_s'] = None
            row['neck_out'] = row['front_facing'] = False
        data = dict(schema_version='phase1-measurements-v5', submissions=[dict(submission_id='test',
                    episodes=[dict(seed=i, samples=deepcopy(s)) for i in (42,43)])])
        r = evaluate_submissions(data)
        self.assertEqual(r['schema_version'], 'phase1-scores-v7')
        self.assertEqual(r['final_score'], 0)
        data['schema_version'] = 'phase1-measurements-v4'
        with self.assertRaises(ValueError): evaluate_submissions(data)
        s[1].pop('hand_out_of_sleeve')
        with self.assertRaises(ValueError): evaluate_episode(s)


if __name__ == '__main__': unittest.main(verbosity=2)
