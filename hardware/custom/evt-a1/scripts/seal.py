"""Seal already verified delivery files. Does not claim manufacture approval."""
from pathlib import Path
import hashlib, json, subprocess, sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'scripts/verify.py')],check=True)
files={}
for f in sorted(root.rglob('*')):
    if not f.is_file() or '__pycache__' in f.parts or f.suffix in ['.pyc','.kicad_prl','.lck'] or f.name in ['files.sha256.json','config.lua']:continue
    files[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()
(root/'files.sha256.json').write_text(json.dumps(dict(revision='EVT-A1',release='HOLD',algorithm='SHA256',files=files),ensure_ascii=False,indent=2)+'\n')
print('Sealed',len(files),'engineering files; physical validation still pending')
