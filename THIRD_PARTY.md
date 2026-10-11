# Third-party software

The vendored `miniprogram/vendor/eviltransform.js` is from
https://github.com/googollee/eviltransform at commit
`03ba58d92dfda57f8a1635f3805483c8fc10bd77`.
Its BSD license is retained alongside the source in `eviltransform.LICENSE`.
Reference coordinate fixtures in `tests/test_location.js` are from the same upstream.
This approximate conversion is used only at the map display boundary; original coordinates remain unchanged.
On-device ground-truth accuracy and geographic boundary behavior still require field verification.
