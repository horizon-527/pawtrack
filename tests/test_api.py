import importlib.util
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
spec = importlib.util.spec_from_file_location('app', Path(__file__).parents[1] / 'server/app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class API(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB = Path(self.tmp.name) / 'test.sqlite3'
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def call(self, path, role=None, data=None):
        req = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={'Authorization': 'Bearer local-' + str(role)})
        try:
            response = urlopen(req)
        except HTTPError as e:
            response = e
        with response:
            return response.code, json.load(response)
    def point(self, sequence=1, **kwargs):
        return dict(deviceId='demo-pet', sequence=sequence, capturedAt=time.time(), latitude=31.2,
                    longitude=121.4, battery=80, coordinateSystem='gcj02', **kwargs)
    def test_auth(self):
        self.assertEqual(self.call('/api/latest')[0], 401)
        self.assertEqual(self.call('/api/positions', 'viewer', self.point())[0], 401)
    def test_duplicate_and_out_of_order(self):
        data = self.point()
        self.assertEqual(self.call('/api/positions', 'device', data)[0], 201)
        self.assertTrue(self.call('/api/positions', 'device', data)[1]['duplicate'])
        old = self.point(2); old['capturedAt'] -= 200
        self.call('/api/positions', 'device', old)
        self.assertEqual(self.call('/api/latest', 'viewer')[1]['sequence'], 1)
        self.assertEqual(len(self.call('/api/track', 'viewer')[1]), 2)
    def test_invalid(self):
        for key, value in [('latitude', 91), ('battery', -1), ('sequence', True), ('capturedAt', time.time()+500), ('longitude', float('nan')), ('coordinateSystem', 'unknown')]:
            data = self.point(); data[key] = value
            self.assertEqual(self.call('/api/positions', 'device', data)[0], 400)
    def test_stale_and_retention(self):
        data = self.point(); data['capturedAt'] -= 90000
        self.call('/api/positions', 'device', data)
        self.assertTrue(self.call('/api/latest', 'viewer')[1]['stale'])
        self.assertEqual(self.call('/api/track', 'viewer')[1], [])
    def test_empty(self):
        self.assertIsNone(self.call('/api/latest', 'viewer')[1])

if __name__ == '__main__': unittest.main()

class RestartAPI(API):
    def test_boot_sequence_reset(self):
        first = self.point(); first['bootId'] = 'boot-one'
        second = self.point(); second['bootId'] = 'boot-two'
        self.assertEqual(self.call('/api/positions', 'device', first)[0], 201)
        self.assertEqual(self.call('/api/positions', 'device', second)[0], 201)
        self.assertEqual(len(self.call('/api/track', 'viewer')[1]), 2)
    def test_conflicting_retransmit(self):
        data = self.point(); self.call('/api/positions', 'device', data)
        data['battery'] = 70
        self.assertEqual(self.call('/api/positions', 'device', data)[0], 409)
