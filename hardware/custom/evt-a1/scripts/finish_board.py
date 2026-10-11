"""Finish only measured CAD issues; rerun native DRC after this operation.
No ERC/DRC exclusions or error-severity reductions are introduced.
"""
from pathlib import Path
import json,wx
app=wx.App(False)
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'cad/pawtrack.kicad_pcb';b=p.LoadBoard(str(path));fps=list(b.GetFootprints())
data=json.loads((ROOT/'design.json').read_text());components={c['ref']:c for c in data['components']}
for f in fps:
 f.SetField('MPN',components[f.GetReference()]['mpn']);f.GetField('MPN').SetVisible(False);f.SetExcludedFromBOM(False)
report=json.loads((ROOT/'reports/drc.json').read_text())
remove={i['uuid'] for v in report['violations'] if v['type']=='via_dangling' for i in v['items']}
for tr in list(b.GetTracks()):
 if tr.m_Uuid.AsString() in remove:b.Delete(tr)
 elif not isinstance(tr,p.PCB_VIA) and tr.GetWidth()<p.FromMM(.15):tr.SetWidth(p.FromMM(.15))
p.SaveBoard(str(path),b)
