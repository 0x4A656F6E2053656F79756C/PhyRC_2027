"""Verify fair contact-based timing independently of the contact detector."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/DexGarmentLab'))
from Policy.evaluation_clock import ContactClock


class ClockTests(unittest.TestCase):
    def test_precontact_delay_does_not_change_score(self):
        scores = []
        for start in (17, 1257):
            clock = ContactClock(1 / 240)
            for tick in range(start + 481):
                clock.update(tick, tick == start)
            result = clock.result(50)
            self.assertEqual(result['task_time_s'], 2)
            self.assertEqual(result['first_contact_tick'], start)
            self.assertEqual(result['score_status'], 'scored')
            scores.append(result['final_score'])
        self.assertEqual(scores, [25, 25])

    def test_contact_before_20hz_sample_is_timed_at_physics_tick(self):
        clock = ContactClock(1 / 240)
        for tick in range(25):
            clock.update(tick, tick == 13)
        self.assertEqual(clock.first_contact_tick, 13)
        self.assertEqual(clock.result(5)['task_time_s'], 11 / 240)

    def test_no_contact_and_zero_denominator_do_not_invent_a_rate(self):
        clock = ContactClock(1 / 240)
        clock.update(0, False)
        self.assertIsNone(clock.result(5)['final_score'])
        self.assertEqual(clock.result(5)['score_status'], 'no_contact')
        clock.update(1, True)
        self.assertIsNone(clock.result(5)['final_score'])
        self.assertEqual(clock.result(5)['score_status'], 'awaiting_elapsed_time')
        clock.update(2, False)
        self.assertEqual(clock.first_contact_tick, 1)
        self.assertEqual(clock.result(5)['final_score'], 1200)

    def test_gaps_duplicates_unknown_evidence_and_invalid_dt_rejected(self):
        for dt in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                ContactClock(dt)
        clock = ContactClock(1 / 240)
        for tick, contact in ((1, False), (0, None), (0, 0), (-1, False)):
            with self.assertRaises(ValueError):
                clock.update(tick, contact)
        clock.update(0, True)
        for tick in (0, 2):
            with self.assertRaises(ValueError):
                clock.update(tick, False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
