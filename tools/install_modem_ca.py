"""Install a supplied trust anchor via modem UART; requires pyserial and physical hardware."""
import argparse
from pathlib import Path
import time

def wait(serial, expected, timeout):
    end=time.monotonic()+timeout
    received=bytearray()
    while time.monotonic()<end:
        received.extend(serial.read(256))
        if b'ERROR' in received: raise RuntimeError('modem rejected certificate operation')
        if expected in received: return
        if len(received)>8192: raise RuntimeError('unexpected modem response')
    raise TimeoutError('modem response timeout')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',required=True)
    parser.add_argument('--certificate',type=Path,required=True)
    parser.add_argument('--name',default='pawtrack-ca.pem')
    args=parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,45}\.pem',args.name): parser.error('invalid certificate filename')
    certificate=args.certificate.read_bytes()
    if not 1<=len(certificate)<=10240 or b'-----BEGIN CERTIFICATE-----' not in certificate: parser.error('supply a valid PEM CA certificate, up to 10240 bytes')
    import serial
    with serial.Serial(args.port,115200,timeout=.2) as connection:
        connection.reset_input_buffer();connection.write(b'AT\r\n');wait(connection,b'OK',5)
        connection.reset_input_buffer()
        command=f'AT+CCERTDOWN="{args.name}",{len(certificate)}\r\n'.encode()
        connection.write(command);wait(connection,b'>',10)
        for offset in range(0,len(certificate),1024):
            connection.write(certificate[offset:offset+1024]);connection.flush()
        wait(connection,b'OK',30)
    print('CA installed. Next verify valid TLS, wrong CA, expired certificate, and wrong hostname behavior on hardware.')

if __name__=='__main__':main()
