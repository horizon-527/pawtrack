import tempfile
import unittest
from pathlib import Path
from tools.outbox import Outbox

class Queue(unittest.TestCase):
    def test_failure_restart_and_acknowledgement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'outbox.sqlite3')
            queue = Outbox(path)
            point = {'bootId': 'boot', 'sequence': 0, 'capturedAt': 123}
            queue.enqueue(point)
            def fail(data):
                raise ConnectionError('offline')
            with self.assertRaises(ConnectionError):
                queue.flush(fail)
            restarted = Outbox(path)
            self.assertEqual(restarted.pending(), 1)
            received = []
            self.assertEqual(restarted.flush(received.append), 1)
            self.assertEqual(received, [point])
            self.assertEqual(restarted.pending(), 0)
    def test_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = Outbox(str(Path(directory) / 'queue.sqlite3'), limit=1)
            queue.enqueue({'sequence': 1})
            with self.assertRaises(OverflowError): queue.enqueue({'sequence': 2})
            self.assertEqual(queue.pending(), 1)
