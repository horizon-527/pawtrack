"""Persistent state for the v1 application. Separate from the original local prototype."""
from contextlib import contextmanager
import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, openid TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS devices (
 id TEXT PRIMARY KEY, secret_digest TEXT NOT NULL, owner_id TEXT REFERENCES users(id),
 name TEXT NOT NULL DEFAULT '我的宠物', binding_digest TEXT, binding_expires REAL,
 desired_mode TEXT NOT NULL DEFAULT 'normal', applied_mode TEXT,
 last_seen REAL, battery REAL, fix_valid INTEGER, firmware TEXT);
CREATE TABLE IF NOT EXISTS points (
 id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
 boot_id TEXT NOT NULL, sequence INTEGER NOT NULL, captured_at REAL NOT NULL, received_at REAL NOT NULL,
 latitude REAL NOT NULL, longitude REAL NOT NULL, coordinate_system TEXT NOT NULL, battery REAL,
 UNIQUE(device_id, boot_id, sequence));
CREATE INDEX IF NOT EXISTS points_device_time ON points(device_id, captured_at, id);
CREATE INDEX IF NOT EXISTS points_retention ON points(captured_at);
CREATE UNIQUE INDEX IF NOT EXISTS devices_secret ON devices(secret_digest);
CREATE UNIQUE INDEX IF NOT EXISTS devices_binding ON devices(binding_digest);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires);
'''

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as con:
            con.executescript(SCHEMA)
        Path(path).chmod(0o600)
    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA journal_mode=WAL')
        try:
            with con: yield con
        finally: con.close()
    def provision(self, device_id, ttl=86400, deliver=None):
        secret, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        data = {'deviceId': device_id, 'deviceToken': secret, 'bindingCode': binding}
        with self.connection() as con:
            con.execute('INSERT INTO devices(id, secret_digest, binding_digest, binding_expires) VALUES(?,?,?,?)',
                        (device_id, digest(secret), digest(binding), time.time()+ttl))
            if deliver is not None:
                deliver(data)
        return data
    def login(self, openid):
        token = secrets.token_urlsafe(32)
        expires = time.time()+7*86400
        with self.connection() as con:
            con.execute('INSERT OR IGNORE INTO users(id,openid) VALUES(?,?)', (secrets.token_hex(16), openid))
            user = con.execute('SELECT id FROM users WHERE openid=?',(openid,)).fetchone()['id']
            con.execute('DELETE FROM sessions WHERE expires <= ?', (time.time(),))
            con.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token),user,expires))
        return {'token':token, 'expiresAt':expires}
    def user(self, token):
        with self.connection() as con:
            row=con.execute('SELECT user_id FROM sessions WHERE digest=? AND expires>?', (digest(token),time.time())).fetchone()
        return row['user_id'] if row else None
    def device(self, token):
        with self.connection() as con:
            row=con.execute('SELECT id FROM devices WHERE secret_digest=?',(digest(token),)).fetchone()
        return row['id'] if row else None
    def bind(self, user_id, code, name):
        with self.connection() as con:
            # Serialized transaction guarantees that a code can be consumed only once.
            con.execute('BEGIN IMMEDIATE')
            row=con.execute('SELECT id FROM devices WHERE binding_digest=? AND binding_expires>? AND owner_id IS NULL',
                            (digest(code),time.time())).fetchone()
            if not row: return None
            con.execute('DELETE FROM points WHERE device_id=?',(row['id'],))
            con.execute('UPDATE devices SET owner_id=?, name=?, binding_digest=NULL, binding_expires=NULL WHERE id=?',
                        (user_id,name,row['id']))
            return row['id']
    def owned(self, user, device):
        with self.connection() as con:
            return con.execute('SELECT * FROM devices WHERE id=? AND owner_id=?',(device,user)).fetchone()
    def insert(self, device, point):
        now=time.time()
        with self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            owner=con.execute('SELECT owner_id FROM devices WHERE id=?',(device,)).fetchone()
            if owner is None or owner['owner_id'] is None: return 'unbound'
            old=con.execute('SELECT * FROM points WHERE device_id=? AND boot_id=? AND sequence=?',
                            (device, point.bootId, point.sequence)).fetchone()
            if old:
                same=all(old[db] == getattr(point,key) for db,key in (
                    ('captured_at','capturedAt'),('latitude','latitude'),('longitude','longitude'),
                    ('coordinate_system','coordinateSystem'),('battery','battery')))
                return 'duplicate' if same else 'conflict'
            con.execute('INSERT INTO points(device_id,boot_id,sequence,captured_at,received_at,latitude,longitude,coordinate_system,battery) VALUES(?,?,?,?,?,?,?,?,?)',
                        (device,point.bootId,point.sequence,point.capturedAt,now,point.latitude,point.longitude,point.coordinateSystem,point.battery))
            # A delayed history point is not a heartbeat or proof of current GNSS health.
            return 'inserted'
    def cleanup(self, days=30):
        with self.connection() as con:
            points=con.execute('DELETE FROM points WHERE captured_at<?',(time.time()-days*86400,)).rowcount
            con.execute('DELETE FROM sessions WHERE expires<=?',(time.time(),))
        return points
