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
