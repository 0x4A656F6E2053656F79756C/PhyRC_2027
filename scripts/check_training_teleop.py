"""Real Isaac collection test, synthetic keyboard events, isolated user slots."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

sys.path.insert(0, '/workspace/DexGarmentLab' if '--runtime' in sys.argv else '/project/src/DexGarmentLab')
root = Path('/output/training_checks') / uuid.uuid4().hex[:10]
os.environ.update(STRETCH4_STATE_DIR=str(root / 'slots'), STRETCH4_TRAINING_RECORD='1',
                  STRETCH4_FULL_RECORD_DIR=str(root / 'raw'), STRETCH4_TRAINING_RECORD_DIR=str(root / 'datasets'))
if '--gui' in sys.argv:
    os.environ['STRETCH4_HEADLESS'] = '0'
from policy_cli import install_failure_handler
install_failure_handler()
import Policy.training_teleop as training
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M
import h5py
import numpy as np
from Policy.teleop_recording import ArchiveReader

callback = None
instance = None
original_input = M.carb.input.acquire_input_interface
original_close = M.simulation_app.close


class Input:
    def __getattr__(self, name):
        return getattr(original_input(), name)

    def subscribe_to_keyboard_events(self, keyboard, handler):
        global callback
        if getattr(handler, '__name__', '') == 'on_keyboard_event':
            callback = handler
            return object()
        return original_input().subscribe_to_keyboard_events(keyboard, handler)

    def unsubscribe_to_keyboard_events(self, *args):
        pass


def key(name, pressed=True):
    kind = M.carb.input.KeyboardEventType.KEY_PRESS if pressed else M.carb.input.KeyboardEventType.KEY_RELEASE
    callback(SimpleNamespace(type=kind, input=SimpleNamespace(name=name), modifiers=0))


OriginalTraining = training.TrainingTeleop


class Training(OriginalTraining):
    def __init__(self, *args, **kwargs):
        global instance
        super().__init__(*args, **kwargs)
        instance = self
        self.controls = 0

    def before_control(self, held):
        self.controls += 1
        schedule = {1: [('W', True), ('NUMPAD_8', True), ('SPACE', True)],
                    2: [('W', False), ('NUMPAD_8', False), ('D', True)],
                    5: [('D', False), ('F2', True)], 8: [('P', True)],
                    12: [('F2', True)], 16: [('J', True), ('LEFT', True)],
                    20: [('ESCAPE', True)]}
        for name, pressed in schedule.get(self.controls, []):
            if name == 'ESCAPE' and '--signal-stop' in sys.argv:
                import signal
                os.kill(os.getpid(), signal.SIGTERM)
            else:
                key(name, pressed)
        if self.controls > 30:
            raise RuntimeError('Test did not terminate')
        return super().before_control(held)


def close(*args, **kwargs):
    M.simulation_app.close = original_close
    if kwargs.get('exit_code', 0):
        return original_close(*args, **kwargs)
    reader = ArchiveReader(instance.recorder.archive.path)
    frames = list(reader.frames())
    raw = {h['tick']: v for h, v in frames if h['kind'] == 'physics'}
    ticks = [h['tick'] for h, _ in frames if h['kind'] == 'physics']
    assert ticks == list(range(1, instance.recorder.tick + 1))
    comparisons = 0
    with h5py.File(instance.writer.path / 'policy.hdf5') as f, h5py.File(instance.writer.path / 'audit.hdf5') as audit:
        assert f.attrs['complete'] and audit.attrs['complete']
        assert len(f['data']) >= 3  # reset and LOAD split episodes
        for name, demo in f['data'].items():
            n = demo.attrs['num_samples']
            assert n and demo.attrs['complete']
            a = audit[name]
            assert np.all(a['end_tick'][:] - a['start_tick'][:] == 12)
            for j, tick in enumerate(a['end_tick'][:]):
                expected = np.stack([raw[int(tick)][f'r{i}_joint_positions'] for i in range(2)]).astype(np.float32).reshape(-1)
                np.testing.assert_array_equal(demo['next_obs/joint_position'][j], expected)
                np.testing.assert_array_equal(demo['next_obs/previous_action'][j], demo['actions'][j])
                comparisons += 1
                for k, control_tick in enumerate(a['control_start_ticks'][j]):
                    controls = np.stack([raw[int(control_tick) + 1][f'r{i}_controls'][:9] for i in range(2)]).astype(np.float32)
                    np.testing.assert_array_equal(a['controller_targets_applied'][j, k], controls)
            for key_name in demo['obs']:
                if n > 1:
                    np.testing.assert_array_equal(demo['next_obs'][key_name][:-1], demo['obs'][key_name][1:])
            for camera in instance.contract['cameras']:
                assert np.ptp(demo['obs'][camera['id'] + '_rgb'][0]) > 0
                assert demo['obs'][camera['id'] + '_depth_valid'][0].any()
            np.testing.assert_array_equal(a['camera_timestamp_s'][:], np.repeat(demo['obs/simulation_time_s'][:], 5, axis=1))
            np.testing.assert_array_equal(a['viewport_timestamp_s'][:], demo['obs/simulation_time_s'][:, 0])
            assert demo['dones'][-1] == demo['truncated'][-1] == 1
        first = f['data/demo_0/actions'][:].reshape(-1, 2, 9)
        assert first[0, 0, 3] == first[0, 1, 3] == 1
        assert first[0, 0, 4] == 0 and first[1, 0, 4] == 1
        assert first[0, 0, 8] == 1
        report = dict(passed=True, gui='--gui' in sys.argv, signal_stop='--signal-stop' in sys.argv,
                      dataset=str(instance.writer.path), raw_archive=str(reader.path),
                      episodes=len(f['data']), transitions=comparisons, physics_ticks=len(ticks),
                      checks=['20Hz contiguous intervals', '60Hz input changes held until next boundary',
                              'RGBD and viewport timestamps', '5 nonempty cameras', 'proprioception vs raw PhysX',
                              'obs/next_obs continuity', 'reset/LOAD splits', 'lossless raw physics ticks', 'gripper intent'])
    root.mkdir(parents=True, exist_ok=True)
    (root / 'report.json').write_text(json.dumps(report, indent=2))
    print('TRAINING-TELEOP-PASS ' + json.dumps(report), flush=True)
    original_close()


training.TrainingTeleop = Training
M.carb.input.acquire_input_interface = lambda: Input()
M.simulation_app.close = close
M.main()
