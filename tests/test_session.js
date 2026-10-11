const assert = require('assert');
let stored = {token: 'expired', expiresAt: Date.now() / 1000 - 1};
let pending;
global.wx = {getStorageSync: () => stored, removeStorageSync: () => {stored = null;}, request: options => {pending = options;}};
const api = require('../miniprogram/utils/api');
assert.equal(api.session(), null);
stored = {token: 'older-session', expiresAt: Date.now() / 1000 + 3600};
const request = api.request('/v1/devices');
stored = {token: 'newer-session', expiresAt: Date.now() / 1000 + 3600};
pending.success({statusCode: 401, data: {detail: 'expired'}});
request.catch(error => {
  assert.equal(error.status, 401);
  assert.equal(api.session().token, 'newer-session', 'late 401 must preserve a newer login');
  console.log('Session expiry and late authentication response checks passed');
});
