# 使用与联调排查

| 现象 | 最先检查 | 下一步 |
|---|---|---|
| 首页空白 | 是否导入miniprogram目录并点击编译，是否运行最新版 | 查看调试器错误；当前已修复坐标库小程序导出兼容问题和marker尺寸 |
| 一直是演示路线 | 首页“体验演示”是否关闭 | 真机项目必须由configure_miniprogram工具生成并登录绑定 |
| 微信登录尚未配置 | 服务.env是否填真实AppID和Secret | 重新启动api；AppID与小程序须一致，不在客户端填Secret |
| code失效/登录401 | code是当前wx.login所得还是已复用/游客模拟值 | 使用真实AppID手机重新登录；不要复用一次性code |
| 真机请求失败但开发工具可用 | request合法域名、HTTPS证书、DNS和手机网络 | doctor检查；真机项目开启urlCheck，不能用localhost |
| 绑定码无效 | 是否用bindingCode而非deviceToken、24h过期/已用 | 未绑定设备用binding-code重发，同时更新固件token |
| 设备日志说Configure... | 固件配置是否有域名/token/APN | menuconfig后重新build/flash；空凭证构建只是编译验证 |
| Modem configuration pending | 4G开关、USB路由、AT口、SIM READY、CA文件 | 用AT自检确认；RX17/TX18须匹配当前PCB |
| 室外也没有定位 | GNSS天线是否接对，是否向天空，CGPSINFO是否为空 | 至少等待初始定位；检查GNSS实装和模组版本 |
| 模组有点而服务没点 | 绑定、APN、域名、CA、模组时间、TLS返回 | 先运行doctor，再做四组TLS验收；不能关闭TLS认证 |
| 页面显示在线但位置过期 | heartbeat与GNSS是两个不同状态 | 看fixValid，移动到开阔地；旧坐标不当成新坐标 |
| 页面一直离线 | lastSeen是否超过180s、首次GNSS时间是否取得 | 首次无时间时固件不上传；查电源/4G/证书/服务 |
| 地图偏移数百米 | 原始坐标到底是WGS84还是GCJ02 | 硬件用WGS84，展示转一次；不要预转后再标WGS84 |
| 轨迹少点/断线 | 是否选错日期、10分钟缺口或离线缓存满 | 默认北京日期，30天保留；64点满后丢新点是明确限制 |
| 找寻模式等待确认 | 在线状态及下一次设备心跳 | 设备实际接收后下一心跳确认；网络阻塞可能超过10秒 |
| 电量暂不可用 | 当前固件没有校准电量计 | 正常现象；不要拿模拟器85%当设备电量 |
| 旧点一直重传 | token401、同bootId/sequence内容冲突409 | 按原因修复；未确认不出队，不先擦除缓存 |
| 自动备份unhealthy | backup容器日志、磁盘空间、卷权限 | 10001用户须能写/backups；查看最近备份并恢复演练 |
| 其他用户也频繁429 | 网关是否转发客户地址、api是否误公开端口 | 保持本仓库Compose结构；不直接对公网暴露api |
| flash串口占用 | monitor/AT软件是否同时开着 | 关闭占用软件，识别正确CH343口；按厂家BOOT/RESET流程 |
| 封装后定位差/重启 | 天线遮挡、电源峰值、线材和散热 | 重做室外和电源测试；不要直接进入佩戴 |

查看服务状态：

```sh
docker compose --env-file .env -f deploy/compose.yaml ps
docker compose --env-file .env -f deploy/compose.yaml logs --tail 100 api backup
```

日志不要贴出.env、配置文件、deviceToken、微信会话或完整轨迹。对外排查使用错误类型、状态码、版本和脱敏画面。恢复数据时按运维说明同时停止api和backup，再执行恢复；不要只复制运行中的数据库文件。
