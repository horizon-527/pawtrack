"""Run the project's local verification suite from one command."""
from pathlib import Path
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=root,check=True)
for file in ('test_location.js','test_miniprogram.js','test_v1_miniprogram.js','test_session.js'):
    subprocess.run(['node','tests/'+file],cwd=root,check=True)
for file in (root/'miniprogram').rglob('*.js'):
    subprocess.run(['node','--check',str(file)],cwd=root,check=True)
compiler=shutil.which('clang') or shutil.which('gcc')
if compiler is None: raise SystemExit('C compiler required for firmware core verification')
(root/'work').mkdir(exist_ok=True)
subprocess.run([compiler,'-Wall','-Wextra','-Werror','-Ifirmware/espidf/main','firmware/espidf/main/tracker_core.c',
                'tests/test_tracker_core.c','-lm','-o','work/test_tracker_core'],cwd=root,check=True)
subprocess.run([str(root/'work/test_tracker_core')],check=True)
subprocess.run(['git','diff','--check'],cwd=root,check=True)
print('All local checks passed. Entity hardware, WeChat auth and public deployment still need external verification.')
