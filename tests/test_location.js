const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const wechatModule = {exports: {}};
vm.runInNewContext(fs.readFileSync(require.resolve('../miniprogram/vendor/eviltransform'), 'utf8'), {module: wechatModule});
assert.equal(typeof wechatModule.exports.wgs2gcj, 'function', 'WeChat loader has module but no exports binding');
const {mapPoint, segments} = require('../miniprogram/utils/location');
// Upstream reference fixture, Shanghai. This is not a real-world accuracy test.
const result = mapPoint({latitude:31.1774276, longitude:121.5272106, coordinateSystem:'wgs84'});
assert(Math.abs(result.latitude - 31.17530398364597) < 1e-6);
assert(Math.abs(result.longitude - 121.531541859215) < 1e-6);
assert.deepStrictEqual(mapPoint({...result, coordinateSystem:'gcj02'}), result);
assert.deepStrictEqual(mapPoint({latitude:40, longitude:-74, coordinateSystem:'wgs84'}), {latitude:40, longitude:-74});
assert.throws(() => mapPoint({latitude:1, longitude:2, coordinateSystem:'bad'}));
const points = [0,10,1000,1010].map(capturedAt => ({...result, capturedAt, coordinateSystem:'gcj02'}));
assert.equal(segments(points).length, 2);
console.log('Coordinate and route gap checks passed');
