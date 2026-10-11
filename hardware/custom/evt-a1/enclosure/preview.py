"""Render actual watertight STL solids; no illustrative generated geometry."""
from pathlib import Path
import numpy as np
import trimesh, cairosvg
root = Path(__file__).resolve().parent
items=[]
for name,offset,color in [('base',0,np.array([76,131,167])),('lid',24,np.array([124,166,191]))]:
    m=trimesh.load(root/(name+'-assembly.stl'),force='mesh')
    assert m.is_watertight and m.is_volume and len(m.split())==1
    vertices=m.vertices.copy();vertices[:,2]+=offset
    transform=np.array([[.866,-.866,0],[.40,.40,-1.]])
    xy=vertices@transform.T
    depth=vertices@np.array([.55,.55,.45])
    for face,normal in zip(m.faces,m.face_normals):
        shade=.48+.52*abs(float(normal@np.array([.4,.3,.866])))
        rgb=np.clip(color*shade,0,255).astype(int)
        points=' '.join(f'{x*6+400:.2f},{y*6+390:.2f}' for x,y in xy[face])
        items.append((float(depth[face].mean()),f'<polygon points="{points}" fill="rgb({rgb[0]},{rgb[1]},{rgb[2]})"/>'))
svg='<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="760"><rect width="1000" height="760" fill="#f5f8fa"/>'
svg+='<text x="35" y="40" font-family="sans-serif" font-size="25">PawTrack EVT-A1 — actual STL / exploded view</text>'
svg+=''.join(item for _,item in sorted(items))
svg+='<text x="35" y="710" font-family="sans-serif" font-size="18">Body 74 × 56 × 27 mm | 20 mm webbing | PA12 prototype</text><text x="35" y="740" font-family="sans-serif" font-size="16">CAD preview. Physical fit, strength, weight and sealing: NOT TESTED.</text></svg>'
(root/'../previews/enclosure.svg').write_text(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to=str(root/'../previews/enclosure.png'))
print('PASS: two STL solids watertight, volume and connected geometry; actual mesh preview exported')
