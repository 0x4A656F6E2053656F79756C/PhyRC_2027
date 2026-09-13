"""v8: instantaneous collar passage, unchanged overall grouping and sim timing."""
from copy import deepcopy
import unittest
from check_sleeve_scoring import samples
from Policy.evaluation import evaluate_episode, evaluate_submissions, format_score_items


def trace():
    rows = samples()
    for row in rows:
        row['neck_passed'] = row['neck_out']
    return rows


class InstantNeckTests(unittest.TestCase):
    def test_single_sample_passage_scores_immediately_and_latches(self):
        rows = trace()
        for i, row in enumerate(rows):
            row['neck_passed'] = row['neck_out'] = i == 1
        early = evaluate_episode(rows[:2])
        final = evaluate_episode(rows)
        for result in (early, final):
            overall = result['score_items']['overall_dressing']
            self.assertEqual(overall['components']['neck'], 10)
            self.assertEqual(overall['neck_confirmed_at_s'], .05)
            self.assertEqual(overall['neck_required_hold_s'], 0)
            self.assertEqual(overall['components']['front_orientation'], 0)
            self.assertFalse(result['success'])
        # The same evidence still uses its historical hold rule in old logs.
        for row in rows:
            row.pop('neck_passed')
        self.assertEqual(evaluate_episode(rows)['breakdown']['neck'], 0)

    def test_overall_grouping_and_fifty_point_allocation_preserved(self):
        result = evaluate_episode(trace())
        self.assertEqual(result['scoring_revision'], 'instant-neck-overall-v8')
        self.assertEqual(list(result['score_items']),
                         ['pickup', 'first_sleeve', 'opposite_shoulder', 'second_sleeve', 'overall_dressing'])
        self.assertEqual(result['overall_dressing_points'], 30)
        self.assertEqual(result['max_overall_dressing_points'], 30)
        self.assertEqual(result['raw_points'], 50)
        self.assertEqual(sum(v['points'] for v in result['score_items'].values()), 50)
        self.assertEqual(sum(v['max_points'] for v in result['score_items'].values()), 50)
        self.assertIn('Overall dressing 30.00/30', format_score_items(result))

    def test_front_and_success_hold_still_use_simulation_time(self):
        rows = trace()
        for row in rows:
            row['neck_passed'] = row['neck_out'] = row['time_s'] >= 1
        before = evaluate_episode(rows[:30])  # t=1.45, only .45s front exposure
        after = evaluate_episode(rows[:31])  # t=1.50
        self.assertEqual(before['breakdown']['neck'], 10)
        self.assertEqual(before['breakdown']['front_orientation'], 0)
        self.assertFalse(before['success'])
        self.assertEqual(after['breakdown']['front_orientation'], 10)
        self.assertTrue(after['success'])
        self.assertEqual(after['task_time_s'], 1.5)
        self.assertAlmostEqual(after['final_score'], after['raw_points'] / 1.5)
        self.assertEqual(evaluate_episode(rows[:60])['breakdown']['pickup'], 0)
        self.assertEqual(evaluate_episode(rows[:61])['breakdown']['pickup'], 5)

    def test_no_contact_aggregation_and_schema_validation(self):
        rows = trace()
        for row in rows:
            row['first_contact_time_s'] = None
            row['neck_passed'] = row['neck_out'] = False
        data = dict(schema_version='phase1-measurements-v6', submissions=[dict(
            submission_id='test', episodes=[dict(seed=i, samples=deepcopy(rows)) for i in (1, 2)])])
        result = evaluate_submissions(data)
        self.assertEqual(result['schema_version'], 'phase1-scores-v8')
        self.assertEqual(result['final_score'], 0)
        for episode in result['submissions'][0]['episodes']:
            self.assertEqual(episode['score_status'], 'no_contact')
            self.assertIsNone(episode['final_score'])
        data['schema_version'] = 'phase1-measurements-v5'
        with self.assertRaises(ValueError):
            evaluate_submissions(data)
        rows[1]['neck_passed'] = True
        with self.assertRaises(ValueError):
            evaluate_episode(rows)
        rows[1].pop('neck_passed')
        with self.assertRaises(ValueError):
            evaluate_episode(rows)


if __name__ == '__main__':
    unittest.main(verbosity=2)
