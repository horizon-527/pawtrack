const transform = require('../vendor/eviltransform');
function mapPoint(point) {
  if (!point || !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) throw new Error('无效坐标');
  if (point.coordinateSystem === 'gcj02') return {latitude: point.latitude, longitude: point.longitude};
  if (point.coordinateSystem !== 'wgs84') throw new Error('未知坐标系');
  const result = transform.wgs2gcj(point.latitude, point.longitude);
  return {latitude: result.lat, longitude: result.lng};
}
function segments(points, gapSeconds = 600) {
  const lines = []; let current = []; let previous;
  for (const point of points) {
    if (previous && point.capturedAt - previous.capturedAt > gapSeconds) {
      if (current.length > 1) lines.push(current);
      current = [];
    }
    current.push(mapPoint(point)); previous = point;
  }
  if (current.length > 1) lines.push(current);
  return lines;
}
module.exports = {mapPoint, segments};
