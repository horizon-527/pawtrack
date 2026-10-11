# Air780EGH 应用固件

`main.lua` 为 LuatOS 应用入口，直接接 API v1；它不在 ESP-IDF 中编译。使用 PIN16/GPIO27 控制默认禁充的 NMOS，PIN96/ADC1 读 TS 温度采样，PIN9/ADC0 读电池电压诊断。上报电量暂缺，避免把电压伪装成精确百分比。

`config.example.lua` 是空配置模板。复制为 `config.lua` 并在工厂安全环境填写 HTTPS 域名、设备独立令牌和根 CA 文件，作为 Luatools 用户文件烧录。`tls_qualified` 默认 false，四组模组 TLS 测试通过才开启；`charge_qualified` 默认 false，温度及充电验收通过才开启。配置已被 Git 忽略。

底层固件由合宙提供，当前还没有在本项目样机上锁定并验证其版本。厂商必须选择支持 Air780EGH、GNSS、http、adc、gpio、fskv、sys 的官方版本，记录文件 SHA256 和实际 `rtos.version()`。不能把 Lua 语法检查说成模组运行验证。

`vendor/exgnss.lua` 来自 openLuat/LuatOS 提交 `a8783cb623edfe336850e35bb94b35e74e389184` 的 `script/libs/exgnss.lua`，带 MIT 许可证。关闭 AGPS 自动网络下载和原始坐标日志，GNSS 常开用于首轮验证；本版没有经过实测的深度休眠或续航优化。

主机测试：`pip install -r ../requirements-design.txt` 后，运行 `python test_protocol.py`。测试执行实际 Lua 协议和队列模块及语法解析，覆盖 UTC/闰日、无效/过期坐标、ACK 身份、模式、队列满和重启恢复、温度故障禁充。测试不模拟 4G/GNSS/TLS/ADC 硬件，不替代样机验收。

从仓库根目录再运行 `python hardware/custom/evt-a1/firmware/test_backend_flow.py`。实际 `main.lua` 在 Lua 5.3 运行，SDK 接口使用测试替身、位置明确为模拟，HTTP 调用接本地真实服务，覆盖绑定、上传、ACK 清队列、寻找模式、无虚构电量、撤销后保留未发送点和温度异常禁充。传入 CA 参数被检查，但它不证明模组真实 TLS 合格。

电源/温度验收时以 `factory_diag.lua` **替代应用 main.lua 作为入口**，同时烧入 `protocol.lua`。该程序不需要设备密钥或真实定位，打印底层版本和 ADC 电压。`CHARGE_TEST_ARMED=false` 默认禁止充电；仅在受控台架和校准流程中由工程师开启。温度估算依赖 B3435 曲线和75µA TS 偏置，实际曲线、偏置公差、ADC 转换均要以样机校准为准。
