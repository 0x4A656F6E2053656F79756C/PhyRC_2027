"""Headless integration test of actual teleop F6/F7/reset/load/quit handlers.

Uses isolated slots and synthetic key events; does not open a GUI window.
Run with STRETCH4_STATE_DIR pointing to a dedicated test directory.
"""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, '/project/src/DexGarmentLab')
from policy_cli import install_failure_handler
install_failure_handler()

root = Path('/output/evaluation/teleop_integration')
os.environ['STRETCH4_STATE_DIR'] = str(root / 'states')
os.environ['STRETCH4_EVALUATION_DIR'] = str(root / 'runs')
import Policy.evaluation_live as live
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M

sessions = []
OriginalSession = live.EvaluationSession


class Session(OriginalSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sessions.append(self)


live.EvaluationSession = Session
callback = None
reports = []
phase = 0
updates = 0


class Input:
    def subscribe_to_keyboard_events(self, keyboard, handler):
        global callback
        callback = handler
        return object()

    def unsubscribe_to_keyboard_events(self, *args):
        pass


original_window = M.omni.appwindow.get_default_app_window
original_input = M.carb.input.acquire_input_interface
M.omni.appwindow.get_default_app_window = lambda: SimpleNamespace(get_keyboard=lambda: None)
M.carb.input.acquire_input_interface = lambda: Input()
original_update = M.simulation_app.update
original_close = M.simulation_app.close


def press(name):
    print('[Teleop integration] key', name, flush=True)
    callback(SimpleNamespace(type=M.carb.input.KeyboardEventType.KEY_PRESS,
                             input=SimpleNamespace(name=name), modifiers=0))


def update(*args, **kwargs):
    global phase, updates
    result = original_update(*args, **kwargs)
    if callback is None or not sessions:
        return result
    updates += 1
    if updates > 800:
        raise RuntimeError('Teleop evaluation test timed out')
    session = sessions[0]
    if phase in (0, 3, 6, 9):
        press('F6')
        phase += 1
    elif phase in (1, 4, 7, 10) and session.active and session.scorer.sample_count >= 5:
        press({1: 'F7', 4: 'P', 7: 'F1', 10: 'ESCAPE'}[phase])
        phase += 1
    elif phase in (2, 5, 8) and not session.active:
        reports.append(session.last_report)
        phase += 1
    return result


def close(*args, **kwargs):
    if sessions:
        reports.append(sessions[0].last_report)
    reasons = [r['reason'] for r in reports]
    valid = [r['valid'] for r in reports]
    passed = reasons == ['user_stop', 'scene_reset', 'checkpoint_load', 'gui_closed'] and valid == [True, False, False, True]
    root.mkdir(parents=True, exist_ok=True)
    (root / 'report.json').write_text(json.dumps({'passed': passed, 'reasons': reasons, 'valid': valid}, indent=2))
    print('TELEOP-EVALUATION-' + ('PASS' if passed else 'FAIL'), flush=True)
    # Kit's shutdown hooks still need the real window/input API.
    M.omni.appwindow.get_default_app_window = original_window
    M.carb.input.acquire_input_interface = original_input
    M.simulation_app.update = original_update
    M.simulation_app.close = original_close
    original_close(exit_code=0 if passed else 1)


M.simulation_app.update = update
M.simulation_app.close = close
M.main()
