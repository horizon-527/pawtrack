# ESP32-S3 + SIM7670G 桌面原型固件

这是待实机验收的源码，不能据此宣称续航、佩戴安全或 10 秒实时性已达到。
目标板：Waveshare ESP32-S3-SIM7670G-4G V2 文档示例默认 RX17、TX18、115200；购买版本不同时必须核对原理图。
实现：串口 AT 指令读取 CGPSINFO、转换为 WGS84 十进制度与真实 UTC；GNSS 时间设置模块时钟；TLS1.2 服务器认证、SNI、有效期验证；HTTPS JSON 上报；NVS 64 点环形队列；确认 accepted 后出队；心跳获取模式并更新上报间隔。
不打印密钥或原始坐标。电量未校准，返回 null，不伪造百分比。当前保持 GNSS 开启，无深度休眠，供电测试后才优化。

## 配置、构建、烧录
ESP-IDF v5.4.2，目标 esp32s3：
```sh
cd firmware/espidf
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py -p 实际串口 flash monitor
```
在 PawTrack 配置中填入 HTTPS 域名（无末尾斜线）、独立设备 token、SIM APN、已导入模块的可信 CA 文件名。默认凭证为空，运行时拒绝开始上传。
先在小程序中绑定设备，再运行固件。模块须已上电、正确连接4G/GNSS天线并有可用SIM。

## CA 和通信验证
导入服务证书对应的可信根 CA，不应把随机下载的证书或服务器叶证书当作长期根 CA。
`python3 -m pip install -r requirements-hardware.txt` 后，用 `tools/install_modem_ca.py --port 模块AT串口 --certificate 私有准备的CA.pem` 导入。
这里需要模块自身的 AT 串口，不是 ESP32 的日志串口；按实际板子的 USB 路由/DIP 开关和厂商指南配置。烧录固件期间不得同时占用串口。
必须做：正确证书成功、错误CA失败、过期证书失败、错误域名失败。当前模块证书链配置来自 AT 手册，主机名验证行为未经实体固件验证；测试不通过则改用 ESP-IDF PPP + ESP-TLS，不降低验证要求。

## 已知限制与下一轮实测
- AT HTTPS 调用会阻塞；网络不稳定时实际周期可能超过10秒。
- 64点缓存满后保留历史点、拒绝新点；需根据容量、闪存寿命和功耗测量调整。
- 无有效 GNSS 时间时不进行 HTTPS 上传，首次定位前可能显示离线。
- 模块硬复位、供电峰值、信号丢失后的长期恢复仍需板上验证。
- 重传冲突或401不会出队；需修复密钥/协议后恢复。30天以外的点在新GNSS时间可用时丢弃。
- NVS数据格式v0，不支持未经迁移直接刷入改变结构体布局的版本。
- 这不是佩戴成品；外壳、电池保护、防水和佩戴测试都未完成。

来源（仅参考参数与协议，未复制厂商示例代码）：
https://docs.waveshare.com/ESP32-S3-SIM7670G-4G/ESP-IDF
https://files.waveshare.com/wiki/SIM7670G-LTE-Cat-1-GNSS-HAT/SIM767XX_Series_AT_Command_Manual_V1.01.pdf
