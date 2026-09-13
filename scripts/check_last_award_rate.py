"""v9 regressions for pickup exclusion and a latched last-award endpoint."""
from copy import deepcopy
import unittest
from check_instant_neck_scoring import trace
from Policy.evaluation import RATE_RULE, evaluate_episode, evaluate_submissions


def rows():
    result = trace()
    for s in result:
        t = s['time_s']
        s.update(rate_rule=RATE_RULE, first_contact_time_s=None if t < 1.025 else 1.025,
                 physics_tick=round(t * 240), physics_dt_s=1 / 240,
                 first_contact_tick=None if t < 1.025 else 246,
                 neck_passed=t >= 2, neck_out=t >= 2, front_facing=False,
                 wrist_in_sleeve=dict(left=False, right=False),
                 hand_out_of_sleeve=dict(left=False, right=False),
                 upper_arm_sleeve_covered=dict(left=False, right=False),
                 garment_beyond_shoulder=dict(left=False, right=False))
    return result


class LastAwardRateTests(unittest.TestCase):
    def test_pickup_and_idle_time_do_not_change_rate_or_endpoint(self):
        s = rows()
        early = evaluate_episode(s[:41])  # Neck 10 at t=2, no pickup yet.
        late = evaluate_episode(s)        # Pickup 5 at t=3, then idle.
        self.assertEqual(early['raw_points'], 10)
        self.assertEqual(late['raw_points'], 15)
        self.assertEqual(late['excluded_pickup_points'], 5)
        for r in (early, late):
            self.assertEqual(r['rate_points'], 10)
            self.assertEqual(r['last_score_award_tick'], 480)
            self.assertEqual(r['last_score_award_time_s'], 2)
            self.assertAlmostEqual(r['task_time_s'], 234 / 240)
            self.assertAlmostEqual(r['final_score'], 10 / (234 / 240))
        self.assertEqual(late['elapsed_episode_time_s'], 4)
        self.assertAlmostEqual(late['contact_elapsed_time_s'], 4 - 1.025)

    def test_next_dressing_award_updates_cumulative_rate_not_interval_rate(self):
        s = rows()
        for row in s:
            row['front_facing'] = row['time_s'] >= 2
        r = evaluate_episode(s)
        self.assertEqual(r['last_score_award_time_s'], 2.5)
        self.assertEqual(r['last_score_award_tick'], 600)
        self.assertEqual(r['raw_points'], 25)
        self.assertEqual(r['rate_points'], 20)
        self.assertAlmostEqual(r['final_score'], 20 / (2.5 - 1.025))

    def test_pickup_only_and_no_contact_failures_aggregate_without_exception(self):
        s = rows()
        for row in s:
            row['neck_passed'] = row['neck_out'] = False
        r = evaluate_episode(s)
        self.assertEqual(r['raw_points'], 5)
        self.assertEqual(r['rate_points'], 0)
        self.assertEqual(r['final_score'], 0)
        self.assertEqual(r['task_time_s'], 0)
        self.assertIsNone(r['last_score_award_time_s'])
        self.assertEqual(r['score_status'], 'no_dressing_points')
        no_contact = deepcopy(s)
        for row in no_contact:
            row['first_contact_time_s'] = row['first_contact_tick'] = None
        data = dict(schema_version='phase1-measurements-v7', submissions=[dict(
            submission_id='test', episodes=[dict(seed=1, samples=s), dict(seed=2, samples=no_contact)])])
        report = evaluate_submissions(data)
        self.assertEqual(report['schema_version'], 'phase1-scores-v9')
        self.assertEqual(report['scoring_revision'], RATE_RULE)
        self.assertEqual(report['final_score'], 0)
        self.assertIsNone(report['submissions'][0]['episodes'][1]['final_score'])
        data['schema_version'] = 'phase1-measurements-v6'
        with self.assertRaises(ValueError):
            evaluate_submissions(data)

    def test_zero_time_positive_points_do_not_become_infinite_after_waiting(self):
        s = rows()
        for row in s:
            row['first_contact_time_s'] = 0
            row['first_contact_tick'] = 0
            row['neck_passed'] = row['neck_out'] = True
        r = evaluate_episode(s)
        self.assertEqual(r['rate_points'], 10)
        self.assertEqual(r['task_time_s'], 0)
        self.assertIsNone(r['final_score'])
        self.assertEqual(r['score_status'], 'awaiting_elapsed_time')

    def test_old_measurements_keep_old_formula_and_mixed_rules_are_rejected(self):
        s = rows()
        for row in s:
            row.pop('rate_rule')
        old = evaluate_episode(s)
        self.assertEqual(old['scoring_revision'], 'instant-neck-overall-v8')
        self.assertAlmostEqual(old['final_score'], 15 / (4 - 1.025))
        s[1]['rate_rule'] = RATE_RULE
        with self.assertRaises(ValueError):
            evaluate_episode(s)


if __name__ == '__main__':
    unittest.main(verbosity=2)
