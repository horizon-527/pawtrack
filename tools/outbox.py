"""Desktop reference for a durable device retry queue (not ESP32 firmware)."""
import json
from contextlib import contextmanager
import sqlite3
from urllib.request import Request, urlopen

@contextmanager
def database(path):
    con = sqlite3.connect(path)
    try:
        with con:
            yield con
    finally:
        con.close()

class Outbox:
    def __init__(self, path, limit=10000):
        self.path, self.limit = path, limit
        with database(path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
    def enqueue(self, payload):
        with database(self.path) as con:
            if con.execute('SELECT COUNT(*) FROM outbox').fetchone()[0] >= self.limit:
                raise OverflowError('outbox full: preserve existing points, reject new point')
            con.execute('INSERT INTO outbox(payload) VALUES(?)', (json.dumps(payload),))
    def pending(self):
        with database(self.path) as con:
            return con.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]
    def flush(self, send, batch=100):
        sent = 0
        for _ in range(batch):
            with database(self.path) as con:
                row = con.execute('SELECT id,payload FROM outbox ORDER BY id LIMIT 1').fetchone()
            if row is None:
                break
            # Delete only after confirmed acceptance. Failures preserve the exact original payload.
            send(json.loads(row[1]))
            with database(self.path) as con:
                con.execute('DELETE FROM outbox WHERE id=?', (row[0],))
            sent += 1
        return sent

def upload(payload, endpoint, token):
    request = Request(endpoint, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    with urlopen(request, timeout=5) as response:
        result = json.load(response)
        if response.status not in (200, 201) or result.get('accepted') is not True:
            raise ValueError('server did not acknowledge telemetry')
        if result.get('bootId') != payload.get('bootId', 'legacy') or result.get('sequence') != payload['sequence']:
            raise ValueError('acknowledgement does not match queued point')
