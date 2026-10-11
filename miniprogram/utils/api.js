const config = require('../config');
function session() { return wx.getStorageSync('pawtrack-session') || null; }
function clear() { wx.removeStorageSync('pawtrack-session'); }
function request(path, {method = 'GET', data, anonymous = false} = {}) {
  const stored = session();
  const header = {'Content-Type': 'application/json'};
  if (!anonymous && stored) header.Authorization = 'Bearer ' + stored.token;
  return new Promise((resolve, reject) => wx.request({
    url: config.apiBase + path, method, data, header, timeout: 10000,
    success(response) {
      if (response.statusCode >= 200 && response.statusCode < 300) return resolve(response.data);
      if (response.statusCode === 401 && !anonymous) clear();
      const error = new Error(response.data && typeof response.data.detail === 'string' ? response.data.detail : '请求失败，请稍后重试');
      error.status = response.statusCode;
      reject(error);
    }, fail: () => reject(new Error('连接失败，请检查网络'))
  }));
}
async function login() {
  const code = await new Promise((resolve, reject) => wx.login({
    success: result => result.code ? resolve(result.code) : reject(new Error('微信登录失败')),
    fail: () => reject(new Error('微信登录失败'))
  }));
  const result = await request('/v1/auth/wechat', {method: 'POST', data: {code}, anonymous: true});
  wx.setStorageSync('pawtrack-session', result);
  return result;
}
function dayRange(date) {
  const start = new Date(date + 'T00:00:00+08:00').getTime() / 1000;
  return {start, end: start + 86400};
}
async function track(device, date) {
  const {start, end} = dayRange(date);
  let after = 0, points = [], truncated = false;
  do {
    const result = await request(`/v1/devices/${encodeURIComponent(device)}/track?start=${start}&end=${end}&after=${after}`);
    points.push(...result.points);
    after = result.nextCursor;
    if (points.length >= 10000 && after !== null) { truncated = true; break; }
  } while (after !== null);
  points.sort((a, b) => a.capturedAt - b.capturedAt || a.sequence - b.sequence);
  return {points, truncated};
}
module.exports = {request, login, session, clear, dayRange, track};
