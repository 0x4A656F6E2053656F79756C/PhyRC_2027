"""Real headless teleop loop: auto start, reset boundary, ESC save; no F6/F7."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

root = Path('/output/competition_checks') / uuid.uuid4().hex[:10]
os.environ.update(STRETCH4_AUTO_EVALUATE='1', STRETCH4_STATE_DIR=str(root/'slots'),
                  STRETCH4_EVALUATION_DIR=str(root/'scores'))
sys.path.insert(0, '/workspace/DexGarmentLab')
from policy_cli import install_failure_handler
install_failure_handler()
import Env_StandAlone.Teleop_TShirt_Stretch4_Env as M

original_input = M.carb.input.acquire_input_interface
original_drive = M.drive_robot
original_close = M.simulation_app.close
callback = None
fired = set()

class Input:
    def __getattr__(self, name):
        return getattr(original_input(), name)
    def subscribe_to_keyboard_events(self, keyboard, handler):
        global callback
        if handler.__name__ == 'on_keyboard_event':
            callback = handler
            return object()
        return original_input().subscribe_to_keyboard_events(keyboard, handler)
    def unsubscribe_to_keyboard_events(self, *args):
        pass

def drive(*args, **kwargs):
    frame = args[5]
    key = 'P' if frame == 12 else 'ESCAPE' if frame == 36 else None
    if key and key not in fired:
        fired.add(key)
        for kind in (M.carb.input.KeyboardEventType.KEY_PRESS, M.carb.input.KeyboardEventType.KEY_RELEASE):
            callback(SimpleNamespace(type=kind, input=SimpleNamespace(name=key), modifiers=0))
    return original_drive(*args, **kwargs)

def close(*args, **kwargs):
    records = [json.loads(p.read_text()) for p in sorted((root/'scores').glob('*/result.json'))]
    assert len(records) == 2, records
    assert records[0]['reason'] == 'scene_reset' and not records[0]['valid']
    assert records[1]['valid'] and records[1]['reason'] == 'gui_closed'
    assert all(r['metadata']['mode'] == 'teleop_auto' for r in records)
    for p in (root/'scores').glob('*/samples.jsonl'):
        samples = [json.loads(s) for s in p.read_text().splitlines()]
        assert samples[0]['physics_tick'] == 0 and samples[0]['time_s'] == 0
        assert len(samples) > 1
    result = dict(passed=True, auto_start=True, reset_invalidates_and_restarts=True,
                  esc_saves_valid_result=True, no_evaluation_hotkeys=True, output=str(root))
    (root/'report.json').write_text(json.dumps(result,indent=2))
    print('AUTO-EVALUATION-PASS ' + json.dumps(result), flush=True)
    return original_close(*args, **kwargs)

M.carb.input.acquire_input_interface = lambda: Input()
M.drive_robot = drive
M.simulation_app.close = close
M.main()
