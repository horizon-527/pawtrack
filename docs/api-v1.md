# API v1

所有时间为 Unix 秒；所有接口使用 JSON，响应禁止缓存。用户与设备分别使用独立 Bearer 令牌，不可混用。默认保留 30 天轨迹。

| 方法与路径 | 身份 | 请求/返回 |
|---|---|---|
| POST /v1/auth/wechat | 无 | code → 服务端交换微信 openid → token、expiresAt |
| POST /v1/auth/logout | 用户会话 | 204，撤销当前会话 |
| POST /v1/devices/bind | 用户 | code、name → deviceId；一次性绑定码 |
| GET /v1/devices | 用户 | 本人的 id、name 列表 |
| GET /v1/devices/{id}/snapshot | 所属用户 | 最新有效点、设备在线、当前电量、定位有效性、期望/已应用模式 |
| GET /v1/devices/{id}/track | 所属用户 | start、end（最多一天）、after（默认0）→ points、nextCursor；每页1000点 |
| POST /v1/devices/{id}/mode | 所属用户 | mode=normal/finding → pending-device-ack |
| DELETE /v1/account | 用户 | 删除会话和在线库轨迹、解除设备归属；同时撤销设备密钥，重新绑定需管理员新码与新密钥 |
| POST /v1/device/positions | 设备 | bootId、sequence、capturedAt、latitude、longitude、coordinateSystem、battery（可null） |
| POST /v1/device/heartbeat | 设备 | battery（可null）、fixValid、appliedMode、firmware → desiredMode、reportIntervalSeconds、serverTime |

上报无需传 deviceId，服务器从独立密钥确认设备。未绑定设备不接收位置。普通模式上报目标60秒，寻找模式10秒；等待设备心跳才发送配置，下一次心跳才确认已应用。定位和通信正常时才可能达到目标。
设备消息以 device + bootId + sequence 去重；同编号不同内容返回409，保留队列并排查，不能当作已收到。有效时间窗口为过去30天至未来60秒；旧历史点不更新在线状态。
地图最新有效点与心跳是不同数据；设备在线可能没有卫星定位。180秒未心跳标记离线；位置采集超过120秒标记过期。
轨迹分页按入库序号读取，客户端按采集时间重新排序，以包含断网补传。查询区间[start,end)，小程序按北京时间的自然日查询。
API v1 使用独立数据库，与 server/app.py 的开发数据库互不迁移。

安全边界：当前单实例限流，设备密钥和用户会话在库中只存 SHA256 摘要，微信 AppSecret 只在服务端环境中。公开接口没有模拟微信登录开关。真实微信验证尚待账号联调。
