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
Compose中的backup服务每天执行一次一致性备份，校验完整性后才清理超过7天的PawTrack备份；失败60秒后重试。备份文件0600，目录700，backup容器无网络。SQLite连接只读，但数据卷须可创建WAL辅助文件，不能简单改为只读挂载。维护restore服务默认不启动。
输出备份转换为DELETE日志模式，是可在只读备份卷直接验证和恢复的独立文件；运行中的在线数据库保持WAL。
生产镜像将SQLite固定为3.53.0并校验官方源码SHA3；此版本包含[官方WAL-reset并发问题修复](https://www.sqlite.org/releaselog/3_53_0.html)。本地实测也是3.53.0；本地联调时使用已修复版本，正式运行建议使用仓库Docker镜像。
位置默认保留 30 天，应用启动后每小时清理；账号删除即时删除在线库轨迹与会话，备份在保留周期到期后销毁。

## 已验证与未验证
已验证应用 API、权限、数据持久化、绑定码、模拟设备交互。真实微信交换和公网证书签发仍需真实账号/域名验收。Docker 容器构建结果见 docs/verification.md。

## 自动备份检查与导出
以下命令均在服务器仓库根目录，使用同一.env和Compose文件：
```sh
docker compose --env-file .env -f deploy/compose.yaml ps
docker compose --env-file .env -f deploy/compose.yaml logs --tail 20 backup
docker compose --env-file .env -f deploy/compose.yaml exec backup ls -1 /backups
```
启动后应出现`Backup verified`和`pawtrack-时间.sqlite3`。健康检查要求近25小时有备份，启动期2分钟。备份失败应处理磁盘、卷权限或数据库问题。
同机命名卷备份不能防服务器丢失。定期导出一份到电脑或受限的独立存储；备份包含微信身份和位置，按敏感数据保管：
```sh
mkdir -p backups
chmod 700 backups
docker compose --env-file .env -f deploy/compose.yaml cp backup:/backups/实际文件名.sqlite3 backups/实际文件名.sqlite3
chmod 600 backups/实际文件名.sqlite3
```
通过自己的SSH通道传至独立位置，手动外部副本也按7天保留策略清理。不要使用`down -v`，它会移除数据库和备份卷。

## 恢复演练/真实恢复
先导出当前一致性备份，记下要恢复的文件名。恢复会回到备份时刻，新于备份的记录不会保留。API与备份worker必须同时停止：
```sh
docker compose --env-file .env -f deploy/compose.yaml stop api backup
docker compose --env-file .env -f deploy/compose.yaml run --rm --no-deps restore \
  python tools/restore.py --backup /backups/实际文件名.sqlite3 --confirm-service-stopped
docker compose --env-file .env -f deploy/compose.yaml up -d api backup gateway
```
restore检查数据库完整性、PawTrack表和外键，再移除旧WAL/SHM并替换离线数据库。此操作期间网关暂时返回服务不可用；完成后用doctor、小程序自己的设备列表及日期轨迹验收。第一次应在隔离测试部署上演练。
恢复会还原备份时存在的用户和数据；如备份后发生账户删除，重新执行相应删除要求后再恢复对外服务。每天清理的7天保留策略最多延迟一个备份周期；独立导出副本也要清理。

## 网关与规模
api仅在Compose内部网络监听，网关转发真实来源地址，防止所有登录共用一个限流桶；不要公开8788。初期维持单实例单worker。每设备普通模式理论1440点/天、寻找模式8640点/天，30天约4.32万/25.92万点；这只是采样数量推算，SQLite实际容量用磁盘测量决定。多人、多设备持续压力上升前，做独立负载测试并迁移到共享数据库/限流。
网关固定Let's Encrypt签发和RSA叶证书；当前真实域名证书仍待部署验收。重新签发/换CA后，检查模组信任根仍可验证实际链，必要时更新CA。
