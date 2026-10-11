"""Synthetic GCJ02 demo route, with persistent retry queue."""
import argparse
import math
import os
from pathlib import Path
import time
import uuid
from urllib.error import URLError
from outbox import Outbox, upload

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--count', type=int, default=0, help='0 means continuous')
    parser.add_argument('--endpoint', default='http://127.0.0.1:8787/api/positions')
    args = parser.parse_args()
    if args.interval <= 0 or args.count < 0:
        parser.error('interval must be positive; count must be nonnegative')
    queue = Outbox(str(Path(__file__).with_name('outbox.sqlite3')))
    boot = uuid.uuid4().hex
    token = os.environ.get('PAWTRACK_DEVICE_TOKEN', 'local-device')
    print('Synthetic pet positions; Ctrl+C to stop. Pending:', queue.pending())
    step = 0
    while not args.count or step < args.count:
        data = {'deviceId': 'demo-pet', 'bootId': boot, 'sequence': step, 'capturedAt': time.time(),
                'latitude': 31.2304 + .001 * math.sin(step / 20),
                'longitude': 121.4737 + .001 * math.cos(step / 20),
                'coordinateSystem': 'gcj02', 'battery': 85}
        try:
            queue.enqueue(data)
        except OverflowError:
            print('Queue full; new synthetic point discarded')
        try:
            sent = queue.flush(lambda p: upload(p, args.endpoint, token))
            print('Uploaded:', sent, 'pending:', queue.pending())
        except (URLError, TimeoutError, OSError, ValueError):
            print('Upload failed; retaining points for retry. Pending:', queue.pending())
        step += 1
        if not args.count or step < args.count:
            time.sleep(args.interval)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Stopped. Unsent points retained.')
