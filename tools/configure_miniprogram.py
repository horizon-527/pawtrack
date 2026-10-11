"""Prepare a separate real-device mini-program project without changing the demo."""
import argparse
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

def configure(destination, appid, base, operator, contact):
    parsed = urlsplit(base)
    if not re.fullmatch(r'wx[0-9a-f]{16}', appid):
        raise ValueError('AppID must be the real wx + 16 hexadecimal digits')
    if (parsed.scheme != 'https' or not parsed.hostname or '.' not in parsed.hostname
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('Supply an HTTPS domain without a path, credentials or custom port')
    if parsed.hostname.endswith('.invalid') or not operator.strip() or not contact.strip():
        raise ValueError('Supply a real domain and operator/contact information')
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Output already exists; choose a new directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'miniprogram', destination,
                    ignore=shutil.ignore_patterns('project.private.config.json'))
    config = {'apiBase': base.rstrip('/'), 'refreshMs': 5000, 'apiMode': 'v1',
              'operatorName': operator.strip(), 'contact': contact.strip()}
    (destination / 'config.js').write_text('module.exports = ' + json.dumps(config, ensure_ascii=False, indent=2) + ';\n')
    project = json.loads((destination / 'project.config.json').read_text())
    project.update(appid=appid, description='PawTrack 真机测试项目')
    project['setting'].update(urlCheck=True, minified=True, uploadWithSourceMap=False)
    (destination / 'project.config.json').write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n')
    return destination

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/miniprogram-real')
    parser.add_argument('--appid', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--operator', required=True)
    parser.add_argument('--contact', required=True)
    args = parser.parse_args()
    try:
        configure(args.output, args.appid, args.base, args.operator, args.contact)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('Real-device project prepared. Import the output directory in WeChat DevTools.')
    print('Configure the request domain and verify real login before publishing.')

if __name__ == '__main__':
    main()
