# Third-party software

The custom tracker vendors `hardware/custom/evt-a1/firmware/vendor/exgnss.lua`
from openLuat/LuatOS commit `a8783cb623edfe336850e35bb94b35e74e389184`.
Its MIT license is retained in that directory. The original source is unchanged.

Footprints in `hardware/custom/evt-a1/cad/PawTrack.pretty` include copied KiCad
10 libraries under CC BY-SA 4.0 with the KiCad library exception. The full
notice is in `cad/KiCad-LIBRARY-LICENSE.md`; provenance is https://gitlab.com/kicad/libraries/kicad-footprints.
Air780EGH footprint geometry is derived from the manufacturer's public PADS
reference; TPS63070 and XFL4020 land patterns are derived from their manufacturer
drawings. These drawings are engineering references, not represented as PawTrack's
original component specifications. Original vendor PDFs are not redistributed.
The copied KiCad `L_0603_1608Metric` pad height is increased from 0.95 to 1.02mm
for the selected Coilcraft 0603HP part; other copied standard footprint geometry is unchanged.

Design generation uses KiCad 10.0.6 (GPLv3), Freerouting 2.5.0 (GPLv3),
trimesh (MIT), Manifold (Apache-2.0), CairoSVG (LGPLv3), and Lupa (MIT).
These tools are not embedded into the device or redistributed in the delivery zip.

The vendored `miniprogram/vendor/eviltransform.js` is from
https://github.com/googollee/eviltransform at commit
`03ba58d92dfda57f8a1635f3805483c8fc10bd77`.
Its BSD license is retained alongside the source in `eviltransform.LICENSE`.
PawTrack modifies only the export initialization to use `module.exports` explicitly for WeChat's module loader, which does not provide the Node.js `exports` parameter. Coordinate algorithms are unchanged.
Reference coordinate fixtures in `tests/test_location.js` are from the same upstream.
This approximate conversion is used only at the map display boundary; original coordinates remain unchanged.
On-device ground-truth accuracy and geographic boundary behavior still require field verification.

The deployment image builds SQLite 3.53.0 from the official amalgamation and verifies the SHA3-256 published at https://www.sqlite.org/releaselog/3_53_0.html. This version includes the WAL-reset fix. SQLite is public domain: https://www.sqlite.org/copyright.html. Build tools and source stay in the build stage; only the runtime library is copied into the application image.
