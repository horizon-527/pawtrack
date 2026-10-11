# PawTrack 定制硬件 EVT-A1

这是一套**工程样机设计**，发布状态为 **HOLD / 尚未获准制造和佩戴使用**。文件可交给国内硬件方案商作原理图评审、DFM 和整机报价；只有完成下面的确认与样机验收，才能把它称为能使用的定位器。没有采购、投板、实体烧录或实测数据。

固定方案：Air780EGH 4G/GNSS OpenCPU + BQ24074 充电及电源路径 + TPS63070 3.8V 稳压 + 带保护板和温度传感器的单节电池。没有额外 ESP32。此板运行 `firmware/` 的 LuatOS 脚本，**不能刷已有的 ESP32 固件**。数据接入仓库的 API v1 和微信小程序。

| 内容 | 文件 | 能说明什么 |
|---|---|---|
| 自定义原理图、布线 PCB、项目库 | `cad/pawtrack.kicad_sch`、`.kicad_pcb`、`.kicad_pro` | KiCad 10 可编辑；不是开发板接线图 |
| BOM、Gerber、钻孔、贴片坐标 | `manufacturing/` | 工程评审/报价输出；默认不贴 RF 调谐电容 |
| 原生检查与独立连接核对 | `reports/` | 电脑上的几何和连接检查；不证明射频、电源和电池合格 |
| 外壳实体、参数源、尺寸图 | `enclosure/` | STL 可作 PA12 打印询价；装配、耐拉和防水未实测 |
| 模组应用及测试 | `firmware/` | 上传协议和队列可在电脑测试；模组 API、TLS、ADC 要在样机验证 |
| 交厂与验收 | `factory-handoff.md`、`acceptance.csv` | 先评审、后样机、通过后再交付，附记录表 |

PCB 为 64×46mm、四层、目标厚度 1.0mm。外壳主体 74×56×27mm，含绑带耳总长 90mm，接受 20mm 织带。**这是保留调试余量的原型，重量尚未测量，不能当作小型猫狗项圈成品。**先用人持设备和等重空壳测试，再决定佩戴对象和下一版尺寸。

先读 `factory-handoff.md`。请勿只把 Gerber 发给 PCB 厂、跳过电路评审。制板贴片服务不自动包含电池选型、射频调试、固件联调和整机验收。

原理图使用嵌入式、自带库的编号符号，保留真实封装焊盘号码及供电/输入/输出类型，连接由网标完成。设计源 `scripts/design.py` 会重建未布线 PCB，**不要在已布线文件上无意运行覆盖**；修改设计后必须重布线、重新导出并重做所有检查。

检查证据见 [verification.md](reports/verification.md)，器件核对及未关闭问题见 [design-review.md](reports/design-review.md)，重新导出说明见 [scripts/README.md](scripts/README.md)。制造包的 SHA256 清单在 `files.sha256.json`；`python scripts/verify.py --manifest` 可核验交付文件是否变动。若改版，先重做原生检查与导出，最后运行 `python scripts/seal.py` 更新清单。
