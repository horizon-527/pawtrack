"""Actual HTTP + actual mini-program controller, with an isolated WeChat exchange fixture."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import uvicorn
from fastapi import HTTPException
from server.production import create_app
from tools.doctor import check

class HttpFlow(unittest.TestCase):
    def test_mini_program_over_real_http(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async def exchange(code):
                if code not in ('test-owner', 'test-other'):
                    raise HTTPException(401, 'invalid fixture code')
                return 'isolated-' + code
            app = create_app(root / 'db.sqlite3', exchange)
            private = root / 'devices.json'
            private.write_text(json.dumps([app.state.store.provision('pet-one'), app.state.store.provision('pet-two')]))
            private.chmod(0o600)
            listener = socket.socket()
            listener.bind(('127.0.0.1', 0)); listener.listen(128)
            base = 'http://127.0.0.1:' + str(listener.getsockname()[1])
            service = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='critical'))
            thread = threading.Thread(target=service.run, kwargs={'sockets': [listener]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not service.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(service.started, 'local HTTP service did not start')
                self.assertTrue(check(base, local=True)['anonymousAccessRejected'])
                with self.assertRaises(ValueError): check(base)
                result = subprocess.run(['node', 'tests/http_flow.js', str(private)],
                                        env={**os.environ, 'PAWTRACK_TEST_BASE': base},
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout.strip())
            finally:
                service.should_exit = True
                thread.join(timeout=10)
                listener.close()
            self.assertFalse(thread.is_alive(), 'HTTP service must shut down')
