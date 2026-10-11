import unittest
from firmware.nmea import parse_rmc

def frame(body):
    checksum=0
    for char in body: checksum ^= ord(char)
    return '$' + body + '*' + format(checksum, '02X')

class NMEA(unittest.TestCase):
    def test_valid_fix_and_time(self):
        data=parse_rmc(frame('GNRMC,123519.00,A,4807.038,N,01131.000,E,0,0,111026,,,A'))
        self.assertAlmostEqual(data['latitude'],48.1173)
        self.assertAlmostEqual(data['longitude'],11.5166666667)
        self.assertEqual(data['coordinateSystem'],'wgs84')
        self.assertEqual(data['capturedAt'],1791722119)
    def test_no_fix(self):
        self.assertIsNone(parse_rmc(frame('GNRMC,123519,V,,,,,,,111026,,,N')))
    def test_checksum(self):
        with self.assertRaises(ValueError): parse_rmc('$GNRMC,bad*00')
    def test_invalid_minutes(self):
        with self.assertRaises(ValueError): parse_rmc(frame('GNRMC,123519,A,4867.038,N,01131.000,E,0,0,111026,,,A'))
