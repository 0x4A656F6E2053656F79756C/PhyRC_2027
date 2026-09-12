"""CPU regression tests for proposal score accounting and trace validation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.evaluation import (Phase1Scorer, Phase1TaskEvaluator, ScoringConfig,
                               evaluate_episode, evaluate_submissions, format_score_items)
from evaluate_phase1 import demo_data


def trace(seconds=4):
    return [{'time_s': tick / 20, 'gripper_holding': [False, False],
             'garment_lifted_clear': False,
             'wrist_in_sleeve': {'left': False, 'right': False},
             'garment_beyond_shoulder': {'left': False, 'right': False},
             'arm_coverage': {'left': 0.0, 'right': 0.0}}
            for tick in range(round(seconds * 20) + 1)]


class ScoringTests(unittest.TestCase):
    def test_separate_items_preserve_formula_and_require_each_milestone(self):
        samples = trace()
        for s in samples:
            s['wrist_in_sleeve'] = dict(left=True, right=True)
            s['arm_coverage'] = dict(left=.3, right=.2)
        result = evaluate_episode(samples)
        items = result['score_items']
        self.assertEqual(items['pickup']['points'], 0)
        self.assertEqual(items['first_sleeve']['points'], 5)
        self.assertEqual(items['opposite_shoulder']['points'], 0)
        self.assertEqual(items['second_sleeve']['points'], 5)
        self.assertEqual(items['overall_dressing']['points'], .3 * 10 + .2 * 20)
        self.assertEqual(result['overall_dressing_points'], 7)
        self.assertEqual(result['max_overall_dressing_points'], 30)
        self.assertEqual(result['raw_points'], sum(item['points'] for item in items.values()))
        self.assertEqual(sum(item['max_points'] for item in items.values()), 50)
        text = format_score_items(result)
        for label in ('Pickup', 'First sleeve', 'Opposite shoulder', 'Second sleeve', 'Overall dressing 7.00/30'):
            self.assertIn(label, text)
        self.assertNotIn('/45', text)
        samples[-1]['garment_beyond_shoulder']['right'] = True
        after = evaluate_episode(samples)
        self.assertEqual(after['score_items']['opposite_shoulder']['points'], 5)
        self.assertEqual(after['overall_dressing_points'], 7)
        self.assertEqual(after['raw_points'], result['raw_points'] + 5)

    def test_contact_clock_latches_and_rejects_retroactive_or_mixed_evidence(self):
        samples = trace()
        for s in samples:
            s['first_contact_time_s'] = 1.025 if s['time_s'] >= 1.025 else None
            s['gripper_holding'][0] = True
            s['garment_lifted_clear'] = True
        score = evaluate_episode(samples)
        self.assertEqual(score['raw_points'], 5)
        self.assertAlmostEqual(score['task_time_s'], 4 - 1.025)
        for mutation in ('change', 'omit', 'retroactive'):
            changed = deepcopy(samples)
            if mutation == 'change':
                changed[-1]['first_contact_time_s'] = 2
            elif mutation == 'omit':
                del changed[-1]['first_contact_time_s']
            else:
                changed[21]['first_contact_time_s'] = .5
            with self.assertRaises(ValueError):
                evaluate_episode(changed)

    def test_v3_requires_contact_evidence_and_does_not_rank_undefined_rates(self):
        data = demo_data()
        data['schema_version'] = 'phase1-measurements-v3'
        del data['submissions'][0]['episodes'][0]['samples'][0]['first_contact_time_s']
        with self.assertRaises(ValueError):
            evaluate_submissions(data)
        for episode in data['submissions'][0]['episodes']:
            for s in episode['samples']:
                s['first_contact_time_s'] = 2 if s['time_s'] >= 2 else None
        self.assertEqual(evaluate_submissions(data)['final_score'], (50 / 8 + 20 / 8) / 2)
        legacy = deepcopy(data)
        legacy['schema_version'] = 'phase1-measurements-v2'
        with self.assertRaisesRegex(ValueError, 'do not mix timing bases'):
            evaluate_submissions(legacy)
        for s in data['submissions'][0]['episodes'][0]['samples']:
            s['first_contact_time_s'] = None
        with self.assertRaisesRegex(ValueError, 'No comparable points/s'):
            evaluate_submissions(data)

    def test_no_progress_and_zero_time(self):
        self.assertEqual(evaluate_episode(trace())['final_score'], 0)
        for samples in ([], trace(0)):
            with self.assertRaises(ValueError):
                evaluate_episode(samples)

    def test_pickup_threshold_and_clearance(self):
        samples = trace()
        for s in samples:
            s['gripper_holding'][0] = True
            s['garment_lifted_clear'] = True
        self.assertEqual(evaluate_episode(samples[:60])['raw_points'], 0)
        at_three = evaluate_episode(samples[:61])
        self.assertEqual(at_three['raw_points'], 5)
        self.assertAlmostEqual(at_three['final_score'], 5 / 3)
        # Grip command/contact while on the table earns no pickup points.
        for s in samples:
            s['garment_lifted_clear'] = False
        self.assertEqual(evaluate_episode(samples)['raw_points'], 0)

    def test_dropped_grip_clearance_and_handoff_reset_timer(self):
        for interruption in ('grip', 'clearance', 'handoff'):
            samples = trace()
            for s in samples:
                s['gripper_holding'][0] = True
                s['garment_lifted_clear'] = True
                if interruption == 'handoff' and s['time_s'] >= 2:
                    s['gripper_holding'] = [False, True]
            if interruption == 'grip':
                samples[40]['gripper_holding'][0] = False
            elif interruption == 'clearance':
                samples[40]['garment_lifted_clear'] = False
            self.assertEqual(evaluate_episode(samples)['raw_points'], 0, interruption)

    def test_milestones_and_best_progress_do_not_decrease(self):
        samples = trace()
        for s in samples[20:40]:
            s['wrist_in_sleeve']['left'] = True
            s['arm_coverage']['left'] = 1.0
        result = evaluate_episode(samples)
        self.assertEqual(result['raw_points'], 15)
        self.assertEqual(result['breakdown']['first_arm_coverage'], 10)
        self.assertEqual(result['milestone_times_s']['first_sleeve'], 1)

    def test_short_sleeve_completion_and_confirmation(self):
        samples = trace(4)
        for s in samples:
            s['wrist_in_sleeve'] = dict(left=True, right=True)
            s['arm_coverage'] = dict(left=.35, right=.35)
            s['dressing_complete'] = s['time_s'] >= 1
        self.assertLess(evaluate_episode(samples[:30])['overall_dressing_points'], 30)
        result = evaluate_episode(samples[:31])
        self.assertEqual(result['overall_dressing_points'], 30)
        self.assertEqual(result['raw_points'], 40)  # Pickup and shoulder remain independent.
        self.assertEqual(result['score_items']['opposite_shoulder']['points'], 0)
        self.assertTrue(result['score_items']['overall_dressing']['full_dressing_override'])
        self.assertEqual(result['score_items']['overall_dressing']['n'], .35)
        self.assertEqual(result['dressing_completed_at_s'], 1.5)
        for s in samples[31:]:
            s['dressing_complete'] = False
            s['arm_coverage'] = dict(left=0, right=0)
        self.assertEqual(evaluate_episode(samples)['raw_points'], 40)
        for s in samples:
            s['gripper_holding'][0] = True
            s['gripper_lifted'] = [True, False]
        self.assertEqual(evaluate_episode(samples)['raw_points'], 45)
        samples[-1]['garment_beyond_shoulder']['right'] = True
        self.assertEqual(evaluate_episode(samples)['raw_points'], 50)

    def test_partial_lift_counts_and_wrong_gripper_cannot_claim_it(self):
        samples = trace(3)
        for s in samples:
            s['gripper_holding'] = [True, False]
            s['gripper_lifted'] = [True, False]
            s['garment_lifted_clear'] = False  # Hem is still on the table.
        result = evaluate_episode(samples)
        self.assertEqual(result['breakdown']['pickup'], 5)
        for s in samples:
            s['gripper_lifted'] = [False, True]
        self.assertEqual(evaluate_episode(samples)['raw_points'], 0)

    def test_completion_needs_both_sleeves_and_continuous_confirmation(self):
        samples = trace(2)
        for s in samples:
            s['wrist_in_sleeve'] = dict(left=True, right=True)
            s['dressing_complete'] = s['time_s'] >= 1.6
        self.assertFalse(evaluate_episode(samples)['dressing_complete'])
        for s in samples:
            s['dressing_complete'] = True
            s['wrist_in_sleeve']['right'] = False
        self.assertFalse(evaluate_episode(samples)['dressing_complete'])

    def test_rate_may_decrease_while_raw_score_is_retained(self):
        samples = trace(4)
        for s in samples:
            s['gripper_holding'][0] = True
            s['gripper_lifted'] = [True, False]
        early, late = evaluate_episode(samples[:61]), evaluate_episode(samples)
        self.assertEqual(early['raw_points'], late['raw_points'])
        self.assertGreater(early['final_score'], late['final_score'])

    def test_first_arm_is_temporal_and_other_shoulder_is_anatomical(self):
        samples = trace()
        for s in samples[20:]:
            s['wrist_in_sleeve']['right'] = True
            s['arm_coverage'] = {'left': 0.25, 'right': 0.5}
            s['garment_beyond_shoulder']['right'] = True  # Wrong shoulder.
        result = evaluate_episode(samples)
        self.assertEqual(result['first_arm'], 'right')
        self.assertEqual(result['raw_points'], 15)  # 5 + 0.5*10 + 0.25*20
        self.assertEqual(result['breakdown']['opposite_shoulder'], 0)
        samples[-1]['garment_beyond_shoulder']['left'] = True
        samples[-1]['wrist_in_sleeve']['left'] = True
        self.assertEqual(evaluate_episode(samples)['raw_points'], 25)

    def test_simultaneous_wrists_have_explicit_tie_policy(self):
        samples = trace()
        samples[-1]['wrist_in_sleeve'] = {'left': True, 'right': True}
        self.assertEqual(evaluate_episode(samples)['first_arm'], 'left')
        config = ScoringConfig(simultaneous_first_arm='right')
        self.assertEqual(evaluate_episode(samples, config)['first_arm'], 'right')

    def test_demo_formula_and_aggregation(self):
        data = demo_data()
        report = evaluate_submissions(data)
        self.assertEqual([e['raw_points'] for e in report['submissions'][0]['episodes']], [50, 20])
        self.assertEqual(report['final_score'], 3.5)
        # Best is chosen across whole submissions, not the best run per seed.
        other = deepcopy(data['submissions'][0])
        other['submission_id'] = 'retry'
        other['episodes'][0]['samples'], other['episodes'][1]['samples'] = (
            other['episodes'][1]['samples'], other['episodes'][0]['samples'])
        data['submissions'].append(other)
        self.assertEqual(evaluate_submissions(data)['final_score'], 3.5)

    def test_mean_of_rates_not_pooled_points_over_time(self):
        data = demo_data()
        # Extend only the partial episode to 20 seconds without new progress.
        samples = data['submissions'][0]['episodes'][1]['samples']
        final = deepcopy(samples[-1])
        for tick in range(201, 401):
            samples.append(dict(deepcopy(final), time_s=tick / 20))
        self.assertEqual(evaluate_submissions(data)['final_score'], 3)  # mean(50/10,20/20)

    def test_invalid_measurements_and_times(self):
        mutations = [lambda s: s.pop('arm_coverage'),
                     lambda s: s['arm_coverage'].update(left=50),
                     lambda s: s['arm_coverage'].update(left=-0.1),
                     lambda s: s['arm_coverage'].update(left=float('nan')),
                     lambda s: s.update(time_s=float('inf')),
                     lambda s: s.update(garment_lifted_clear=1),
                     lambda s: s.update(gripper_holding=[True]),
                     lambda s: s['wrist_in_sleeve'].update(left='false')]
        for mutate in mutations:
            samples = trace()
            mutate(samples[-1])
            with self.assertRaises(ValueError):
                evaluate_episode(samples)
        for samples in (trace()[1:], trace()[::2], trace() + [trace()[-1]]):
            with self.assertRaises(ValueError):
                evaluate_episode(samples)

    def test_deadline_and_configuration(self):
        self.assertEqual(evaluate_episode(trace(3), ScoringConfig(time_limit_s=3))['task_time_s'], 3)
        with self.assertRaises(ValueError):
            evaluate_episode(trace(4), ScoringConfig(time_limit_s=3))
        for kwargs in ({'max_sample_gap_s': 0}, {'time_limit_s': -1},
                       {'simultaneous_first_arm': 'robot1'}):
            with self.assertRaises(ValueError):
                ScoringConfig(**kwargs)

    def test_seed_validation(self):
        for variant in ('duplicate', 'missing', 'unequal', 'single'):
            data = demo_data()
            episodes = data['submissions'][0]['episodes']
            if variant == 'duplicate':
                episodes[1]['seed'] = episodes[0]['seed']
            elif variant == 'missing':
                episodes[1].pop('seed')
            elif variant == 'single':
                episodes.pop()
            else:
                other = deepcopy(data['submissions'][0])
                other['submission_id'] = 'other'
                other['episodes'][0]['seed'] = 999
                data['submissions'].append(other)
            with self.assertRaises(ValueError):
                evaluate_submissions(data)

    def test_live_hook_uses_episode_clock_and_resets(self):
        samples = demo_data()['submissions'][0]['episodes'][0]['samples'][:61]
        evaluator = Phase1TaskEvaluator(lambda info: info['measurement'], ScoringConfig(time_limit_s=3))
        for _ in range(2):
            evaluator.reset({'episode_time_s': 0, 'measurement': samples[0]})
            total_reward = 0
            for sample in samples[1:]:
                reward, terminated, report = evaluator(None, None, None,
                    {'episode_time_s': sample['time_s'], 'measurement': dict(sample, time_s=999)})
                total_reward += reward
            self.assertEqual(total_reward, 5)
            self.assertTrue(terminated)
            self.assertAlmostEqual(report['final_score'], 5 / 3)
            self.assertTrue(report['success_evaluated'])
            self.assertFalse(report['success'])

    def test_cli_outputs_json_and_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'scores.json'
            source = Path(tmp) / 'measurements.json'
            command = [sys.executable, str(ROOT / 'scripts/evaluate_phase1.py')]
            run = subprocess.run(command + ['--demo', '--output', str(output),
                                            '--write-demo-input', str(source)],
                                 check=True, capture_output=True, text=True)
            self.assertIn('FINAL SCORE: 3.500000 points/s', run.stdout)
            self.assertTrue(json.loads(output.read_text())['synthetic_demo'])
            subprocess.run(command + ['--input', str(source), '--output', str(output)],
                           check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text())['final_score'], 3.5)
            source.write_text('{"schema_version":"wrong"}')
            run = subprocess.run(command + ['--input', str(source)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn('FINAL SCORE:', run.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
