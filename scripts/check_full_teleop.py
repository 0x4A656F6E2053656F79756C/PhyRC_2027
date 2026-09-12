"""GPU full-record integration with real teleop input and isolated slots."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

sys.path.insert(0, '/project/src/DexGarmentLab')
root = Path('/output/full_record_checks') / uuid.uuid4().hex[:10]
os.environ['STRETCH4_STATE_DIR'] = str(root / 'slots')
os.environ['STRETCH4_FULL_RECORD'] = '1'
os.environ['STRETCH4_FULL_RECORD_DIR'] = str(root / 'recordings')
from policy_cli import install_failure_handler
install_failure_handler()
import Policy.teleop_recording as recording
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M
import numpy as np
import Policy.evaluation_live as evaluation_live
from Policy.evaluation_replay import ReplayEvaluation

instances = []
evaluation_trials = []
OriginalSession = evaluation_live.EvaluationSession


class Session(OriginalSession):
    def start(self, *args, **kwargs):
        self.record_start_tick = instances[0].tick
        self.output = root / 'live_evaluation'
        return super().start(*args, **kwargs)

    def finish(self, *args, **kwargs):
        was_active = self.active
        result = super().finish(*args, **kwargs)
        if was_active and result['valid']:
            evaluation_trials.append((self.record_start_tick, instances[0].tick, result, list(self.trace)))
        return result


evaluation_live.EvaluationSession = Session
OriginalRecorder = recording.FullTeleopRecorder


class Recorder(OriginalRecorder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instances.append(self)


recording.FullTeleopRecorder = Recorder
callback, updates = None, 0


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


original_window = M.omni.appwindow.get_default_app_window
original_input = M.carb.input.acquire_input_interface
original_update = M.simulation_app.update
original_close = M.simulation_app.close
M.carb.input.acquire_input_interface = lambda: Input()


def key(name, pressed=True):
    kind = M.carb.input.KeyboardEventType.KEY_PRESS if pressed else M.carb.input.KeyboardEventType.KEY_RELEASE
    callback(SimpleNamespace(type=kind, input=SimpleNamespace(name=name), modifiers=0))


def update(*args, **kwargs):
    global updates
    result = original_update(*args, **kwargs)
    if callback is None or not instances or instances[0].suspended:
        return result
    updates += 1
    schedule = {1: [('F6', True), ('W', True), ('NUMPAD_8', True), ('SPACE', True)],
                9: [('W', False), ('NUMPAD_8', False)],
                10: [('D', True), ('NUMPAD_6', True)],
                14: [('F7', True), ('D', False), ('NUMPAD_6', False)],
                16: [('F2', True)], 20: [('P', True)],
                24: [('F2', True)], 28: [('ESCAPE', True)]}
    for name, pressed in schedule.get(updates, []):
        if name == 'ESCAPE' and '--signal-stop' in sys.argv:
            import signal
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            key(name, pressed)
            if name == 'W' and pressed:
                # Real GUI input also emits CHAR events whose input is text.
                callback(SimpleNamespace(type=M.carb.input.KeyboardEventType.CHAR,
                                         input='w', modifiers=0))
    if updates > 60:
        raise RuntimeError('Recording integration did not finish')
    return result


def close(*args, **kwargs):
    M.omni.appwindow.get_default_app_window = original_window
    M.carb.input.acquire_input_interface = original_input
    M.simulation_app.update = original_update
    M.simulation_app.close = original_close
    recorder = instances[0]
    reader = recording.ArchiveReader(recorder.archive.path, allow_incomplete=True)
    frames = list(reader.frames())
    events = [json.loads(line) for line in (reader.path / 'events.jsonl').read_text().splitlines()]
    kinds = [header['kind'] for header, _ in frames]
    physics = [h['tick'] for h, _ in frames if h['kind'] == 'physics']
    joints = [np.stack([v[f'r{i}_joint_positions'] for _, v in frames]) for i in range(2)]
    movement = [float(np.ptp(j, axis=0).max()) for j in joints]
    press = next(e for e in events if e.get('key') == 'W' and e.get('event_type') == 'KEY_PRESS')
    control = next(e for e in events if e['sequence'] > press['sequence'] and e['kind'] == 'control')
    before = [v for h, v in frames if h['tick'] == press['tick']][-1]
    after = next(v for h, v in frames if h['tick'] == press['tick'] + 1)
    exact_input_tick = bool(control['tick'] == press['tick'] and 'W' in control['held_keys']
                            and before['r0_controls'][0] == 0 and after['r0_controls'][0] > 0)
    scores_identical = len(evaluation_trials) == 1
    for start, end, live_report, trace in evaluation_trials:
        evaluator = ReplayEvaluation(reader.manifest['metadata'], root / 'replay_evaluation', start, end)
        for header, values in frames:
            evaluator.consume(header, values)
        replay_report = evaluator.finish()
        scores_identical &= replay_report['result'] == live_report['result'] and evaluator.session.trace == trace
    passed = (reader.manifest['complete'] and physics == list(range(1, recorder.tick + 1))
              and {'before_reset', 'after_reset', 'before_load_F2', 'after_load_F2'}.issubset(kinds)
              and all(m > .01 for m in movement) and exact_input_tick and scores_identical
              and any(e.get('key') == 'w' and e.get('event_type') == 'CHAR' for e in events)
              and any(e.get('key') == 'W' and e.get('event_type') == 'KEY_RELEASE' for e in events))
    report = {'passed': passed, 'recording': str(reader.path), 'frames': len(frames),
              'shutdown': 'SIGTERM' if '--signal-stop' in sys.argv else 'ESCAPE',
              'physics_ticks': recorder.tick, 'joint_motion_max': movement,
              'exact_input_application_tick': exact_input_tick,
              'live_replay_scores_and_samples_identical': scores_identical,
              'evaluation_tick_ranges': [[s, e] for s, e, _, _ in evaluation_trials],
              'boundary_kinds': sorted(set(kinds)), 'events': len(events)}
    (root / 'report.json').write_text(json.dumps(report, indent=2))
    Path('/output/full_record_checks/latest.json').write_text(json.dumps(report, indent=2))
    print('FULL-TELEOP-' + ('PASS ' if passed else 'FAIL ') + json.dumps(report), flush=True)
    original_close(exit_code=0 if passed else 1)


M.simulation_app.update = update
M.simulation_app.close = close
M.main()
