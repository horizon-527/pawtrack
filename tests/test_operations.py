from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from server.storage import Store
from tools.backup import backup_once
from tools.configure_miniprogram import configure
from tools.restore import restore

class Operations(unittest.TestCase):
    def test_backup_retention_and_offline_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = root / 'service.sqlite3'; store = Store(db)
            credentials = store.provision('real-test')
            self.assertEqual(db.stat().st_mode & 0o777, 0o600)
            session = store.login('test-owner'); owner = store.user(session['token'])
            store.bind(owner, credentials['bindingCode'], '宠物')
            folder = root / 'backups'; folder.mkdir()
            old = folder / 'pawtrack-old.sqlite3'; old.write_bytes(b'old')
            os.utime(old, (time.time() - 8 * 86400,) * 2)
            unrelated = folder / 'other.sqlite3'; unrelated.write_bytes(b'keep')
            backup = backup_once(db, folder)
            self.assertFalse(old.exists()); self.assertTrue(unrelated.exists())
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
            with closing(sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True)) as readonly:
                self.assertEqual(readonly.execute('PRAGMA journal_mode').fetchone()[0],'delete')
            folder.chmod(0o500)
            restored = root / 'restored.sqlite3'; restore(backup, restored)
            self.assertEqual(list(folder.glob('*.sqlite3-*')),[])
            folder.chmod(0o700)
            self.assertEqual(Store(restored).owned(owner, 'real-test')['name'], '宠物')
            self.assertEqual(Store(restored).device(credentials['deviceToken']), 'real-test')
    def test_invalid_restore_leaves_destination_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = root / 'db.sqlite3'; store = Store(db)
            store.provision('existing')
            bad = root / 'bad.sqlite3'; bad.write_bytes(b'not a database')
            with self.assertRaises((ValueError, sqlite3.Error)): restore(bad, db)
            with store.connection() as con:
                self.assertEqual(con.execute('SELECT count(*) FROM devices').fetchone()[0], 1)
            empty = root / 'empty.sqlite3'
            sqlite3.connect(empty).close()
            with self.assertRaises(ValueError): restore(empty, db)
    def test_real_project_is_separate_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); destination = root / 'miniprogram'
            for base in ('http://example.com', 'https://user:pass@example.com', 'https://example.com/api', 'https://test.invalid'):
                with self.assertRaises(ValueError): configure(destination, 'wx0123456789abcdef', base, '运营方', 'test@example.com')
            self.assertFalse(destination.exists())
            configure(destination, 'wx0123456789abcdef', 'https://example.com/', '运营方', 'test@example.com')
            import json
            project = json.loads((destination / 'project.config.json').read_text())
            self.assertTrue(project['setting']['urlCheck'])
            self.assertNotIn('local-viewer', (destination / 'config.js').read_text())
            with self.assertRaises(ValueError): configure(destination, 'wx0123456789abcdef', 'https://example.com', '运营方', 'test@example.com')
