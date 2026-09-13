"""CPU cadence tests for the rendering-free collector, including error boundaries."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import numpy as np
ROOT=Path('/project') if Path('/project/config').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/DexGarmentLab'))
from Policy.training_deferred import DeferredTrainingTeleop
from Policy.contract import load_contract


class DeferredTests(unittest.TestCase):
    def setUp(self):
        self.c=DeferredTrainingTeleop.__new__(DeferredTrainingTeleop)
        c=self.c
        c.contract=load_contract(ROOT/'config/policy_interface.json')
        c.runtime={f['runtime_scale']:1 for f in c.contract['action']['fields'][:-1]}
        names=('base_fwd','base_strafe','base_turn','lift','arm','yaw','pitch','roll')
        keymap={n+'_'+s:n+'_'+s for n in names for s in ('pos','neg')}
        c.M=SimpleNamespace(ROBOT1_KEYMAP=keymap,ROBOT2_KEYMAP=keymap)
        c.rigs=[{'state':{'gripper_closed':False}},{'state':{'gripper_closed':False}}]
        c.toggles=[lambda: c.rigs[0]['state'].update(gripper_closed=not c.rigs[0]['state']['gripper_closed']),lambda:None]
        c.recorder=SimpleNamespace(tick=0,event=lambda *args,**kwargs:None)
        c.phase,c.frame,c.samples,c.inflight=0,0,0,False
        c.active,c.episode=True,0
        c.pending_toggles=[0,0]
        c.previous=np.zeros((2,9),np.float32)
        c.path=Path('/unused')
        c.captured=[]
        c._capture=lambda targets=None:c.captured.append((c.recorder.tick,c.previous.copy(),targets))

    def test_held_action_applies_through_three_control_ticks(self):
        c=self.c
        for i,held in enumerate([{'lift_pos'},set(),{'arm_pos'}]):
            commands=c.before_control(held)
            self.assertEqual(commands[0]['velocity_commands']['lift_rate'],1)
            self.assertEqual(commands[0]['velocity_commands']['arm_rate'],0)
            c.targets.append(np.zeros((2,9),np.float32))
            c.recorder.tick+=4
            c.after_control()
        self.assertEqual(len(c.captured),1)
        self.assertEqual(c.captured[0][0],12)
        self.assertFalse(c.inflight)
        commands=c.before_control({'arm_pos'})
        self.assertEqual(commands[0]['velocity_commands']['lift_rate'],0)
        self.assertEqual(commands[0]['velocity_commands']['arm_rate'],1)

    def test_clock_gap_fails_before_capture(self):
        c=self.c
        c.before_control(set())
        c.recorder.tick=5
        with self.assertRaisesRegex(RuntimeError,'expected 4'):
            c.after_control()
        self.assertEqual(len(c.captured),0)

    def test_gripper_toggle_waits_for_next_policy_boundary(self):
        c=self.c
        c.before_control(set())
        c.targets.append(np.zeros((2,9),np.float32))
        c.recorder.tick=4
        c.after_control()
        c.toggle(0)
        for tick in (8,12):
            c.before_control(set())
            self.assertFalse(c.rigs[0]['state']['gripper_closed'])
            c.targets.append(np.zeros((2,9),np.float32))
            c.recorder.tick=tick
            c.after_control()
        c.before_control(set())
        self.assertTrue(c.rigs[0]['state']['gripper_closed'])
        self.assertEqual(c.action[0,8],1)

    def test_partial_boundary_is_invalid(self):
        events=[]
        self.c.recorder.event=lambda *args,**kwargs:events.append((args,kwargs))
        self.c.before_control(set())
        self.c.boundary('window_closed')
        self.assertFalse(events[-1][1]['valid'])
        self.assertFalse(self.c.active)


if __name__=='__main__':
    unittest.main()
