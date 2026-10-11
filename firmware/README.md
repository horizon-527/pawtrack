# 固件待硬件联调
现有 `espidf/` 中的固件源码已通过 ESP32-S3 编译，但尚无实体板烧录/运行验收。以厂商 ESP-IDF 示例验证串口、SIM/APN、GNSS，再实现 docs/protocol.md。
必须：仅上报有效定位，携带采集时间；断网有限缓存；消息序号与重传去重；指数退避；密钥每设备独立；TLS 验证；电量需校准。
模式命令、休眠和寻找模式响应时间在供电验证后实现，不能仅靠小程序开关假装已控制设备。

## 已实现的桌面参考组件
`nmea.py` 校验 RMC 校验和、有效定位标记、坐标与 UTC 采集时间；支持 GPRMC / GNRMC。
`python3 tools/nmea_replay.py path/to/serial.log --battery 80` 可把厂商 GNSS 示例导出的日志上传到本地服务。电量参数须来自测量，NMEA 本身不提供电量。
该流程只是桌面日志联调，并非项圈独立联网。日志中的旧点保留原时间，不伪装成实时。
断网持久化队列参考实现见 tools/outbox.py，后续移植到 ESP32 闪存并验证写入寿命和容量。
厂商 GNSS / HTTP 示例：https://docs.waveshare.com/ESP32-S3-SIM7670G-4G/ESP-IDF
