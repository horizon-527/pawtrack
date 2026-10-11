const config = require('../../config');
const API = config.apiBase;
const location = require('../../utils/location');
function request(path) {
  return new Promise((resolve, reject) => wx.request({
    url: API + path, header: {Authorization: 'Bearer ' + config.viewerToken}, timeout: 5000,
    success: r => r.statusCode === 200 ? resolve(r.data) : reject(new Error('接口请求失败')),
    fail: reject
  }));
}
Page({
  data: {demo: true, latitude: 31.2304, longitude: 121.4737, markers: [], polyline: [],
    battery: '--', updated: '--', count: 0, status: '模拟演示 · 并非宠物真实位置'},
  onShow() { this.active = true; this.refresh(); clearInterval(this.timer); this.timer = setInterval(() => this.refresh(), config.refreshMs); },
  onHide() { this.stop(); },
  onUnload() { this.stop(); },
  stop() { this.active = false; clearInterval(this.timer); this.revision = (this.revision || 0) + 1; },
  toggleDemo(e) {
    this.revision = (this.revision || 0) + 1;
    this.setData({demo: e.detail.value, markers: [], polyline: [], count: 0, battery: '--', updated: '--', status: '正在加载'});
    this.refresh();
  },
  async refresh() {
    const revision = this.revision || 0;
    if (this.pendingRevision === revision) return;
    this.pendingRevision = revision;
    try {
      let latest, points;
      if (this.data.demo) {
        const now = Date.now() / 1000;
        points = Array.from({length: 40}, (_, i) => ({latitude: 31.2304 + .001 * Math.sin(i / 12),
          longitude: 121.4737 + .001 * Math.cos(i / 12), coordinateSystem: 'gcj02', capturedAt: now - (39-i)*5}));
        latest = {...points[39], battery: 85, stale: false};
      } else {
        [latest, points] = await Promise.all([request('/api/latest'), request('/api/track')]);
      }
      if (!this.active || revision !== (this.revision || 0)) return;
      if (!latest) { this.setData({status: '尚未收到设备定位', markers: [], polyline: []}); return; }
      const mapLatest = location.mapPoint(latest);
      const lines = location.segments(points);
      this.setData({latitude: mapLatest.latitude, longitude: mapLatest.longitude,
        markers: [{id: 1, latitude: mapLatest.latitude, longitude: mapLatest.longitude,
          callout: {content: this.data.demo ? '演示宠物' : '设备最近位置', display: 'ALWAYS'}}],
        polyline: lines.map(points => ({points, color: '#245a3c', width: 4})), battery: latest.battery,
        updated: new Date(latest.capturedAt * 1000).toLocaleString(), count: points.length,
        status: this.data.demo ? '模拟演示 · 并非宠物真实位置' : latest.stale ? '位置已过期，请检查设备定位和网络' : '本地服务 · 最近位置已更新'});
    } catch (e) {
      if (this.active && revision === (this.revision || 0)) this.setData({status: '连接失败 · 当前显示保留数据，位置可能已过期'});
    } finally { if (this.pendingRevision === revision) this.pendingRevision = null; }
  }
});
