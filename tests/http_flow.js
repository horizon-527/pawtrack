// Test-only wx adapter: real HTTP transport, no change to production authentication.
const assert = require('assert');
const fs = require('fs');
const credentials = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = process.env.PAWTRACK_TEST_BASE;
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(base), 'test transport must stay on loopback');
require('../miniprogram/config').apiBase = base;
let stored = null, page;
let requests = [];
global.Page = definition => { page = definition; };
global.wx = {
  getStorageSync: () => stored,
  removeStorageSync: () => {stored = null;},
  setStorageSync: (_, value) => {stored = value;},
  login: options => options.success({code: 'test-owner'}),
  showModal: options => options.success({confirm: true}),
  request(options) {
    requests.push(options.url);
    fetch(options.url, {method: options.method || 'GET', headers: options.header,
      body: options.data === undefined ? undefined : JSON.stringify(options.data)})
      .then(async result => options.success({statusCode: result.status,
        data: result.status === 204 ? null : await result.json()}))
      .catch(() => options.fail());
  }
};
require('../miniprogram/pages/index/index');
page.data = {...page.data}; page.active = true;
page.setData = values => Object.assign(page.data, values);
const api = require('../miniprogram/utils/api');
async function call(path, method = 'GET', data, token) {
  const result = await fetch(base + path, {method, headers: {'Content-Type': 'application/json',
    ...(token ? {Authorization: 'Bearer ' + token} : {})},
    body: data === undefined ? undefined : JSON.stringify(data)});
  return {status: result.status, data: result.status === 204 ? null : await result.json()};
}
async function settle() {
  for (let i = 0; i < 500 && page.pendingRevision != null; i++) await new Promise(resolve => setTimeout(resolve, 5));
  assert(page.pendingRevision == null, 'page refresh timed out');
}
(async () => {
  await page.login(); await settle();
  assert(page.data.loggedIn); assert(!page.data.demo); assert.equal(page.data.devices.length, 0);
  const userToken = stored.token;
  for (const [i, device] of credentials.entries()) {
    if (i) page.toggleAdding();
    page.bindingInput({detail: {value: device.bindingCode}});
    page.nameInput({detail: {value: '测试宠物' + i}});
    await page.bindDevice(); await settle();
    assert.equal(page.data.deviceId, device.deviceId);
    assert.equal(page.data.addingDevice, false);
  }
  assert.equal(page.data.devices.length, 2);
  page.selectDevice({detail: {value: '0'}}); await settle();
  const now = Date.now() / 1000;
  const point = {bootId: 'http-test', sequence: 0, capturedAt: now, latitude: 31.2, longitude: 121.4,
    coordinateSystem: 'wgs84', battery: null};
  assert.equal((await call('/v1/device/positions', 'POST', point, credentials[0].deviceToken)).status, 201);
  assert((await call('/v1/device/positions', 'POST', point, credentials[0].deviceToken)).data.duplicate);
  const heartbeat = {battery: null, fixValid: true, appliedMode: 'normal', firmware: 'http-test'};
  await call('/v1/device/heartbeat', 'POST', heartbeat, credentials[0].deviceToken);
  await page.refreshNow();
  assert.equal(page.data.count, 1); assert.equal(page.data.battery, '--'); assert(page.data.online);
  assert.notEqual(page.data.latitude, point.latitude);
  const count = requests.filter(url => url.includes('/track?')).length;
  await page.refresh();
  assert.equal(requests.filter(url => url.includes('/track?')).length, count, 'polling must reuse track cache');
  await page.setMode({currentTarget: {dataset: {mode: 'finding'}}}); await settle();
  assert.equal((await call('/v1/device/heartbeat', 'POST', heartbeat, credentials[0].deviceToken)).data.reportIntervalSeconds, 10);
  await call('/v1/device/heartbeat', 'POST', {...heartbeat, appliedMode: 'finding'}, credentials[0].deviceToken);
  await page.refreshNow();
  assert.equal(page.data.modeText, '设备已确认寻找模式');
  const other = (await call('/v1/auth/wechat', 'POST', {code: 'test-other'})).data.token;
  assert.equal((await call('/v1/devices/pet-one/snapshot', 'GET', undefined, other)).status, 404);
  page.selectDate({detail: {value: '2026-01-01'}}); await settle();
  assert.equal(page.data.count, 0);
  page.selectDevice({detail: {value: '1'}}); await settle();
  assert.equal(page.data.markers.length, 0);
  await page.deleteAccount(); await settle();
  assert.equal(stored, null); assert(page.data.demo);
  assert.equal((await call('/v1/devices', 'GET', undefined, userToken)).status, 401);
  assert.equal((await call('/v1/device/positions', 'POST', point, credentials[0].deviceToken)).status, 401);
  page.stop();
  console.log('Real HTTP + mini-program flow passed: login, two devices, binding, coordinates, cache, mode, history, ownership, deletion');
})().catch(error => {console.error(error); process.exitCode = 1;});
