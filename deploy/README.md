# 部署与运行

## 本机 v1 联调
```sh
python3 -m venv work/venv
work/venv/bin/pip install -r requirements.lock.txt
work/venv/bin/uvicorn server.production:create_app --factory --host 127.0.0.1 --port 8788 --no-access-log
```
默认不会伪造微信登录。未配置 WECHAT_APP_ID / WECHAT_APP_SECRET 时登录返回 503。
无需登录的模拟体验仍可直接在小程序中使用。

## 配置真实服务
准备已解析至服务器的域名、微信小程序账号与对应 AppID/Secret。把 .env.example 复制为根目录 .env，填入真实值。
```sh
docker compose --env-file .env -f deploy/compose.yaml up -d --build
```
HTTPS 由 Caddy 管理，需要域名可达及 80/443 端口。小程序 config.js 的 apiBase 改为该 HTTPS 域名，在微信后台配置 request 合法域名；开发版 urlCheck=false 改为 true。
服务只支持单实例单 worker + SQLite；扩容前迁移数据库和共享限流。日志不记录访问 URL，避免泄露微信凭证和轨迹。

## 设备初始化（管理员线下操作）
本地：
```sh
work/venv/bin/python tools/manage.py provision pet-001 --output secrets/pet-001.json
```
部署后：
```sh
docker compose --env-file .env -f deploy/compose.yaml exec api python tools/manage.py provision pet-001 --output /data/pet-001.json
```
凭证写入权限为 0600 的文件，不会打印到终端。deviceToken 只用于固件，bindingCode 只用于小程序绑定，默认 24 小时有效。打印/分发绑定码时不要附带设备密钥。
未绑定设备的过期码可用 `binding-code pet-001 --output 新的私有文件路径` 重新生成；同时轮换设备 token，需更新固件。已绑定设备不允许通过此命令转移归属。

## 备份、恢复和删除
`python tools/manage.py backup backups/日期.sqlite3` 使用 SQLite 一致性备份接口；不可用复制活动数据库单文件的方式备份。
定期备份，并将备份放在受限权限的独立位置；建议每天备份，保留 7 天，按实际服务需求安排计划任务。保留策略是运维要求，当前未在未知服务器上创建任务。
恢复时停止 API，把备份放回 PAWTRACK_DB 路径，确保目录可写；重启后进行用户归属和轨迹查询验收。
位置默认保留 30 天，应用启动后每小时清理；账号删除即时删除在线库轨迹与会话，备份在保留周期到期后销毁。

## 已验证与未验证
已验证应用 API、权限、数据持久化、绑定码、模拟设备交互。真实微信交换和公网证书签发仍需真实账号/域名验收。Docker 容器构建结果见 docs/verification.md。
