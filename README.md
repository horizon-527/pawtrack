# PawTrack
宠物独立联网定位器与微信小程序。当前为本地开发原型，未连接实体硬件、未部署、未进行微信真机验收。

## 本地体验
1. `python3 server/app.py` 启动仅监听本机的开发服务。
2. `python3 tools/simulate.py` 持续上传模拟轨迹。
3. 微信开发者工具导入 `miniprogram/`，使用自己的测试 AppID；本地调试关闭合法域名校验。打开小程序首页，默认模拟模式可直接看演示，关闭模拟开关后连接本地服务。
4. `node tests/test_location.js` 验证地图转换与轨迹缺口。
5. `python3 -m unittest discover -s tests` 验证接口。

本地 API 的开发令牌是 `local-viewer` / `local-device`，只用于本地。禁止直接对公网开放此服务。手机真机无法使用电脑的 127.0.0.1。

## 文档
- [产品与实施计划](docs/plan.md)
- [硬件采购与测试](hardware/README.md)
- [接口协议](docs/protocol.md)
- [正式上线清单](docs/release.md)

当前完成：本地数据接收、SQLite 存储、最新位置、最近 24 小时轨迹、小程序原型、模拟设备、自动化测试。
待完成：真实设备固件、实测续航、微信登录与绑定、线上部署、坐标转换实地验收、项圈结构与真机验收。

## 本轮增强
支持 bootId 与序号联合去重、冲突重传拒绝、WGS84 地图转换、轨迹缺口断线、持久化模拟器断网重传。配置小程序服务地址见 `miniprogram/config.js`；服务令牌可通过 PAWTRACK_DEVICE_TOKEN / PAWTRACK_VIEWER_TOKEN 环境变量设置。
