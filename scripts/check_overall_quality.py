"""Regression tests for upper-arm-only coverage, neck and V-neck orientation."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path('/project') if Path('/project/config').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/DexGarmentLab'))
from Policy.evaluation import evaluate_episode, evaluate_submissions, format_score_items
from Policy.evaluation_geometry import front_alignment, GarmentGeometry
from check_phase1_evaluation import trace
from check_phase1_live import tube


def quality_trace():
    samples=trace(4)
    for s in samples:
        s.update(first_contact_time_s=0.,gripper_lifted=[True,False],gripper_holding=[True,False],
                 upper_arm_coverage=dict(left=.35,right=.35),neck_out=True,front_facing=True,dressing_complete=True)
        s['wrist_in_sleeve']=dict(left=True,right=True)
        s['garment_beyond_shoulder']['right']=True
    return samples


class QualityTests(unittest.TestCase):
    def test_correct_short_sleeve_dressing_can_score_50_with_no_forearm_coverage(self):
        result=evaluate_episode(quality_trace())
        self.assertEqual(result['scoring_revision'],'upper-arm-neck-front-v6')
        self.assertEqual(result['raw_points'],50)
        self.assertTrue(result['success'])
        self.assertFalse(result['coverage_score_overridden'])
        self.assertEqual(result['score_items']['overall_dressing']['components'],
                         dict(left_upper_arm=5,right_upper_arm=5,neck=10,front_orientation=10))
        self.assertEqual(sum(result['breakdown'].values()),result['raw_points'])
        self.assertIn('V-neck front 10.00/10',format_score_items(result))

    def test_partial_upper_coverage_linear_and_lower_arm_ignored(self):
        samples=quality_trace()
        for s in samples:
            s['upper_arm_coverage']=dict(left=.175,right=0)
            s['neck_out']=s['front_facing']=s['dressing_complete']=False
        a=evaluate_episode(samples)
        for s in samples:s['arm_coverage']=dict(left=1.,right=1.)
        b=evaluate_episode(samples)
        self.assertEqual(a['overall_dressing_points'],2.5)
        self.assertEqual(a['overall_dressing_points'],b['overall_dressing_points'])

    def test_backwards_and_neck_not_out_cannot_earn_orientation(self):
        samples=quality_trace()
        for s in samples:s['front_facing']=False
        r=evaluate_episode(samples)
        self.assertEqual(r['overall_dressing_points'],20)
        self.assertFalse(r['success'])
        for s in samples:s['front_facing']=True;s['neck_out']=False
        r=evaluate_episode(samples)
        self.assertEqual(r['overall_dressing_points'],10)
        self.assertFalse(r['success'])

    def test_confirmation_resets_and_awarded_progress_does_not_fall(self):
        samples=quality_trace()
        for s in samples:
            s['neck_out']=s['time_s']>=1
            s['front_facing']=s['time_s']>=2
        r=evaluate_episode(samples[:50])
        self.assertEqual(r['score_items']['overall_dressing']['components']['front_orientation'],0)
        r=evaluate_episode(samples[:51])
        self.assertEqual(r['score_items']['overall_dressing']['front_confirmed_at_s'],2.5)
        for s in samples[51:]:s['neck_out']=s['front_facing']=False;s['upper_arm_coverage']=dict(left=0,right=0)
        self.assertEqual(evaluate_episode(samples)['overall_dressing_points'],30)
        samples=quality_trace()
        samples[5]['neck_out']=False
        self.assertEqual(evaluate_episode(samples[:15])['score_items']['overall_dressing']['components']['neck'],0)

    def test_v4_schema_and_legacy_measurements_cannot_mix(self):
        samples=quality_trace()
        data=dict(schema_version='phase1-measurements-v4',submissions=[dict(submission_id='test',
                  episodes=[dict(seed=s,samples=deepcopy(samples)) for s in (42,43)])])
        self.assertEqual(evaluate_submissions(data)['final_score'],12.5)
        data['submissions'][0]['episodes'][1]['samples'][-1].pop('front_facing')
        with self.assertRaises(ValueError):evaluate_submissions(data)
        samples[1].pop('neck_out');samples[1].pop('front_facing');samples[1].pop('upper_arm_coverage')
        with self.assertRaisesRegex(ValueError,'mix legacy'):evaluate_episode(samples)

    def test_new_no_contact_attempts_are_zero_ranked(self):
        samples=quality_trace()
        for s in samples:s['first_contact_time_s']=None;s['neck_out']=s['front_facing']=False
        data=dict(schema_version='phase1-measurements-v4',submissions=[dict(submission_id='test',
                  episodes=[dict(seed=i,samples=samples) for i in (42,43)])])
        r=evaluate_submissions(data)
        self.assertEqual(r['final_score'],0)
        self.assertEqual(r['submissions'][0]['success_rate'],0)

    def test_front_alignment_respects_anatomical_yaw_and_rejects_reverse_and_collapse(self):
        points=np.array([[-.1,0,1],[.1,0,1],[0,.1,1],[0,-.15,.9]])
        arms=dict(left=np.array([[.2,0,.7]]),right=np.array([[-.2,0,.7]]))
        neck=np.array([[0,0,.7],[0,0,1],[0,0,1.3]])
        self.assertTrue(front_alignment(points,[0,1,2],[3],arms,neck)['front_facing'])
        rot=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        moved=front_alignment(points@rot+3,[0,1,2],[3],{k:v@rot+3 for k,v in arms.items()},neck@rot+3)
        self.assertTrue(moved['front_facing'])
        points[3,1]=.2
        self.assertFalse(front_alignment(points,[0,1,2],[3],arms,neck)['front_facing'])
        points[3]=points[:3].mean(0)
        self.assertFalse(front_alignment(points,[0,1,2],[3],arms,neck)['front_facing'])

    def test_upper_measurement_is_independent_of_forearm_length(self):
        points,faces,loops=tube()
        g=GarmentGeometry.__new__(GarmentGeometry)
        g.faces,g.loops=faces,loops
        g.cuffs,g.inner=[np.arange(32,64)],[np.arange(32)]
        g.coverage_samples=40
        chain=np.array([[.2,0,0],[1.5,0,0],[2.5,0,0],[2.7,0,0]])
        a=g.measure(points,dict(left=chain))[2]['left']['upper_arm_coverage']
        chain[2:]+=np.array([2.,0,0])
        b=g.measure(points,dict(left=chain))[2]['left']['upper_arm_coverage']
        self.assertEqual(a,b)
        self.assertGreater(a,0)


if __name__=='__main__':unittest.main(verbosity=2)
