"""Loopback-only development API; not a production server."""
import json
from contextlib import contextmanager
import math
import os
import hmac
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB = Path(os.environ.get('PAWTRACK_DB', str(Path(__file__).with_name('positions.sqlite3'))))
DEVICE_TOKEN = os.environ.get('PAWTRACK_DEVICE_TOKEN', 'local-device')
VIEWER_TOKEN = os.environ.get('PAWTRACK_VIEWER_TOKEN', 'local-viewer')

def open_database():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS positions (
      sequence INTEGER PRIMARY KEY, capturedAt REAL NOT NULL, receivedAt REAL NOT NULL,
      latitude REAL NOT NULL, longitude REAL NOT NULL, battery REAL NOT NULL,
      coordinateSystem TEXT NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS telemetry (
      bootId TEXT NOT NULL, sequence INTEGER NOT NULL, capturedAt REAL NOT NULL,
      receivedAt REAL NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
      battery REAL NOT NULL, coordinateSystem TEXT NOT NULL,
      PRIMARY KEY (bootId, sequence))''')
    con.execute("INSERT OR IGNORE INTO telemetry SELECT 'legacy', sequence, capturedAt, receivedAt, latitude, longitude, battery, coordinateSystem FROM positions")
    con.commit()
    return con

@contextmanager
def connect():
    con = open_database()
    try:
        with con:
            yield con
    finally:
        con.close()

def validate(data):
    if not isinstance(data, dict) or data.get('deviceId') != 'demo-pet':
        raise ValueError('unknown device')
    data = dict(data)
    data.setdefault('bootId', 'legacy')
    if not isinstance(data['bootId'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', data['bootId']):
        raise ValueError('invalid bootId')
    if type(data.get('sequence')) is not int or data['sequence'] < 0:
        raise ValueError('invalid sequence')
    for key, low, high in [('latitude', -90, 90), ('longitude', -180, 180),
                           ('battery', 0, 100), ('capturedAt', 1, time.time() + 60)]:
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('invalid ' + key)
    if data.get('coordinateSystem') not in ('wgs84', 'gcj02'):
        raise ValueError('coordinateSystem required')
    return data

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log credentials or position data.

    def reply(self, status, data):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, role):
        token = DEVICE_TOKEN if role == 'device' else VIEWER_TOKEN
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
            self.reply(401, {'error': 'unauthorized'})
            return False
        return True

    def do_GET(self):
        if self.path == '/health':
            return self.reply(200, {'ok': True, 'mode': 'local-development'})
        if self.path not in ('/api/latest', '/api/track'):
            return self.reply(404, {'error': 'not found'})
        if not self.authorized('viewer'):
            return
        with connect() as con:
            if self.path == '/api/latest':
                row = con.execute('SELECT * FROM telemetry ORDER BY capturedAt DESC, receivedAt DESC LIMIT 1').fetchone()
                data = dict(row) if row else None
                if data:
                    data['ageSeconds'] = max(0, int(time.time() - data['capturedAt']))
                    data['stale'] = data['ageSeconds'] > 120
            else:
                rows = con.execute('SELECT * FROM telemetry WHERE capturedAt >= ? ORDER BY capturedAt DESC, receivedAt DESC LIMIT 2000', (time.time() - 86400,)).fetchall()
                data = [dict(row) for row in reversed(rows)]
        self.reply(200, data)

    def do_POST(self):
        if self.path != '/api/positions':
            return self.reply(404, {'error': 'not found'})
        if not self.authorized('device'):
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('invalid body length')
            data = validate(json.loads(self.rfile.read(size)))
        except (ValueError, TypeError, UnicodeDecodeError):
            return self.reply(400, {'error': 'invalid telemetry'})
        with connect() as con:
            cursor = con.execute('INSERT OR IGNORE INTO telemetry VALUES (?,?,?,?,?,?,?,?)',
                (data['bootId'], data['sequence'], data['capturedAt'], time.time(), data['latitude'],
                 data['longitude'], data['battery'], data['coordinateSystem']))
            inserted = cursor.rowcount == 1
        if not inserted:
            with connect() as con:
                existing = con.execute('SELECT * FROM telemetry WHERE bootId=? AND sequence=?', (data['bootId'], data['sequence'])).fetchone()
            if any(existing[key] != data[key] for key in ('capturedAt', 'latitude', 'longitude', 'battery', 'coordinateSystem')):
                return self.reply(409, {'error': 'sequence reused with different telemetry'})
        self.reply(201 if inserted else 200, {'accepted': True, 'duplicate': not inserted, 'bootId': data['bootId'], 'sequence': data['sequence']})

if __name__ == '__main__':
    print('PawTrack local API: http://127.0.0.1:8787')
    ThreadingHTTPServer(('127.0.0.1', 8787), Handler).serve_forever()
