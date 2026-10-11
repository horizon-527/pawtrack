# 器件与电路核对记录

日期：2026-10-11；范围：资料、连接及 CAD 核对，**不包括物料现货、样机测量或量产批准**。

| 对象 | 本版核对结果 | 制造前仍须关闭 |
|---|---|---|
| Air780EGH | 厂商109焊盘参考坐标、15.8×17.7mm方向；SIM/USB/GPIO/ADC供电与最新参考图连接 | PIN2/PIN103 与 V2.2 手册矛盾；实际批次、底层固件和 GNSS_VDD 能力 |
| BQ24074RGTR | 16脚+EP17；EN1=VBUS、EN2=GND 的500mA模式；ISET=2.55kΩ，按典型890AΩ计算约349mA；SYS标称4.4V走稳压器，不直供模组 | 输入/充电公差、热降额、实际电池允许范围、CE与TS状态、断电及故障注入 |
| TPS63070RNMR | RNM0015A真实15脚，包括成对功率焊盘；FB参考0.8V，750k/200k得到3.8V；SYS最大值处于芯片范围内 | 环路与布局、有效电容、峰值电流、热、USB/BAT切换 |
| XFL4020-102MEC | 1µH，厂家表4.5/5.1/5.4A分别对应电感下降10/20/30%，DCR最大11.9mΩ；定制焊盘按厂家图 | 不把5.4A当作电感不下降的额定值；真实料号/批次、发射与低电池电压裕量、替料重新核算 |
| 电容 | 22µF/6.3V X5R为0805；4.7µF/10V与100nF/16V为0603；100µF/6.3V聚合物近模组 | DC偏置下有效容量、温度公差、C14极性；不能以标称容量替代实际容量 |
| 反馈/限流/分压电阻 | BOM逐个确定阻值/0603型号，控制和采样阻值匹配连接；BAT分压4.3倍，4.2V时ADC约977mV | 电阻公差、ADC校准、漏电和高阻采样带宽 |
| TS采样 | 3.3M/1M分压，程序考虑4.3M加载；按75µA偏置、B3435计算温度，软件许可5–40°C | 实际NTC曲线/TS偏置、CE禁充时TS是否保持有效偏置、ADC误差；关键区≤2°C |
| Q1/充电许可 | 2N7002 SOT23：1=G，2=S接地，3=D接CE；CE被100k拉VBUS，GPIO27默认低且有100k下拉 | 关机/复位/应用停滞时GPIO状态；底层看门狗停止后复位行为必须验证，不能仅依靠软件定时器保护 |
| RF连接器 | KiCad U.FL焊盘1为信号、2为两个地；料号(10)为卷带型号 | 实物相配插头、线缆卸力、RF接触及焊接 |
| GNSS偏置 | 33pF串联隔直、47nH偏置电感；0603HP-47NXJRW 5%锡端卷带，厂家SRF典型2.3GHz，针对0603HP高度1.02mm调整焊盘 | 实测L1频段匹配/插损、供电噪声，天线型号及净空；SRF不是系统RF认证 |
| SIM | NSIM-2-C 的1/2/3/5/7正确；6/CD悬空，SH接地；22Ω串联/ESD/IO10k上拉 | 精确后缀、卡盖、卡座实物方向、SIM接口电平和组装访问性 |
| USB-C/ESD | CC各5.1k下拉，重复USB2触点同网；PESD5V0S1UL/PESD3V3S1UL编号核对为1信号、2地 | 90Ω差分/耦合布线收敛、接口真实机械图、ESD与下载实测 |
| 外壳 | CSG实体上下盖、闭合STL、孔位和电池/SIM规划空间 | 三维器件实高、线束/USB插头/天线净空、打印公差、重量、强度及宠物适配 |

原理图中的外部 BAT/VBUS 与地使用 PWR_FLAG 声明来源，不代表电池保护已集成在PCB中。保护功能必须由合格电池包提供，并按验收表验证。当前没有温度传感器被省略的二线电池替代方案。

主要资料：[Air780EGH](https://docs.openluat.com/air780egh/product/)、[BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf)、[TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf)、[XFL4020](https://www.coilcraft.com/en-us/products/power/high-voltage-inductors/xfl/xfl4020/xfl4020-102/)、[0603HP原厂数据](https://www.coilcraft.com/getmedia/624a615f-2f4d-4200-95a6-61764a49bbc8/0603hp.pdf)、[U.FL卷带型号](https://support.hirose.com/en/support/solutions/articles/68000029558-what-is-the-reel-type-part-number-of-u-fl-r-smt-1-01-)。原始下载校验值在 `sources.json`。
