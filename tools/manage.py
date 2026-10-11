"""Offline administration. Secrets are written once to a private file, never printed."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.storage import Store, digest

def private_file(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(data,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',default=os.environ.get('PAWTRACK_DB','data/pawtrack.sqlite3'))
    sub=parser.add_subparsers(dest='command',required=True)
    provision=sub.add_parser('provision'); provision.add_argument('device'); provision.add_argument('--output',required=True)
    renew=sub.add_parser('binding-code'); renew.add_argument('device'); renew.add_argument('--output',required=True)
    backup=sub.add_parser('backup'); backup.add_argument('output')
    cleanup=sub.add_parser('cleanup')
    args=parser.parse_args(); store=Store(args.db)
    if args.command in ('provision','binding-code'):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',args.device): parser.error('invalid device ID')
        if Path(args.output).exists(): parser.error('output already exists; choose a new private path')
        if args.command=='provision': store.provision(args.device,deliver=lambda data:private_file(args.output,data))
        else:
            code=secrets.token_urlsafe(24)
            token=secrets.token_urlsafe(32)
            with store.connection() as con:
                cursor=con.execute('UPDATE devices SET binding_digest=?,binding_expires=?,secret_digest=? WHERE id=? AND owner_id IS NULL',
                                   (digest(code),time.time()+86400,digest(token),args.device))
                if cursor.rowcount!=1: parser.error('device missing or still owned')
                data={'deviceId':args.device,'bindingCode':code,'deviceToken':token}
                private_file(args.output,data)
        print('Private provisioning file created; expires in 24 hours.')
    elif args.command=='backup':
        target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(descriptor)
        destination=sqlite3.connect(target)
        try:
            with store.connection() as source: source.backup(destination)
            destination.execute('PRAGMA journal_mode=DELETE')
        finally: destination.close()
        print('Consistent SQLite backup created.')
    elif args.command=='cleanup': print('Expired positions removed:',store.cleanup())

if __name__=='__main__': main()
