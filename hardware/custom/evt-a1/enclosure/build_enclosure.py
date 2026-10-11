#!/usr/bin/env python3
"""Construct prototype shells by exact solid boolean operations (millimetres).
STL and SCAD generated from shared primitives, no hand-edited meshes.
"""
from pathlib import Path
import json,math
import trimesh
ROOT=Path(__file__).resolve().parent
W,H=74,56
# Nodes represent actual CSG; reference envelopes are excluded from print exports.
def box(size,center):return {'box':size,'center':center}
def cyl(radius,height,center):return {'cylinder':radius,'height':height,'center':center}
def union(*nodes):return {'union':list(nodes)}
def difference(a,*b):return {'difference':[a,*b]}
def rounded(w,h,z,center,r):
 x,y,zz=center
 return union(box([w-2*r,h,z],center),box([w,h-2*r,z],center),*[cyl(r,z,[x+sx*(w/2-r),y+sy*(h/2-r),zz]) for sx in [-1,1] for sy in [-1,1]])
def mesh(node):
 if 'box' in node:m=trimesh.creation.box(node['box']);m.apply_translation(node['center']);return m
 if 'cylinder' in node:m=trimesh.creation.cylinder(node['cylinder'],node['height'],sections=64);m.apply_translation(node['center']);return m
 if 'union' in node:return trimesh.boolean.union([mesh(n) for n in node['union']],engine='manifold')
 if 'difference' in node:return trimesh.boolean.difference([mesh(n) for n in node['difference']],engine='manifold')
def scad(n):
 if 'box' in n:return 'translate(%s) cube(%s,center=true);'%(n['center'],n['box'])
 if 'cylinder' in n:return 'translate(%s) cylinder(r=%s,h=%s,center=true,$fn=64);'%(n['center'],n['cylinder'],n['height'])
 if 'union' in n:return 'union(){'+''.join(scad(c) for c in n['union'])+'}'
 return 'difference(){'+''.join(scad(c) for c in n['difference'])+'}'
# 2mm floor/wall; PCB bottom at z15.0; battery max z9, SIM below PCB max z10.5.
base=difference(rounded(W,H,18,[W/2,H/2,9],4),rounded(70,52,18,[W/2,H/2,11],2))
posts=[cyl(2.5,13,[x,y,8.5]) for x,y in [(8,8),(66,8),(8,48),(66,48)]]
# Integral loops accept 20mm harness webbing; local slot clearance22x3.0.
loops=[difference(rounded(10,30,5,[x,28,4.5],2),box([5,22,7],[x,28,4.5])) for x in [-3,77]]
base=union(base,*posts,*loops)
usb=box([14,16,9],[72,40,17.5])
base=difference(base,usb,*[cyl(1.6,6,[x,y,13]) for x,y in [(8,8),(66,8),(8,48),(66,48)]])
# Lid is in assembly coordinates z18..27; STL also exported flat with lower face z0.
lid=difference(rounded(W,H,9,[37,28,22.5],4),rounded(70,52,7,[37,28,21.5],2),usb)
lid=difference(lid,*[cyl(1.1,12,[x,y,22.5]) for x,y in [(8,8),(66,8),(8,48),(66,48)]],*[cyl(2.2,2,[x,y,26.5]) for x,y in [(8,8),(66,8),(8,48),(66,48)]])
# GNSS patch bonding zone on roof: 25x25 including supplied ground plane.
# Adhesive/mounting vendor-qualified; no screw through ceramic antenna.
models={'base':base,'lid':lid}
report={'units':'mm','release':'ENGINEERING PROTOTYPE / NO IP RATING','outer_body_mm':[W,H,27],'overall_with_loops_mm':[90,H,27],'pcb_offset_mm':[5,5,15],'board_mm':[64,46,1],'battery_envelope_mm':[42,32,7],'battery_bounds_mm':[[14,12,2],[56,44,9]],'sim_bottom_min_z_mm':10.5,'battery_to_sim_min_clearance_mm':1.5,'gnss_roof_zone_mm':[[10,10,21],[35,35,25]],'materials':'PA12 prototype; screws M2; insert OD3.2mm L4mm subject to selected supplier; no sealing claim','parts':{}}
for name,node in models.items():
 m=mesh(node)
 assert m.is_watertight and m.is_volume,(name,m.is_watertight)
 assert len(m.split())==1,(name,'disconnected geometry')
 report['parts'][name]={'watertight':bool(m.is_watertight),'connected_solids':len(m.split()),'volume_mm3':float(m.volume),'triangles':len(m.faces),'bounds':m.bounds.tolist()}
 m.export(ROOT/(name+'-assembly.stl'))
 if name=='lid':m.apply_translation([0,0,-18])
 m.export(ROOT/(name+'-print.stl'))
(ROOT/'enclosure.scad').write_text('// PawTrack EVT A1. Millimetres. Prototyping only; fit and sealing require samples.\npart="assembly";\nif(part=="base" || part=="assembly")'+scad(base)+'\nif(part=="lid")translate([0,0,-18])'+scad(lid)+'\nif(part=="assembly")'+scad(lid)+'\n// Reference PCB and battery (preview only):\n%translate([5,5,15])cube([64,46,1]);\n%translate([14,12,2])cube([42,32,7]);\n')
(ROOT/'mechanical-check.json').write_text(json.dumps(report,indent=2))
# Dimensioned top view, dimensions match CSG and board mounting centres.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="980" height="650" viewBox="-12 -12 98 80"><style>text{font-family:sans-serif;font-size:2px}.d{stroke:#555;stroke-width:.2;fill:none}</style><rect x="0" y="0" width="74" height="56" rx="4" fill="#dde7ef" stroke="#345" stroke-width=".3"/><rect x="5" y="5" width="64" height="46" fill="#238854" opacity=".7"/><rect x="14" y="12" width="42" height="32" fill="#f5ca65" opacity=".5"/><rect x="10" y="10" width="25" height="25" fill="#79b9df" opacity=".5"/>']
for x,y in [(8,8),(66,8),(8,48),(66,48)]:svg.append('<circle cx="%s" cy="%s" r="1.1" fill="white" stroke="#345" stroke-width=".2"/>'%(x,y))
for x in [-8,72]:svg.append('<rect x="%s" y="13" width="10" height="30" rx="2" fill="#dde7ef" stroke="#345" stroke-width=".2"/><rect x="%s" y="17" width="5" height="22" fill="white"/>'%(x,x+2.5))
svg+=['<path class="d" d="M0 -5H74 M0 -7V-3 M74 -7V-3 M80 0V56 M78 0H82 M78 56H82"/><text x="29" y="-6">74 mm</text><text x="81" y="29">56 mm</text><text x="32" y="35">PCB 64 x 46 mm</text><text x="30" y="39">Battery 42 x 32 x 7 MAX</text><text x="5" y="10">GNSS roof clearance</text><text x="2" y="62">Body height 27 mm; USB side opening 16 x 9 mm</text><text x="2" y="66">ENGINEERING PROTOTYPE - physical fit / weight / sealing pending</text></svg>']
(ROOT/'dimensions.svg').write_text(''.join(svg))
print(json.dumps(report['parts'],indent=2))
