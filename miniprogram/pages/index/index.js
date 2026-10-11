const config = require('../../config');
const location = require('../../utils/location');
const api = require('../../utils/api');
function today() { return new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); }
function prototypeRequest(path) {
  return new Promise((resolve, reject) => wx.request({url: config.apiBase + path,
    header: {Authorization: 'Bearer ' + config.viewerToken}, timeout: 5000,
    success: r => r.statusCode === 200 ? resolve(r.data) : reject(new Error('接口请求失败')), fail: reject}));
}
Page({
  data: {demo: true, latitude: 31.2304, longitude: 121.4737, markers: [], polyline: [],
    battery: '--', updated: '--', count: 0, status: '模拟演示 · 并非宠物真实位置',
    loggedIn: false, devices: [], deviceIndex: 0, deviceId: '', petName: '演示宠物',
    bindingCode: '', bindingName: '', date: today(), maxDate: today(), online: false,
    desiredMode: 'normal', appliedMode: '', modeText: '尚未收到设备确认', busy: false},
  onShow() {
    this.active = true;
    this.setData({maxDate: today(), loggedIn: config.apiMode === 'prototype' || !!api.session()});
    this.refresh();
    clearInterval(this.timer);
    this.timer = setInterval(() => this.refresh(), config.refreshMs);
  },
  onHide() { this.stop(); }, onUnload() { this.stop(); },
  stop() { this.active = false; clearInterval(this.timer); this.invalidate(); },
  invalidate() { this.revision = (this.revision || 0) + 1; },
  resetMap() { this.setData({markers: [], polyline: [], count: 0, battery: '--', updated: '--', online: false}); },
  toggleDemo(e) {
    this.invalidate(); this.resetMap();
    this.setData({demo: e.detail.value, status: '正在加载', petName: e.detail.value ? '演示宠物' : '我的宠物'});
    if (!e.detail.value && config.apiMode === 'v1' && this.data.loggedIn) this.loadDevices();
    else this.refresh();
  },
  async login() {
    if (this.data.busy) return;
    this.setData({busy: true});
    try {
      await api.login(); this.invalidate();
      this.setData({loggedIn: true, demo: false}); this.resetMap();
      await this.loadDevices();
    } catch (error) { this.setData({status: error.message}); }
    finally { this.setData({busy: false}); }
  },
  async loadDevices() {
    const revision = this.revision || 0;
    try {
      const devices = await api.request('/v1/devices');
      if (!this.active || revision !== (this.revision || 0)) return;
      const index = Math.max(0, devices.findIndex(d => d.id === this.data.deviceId));
      this.setData({devices, deviceIndex: index, deviceId: devices[index] ? devices[index].id : '',
        petName: devices[index] ? devices[index].name : '我的宠物'});
      this.refresh();
    } catch (error) { this.handleError(error); }
  },
  bindingInput(e) { this.setData({bindingCode: e.detail.value}); },
  nameInput(e) { this.setData({bindingName: e.detail.value}); },
  async bindDevice() {
    if (this.data.busy) return;
    const code = this.data.bindingCode.trim();
    if (!code) { this.setData({status: '请输入设备绑定码'}); return; }
    this.setData({busy: true});
    try {
      const result = await api.request('/v1/devices/bind', {method: 'POST', data: {code, name: this.data.bindingName.trim() || '我的宠物'}});
      this.invalidate(); this.resetMap();
      this.setData({deviceId: result.deviceId, bindingCode: '', bindingName: ''});
      await this.loadDevices();
    } catch (error) { this.handleError(error); }
    finally { this.setData({busy: false}); }
  },
  selectDevice(e) {
    const index = Number(e.detail.value), selected = this.data.devices[index];
    if (!selected) return;
    this.invalidate(); this.resetMap();
    this.setData({deviceIndex: index, deviceId: selected.id, petName: selected.name}); this.refresh();
  },
  selectDate(e) { this.invalidate(); this.setData({date: e.detail.value, polyline: [], count: 0}); this.refresh(); },
  async setMode(e) {
    if (this.data.busy || !this.data.deviceId) return;
    this.setData({busy: true});
    const revision = this.revision || 0;
    const deviceId = this.data.deviceId;
    try {
      const result = await api.request(`/v1/devices/${encodeURIComponent(deviceId)}/mode`,
        {method: 'POST', data: {mode: e.currentTarget.dataset.mode}});
      if (!this.active || revision !== (this.revision || 0)) return;
      this.setData({desiredMode: result.desiredMode, modeText: '已请求，等待设备确认'}); this.refresh();
    } catch (error) { this.handleError(error); }
    finally { this.setData({busy: false}); }
  },
  async logout() {
    this.invalidate(); api.request('/v1/auth/logout', {method: 'POST'}).catch(() => {});
    api.clear(); this.resetMap();
    this.setData({loggedIn: false, devices: [], deviceId: '', demo: true, petName: '演示宠物'}); this.refresh();
  },
  async deleteAccount() {
    const result = await new Promise(resolve => wx.showModal({title: '删除账户与轨迹',
      content: '将删除你的定位记录并解除设备归属。重新绑定需要重新生成绑定码。此操作无法撤销。', confirmText: '删除', success: resolve}));
    if (!result.confirm) return;
    try { await api.request('/v1/account', {method: 'DELETE'}); await this.logout(); }
    catch (error) { this.handleError(error); }
  },
  showPrivacy() { wx.navigateTo({url: '/pages/privacy/privacy'}); },
  handleError(error) {
    if (error.status === 401) {
      this.invalidate(); this.resetMap();
      this.setData({loggedIn: false, devices: [], deviceId: '', status: '登录已过期，请重新登录'});
    } else this.setData({status: error.message + ' · 已显示的位置可能过期'});
  },
  async refresh() {
    const revision = this.revision || 0;
    if (this.pendingRevision === revision) return;
    if (!this.data.demo && config.apiMode === 'v1') {
      if (!this.data.loggedIn) { this.setData({status: '请登录并绑定你的设备'}); return; }
      if (!this.data.deviceId) { this.setData({status: '请先使用设备绑定码添加宠物'}); return; }
    }
    this.pendingRevision = revision;
    try {
      let latest, points, snapshot, truncated = false;
      if (this.data.demo) {
        const now = Date.now() / 1000, phase = Math.floor(now / 5) % 240;
        points = Array.from({length: 40}, (_, i) => ({latitude: 31.2304 + .001 * Math.sin((phase - 39 + i) / 20),
          longitude: 121.4737 + .001 * Math.cos((phase - 39 + i) / 20), coordinateSystem: 'gcj02', capturedAt: now - (39-i)*5}));
        latest = {...points[39], battery: 85};
      } else if (config.apiMode === 'prototype') {
        [latest, points] = await Promise.all([prototypeRequest('/api/latest'), prototypeRequest('/api/track')]);
      } else {
        const device = encodeURIComponent(this.data.deviceId);
        const results = await Promise.all([api.request(`/v1/devices/${device}/snapshot`), api.track(this.data.deviceId, this.data.date)]);
        snapshot = results[0]; latest = snapshot.latest; points = results[1].points; truncated = results[1].truncated;
      }
      if (!this.active || revision !== (this.revision || 0)) return;
      if (snapshot) {
        this.setData({online: snapshot.online, desiredMode: snapshot.desiredMode, appliedMode: snapshot.appliedMode || '',
          modeText: snapshot.appliedMode === snapshot.desiredMode ? (snapshot.appliedMode === 'finding' ? '设备已确认寻找模式' : '设备已确认普通模式') : '等待设备确认',
          battery: snapshot.battery === null ? '--' : snapshot.battery});
      }
      if (!latest) { this.setData({status: '尚未收到有效定位', markers: [], polyline: [], count: 0, updated: '--'}); return; }
      const mapLatest = location.mapPoint(latest), lines = location.segments(points);
      const stale = Date.now() / 1000 - latest.capturedAt > 120;
      let status = this.data.demo ? '模拟演示 · 并非宠物真实位置' : stale ? '位置已过期，显示最近有效位置' : '位置已更新';
      if (snapshot && !snapshot.online) status += ' · 设备离线';
      if (snapshot && snapshot.fixValid === false) status += ' · 暂无卫星定位';
      if (truncated) status += ' · 轨迹仅显示前 10000 点';
      this.setData({latitude: mapLatest.latitude, longitude: mapLatest.longitude,
        markers: [{id: 1, latitude: mapLatest.latitude, longitude: mapLatest.longitude,
          callout: {content: this.data.petName, display: 'ALWAYS'}}],
        polyline: lines.map(points => ({points, color: '#245a3c', width: 4})),
        battery: snapshot ? this.data.battery : (latest.battery === null ? '--' : latest.battery),
        updated: new Date(latest.capturedAt * 1000).toLocaleString(), count: points.length, status});
    } catch (error) {
      if (this.active && revision === (this.revision || 0)) this.handleError(error);
    } finally { if (this.pendingRevision === revision) this.pendingRevision = null; }
  }
});
