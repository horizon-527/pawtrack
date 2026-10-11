"""Private test CA and HTTPS fixtures for modem validation; never uses device credentials."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import ssl
import subprocess

def generate(directory, hostname):
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?', hostname) or '.' not in hostname:
        raise ValueError('Supply a test DNS hostname')
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, mode=0o700)
    def run(*arguments):
        subprocess.run(['openssl', *arguments], cwd=directory, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for name in ('ca', 'untrusted-ca'):
            run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '365',
                '-subj', '/CN=PawTrack-' + name, '-keyout', name + '.key', '-out', name + '.pem',
                '-addext', 'basicConstraints=critical,CA:TRUE',
                '-addext', 'keyUsage=critical,keyCertSign,cRLSign',
                '-addext', 'subjectKeyIdentifier=hash')
        (directory / 'index.txt').write_text(''); (directory / 'serial').write_text('1000\n')
        (directory / 'newcerts').mkdir()
        for mode in ('valid', 'expired', 'wrong-host'):
            host = 'wrong.' + hostname if mode == 'wrong-host' else hostname
            (directory / 'ca.cnf').write_text('''[ca]
default_ca=lab
[lab]
database=index.txt
serial=serial
new_certs_dir=newcerts
certificate=ca.pem
private_key=ca.key
default_md=sha256
default_days=7
policy=policy
unique_subject=no
[policy]
commonName=supplied
[server]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
subjectAltName=DNS:''' + host + '\n')
            run('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=' + host,
                '-keyout', mode + '.key', '-out', mode + '.csr')
            dates = ('-startdate', '20200101000000Z', '-enddate', '20200102000000Z') if mode == 'expired' else ()
            run('ca', '-batch', '-notext', '-config', 'ca.cnf', '-extensions', 'server',
                '-in', mode + '.csr', '-out', mode + '.pem', *dates)
        (directory / 'fixture.json').write_text(json.dumps({'hostname': hostname, 'testOnly': True}))
    finally:
        for path in directory.rglob('*'):
            if path.is_file(): path.chmod(0o600)
            elif path.is_dir(): path.chmod(0o700)
    return directory

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *arguments):
        pass
    def do_GET(self):
        body = b'{"ok":true,"testOnly":true}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        self.send_error(405, 'Use credential-free GET for TLS testing')

def make_server(directory, mode, host='127.0.0.1', port=0):
    directory = Path(directory)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(directory / (mode + '.pem'), directory / (mode + '.key'))
    server = ThreadingHTTPServer((host, port), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.socket.settimeout(10)
    return server

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    generator = commands.add_parser('generate')
    generator.add_argument('--directory', required=True); generator.add_argument('--hostname', required=True)
    service = commands.add_parser('serve')
    service.add_argument('--directory', required=True)
    service.add_argument('--mode', choices=('valid', 'expired', 'wrong-host'), required=True)
    service.add_argument('--host', default='127.0.0.1'); service.add_argument('--port', type=int, default=8443)
    args = parser.parse_args()
    if args.command == 'generate':
        generate(args.directory, args.hostname)
        print('Private TLS fixtures created; do not upload test CA keys or use them in production.')
    else:
        server = make_server(args.directory, args.mode, args.host, args.port)
        print('Credential-free TLS fixture serving:', args.mode, flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()

if __name__ == '__main__':
    main()
