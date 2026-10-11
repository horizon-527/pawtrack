"""Read final board using KiCad's native pcbnew; never modifies CAD."""
from pathlib import Path
import json, hashlib
import wx
app = wx.App(False)
import pcbnew as p
root = Path(__file__).resolve().parents[1]
source = root / 'cad/pawtrack.kicad_pcb'
board = p.LoadBoard(str(source))
parts = []
for f in board.GetFootprints():
    pins = {}
    for pad in f.Pads():
        net = pad.GetNetname()
        normalized = None if not net or net.startswith('unconnected-') else net
        number = pad.GetNumber()
        if number in pins:
            assert pins[number] == normalized, (f.GetReference(), number)
        pins[number] = normalized
    parts.append(dict(ref=f.GetReference(), value=f.GetValue(), mpn=f.GetFieldText('MPN'),
        footprint=str(f.GetFPID().GetLibItemName()), x=p.ToMM(f.GetPosition().x),
        y=p.ToMM(f.GetPosition().y), rotation=f.GetOrientationDegrees(),
        side='B' if f.GetLayer() == p.B_Cu else 'F', populate=not f.IsDNP(), pins=pins))
report = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    copper_layers=board.GetCopperLayerCount(), thickness_mm=p.ToMM(board.GetDesignSettings().GetBoardThickness()),
    tracks=sum(not isinstance(t, p.PCB_VIA) for t in board.GetTracks()),
    vias=sum(isinstance(t, p.PCB_VIA) for t in board.GetTracks()), components=parts)
(root / 'reports/board-inventory.json').write_text(json.dumps(report, indent=2))
print('Native board inventory:', len(parts), 'footprints;', report['tracks'], 'tracks;', report['vias'], 'vias')
