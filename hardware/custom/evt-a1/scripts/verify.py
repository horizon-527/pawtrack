"""Independent consistency check of final native exports (Python standard library)."""
from pathlib import Path
import csv, hashlib, json, sys, xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
design = json.loads((root/'design.json').read_text())
expected = {c['ref']: c for c in design['components']}
inventory = json.loads((root/'reports/board-inventory.json').read_text())
assert inventory['source_sha256'] == hashlib.sha256((root/'cad/pawtrack.kicad_pcb').read_bytes()).hexdigest(), 'Stale board inventory'
assert inventory['copper_layers'] == 4 and inventory['thickness_mm'] == 1
actual = {c['ref']: c for c in inventory['components']}
assert actual.keys() == expected.keys()
for ref, c in expected.items():
    a = actual[ref]
    for field in ['value', 'mpn', 'x', 'y', 'side', 'populate']:
        assert a[field] == c[field], (ref, field, a[field], c[field])
    assert a['footprint'] == c['footprint'].split(':')[1], ref
    assert {k:v for k,v in a['pins'].items() if v} == {k:v for k,v in c['pins'].items() if v}, (ref, 'PCB net mismatch')
netlist = ET.parse(root/'reports/netlist.xml').getroot()
native = {c.attrib['ref']: c for c in netlist.find('components') if not c.attrib['ref'].startswith('#')}
assert native.keys() == expected.keys()
connections = {}
for net in netlist.find('nets'):
    if net.attrib['name'].startswith('unconnected-'): continue
    for node in net.findall('node'):
        if not node.attrib['ref'].startswith('#'):
            connections[node.attrib['ref'], node.attrib['pin']] = net.attrib['name']
assert connections == {(ref,pin):net for ref,c in expected.items() for pin,net in c['pins'].items() if net}, 'Schematic net mismatch'
for ref, c in expected.items():
    assert native[ref].findtext('value') == c['value'], ref
    assert native[ref].findtext('footprint') == 'PawTrack:'+c['footprint'].split(':')[1], ref
    assert next(f.text for f in native[ref].find('fields') if f.attrib['name']=='MPN') == c['mpn'], ref
with (root/'manufacturing/bom.csv').open() as f: bom = {c['Reference']:c for c in csv.DictReader(f)}
assert bom.keys() == expected.keys()
for ref,c in expected.items():
    row = bom[ref]
    assert (row['MPN'],row['Value'],row['Footprint'],row['Populate'],row['Side']) == (c['mpn'],c['value'],c['footprint'],str(int(c['populate'])),c['side']), ref
with (root/'manufacturing/placements.csv').open() as f: placements = {c['Ref']:c for c in csv.DictReader(f)}
assert placements.keys() == {ref for ref,c in expected.items() if c['populate']}
for ref,c in placements.items():
    e = expected[ref]
    assert float(c['PosX']) == e['x'] and float(c['PosY']) == -e['y'], ref
    assert c['Package'] == e['footprint'].split(':')[1] and c['Val'] == e['value'], ref
    assert c['Side'] == ('bottom' if e['side']=='B' else 'top'), ref
    # KiCad bottom rotation includes its flip; compare with actual board, not a guessed machine convention.
    assert abs((float(c['Rot'])-actual[ref]['rotation']) % 360) < 1e-6, (ref,'rotation')
drc = json.loads((root/'reports/drc.json').read_text())
assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
erc = json.loads((root/'reports/erc.json').read_text())
assert all(not s['violations'] for s in erc['sheets'])
gerbers = list((root/'manufacturing/gerber').glob('*'))
assert len([f for f in gerbers if f.suffix != '.gbrjob']) == 11
for f in gerbers:
    assert f.stat().st_size > 100, f
for kind in ['PTH','NPTH']:
    f = root/f'manufacturing/drill/pawtrack-{kind}.drl'
    assert 'M48' in f.read_text() and 'M30' in f.read_text(), f
with (root/'acceptance.csv').open() as f: acceptance = list(csv.DictReader(f))
assert len(acceptance) == 36 and all(c['状态']=='NOT_RUN' for c in acceptance)
if '--manifest' in sys.argv:
    manifest = json.loads((root/'files.sha256.json').read_text())
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, ('Modified/stale delivery file',name)
print(f'PASS: {len(expected)} parts, {len(placements)} fitted placements, native schematic/PCB/BOM nets and metadata; 11 Gerbers + PTH/NPTH; ERC/DRC/parity zero; 36 physical tests pending')
