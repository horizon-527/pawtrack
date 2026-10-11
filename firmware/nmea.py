"""Host reference RMC parser for firmware porting; does not drive the modem."""
from datetime import datetime, timezone
import math

def coordinate(raw, direction):
    value = float(raw)
    degrees = int(value / 100)
    minutes = value - degrees * 100
    if not math.isfinite(value) or value < 0 or not 0 <= minutes < 60:
        raise ValueError('invalid coordinate')
    result = degrees + minutes / 60
    return -result if direction in ('S', 'W') else result

def parse_rmc(line):
    line = line.strip()
    if not line.startswith('$') or '*' not in line:
        raise ValueError('missing NMEA frame/checksum')
    body, checksum = line[1:].split('*', 1)
    value = 0
    for char in body:
        value ^= ord(char)
    if len(checksum) != 2 or value != int(checksum, 16):
        raise ValueError('checksum mismatch')
    fields = body.split(',')
    if len(fields) < 10 or fields[0] not in ('GPRMC', 'GNRMC'):
        raise ValueError('not a supported RMC sentence')
    if fields[2] != 'A':
        return None
    if len(fields) > 12 and fields[12] == 'N':
        return None
    if fields[4] not in ('N', 'S') or fields[6] not in ('E', 'W'):
        raise ValueError('invalid hemisphere')
    lat = coordinate(fields[3], fields[4]); lon = coordinate(fields[5], fields[6])
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('coordinate out of range')
    date, clock = fields[9], fields[1]
    if len(date) != 6 or len(clock.split('.')[0]) != 6:
        raise ValueError('invalid date/time')
    # This project accepts modern GNSS dates, not ambiguous historical two-digit years.
    year = 2000 + int(date[4:6])
    second = float(clock[4:])
    if not 0 <= second < 60:
        raise ValueError('unsupported leap second')
    captured = datetime(year, int(date[2:4]), int(date[:2]), int(clock[:2]),
                        int(clock[2:4]), int(second), int((second % 1)*1_000_000), tzinfo=timezone.utc)
    return {'latitude': lat, 'longitude': lon, 'coordinateSystem': 'wgs84',
            'capturedAt': captured.timestamp()}
