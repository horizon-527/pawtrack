"""Replay a captured GNSS serial log into the local API, retaining original UTC timestamps."""
import argparse
import os
from pathlib import Path
import sys
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from firmware.nmea import parse_rmc
from tools.outbox import Outbox, upload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--battery', type=float, required=True, help='Measured battery percent; not inferred from NMEA')
    args=parser.parse_args()
    if not 0 <= args.battery <= 100: parser.error('battery out of range')
    queue=Outbox(str(Path(__file__).with_name('nmea-outbox.sqlite3')))
    boot=uuid.uuid4().hex
    accepted=0
    with args.log.open() as stream:
        for line in stream:
            if not line.startswith(('$GPRMC,', '$GNRMC,')): continue
            try: point=parse_rmc(line)
            except ValueError: continue
            if point is None: continue
            queue.enqueue(dict(point, deviceId='demo-pet', bootId=boot, sequence=accepted, battery=args.battery))
            accepted += 1
    print('Valid fixes queued:',accepted)
    try:
        while queue.pending():
            queue.flush(lambda point: upload(point, 'http://127.0.0.1:8787/api/positions', os.environ.get('PAWTRACK_DEVICE_TOKEN','local-device')))
    except (OSError, ValueError):
        print('Upload not acknowledged. Pending points retained:', queue.pending())
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
