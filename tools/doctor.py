"""Read-only deployment checks. No login credential or location is sent or printed."""
import argparse
import json
import ssl
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

def check(base, ca=None, local=False):
    parsed = urlsplit(base)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/') or not parsed.hostname):
        raise ValueError('Supply an API origin without credentials or path')
    if parsed.scheme != 'https' and not (local and parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')):
        raise ValueError('HTTPS is required; --local permits a loopback HTTP test only')
    base = base.rstrip('/')
    context = ssl.create_default_context(cafile=ca)
    with urlopen(base + '/health', timeout=10, context=context) as response:
        if response.geturl() != base + '/health':
            raise RuntimeError('API health endpoint must not redirect')
        if response.status != 200 or json.load(response).get('ok') is not True:
            raise RuntimeError('health check failed')
    try:
        with urlopen(Request(base + '/v1/devices'), timeout=10, context=context):
            raise RuntimeError('unauthenticated device access was not rejected')
    except HTTPError as error:
        if error.code != 401 or error.geturl() != base + '/v1/devices':
            raise RuntimeError('unexpected authentication response') from None
    return {'health': 'passed', 'anonymousAccessRejected': True,
            'tlsChainAndHostnameVerifiedOnComputer': parsed.scheme == 'https',
            'hardwareTlsVerified': False, 'realWeChatLoginVerified': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--ca', help='also check the exact root CA intended for the modem')
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    try:
        result = check(args.base, args.ca, args.local)
    except Exception as error:
        print(json.dumps({'passed': False, 'errorType': type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
