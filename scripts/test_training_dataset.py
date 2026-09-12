"""CPU checks for action labels, timing rejection, public data, and HDF5 lifecycle."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import h5py
import numpy as np

ROOT = Path('/project') if Path('/project/config').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.contract import observation_shapes, decode_action
from Policy.training_dataset import DatasetWriter, keyboard_action, training_observation
from Policy.dataset_reader import PolicyDataset


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.contract = json.loads((ROOT / 'config/policy_interface.json').read_text())
        self.contract['default_dimensions'].update(width=16, height=16)
        self.obs = {k: np.zeros(shape, dtype=self.contract['observations'][k]['dtype'])
                    for k, shape in observation_shapes(self.contract, robots=2, joints=13, profile='actor_rgbd').items()}
        self.action = np.zeros((2, 9), np.float32)
        self.action[1, 3] = .25
        self.next = {k: v.copy() for k, v in self.obs.items()}
        self.next['simulation_time_s'][...] = .05
        self.next['previous_action'] = self.action.copy()
        self.writer = DatasetWriter(Path(self.tmp.name) / 'dataset', self.contract, {'private_seed': 123})
        self.writer.start_episode({'seed': 123})

    def tearDown(self):
        self.writer.close(complete=False)
        self.tmp.cleanup()

    def append(self, **kwargs):
        self.writer.append(self.obs, self.action, self.next, **dict(start_tick=0, end_tick=12,
                           audit={'viewport_rgb': np.zeros((16, 16, 3), np.uint8)}, **kwargs))

    def test_roundtrip_and_public_reader(self):
        self.append()
        self.writer.finish_episode('gui_closed', {'valid': True, 'result': {'dressing_complete': True}})
        self.writer.close()
        reader = PolicyDataset(self.writer.path / 'policy.hdf5')
        obs, action = reader[0]
        np.testing.assert_array_equal(action.reshape(2, 9), self.action)
        np.testing.assert_array_equal(obs['robot_0_head_depth'], self.obs['depth'][3])
        self.assertNotIn('viewport_rgb', obs)
        reader.close()
        with h5py.File(self.writer.path / 'audit.hdf5') as f:
            self.assertTrue(f['demo_0'].attrs['success'])

    def test_gap_rejected(self):
        self.append()
        with self.assertRaisesRegex(ValueError, 'physics ticks'):
            self.writer.append(self.obs, self.action, self.next, start_tick=24, end_tick=36, audit={})
        self.assertEqual(self.writer.data.attrs['total'], 1)

    def test_stale_camera_clock_rejected(self):
        self.next['simulation_time_s'][...] = .049
        with self.assertRaisesRegex(ValueError, 'clock'):
            self.append()

    def test_wrong_action_history_rejected(self):
        self.next['previous_action'].fill(0)
        with self.assertRaisesRegex(ValueError, 'previous_action'):
            self.append()

    def test_privileged_observation_rejected(self):
        self.obs['cloth_vertices'] = np.zeros((3, 3), np.float32)
        with self.assertRaisesRegex(ValueError, 'Observation keys'):
            self.append()
        self.assertEqual(self.writer.data.attrs['total'], 0)

    def test_incomplete_rejected(self):
        self.append()
        self.writer.close(complete=False)
        with self.assertRaisesRegex(ValueError, 'complete'):
            PolicyDataset(self.writer.path / 'policy.hdf5')

    def test_writer_failure_not_counted_complete(self):
        def fail(*args):
            raise OSError('disk full')
        self.writer._append = fail
        with self.assertRaisesRegex(OSError, 'disk full'):
            self.append()
        self.assertEqual(self.writer.data.attrs['total'], 0)
        self.writer.close(complete=False)
        with h5py.File(self.writer.path / 'policy.hdf5') as f:
            self.assertFalse(f.attrs['complete'])

    def test_keyboard_signs_conflicts_and_toggle_parity(self):
        names = ('base_fwd', 'base_strafe', 'base_turn', 'lift', 'arm', 'yaw', 'pitch', 'roll')
        keymap = {f'{n}_{s}': f'{n}_{s}' for n in names for s in ('pos', 'neg')}
        held = {'base_strafe_neg', 'lift_pos', 'lift_neg', 'yaw_pos'}
        action = keyboard_action(held, (keymap, keymap), [False, True], [1, 2])
        self.assertEqual(action[0, 1], 1)
        self.assertEqual(action[0, 3], 0)
        self.assertEqual(action[0, 5], 1)
        self.assertEqual(action[0, 8], 1)
        self.assertEqual(action[1, 8], 0)
        runtime = {f['runtime_scale']: 1 for f in self.contract['action']['fields'][:-1]}
        decoded = decode_action(action, self.contract, runtime)
        self.assertEqual(decoded[0]['velocity_commands']['base_strafe'], -1)


if __name__ == '__main__':
    unittest.main()
