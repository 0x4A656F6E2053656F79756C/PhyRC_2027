"""Exercise the production teleop callback with real Carb events, without a GUI/GPU.

Run via Isaac's python.sh. A logical keyboard belongs only to this test process.
No scene, physics, user keyboard subscription or saved slot is touched.
"""
import argparse
import ast
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path('/project') if Path('/project/src/DexGarmentLab').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.teleop_recording import StateArchive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'src/DexGarmentLab/Env_StandAlone/Teleop_TShirt_Stretch4_Env.py')
    parser.add_argument('--expect-character-error', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    import carb
    import carb.input
    carb.get_framework().load_plugins(loaded_file_wildcards=['carb.input.plugin'],
                                     search_paths=['/isaac-sim/kit/kernel/plugins'])
    interface = carb.input.acquire_input_interface()
    provider = carb.input.acquire_input_provider()
    keyboard = provider.create_keyboard('phyrc-recording-regression-isolated')
    tree = ast.parse(args.source.read_text())
    callback_node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'on_keyboard_event')
    errors, events, snapshots, grips = [], [], [], []
    tick = [12]
    with tempfile.TemporaryDirectory() as temporary:
        archive = StateArchive(Path(temporary)/'recording', {})
        def record(kind, **fields):
            archive.event(tick[0], kind, **fields)
        scope = dict(carb=carb, full_recorder=SimpleNamespace(event=record), held=set(),
                     quit_flag={'quit': False}, pending_evaluation={'command': None},
                     RESET_KEY='P', RECORD_START_KEY='F9', RECORD_STOP_KEY='F10',
                     STATE_SLOT_KEYS=('F1','F2','F3','F4','F5'), STATE_CLEAR_KEY='F8',
                     ROBOT1_GRIP_KEYS=('SPACE','KEY_0'), ROBOT2_GRIP_KEYS=('NUMPAD_0','NUMPAD_ENTER'),
                     toggle_gripper1=lambda:grips.append(0), toggle_gripper2=lambda:grips.append(1))
        exec(compile(ast.Module(body=[callback_node], type_ignores=[]), str(args.source), 'exec'), scope)
        callback = scope['on_keyboard_event']
        def dispatch(event):
            events.append({'type':event.type.name, 'input_type':type(event.input).__name__})
            try:
                result = callback(event)
                assert result is True
            except Exception as exc:
                errors.append(f'{type(exc).__name__}: {exc}')
            snapshots.append(sorted(scope['held']))
            return True
        subscription = interface.subscribe_to_keyboard_events(keyboard, dispatch)
        try:
            key = lambda kind, name: provider.buffer_keyboard_key_event(keyboard, kind, name, 0)
            types, inputs = carb.input.KeyboardEventType, carb.input.KeyboardInput
            key(types.KEY_PRESS, inputs.W)
            provider.buffer_keyboard_char_event(keyboard, 'w', 0)
            provider.buffer_keyboard_char_event(keyboard, '한', 0)
            key(types.KEY_REPEAT, inputs.W)
            interface.distribute_buffered_events()
            assert scope['held'] == {'W'}
            tick[0] = 16
            key(types.KEY_RELEASE, inputs.W)
            key(types.KEY_PRESS, inputs.F6)
            key(types.KEY_PRESS, inputs.SPACE)
            key(types.KEY_PRESS, inputs.ESCAPE)
            interface.distribute_buffered_events()
            assert scope['held'] == set()
            assert scope['pending_evaluation']['command'] == 'F6'
            assert scope['quit_flag']['quit'] and grips == [0]
        finally:
            interface.unsubscribe_to_keyboard_events(keyboard, subscription)
            provider.destroy_keyboard(keyboard)
            archive.close()
        journal = [json.loads(s) for s in (archive.path/'events.jsonl').read_text().splitlines()]
        if args.expect_character_error:
            assert len(errors) == 2 and all("'str' object has no attribute 'name'" in e for e in errors), errors
        else:
            assert not errors, errors
            assert len(journal) == 8
            assert [e['sequence'] for e in journal] == list(range(8))
            assert [e['key'] for e in journal[:5]] == ['W','w','한','W','W']
            assert [e['tick'] for e in journal] == [12]*4 + [16]*4
            assert [e['event_type'] for e in journal[:5]] == ['KEY_PRESS','CHAR','CHAR','KEY_REPEAT','KEY_RELEASE']
            assert all(s == ['W'] for s in snapshots[:4])
        report = {'passed':True,'expected_old_bug':args.expect_character_error,'errors':errors,
                  'native_events':events,'journal':journal,'held_key_snapshots':snapshots,
                  'scope':'real Carb input events through production callback; no GUI or physics'}
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print('TELEOP-KEYBOARD-PASS' + (' (old failure reproduced)' if args.expect_character_error else ' (recording fixed)'),flush=True)


if __name__ == '__main__':
    main()
