#!/usr/bin/env python3
"""EVT A1 connectivity/placement source. Run with KiCad 10 pcbnew Python.
Manufacturing release remains ON HOLD pending review and physical validation.
"""
from pathlib import Path
import csv,json,hashlib,re,uuid,shutil,os
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
WORK=REPO/'work/hardware-design'
LIB=WORK/'kicad-mount/KiCad/KiCad.app/Contents/SharedSupport/footprints'
CAD=ROOT/'cad'; CUSTOM=CAD/'PawTrack.pretty'; CUSTOM.mkdir(exist_ok=True)
components=[]
def add(ref,val,foot,pins,x,y,rot=0,mpn='',pop=True,note='',side='F'):
    components.append(dict(ref=ref,value=val,footprint=foot,pins={str(k):v for k,v in pins.items()},x=x,y=y,rotation=rot,mpn=mpn or val,populate=pop,note=note,side=side))
def passive(ref,val,nets,x,y,rot=0,kind='R',mpn='',pop=True,note=''):
    size='0603_1608Metric'
    if kind=='C': fp='Capacitor_SMD:C_'+size
    elif kind=='L': fp='Inductor_SMD:L_'+size
    else: fp='Resistor_SMD:R_'+size
    add(ref,val,fp,dict(enumerate(nets,1)),x,y,rot,mpn,pop,note)
def uid(key): return str(uuid.uuid5(uuid.NAMESPACE_URL,'pawtrack-evt-a1/'+key))
def pad(n,x,y,w,h,typ='smd',layers='"F.Cu" "F.Paste" "F.Mask"',drill=None):
    return '(pad "%s" %s %s (at %.6f %.6f) (size %.6f %.6f) %s(layers %s))'%(n,typ,'circle' if drill else 'roundrect',x,y,w,h,('(drill %.4f) '%drill if drill else '(roundrect_rratio 0.1) '),layers)
def footprint(name,pads,w,h):
    text='(footprint "%s" (version 20241229) (generator "pawtrack") (layer "F.Cu") (attr smd)\n'%name
    text+='(property "Reference" "REF**" (at 0 %.3f) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'%(-h/2-1)
    text+='(property "Value" "%s" (at 0 %.3f) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'%(name,h/2+1)
    for layer,expand,width in [('F.Fab',0,0.1),('F.CrtYd',.3,.05)]:
        text+='(fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width %.3f) (type default)) (fill none) (layer "%s"))\n'%(-w/2-expand,-h/2-expand,w/2+expand,h/2+expand,width,layer)
    text+='\n'.join(pads)+'\n)\n'
    (CUSTOM/(name+'.kicad_mod')).write_text(text)
# Manufacturer PADS decal imported as coordinates, NOT guessed generic LGA.
asc=next((WORK/'Air780EGH_参考封装20251216').rglob('Air780EGH.asc')).read_text(errors='replace')
block=asc.split('AIR800E          M')[1].split('AIR780E          M')[0]
terms=re.findall(r'^T(-?\d+)\s+(-?\d+)\s+-?\d+\s+-?\d+\s+(\d+)\s*$',block,re.M)
stacks={}
for n,ht,angle,wd in re.findall(r'^PAD (\d+) 5\s*\n-2\s+(\d+)\s+RF\s+([\d.]+)\s+(\d+)',block,re.M):
    w,h=int(wd)/1500000,int(ht)/1500000
    if float(angle)%180: w,h=h,w
    stacks[int(n)]=(w,h)
assert len(terms)==109, len(terms)
modulepads=[]; modulegeom={}
for xx,yy,nn in terms:
    n=int(nn); x,y=int(xx)/1500000,-int(yy)/1500000; w,h=stacks.get(n,stacks[0]); modulegeom[str(n)]=[x,y,w,h]
    modulepads.append(pad(n,x,y,w,h))
footprint('Air780EGH_109',modulepads,15.8,17.7)
# TI RNM0015A p40. Pins 7/8 and 12/13 are merged copper with two identifiers.
tps=[]
for n,y in [(1,-.75),(2,-.25),(3,.25),(4,.75)]: tps.append(pad(n,-1.15,y,.6,.25))
for n,x in [(5,-.725),(6,-.225),(14,-.225),(15,-.725)]: tps.append(pad(n,x,1.4 if n<7 else -1.4,.25,.6))
# U-shaped paired power pads, made from rectangles; all same-net overlap is intentional.
for n,x,y in [(7,.275,1.4),(8,.775,1.4),(12,.775,-1.4),(13,.275,-1.4)]:
    tps.append(pad(n,x,y,.25,.6)); tps.append(pad(n,.525,1.1 if y>0 else -1.1,.75,.25))
for n,y,w,cx in [(9,.5,1.35,.525),(10,0,1.7,.35),(11,-.5,1.35,.525)]: tps.append(pad(n,cx,y,w,.25))
footprint('TPS63070_RNM0015A',tps,2.5,3)
footprint('XFL4020', [pad(1,-1.55,0,1.3,3.6),pad(2,1.55,0,1.3,3.6)],4,4)
# Three-wire protected battery pack: keyed PH, numbered connector is mandatory.
module={1:'GND',2:'GNSS_IN',7:'PWRKEY',9:'BAT_SENSE',10:'GND',11:'SIM_IO_M',12:'SIM_RST_M',13:'SIM_CLK_M',14:'SIM_VDD',15:'RESET_N',16:'CHG_CTRL',96:'TS_SENSE',24:'VDD_EXT',27:'GND',34:'GND',35:'LTE_IN',36:'GND',37:'GND',38:'DBG_RX',39:'DBG_TX',40:'GND',41:'GND',42:'V_MODEM',43:'V_MODEM',45:'GND',46:'GND',47:'GND',48:'GND',59:'USB_DP',60:'USB_DM',61:'VBUS',70:'GND',71:'GND',72:'GND',73:'GND',82:'USB_BOOT',88:'GND',89:'GND',90:'GND',91:'GND',92:'GND',93:'GND',94:'GND',95:'GND',98:'GNSS_VDD',103:'GND'}
add('U1','Air780EGH','PawTrack:Air780EGH_109',module,30,15,mpn='Air780EGH',note='Pin 2/103 document conflict; factory confirmation HOLD')
add('U2','BQ24074RGTR','Package_DFN_QFN:WQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm',{1:'NTC',2:'BAT',3:'BAT',4:'CHG_DISABLE',5:'GND',6:'VBUS',7:None,8:'GND',9:None,10:'SYS',11:'SYS',12:'ILIM',13:'VBUS',16:'ISET',17:'GND'},45,35)
add('U3','TPS63070RNMR','PawTrack:TPS63070_RNM0015A',{1:'GND',2:None,3:'VAUX',4:'GND',5:'FB',7:'V_MODEM',8:'V_MODEM',9:'SW2',10:'GND',11:'SW1',12:'SYS',13:'SYS',14:'REG_EN',15:'GND'},17,35)
add('L1','1uH 5.4A','PawTrack:XFL4020',{1:'SW1',2:'SW2'},21.5,35,90,'XFL4020-102MEC',note='Isat>=5.4A; DCR<=15mohm; no unreviewed substitute')
add('J1','USB-C','Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',{'A1':'GND','A4':'VBUS','A5':'CC1','A6':'USB_DP','A7':'USB_DM','A8':None,'A9':'VBUS','A12':'GND','B1':'GND','B4':'VBUS','B5':'CC2','B6':'USB_DP','B7':'USB_DM','B8':None,'B9':'VBUS','B12':'GND','SH':'GND'},59,35,90,'TYPE-C-31-M-12')
add('J2','Protected LiPo+NTC','Connector_JST:JST_PH_B3B-PH-SM4-TB_1x03-1MP_P2.00mm_Vertical',{1:'BAT',2:'GND',3:'NTC','MP':'GND'},7,35,0,'B3B-PH-SM4-TB(LF)(SN)',note='Pin1 BAT+, pin2 BAT-, pin3 NTC to BAT-; manufacturer must key-match harness')
add('J3','LTE 50ohm','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',{1:'LTE_FEED',2:'GND'},46,8.4,0,'U.FL-R-SMT-1(10)')
add('J4','GNSS active','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',{1:'GNSS_FEED',2:'GND'},14,9.5,180,'U.FL-R-SMT-1(10)')
add('J5','nanoSIM','Connector_Card:nanoSIM_Hinged_CUI_NSIM-2-C',{1:'SIM_VDD',2:'SIM_RST',3:'SIM_CLK',5:'GND',6:None,7:'SIM_IO','SH':'GND','CD':None},47,16,0,'NSIM-2-C',side='B',note='No hot insertion; factory verify exact connector stock drawing')
add('SW1','POWER KEY','Button_Switch_SMD:SW_SPST_SKQG_WithoutStem',{1:'PWRKEY',2:'GND'},9,21,0,'SKQGAKE010')
add('SW2','RESET','Button_Switch_SMD:SW_SPST_SKQG_WithoutStem',{1:'RESET_N',2:'GND'},9,27,0,'SKQGAKE010')
# Charger and regulator decoupling: GRM part numbers are fixed dielectric/voltage.
capmpn={'100nF':'GRM188R71C104KA01D','1uF':'GRM188R61A105KA61D','4.7uF':'GRM188R61A475KE15D','22uF':'GRM21BR60J226ME39L'}
for ref,val,nets,x,y,rot in [('C1','4.7uF',('VBUS','GND'),48.5,32,90),('C2','4.7uF',('BAT','GND'),42,32,90),('C3','22uF',('SYS','GND'),42,38,0),('C4','22uF',('SYS','GND'),13,35,90),('C5','100nF',('SYS','GND'),14.5,32,0),('C6','100nF',('VAUX','GND'),15,38,0),('C7','22uF',('V_MODEM','GND'),23.5,31,0),('C8','22uF',('V_MODEM','GND'),23.5,39,0),('C9','100nF',('V_MODEM','GND'),36,26.5,0),('C10','1uF',('V_MODEM','GND'),33,26.5,0),('C11','100nF',('GNSS_VDD','GND'),14,14,0),('C12','100nF',('SIM_VDD','GND'),20,26,0),('C13','100nF',('BAT_SENSE','GND'),20,21,90)]:
    passive(ref,val,nets,x,y,rot,'C',capmpn[val])
    if val=='22uF': components[-1]['footprint']='Capacitor_SMD:C_0805_2012Metric'
add('C14','100uF 6.3V','Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B',{1:'V_MODEM',2:'GND'},28,32,90,'T520B107M006ATE070',note='Polymer ESR70mohm; polarity positive pad1')
for ref,val,nets,x,y,rot in [('R1','5.1k',('CC1','GND'),53,30,0),('R2','5.1k',('CC2','GND'),53,32,0),('R3','2.55k',('ISET','GND'),47.5,38,90),('R4','3.24k',('ILIM','GND'),42,35,90),('R5','750k',('V_MODEM','FB'),17,40,0),('R6','200k',('FB','GND'),14,40,0),('R7','100k',('SYS','REG_EN'),17,30,0),('R8','330k',('BAT','BAT_SENSE'),19,18,90),('R9','100k',('BAT_SENSE','GND'),19,24,90),('R10','22',('SIM_IO_M','SIM_IO'),21,13,0),('R11','22',('SIM_RST_M','SIM_RST'),21,14.5,0),('R12','22',('SIM_CLK_M','SIM_CLK'),21,16,0),('R13','0',('LTE_IN','LTE_FEED'),41,13,0),('R14','0',('GNSS_VDD','GNSS_BIAS'),16,15.5,0),('R15','10k',('SIM_VDD','SIM_IO'),20,11,0)]:
    value={'5.1k':'5K1','2.55k':'2K55','3.24k':'3K24','750k':'750K','200k':'200K','100k':'100K','330k':'330K','22':'22R','0':'0R','10k':'10K'}[val]
    passive(ref,val,nets,x,y,rot,mpn=('RC0603JR-070RL' if val=='0' else 'RC0603FR-07'+value+'L'))
# RF network follows Air780EGH reference 20260914: 33pF AC block, 47nH bias choke.
passive('C15','33pF',('GNSS_IN','GNSS_FEED'),18,9.5,0,'C','GRM1885C1H330JA01D')
passive('L2','47nH',('GNSS_BIAS','GNSS_FEED'),14,12,90,'L','0603HP-47NXJRW')
for ref,n,x,y in [('C16','LTE_IN',40,10.5),('C17','LTE_FEED',43,10.5),('C18','GNSS_IN',20.5,7),('C19','GNSS_FEED',16,7)]: passive(ref,'DNP tuning',(n,'GND'),x,y,90,'C',pop=False,note='RF engineer tune only; default NOT fitted')
# Independent ESD channels avoid wrong array pin substitutions.
for i,n,x,y in [(1,'USB_DP',54,38),(2,'USB_DM',54,40),(3,'SIM_IO',20,29),(4,'SIM_RST',22,29),(5,'SIM_CLK',24,29)]:
    add('D'+str(i),'ESD','Diode_SMD:D_SOD-882',{1:n,2:'GND'},x,y,0,'PESD5V0S1UL,315' if i<3 else 'PESD3V3S1UL,315')
for i,n,x,y in [(1,'VDD_EXT',30,27),(2,'USB_BOOT',30,29),(3,'DBG_RX',38,29),(4,'DBG_TX',38,31),(5,'GND',30,41),(6,'SYS',10,41),(7,'V_MODEM',26,41),(8,'REG_EN',18,27),(9,'BAT',7,41)]:
    add('TP'+str(i),n,'TestPoint:TestPoint_Pad_D1.0mm',{1:n},x,y,pop=False,mpn='PCB pad',note='DNP/no component; factory jig access')
for i,(x,y) in enumerate([(3,3),(61,3),(3,43),(61,43)],1): add('H'+str(i),'M2 clearance','MountingHole:MountingHole_2.2mm_M2',{},x,y,pop=False,mpn='PCB feature')
# Charger defaults OFF: 5V CE is isolated from 3V GPIO by NMOS.
add('Q1','2N7002','Package_TO_SOT_SMD:SOT-23',{1:'CHG_GATE',2:'GND',3:'CHG_DISABLE'},52,20,0,'2N7002,215')
passive('R16','100k',('VBUS','CHG_DISABLE'),49,20,0,mpn='RC0603FR-07100KL')
passive('R17','100k',('CHG_GATE','GND'),52,23,0,mpn='RC0603FR-07100KL')
passive('R18','1k',('CHG_CTRL','CHG_GATE'),49,23,0,mpn='RC0603FR-071KL')
passive('R19','3.3M',('NTC','TS_SENSE'),15,19,0,mpn='RC0603FR-073M3L')
passive('R20','1M',('TS_SENSE','GND'),12,19,0,mpn='RC0603FR-071ML')
passive('C20','100nF',('TS_SENSE','GND'),15,21.5,0,'C','GRM188R71C104KA01D')
# Placement adjustments from native DRC: keep connector bodies and LGA escape clear.
updates={'C15':(19,9.5,180),'R15':(18,5.5,0),'R20':(10,16.5,0),'R19':(16,27.5,0),'TP8':(4,15,0),'TP6':(12,44,0),'C20':(16,23.5,0),'R16':(48,20,0),'R13':(41,8.4,0),'J3':(46,8.4,0),
 'C16':(39.5,5,90),'C17':(43.5,5,90),'C19':(12,5,90),
 'L2':(14,14,90),'C11':(11,14,0),'R14':(14,17,0),
 'R10':(18,13,0),'R11':(18,15,0),'R12':(18,17,0),
 'R8':(20,20,90),'R9':(20,24,90),'C13':(17,21,90),
 'C12':(20,26.5,0),'TP8':(4,15,0),'TP2':(33,29,0),
 'L1':(21.5,35,270),'R1':(49,28,0),'R2':(49,30,0),
 'D1':(49,40,0),'D2':(49,42,0),'C4':(14,35,90),'C5':(11,42,0),'R4':(41,35,90),'R2':(49,27,0),'R1':(49,25,0),'D1':(51,40,0),
 'C9':(25,3,0),'C10':(28,3,0),'C14':(32,3,0)}
for c in components:
    if c['ref'] in updates:c['x'],c['y'],c['rotation']=updates[c['ref']]
# Real KiCad-native board.
import wx
app=wx.App(False)
import pcbnew as p
mm=p.FromMM
def pt(x,y):return p.VECTOR2I(mm(x),mm(y))
b=p.BOARD(); b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(mm(1.0))
names=sorted({n for c in components for n in c['pins'].values() if n})
netmap={}
for n in names: ni=p.NETINFO_ITEM(b,n);b.Add(ni);netmap[n]=ni
footprints={}
for c in components:
    lib,name=c['footprint'].split(':')
    path=CUSTOM if lib=='PawTrack' else LIB/(lib+'.pretty')
    assert (path/(name+'.kicad_mod')).exists(),str(path/name)
    if lib!='PawTrack': shutil.copy2(path/(name+'.kicad_mod'), CUSTOM/(name+'.kicad_mod'))
    if c['ref']=='L2':
        # Coilcraft 0603HP land-pattern pad height 1.02mm; retain generous 0.875mm pad length.
        copied=CUSTOM/(name+'.kicad_mod')
        copied.write_text(copied.read_text().replace('(size 0.875 0.95)','(size 0.875 1.02)'))
        path=CUSTOM
    f=p.FootprintLoad(str(path),name); f.SetReference(c['ref']); f.SetValue(c['value']);f.SetDNP(not c['populate']);f.SetExcludedFromBOM(False);f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False);f.SetExcludedFromPosFiles(not c['populate']);f.SetFPID(p.LIB_ID('PawTrack',name))
    f.SetPosition(pt(c['x'],c['y']));f.SetOrientationDegrees(c['rotation']);f.SetPath(p.KIID_PATH('/'+uid('root')+'/'+uid(c['ref'])))
    b.Add(f)
    if c['side']=='B': f.Flip(f.GetPosition(),False)
    f.Reference().SetTextSize(pt(.85,.85));f.Reference().SetTextThickness(mm(.1));f.Value().SetVisible(False);f.Reference().SetLayer(p.F_Fab if c['side']=='F' else p.B_Fab)
    for pd in f.Pads():
        n=c['pins'].get(pd.GetNumber());
        if n: pd.SetNet(netmap[n])
    footprints[c['ref']]=f
    # Check all logical pin identifiers exist in actual copper footprint.
    actual={pd.GetNumber() for pd in f.Pads() if pd.GetNumber()}
    unknown=set(c['pins'])-actual
    if unknown: print('PIN MISMATCH',c['ref'],unknown,actual)
for a,bb in [((0,0),(64,0)),((64,0),(64,46)),((64,46),(0,46)),((0,46),(0,0))]:
    e=p.PCB_SHAPE(); e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(pt(*a));e.SetEnd(pt(*bb));e.SetLayer(p.Edge_Cuts);e.SetWidth(mm(.05));b.Add(e)
def loc(ref,num):
    for pd in footprints[ref].Pads():
        if pd.GetNumber()==str(num):return pd.GetPosition()
    raise ValueError((ref,num))
def track(n,a,bb,width=.25,layer=p.F_Cu):
    t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(bb);t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(netmap[n]);b.Add(t)
def link(n,r1,p1,r2,p2,width=.25): track(n,loc(r1,p1),loc(r2,p2),width)
# Critical RF and switching traces are fixed before autorouting, visible in CAD.
link('GNSS_IN','U1',2,'C15',1,.2);link('GNSS_FEED','C15',2,'J4',1,.2)
track('GNSS_IN',pt(20.5,7.775),pt(20.5,9.5),.2)
track('LTE_FEED',pt(43.5,5.775),pt(43.5,8.4),.2)
link('LTE_IN','U1',35,'R13',1,.2);link('LTE_FEED','R13',2,'J3',1,.2)
track('SW1',loc('U3',11),pt(19.5,34.5),.3);track('SW1',pt(19.5,34.5),loc('L1',1),.5)
track('SW2',loc('U3',9),pt(19.5,35.5),.3);track('SW2',pt(19.5,35.5),loc('L1',2),.5)
# Fixed filled/capped vias are present before routing, so other nets avoid them.
def vip(ref,num,net):
    pos=loc(ref,num);v=p.PCB_VIA(b);v.SetPosition(pos);v.SetWidth(mm(.5));v.SetDrill(mm(.25));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(netmap[net]);b.Add(v)
for ref,num,net in [('U1',42,'V_MODEM'),('U1',43,'V_MODEM'),('C7',1,'V_MODEM'),('C8',1,'V_MODEM'),('C9',1,'V_MODEM'),('C10',1,'V_MODEM'),('C14',1,'V_MODEM'),('R5',1,'V_MODEM'),('TP7',1,'V_MODEM'),('C3',1,'SYS'),('C4',1,'SYS'),('C2',1,'BAT'),('J2',1,'BAT'),('R4',2,'GND'),('D3',2,'GND'),('U1',10,'GND'),('J3',2,'GND'),('R20',2,'GND')]:vip(ref,num,net)
v=p.PCB_VIA(b);v.SetPosition(pt(17.525,37.2));v.SetWidth(mm(.5));v.SetDrill(mm(.25));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(netmap['V_MODEM']);b.Add(v)
track('V_MODEM',loc('U3',7),v.GetPosition(),.2)
# Ground planes are filled only after routing; reserve inner1 continuous GND.
for layer in [p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu]:
    z=p.ZONE(b);z.SetLayer(layer);z.SetNet(netmap['V_MODEM' if layer==p.In2_Cu else 'GND']);z.SetLocalClearance(mm(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(mm(.15))
    poly=z.Outline();poly.NewOutline()
    for x,y in [(.3,.3),(63.7,.3),(63.7,45.7),(.3,45.7)]:poly.Append(mm(x),mm(y))
    b.Add(z)
# Copper distribution supplements short signal-width pad necks during LTE bursts.
for net,vertices in [('SYS',[(11,33.3),(48,33.3),(48,42),(11,42)]),('BAT',[(4,28),(46,28),(46,33),(10,33),(10,42),(4,42)])]:
    z=p.ZONE(b);z.SetLayer(p.B_Cu);z.SetNet(netmap[net]);z.SetAssignedPriority(1);z.SetLocalClearance(mm(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(mm(.15))
    poly=z.Outline();poly.NewOutline()
    for x,y in vertices:poly.Append(mm(x),mm(y))
    b.Add(z)
label=p.PCB_TEXT(b);label.SetText('PawTrack EVT-A1 / REVIEW HOLD');label.SetPosition(pt(32,44.5));label.SetTextSize(pt(.85,.85));label.SetTextThickness(mm(.12));label.SetLayer(p.F_SilkS);b.Add(label)
p.SaveBoard(str(CAD/'pawtrack.kicad_pcb'),b)
# Project netclasses plus explicit routing current targets. Inner planes reserved by DSN edit later.
project={'meta':{'filename':'pawtrack.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.5,'min_through_hole_diameter':.25,'min_copper_edge_clearance':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.2,'track_width':.2,'via_diameter':.6,'via_drill':.3},{'name':'Power','clearance':.2,'track_width':.8,'via_diameter':.8,'via_drill':.4},{'name':'RF','clearance':.2,'track_width':.2,'via_diameter':.6,'via_drill':.3}], 'netclass_assignments':{'SYS':'Power','BAT':'Power','V_MODEM':'Power','VBUS':'Power','GNSS_IN':'RF','GNSS_FEED':'RF','LTE_IN':'RF','LTE_FEED':'RF'},'meta':{'version':4}}}
(CAD/'pawtrack.kicad_pro').write_text(json.dumps(project,indent=2))
(CAD/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "PawTrack") (type "KiCad") (uri "${KIPRJMOD}/PawTrack.pretty") (options "") (descr "EVT and KiCad derived footprints")))\n')
# A0 review schematic: each pad is named, explicit net wires and NC markers.
# Embedded native symbols make this file independent of installed symbol libraries.
q=lambda s:json.dumps(str(s),ensure_ascii=False)
symdefs=[]; instances=[]; wires=[]; labels=[]; ncs=[]
for index,c in enumerate(components):
    pins=dict(c['pins'])
    if c['ref']=='U1': pins={str(n):pins.get(str(n)) for n in range(1,110)}
    elif c['ref']=='U2':pins={str(n):pins.get(str(n)) for n in range(1,18)}
    elif c['ref']=='U3':pins={str(n):pins.get(str(n)) for n in range(1,16)}
    # Symbols carry physical pad numbers, electrically passive generic review model.
    # ERC does not certify power electronics; review checklist covers electrical roles.
    height=max(7.62,len(pins)*2.54); name='PawTrack:'+c['ref']
    sd='(symbol %s (pin_names (offset 0.5)) (in_bom yes) (on_board yes) (property "Reference" %s (at 0 4 0) (effects (font (size 1.27 1.27)))) (property "Value" %s (at 0 2 0) (effects (font (size 1.27 1.27)))) (symbol %s (rectangle (start 0 0) (end 28 %.2f) (stroke (width .254) (type default)) (fill (type background)))) (symbol %s '%(q(name),q(c['ref']),q(c['value']),q(c['ref']+'_0_1'),-height,q(c['ref']+'_1_1'))
    for k,(num,n) in enumerate(pins.items()):
        yy=-2.54*(k+1)
        role='passive'
        if c['ref']=='U1':
            if n in ['GND','V_MODEM','VBUS']:role='power_in'
            elif n in ['VDD_EXT','GNSS_VDD','SIM_VDD']:role='power_out'
            elif n in ['PWRKEY','RESET_N','USB_BOOT','BAT_SENSE','TS_SENSE','GNSS_IN','DBG_RX']:role='input'
            elif n in ['SIM_RST_M','SIM_CLK_M','DBG_TX','CHG_CTRL']:role='output'
            elif n in ['USB_DP','USB_DM','SIM_IO_M','LTE_IN']:role='bidirectional'
        if c['ref']=='U2':
            if num in ['8','13','17']:role='power_in'
            elif num=='10':role='power_out'
            elif num in ['1','4','5','6','12','16']:role='input'
        if c['ref']=='U3':
            if num in ['4','10','12']:role='power_in'
            elif num=='7':role='power_out'
            elif num in ['1','5','14','15']:role='input'
        sd+='(pin '+role+' line (at -5.08 %.2f 0) (length 5.08) (name %s (effects (font (size 1 1)))) (number %s (effects (font (size 1 1)))))'%(yy,q(n or 'NC'),q(num))
    symdefs.append(sd+'))')
    if c['ref']=='U1': x,y=63.5,40.64
    else:
        j=index-1; x=146.05+(j%12)*83.82;y=40.64+(j//12)*101.6
    sx=uid(c['ref'])
    inst='(symbol (lib_id %s) (at %.2f %.2f 0) (unit 1) (in_bom yes) (on_board yes) (dnp %s) (uuid %s)'%(q(name),x,y,'no' if c['populate'] else 'yes',sx)
    for prop,val,yy,hide in [('Reference',c['ref'],y-5,False),('Value',c['value'],y-2,False),('Footprint','PawTrack:'+c['footprint'].split(':')[1],y,True),('MPN',c['mpn'],y,True)]:
        inst+='(property %s %s (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) %s))'%(q(prop),q(val),x,yy,'(hide yes)' if hide else '')
    for num in pins:inst+='(pin %s (uuid %s))'%(q(num),uid(c['ref']+'/pin/'+num))
    inst+='(instances (project "pawtrack" (path %s (reference %s) (unit 1)))))'%(q('/'+uid('root')),q(c['ref']))
    instances.append(inst)
    for k,(num,n) in enumerate(pins.items()):
        yy=y+2.54*(k+1); xx=x-5.08
        if n:
            end=xx-12.7
            wires.append('(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid %s))'%(xx,yy,end,yy,uid(c['ref']+'/wire/'+num)))
            labels.append('(global_label %s (shape input) (at %.2f %.2f 0) (effects (font (size 1 1)) (justify left bottom)) (uuid %s))'%(q(n),end,yy,uid(c['ref']+'/label/'+num)))
        else: ncs.append('(no_connect (at %.2f %.2f) (uuid %s))'%(xx,yy,uid(c['ref']+'/nc/'+num)))
# External sources: regulated USB and protected pack; GND return.
symdefs.append('(symbol "PawTrack:PWR_FLAG" (pin_names (offset 0)) (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 2.54 0) (effects (font (size 1 1)))) (property "Value" "PWR_FLAG" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 0) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))')
for i,net in enumerate(['GND','VBUS','BAT']):
    x=63.5;y=355.6+i*7.62;ref='#FLG0'+str(i+1)
    instances.append('(symbol (lib_id "PawTrack:PWR_FLAG") (at %.2f %.2f 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid %s) (property "Reference" "%s" (at %.2f %.2f 0) (effects (font (size 1 1)))) (property "Value" "PWR_FLAG" (at %.2f %.2f 0) (effects (font (size 1 1)) (hide yes))) (pin "1" (uuid %s)) (instances (project "pawtrack" (path "/%s" (reference "%s") (unit 1)))))'%(x,y,uid(ref),ref,x,y-2.54,x,y,uid(ref+'/pin'),uid('root'),ref))
    labels.append('(global_label "%s" (shape input) (at %.2f %.2f 0) (effects (font (size 1 1)) (justify left bottom)) (uuid %s))'%(net,x,y,uid(ref+'/label')))
sch='(kicad_sch (version 20250114) (generator "pawtrack") (uuid %s) (paper "A0") (title_block (title "PawTrack EVT-A1 - ENGINEERING REVIEW / NOT RELEASED") (rev "A1") (comment 1 "Generic pad-numbered review symbols; electrical role/physical tests pending")) (lib_symbols %s) %s %s %s %s (embedded_fonts no))\n'%(uid('root'),'\n'.join(symdefs),'\n'.join(instances),'\n'.join(wires),'\n'.join(labels),'\n'.join(ncs))
(CAD/'pawtrack.kicad_sch').write_text(sch)
(CAD/'PawTrack.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "pawtrack") '+''.join(s.replace('PawTrack:','') for s in symdefs)+')')
(CAD/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "PawTrack") (type "KiCad") (uri "${KIPRJMOD}/PawTrack.kicad_sym") (options "") (descr "Pad-numbered review symbols")))')
(ROOT/'design.json').write_text(json.dumps({'revision':'EVT-A1','release':'HOLD','board':{'width_mm':64,'height_mm':46,'thickness_mm':1,'layers':4},'module_pad_geometry':modulegeom,'components':components},ensure_ascii=False,indent=2))
with (ROOT/'manufacturing/bom.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Reference','Value','MPN','Footprint','Populate','Side','Notes'])
    for c in components:w.writerow([c['ref'],c['value'],c['mpn'],c['footprint'],int(c['populate']),c['side'],c['note']])
print('Wrote',len(components),'components;',len(names),'nets; module pads',len(terms))
# Floating pads are real copper obstacles to router, but stay NC on the saved PCB.
for f in b.GetFootprints():
    for pd in f.Pads():
        if pd.GetNumber() and not pd.GetNetCode() and pd.GetAttribute()==p.PAD_ATTRIB_SMD:
            ni=p.NETINFO_ITEM(b,'NC_'+f.GetReference()+'_'+pd.GetNumber());b.Add(ni);pd.SetNet(ni)
print('DSN export',p.ExportSpecctraDSN(b,str(CAD/'pawtrack.dsn')))
