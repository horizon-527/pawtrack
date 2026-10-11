# Third-party software

The vendored `miniprogram/vendor/eviltransform.js` is from
https://github.com/googollee/eviltransform at commit
`03ba58d92dfda57f8a1635f3805483c8fc10bd77`.
Its BSD license is retained alongside the source in `eviltransform.LICENSE`.
PawTrack modifies only the export initialization to use `module.exports` explicitly for WeChat's module loader, which does not provide the Node.js `exports` parameter. Coordinate algorithms are unchanged.
Reference coordinate fixtures in `tests/test_location.js` are from the same upstream.
This approximate conversion is used only at the map display boundary; original coordinates remain unchanged.
On-device ground-truth accuracy and geographic boundary behavior still require field verification.

The deployment image builds SQLite 3.53.0 from the official amalgamation and verifies the SHA3-256 published at https://www.sqlite.org/releaselog/3_53_0.html. This version includes the WAL-reset fix. SQLite is public domain: https://www.sqlite.org/copyright.html. Build tools and source stay in the build stage; only the runtime library is copied into the application image.
