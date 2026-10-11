"""Keep signal routing on outer layers; power planes are not blindly treated as solid.
Parses complete plane expressions (they can span lines). Never delete partial DSN nodes.
"""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'cad/pawtrack.dsn'
s=p.read_text().replace('(layer In1.Cu\n      (type signal)', '(layer In1.Cu\n      (type power)').replace('(layer In2.Cu\n      (type signal)', '(layer In2.Cu\n      (type power)')
index=0
while True:
    start=s.find('(plane ',index)
    if start<0:break
    depth=0
    for end in range(start,len(s)):
        depth+=(s[end]=='(')-(s[end]==')')
        if depth==0:break
    node=s[start:end+1]
    if '(plane SYS ' in node or '(plane BAT ' in node:
        s=s[:start]+s[end+1:];index=start
    else:index=end+1
assert s.count('(place ')==71
p.write_text(s)
