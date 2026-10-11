import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from server.storage import Store

class Management(unittest.TestCase):
    def test_delivery_failure_rolls_back_device_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/'db.sqlite3')
            def failing(data): raise OSError('output unavailable')
            with self.assertRaises(OSError): store.provision('pet-undelivered',deliver=failing)
            with store.connection() as con:
                self.assertEqual(con.execute('SELECT count(*) FROM devices').fetchone()[0],0)
    def test_private_provision_and_backup_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); db=base/'db.sqlite3'; output=base/'device.json'; backup=base/'backup.sqlite3'
            subprocess.run([sys.executable,'tools/manage.py','--db',str(db),'provision','pet-test','--output',str(output)],check=True,capture_output=True)
            self.assertEqual(output.stat().st_mode & 0o777,0o600)
            credentials=json.loads(output.read_text());store=Store(db)
            token=store.login('owner')['token'];user=store.user(token)
            self.assertEqual(store.bind(user,credentials['bindingCode'],'团团'),'pet-test')
            subprocess.run([sys.executable,'tools/manage.py','--db',str(db),'backup',str(backup)],check=True,capture_output=True)
            restored=Store(backup)
            self.assertEqual(restored.device(credentials['deviceToken']),'pet-test')
            self.assertEqual(restored.user(token),user)
            self.assertEqual(restored.owned(user,'pet-test')['name'],'团团')
            # Refuse overwrites to preserve both old backups and private provisioning files.
            result=subprocess.run([sys.executable,'tools/manage.py','--db',str(db),'backup',str(backup)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
