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
    def test_wrong_ack_keeps_queued_point(self):
        import io
        import json
        from unittest.mock import patch
        from tools.outbox import upload
        class Reply(io.BytesIO):
            status=201
        with tempfile.TemporaryDirectory() as directory:
            queue=Outbox(str(Path(directory)/'queue.sqlite3'))
            point={'bootId':'current','sequence':2}
            queue.enqueue(point)
            with patch('tools.outbox.urlopen',return_value=Reply(json.dumps({'accepted':True,'bootId':'older','sequence':1}).encode())):
                with self.assertRaises(ValueError):
                    queue.flush(lambda p:upload(p,'http://127.0.0.1/positions','test'))
            self.assertEqual(queue.pending(),1)
