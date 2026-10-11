"""Consistent daily SQLite backups with a seven-day retention policy."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import time

def backup_once(database, directory, keep_days=7, now=None):
    if keep_days < 1:
        raise ValueError('keep_days must be positive')
    database = Path(database).resolve()
    if not database.is_file():
        raise FileNotFoundError('database not found; start the API first')
    now = time.time() if now is None else now
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    final = directory / ('pawtrack-' + stamp + '.sqlite3')
    pending = final.with_suffix('.pending')
    fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        source = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
        try:
            target = sqlite3.connect(pending)
            try:
                source.backup(target)
                # A backup is a closed standalone file, including on a read-only mount.
                # Keeping the source WAL flag would require writable -wal/-shm files.
                target.execute('PRAGMA journal_mode=DELETE')
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('backup integrity check failed')
            finally:
                target.close()
        finally:
            source.close()
        # Timestamp names should be unique. Refuse to overwrite an existing backup.
        os.link(pending, final)
        pending.unlink()
        for old in list(directory.glob('pawtrack-*.sqlite3')) + list(directory.glob('pawtrack-*.pending')):
            if old != final and not old.is_symlink() and old.stat().st_mtime < now - keep_days * 86400:
                old.unlink()
        return final
    finally:
        if pending.exists():
            pending.unlink()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=os.environ.get('PAWTRACK_DB', 'data/pawtrack.sqlite3'))
    parser.add_argument('--directory', default='/backups')
    parser.add_argument('--keep-days', type=int, default=7)
    parser.add_argument('--interval', type=int, default=86400, help='0 for a single backup')
    args = parser.parse_args()
    if args.keep_days < 1 or args.interval < 0:
        parser.error('invalid retention or interval')
    while True:
        try:
            path = backup_once(args.db, args.directory, args.keep_days)
            print('Backup verified:', path.name, flush=True)
        except (OSError, sqlite3.Error, RuntimeError) as error:
            # Report the error class; no credentials or location data are logged.
            print('Backup failed:', type(error).__name__, flush=True)
            if not args.interval:
                raise SystemExit(1)
            time.sleep(60)
            continue
        if not args.interval:
            break
        time.sleep(args.interval)

if __name__ == '__main__':
    main()
