"""Recheck and export the existing ROUTED board. Never runs design.py.
Usage: python export.py --cli /path/to/kicad-cli --pcb-python /path/to/python-with-pcbnew
"""
from pathlib import Path
import argparse, subprocess, sys
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli',default='kicad-cli')
parser.add_argument('--pcb-python',default=sys.executable)
args=parser.parse_args()
def run(*command): subprocess.run([args.cli,*map(str,command)],check=True)
pcb=root/'cad/pawtrack.kicad_pcb';sch=root/'cad/pawtrack.kicad_sch'
m=root/'manufacturing';pre=root/'previews';reports=root/'reports'
for directory in [m/'gerber',m/'drill',pre,reports]:directory.mkdir(exist_ok=True)
run('sch','erc','--severity-all','--format','json','--exit-code-violations','-o',reports/'erc.json',sch)
run('pcb','drc','--schematic-parity','--severity-all','--format','json','--refill-zones','--save-board','--exit-code-violations','-o',reports/'drc.json',pcb)
run('sch','export','netlist','--format','kicadxml','-o',reports/'netlist.xml',sch)
run('pcb','export','gerbers','-o',str(m/'gerber')+'/', '-l','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts','--subtract-soldermask',pcb)
run('pcb','export','drill','-o',str(m/'drill')+'/', '--format','excellon','--excellon-units','mm','--excellon-separate-th','--generate-map','--map-format','svg','--generate-report',pcb)
run('pcb','export','pos','-o',m/'placements.csv','--format','csv','--units','mm','--side','both','--smd-only','--exclude-dnp',pcb)
for name,layers in [('pcb-top','F.Cu,F.Fab,Edge.Cuts'),('pcb-bottom','B.Cu,B.Fab,Edge.Cuts')]:
    run('pcb','export','svg','-o',pre/(name+'.svg'),'--layers',layers,'--mode-single','--page-size-mode','2','--exclude-drawing-sheet',*(['--mirror'] if name.endswith('bottom') else []),pcb)
run('sch','export','svg','-o',str(pre)+'/',sch)
subprocess.run([args.pcb_python,str(root/'scripts/inventory.py')],check=True)
subprocess.run([sys.executable,str(root/'scripts/verify.py')],check=True)
print('PASS: native ERC/DRC/parity, all manufacturing exports and independent consistency check')
