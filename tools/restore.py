"""Validate and restore a SQLite backup while API and backup worker are stopped."""
import argparse
import os
from pathlib import Path
import sqlite3

def restore(backup, database):
    backup, database = Path(backup).resolve(), Path(database).resolve()
    if not backup.is_file() or backup == database:
        raise ValueError('Supply a separate existing backup')
    source = sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)
    pending = database.with_suffix('.restore-pending')
    reserved = False
    try:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Corrupt backup')
        tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'users', 'devices', 'points', 'sessions'} <= tables:
            raise ValueError('Not a PawTrack v1 backup')
        if source.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Backup has invalid ownership references')
        database.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd); reserved = True
        target = sqlite3.connect(pending)
        try:
            source.backup(target)
            target.execute('PRAGMA journal_mode=DELETE')
        finally:
            target.close()
        with pending.open('rb') as stream:
            os.fsync(stream.fileno())
        # The caller must stop all database users; old WAL must not replay after replacement.
        for suffix in ('-wal', '-shm'):
            Path(str(database) + suffix).unlink(missing_ok=True)
        os.replace(pending, database)
    finally:
        source.close()
        if reserved:
            pending.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', required=True)
    parser.add_argument('--db', default=os.environ.get('PAWTRACK_DB', 'data/pawtrack.sqlite3'))
    parser.add_argument('--confirm-service-stopped', action='store_true', required=True)
    args = parser.parse_args()
    try:
        restore(args.backup, args.db)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.error(str(error))
    print('Backup restored. Restart services and verify login, ownership and tracks.')

if __name__ == '__main__':
    main()
