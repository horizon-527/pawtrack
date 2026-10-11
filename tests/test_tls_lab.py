from pathlib import Path
import socket
import ssl
import tempfile
import threading
import unittest
from tools.tls_lab import generate, make_server

class TlsLab(unittest.TestCase):
    def test_positive_and_three_distinct_tls_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = generate(Path(temporary) / 'lab', 'tracker.test')
            self.assertEqual((directory / 'valid.key').stat().st_mode & 0o777, 0o600)
            for mode, ca, error_code in (('valid', 'ca.pem', None), ('valid', 'untrusted-ca.pem', 20),
                                          ('expired', 'ca.pem', 10), ('wrong-host', 'ca.pem', 62)):
                with self.subTest(mode=mode, ca=ca):
                    server = make_server(directory, mode)
                    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                    context = ssl.create_default_context(cafile=str(directory / ca))
                    try:
                        def connect():
                            with socket.create_connection(server.server_address, timeout=3) as connection:
                                with context.wrap_socket(connection, server_hostname='tracker.test') as secured:
                                    secured.sendall(b'GET /health HTTP/1.1\r\nHost: tracker.test\r\nConnection: close\r\n\r\n')
                                    self.assertIn(b'200 OK', secured.recv(4096))
                        if error_code:
                            with self.assertRaises(ssl.SSLCertVerificationError) as failure: connect()
                            self.assertEqual(failure.exception.verify_code, error_code)
                        else: connect()
                    finally:
                        server.shutdown(); server.server_close(); thread.join(5)
