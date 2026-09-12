"""CPU checks for lossless recording, frame order and corruption detection."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import threading
import time

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/DexGarmentLab'))
from Policy.teleop_recording import ArchiveReader, StateArchive


class ArchiveTests(unittest.TestCase):
    def test_exact_roundtrip_and_ordered_reset_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'recording'
            writer = StateArchive(path, {'physics_dt_s': 1 / 240}, chunk_frames=3)
            frames = []
            for i, tick in enumerate([0, 1, 2, 2, 2, 3, 4]):
                values = {'points': np.random.default_rng(i).normal(size=(17, 3)).astype(np.float32),
                          'event_name': np.array('초기화' if i == 3 else 'physics'),
                          'endian_signed_zero': np.array([-0.0, 1.25], dtype='>f4'),
                          'grasp_indices': np.arange(i, dtype=np.int64)}
                writer.append(tick, 'boundary' if i in (0, 3, 4) else 'physics', values)
                frames.append(values)
            writer.event(4, 'keyboard', key='ESCAPE', event_type='KEY_PRESS')
            writer.close()
            reader = ArchiveReader(path)
            received = list(reader.frames())
            self.assertEqual(len(received), len(frames))
            for (_, actual), expected in zip(received, frames):
                for key in expected:
                    np.testing.assert_array_equal(actual[key], expected[key])
                    self.assertEqual(actual[key].dtype, expected[key].dtype)
                    self.assertEqual(actual[key].tobytes(), expected[key].tobytes())
            self.assertEqual(reader.manifest['events'], 1)

    def test_incomplete_is_explicit_and_flushed_chunks_are_recoverable(self):
        with tempfile.TemporaryDirectory() as temporary:
            writer = StateArchive(Path(temporary) / 'recording', {}, chunk_frames=2)
            writer.append(0, 'initial', {'x': np.array([1.0])})
            writer.append(1, 'physics', {'x': np.array([2.0])})
            writer.sync()
            with self.assertRaises(ValueError):
                ArchiveReader(writer.path)
            self.assertEqual(len(list(ArchiveReader(writer.path, True).frames())), 2)
            writer.close(complete=False, reason='interrupted')
            self.assertFalse(ArchiveReader(writer.path, True).manifest['complete'])

    def test_corrupt_chunk_and_missing_tick_are_rejected(self):
        for corrupt in (True, False):
            with tempfile.TemporaryDirectory() as temporary:
                writer = StateArchive(Path(temporary) / 'recording', {})
                writer.append(0, 'initial', {'x': np.array([1.0])})
                writer.append(1 if corrupt else 3, 'physics', {'x': np.array([2.0])})
                writer.close()
                if corrupt:
                    path = writer.path / writer.manifest['chunks'][0]['file']
                    path.write_bytes(path.read_bytes() + b'corruption')
                with self.assertRaises(ValueError):
                    list(ArchiveReader(writer.path).frames())

    def test_input_event_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            writer = StateArchive(Path(temporary) / 'recording', {})
            writer.append(0, 'initial', {'x': np.array([1.0])})
            writer.event(0, 'keyboard', key='W')
            writer.close()
            (writer.path / 'events.jsonl').write_text('{}\n')
            with self.assertRaises(ValueError):
                ArchiveReader(writer.path)

    def test_slow_writer_blocks_without_dropping_or_aliasing(self):
        with tempfile.TemporaryDirectory() as temporary:
            writer = StateArchive(Path(temporary) / 'recording', {}, chunk_frames=1, queue_chunks=1)
            entered, release = threading.Event(), threading.Event()
            original = writer._write_chunk
            def slow(*args):
                entered.set()
                self.assertTrue(release.wait(5))
                original(*args)
            with patch.object(writer, '_write_chunk', slow):
                source = np.array([0.0], dtype=np.float32)
                writer.append(0, 'initial', {'x': source})
                self.assertTrue(entered.wait(5))
                source[0] = 1
                writer.append(1, 'physics', {'x': source})
                done = threading.Event()
                def produce():
                    writer.append(2, 'physics', {'x': np.array([2.0], dtype=np.float32)})
                    done.set()
                producer = threading.Thread(target=produce)
                producer.start()
                self.assertFalse(done.wait(.05))
                release.set()
                producer.join(5)
                self.assertTrue(done.is_set())
                writer.close()
            self.assertEqual([float(v['x'][0]) for _, v in ArchiveReader(writer.path).frames()], [0, 1, 2])
            self.assertFalse(writer._worker.is_alive())

    def test_worker_error_propagates_and_never_marks_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            writer = StateArchive(Path(temporary) / 'recording', {}, chunk_frames=1)
            with patch.object(writer, '_write_chunk', side_effect=OSError('disk full')):
                writer.append(0, 'initial', {'x': np.array([1.0])})
                writer._queue.join()
                with self.assertRaisesRegex(RuntimeError, 'disk full'):
                    writer.check()
                with self.assertRaisesRegex(RuntimeError, 'disk full'):
                    writer.close()
            self.assertFalse(writer._worker.is_alive())
            self.assertFalse(ArchiveReader(writer.path, True).manifest['complete'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
