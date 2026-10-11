from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2]
f=ROOT/'cad/pawtrack.kicad_pcb';b=p.LoadBoard(str(f))
print('Import session',p.ImportSpecctraSES(b,str(ROOT/'routing/pawtrack.ses')))
# Ground stitching uses conservative pad envelopes plus exact trace distance.
# All vias are off-pad, no filled/capped via-in-pad process assumed.
import math
ground=b.FindNet('GND');placed=[]
def distance(pos,a,bb):
    x,y=pos.x,pos.y;dx,dy=bb.x-a.x,bb.y-a.y
    t=max(0,min(1,((x-a.x)*dx+(y-a.y)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-a.x-t*dx,y-a.y-t*dy)
def safe(pos):
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            box=pd.GetBoundingBox();box.Inflate(p.FromMM(.52))
            if box.Contains(pos):return False
    for tr in b.GetTracks():
        if isinstance(tr,p.PCB_VIA):
            if distance(pos,tr.GetPosition(),tr.GetPosition())<tr.GetWidth(p.F_Cu)/2+p.FromMM(.52):return False
        elif tr.GetNetCode()!=ground.GetNetCode():
            if distance(pos,tr.GetStart(),tr.GetEnd())<tr.GetWidth()/2+p.FromMM(.52):return False
    for fp in b.GetFootprints():
        for z in fp.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Contains(pos):return False
    return True
def put(x,y):
    pos=p.VECTOR2I(p.FromMM(x),p.FromMM(y))
    if not safe(pos):return False
    v=p.PCB_VIA(b);v.SetPosition(pos);v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(ground);b.Add(v);placed.append(pos);return True
for fp in b.GetFootprints():
    for pd in fp.Pads():
        if pd.GetNetCode()!=ground.GetNetCode():continue
        pos=pd.GetPosition();x,y=p.ToMM(pos.x),p.ToMM(pos.y)
        if any(distance(pos,v,v)<p.FromMM(1.8) for v in placed):continue
        found=False
        for r in [1,1.4,1.8,2.2]:
            for angle in range(0,360,30):
                xx=x+r*math.cos(math.radians(angle));yy=y+r*math.sin(math.radians(angle))
                if 1<xx<63 and 1<yy<45 and put(xx,yy):found=True;break
            if found:break
for x,y in [(10,4),(19,4),(42,3),(51,4),(58,12),(60,24),(40,42),(5,17),(35,38)]:put(x,y)
print('Safe ground stitching vias',len(placed))
b.GetDesignSettings().SetBoardThickness(p.FromMM(1.0))
p.SaveBoard(str(f),b)
