"""Synchronize KiCad's explicit per-pin no-connect net identities without adding tracks."""
from pathlib import Path
import xml.etree.ElementTree as ET
import wx
app=wx.App(False)
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'cad/pawtrack.kicad_pcb';b=p.LoadBoard(str(path));fps={f.GetReference():f for f in b.GetFootprints()}
xml=ET.parse(ROOT/'reports/netlist.xml')
for net in xml.findall('nets/net'):
 name=net.attrib['name']
 if not name.startswith('unconnected-'):continue
 nodes=net.findall('node');assert len(nodes)==1
 node=nodes[0];ni=p.NETINFO_ITEM(b,name);b.Add(ni)
 for pd in fps[node.attrib['ref']].Pads():
  if pd.GetNumber()==node.attrib['pin']:pd.SetNet(ni)
for tr in b.GetTracks():
 if isinstance(tr,p.PCB_VIA) and tr.GetWidth(p.F_Cu)<p.FromMM(.5):tr.SetWidth(p.FromMM(.5));tr.SetDrill(p.FromMM(.25))
p.SaveBoard(str(path),b)
