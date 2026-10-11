import wx
app=wx.App(False)
import pcbnew as p,math
from pathlib import Path
path=str(Path(__file__).resolve().parents[1]/'cad/pawtrack.kicad_pcb');b=p.LoadBoard(path);ground=b.FindNet('GND');placed=[]
def distance(pos,a,bb):
 x,y=pos.x,pos.y;dx,dy=bb.x-a.x,bb.y-a.y
 t=max(0,min(1,((x-a.x)*dx+(y-a.y)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
 return math.hypot(x-a.x-t*dx,y-a.y-t*dy)
def safe(pos):
 for f in b.GetFootprints():
  for pd in f.Pads():
   box=pd.GetBoundingBox();box.Inflate(p.FromMM(.36 if pd.GetNetCode()==ground.GetNetCode() else .44))
   if box.Contains(pos):return False
 for tr in b.GetTracks():
  if isinstance(tr,p.PCB_VIA):
   if distance(pos,tr.GetPosition(),tr.GetPosition())<tr.GetWidth(p.F_Cu)/2+p.FromMM(.44):return False
  elif tr.GetNetCode()!=ground.GetNetCode() and distance(pos,tr.GetStart(),tr.GetEnd())<tr.GetWidth()/2+p.FromMM(.44):return False
 for f in b.GetFootprints():
  for z in f.Zones():
   if z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Contains(pos):return False
 return True
for z in b.Zones():
 if z.GetNetname()!='GND' or z.GetLayer() not in [p.F_Cu,p.B_Cu]:continue
 pol=z.GetFill(z.GetLayer())
 for i in range(pol.OutlineCount()):
  vias=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetCode()==ground.GetNetCode()]
  if any(pol.Contains(t.GetPosition(),i) for t in vias):continue
  bb=pol.Outline(i).BBox();found=False
  for x in range(bb.GetX()+p.FromMM(.2),bb.GetRight(),p.FromMM(.2)):
   for y in range(bb.GetY()+p.FromMM(.2),bb.GetBottom(),p.FromMM(.2)):
    pos=p.VECTOR2I(x,y)
    if pol.Contains(pos,i) and safe(pos):
     v=p.PCB_VIA(b);v.SetPosition(pos);v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.25));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(ground);b.Add(v);placed.append((p.ToMM(x),p.ToMM(y)));found=True;break
   if found:break
  print('island',z.GetLayer(),i,'found',found)
print('Added',placed)
p.SaveBoard(path,b)
