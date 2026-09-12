#!/usr/bin/env python3
"""Score a continuous full-teleop recording interval on CPU, without Isaac Sim."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path('/project') if Path('/project/src/DexGarmentLab').is_dir() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/DexGarmentLab'))
from Policy.teleop_recording import ArchiveReader
from Policy.evaluation_replay import ReplayEvaluation
from Policy.evaluation_contact import recording_contact_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start-tick', type=int, default=0)
    parser.add_argument('--end-tick', type=int)
    parser.add_argument('--contact-context', type=Path, help='Optional exported collision context for older v2 recordings')
    args = parser.parse_args()
    if args.output.resolve() == args.recording.resolve() or args.recording.resolve() in args.output.resolve().parents:
        parser.error('Evaluation output must be outside the original recording')
    reader = ArchiveReader(args.recording)
    contact = recording_contact_context(reader, args.contact_context)
    evaluation = ReplayEvaluation(reader.manifest['metadata'], args.output, args.start_tick, args.end_tick, contact)
    # Read to EOF even for a shorter scoring interval to verify the whole archive.
    try:
        for header, values in reader.frames():
            evaluation.consume(header, values)
    except BaseException:
        if evaluation.session and evaluation.session.active:
            evaluation.session.finish(reason='archive_read_failed', valid=False, take_final=False)
        raise
    report = evaluation.finish()
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
