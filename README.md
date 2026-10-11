# PawTrack

宠物独立联网定位器 + 微信小程序。目标：项圈设备获取 GNSS 位置，通过 4G 回传，主人在微信中查看位置和运动轨迹。

**当前状态：软件与可编译硬件原型已建立；尚未完成实体板定位、真实微信登录、公网部署及佩戴验收。**

## 已实现
- 微信小程序地图、实时刷新、按日期查询轨迹、坐标转换、轨迹缺口分段。
- 微信登录接口、设备绑定、用户设备隔离、在线/定位过期状态、寻找模式请求与设备确认。
- FastAPI + SQLite 服务，独立设备密钥、一次性绑定码、会话过期/撤销、限流、数据删除与30天保留。
- ESP-IDF v5.4.2 固件：SIM7670G AT通信、GNSS读取、HTTPS上传、NVS缓存、模式心跳；ESP32-S3构建通过。
- 设备模拟器、GNSS日志回放、设备初始化、备份恢复工具、Docker/Caddy配置、CI。

## 先体验小程序
微信开发者工具导入 `miniprogram/`。默认使用游客 AppID 和模拟路线，明确标记演示数据。演示无需真实硬件、服务器或微信登录。
正式接入必须替换 AppID 和 HTTPS 服务地址；项目未使用其他项目的 AppID 或密钥。

## 本地运行与验证
```sh
python3 -m venv work/venv
work/venv/bin/pip install -r requirements.lock.txt
work/venv/bin/python tools/check.py
work/venv/bin/uvicorn server.production:create_app --factory --host 127.0.0.1 --port 8788 --no-access-log
```
不配置真实微信密钥时，登录返回“尚未配置”，不会伪造用户身份。接口测试使用隔离的微信响应替身，不代表真实微信认证通过。

## 文档入口
- [实施与验收计划](docs/plan.md)
- [硬件采购路线](hardware/README.md)
- [固件配置与烧录](firmware/espidf/README.md)
- [服务部署和备份](deploy/README.md)
- [API v1](docs/api-v1.md)
- [测试记录与待办](docs/verification.md)
- [上线门槛](docs/release.md)
- [开源许可](THIRD_PARTY.md)

## 原始本地原型
`python3 server/app.py`（8787）与 `python3 tools/simulate.py` 为早期本机开发原型；仅监听本机，固定开发令牌，不可公网部署。它的数据库与 v1 独立。
小程序 `config.js` 可切换 apiMode=prototype 且 apiBase 改为8787进行旧版联调；正式流程保持v1。

## 完成产品仍需的外部条件
实体开发板与SIM；小程序AppID/Secret；可部署的服务器/域名；实际定位、TLS证书验证、功耗及佩戴测试。开发板用于桌面验证，不能直接作为宠物项圈成品。
