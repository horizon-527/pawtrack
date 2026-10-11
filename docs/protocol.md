# 本地原型协议 v0
所有开发接口固定设备 demo-pet。
POST /api/positions，Authorization: Bearer local-device
JSON：deviceId=demo-pet, sequence（非负整数）, capturedAt（Unix 秒）, latitude, longitude, battery（0–100）。新增 bootId（1–64 位字母、数字、下划线或短横线），每次重启生成新值；同 bootId + sequence 重传去重，内容冲突返回 409。省略 bootId 的旧客户端归入 legacy。
GET /api/latest 和 /api/track，Authorization: Bearer local-viewer
GET /health 无授权，只返回服务存活。
坐标必须附带 coordinateSystem（wgs84 或 gcj02）；原型最新位置返回 ageSeconds、stale（采集时间超过 120 秒）、receivedAt。轨迹只返回最近 24 小时按采集时间排序的最多 2000 点。
模拟器故意上传 gcj02 演示坐标以直接显示地图；真实 GNSS 必须上传 wgs84。小程序展示边界使用 eviltransform 将 wgs84 转换为 GCJ02；数据库保留原始坐标。已验证上游参考点，真实地标仍需实测。轨迹间隔超过 10 分钟断开绘制。
