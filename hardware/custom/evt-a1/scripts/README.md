# 设计来源、重建和重新发布

直接用 KiCad 10 打开 `cad/pawtrack.kicad_pro`，项目随附符号、封装库，已布线文件可编辑。无需先运行生成器。STEP 模型链接指向 KiCad 系统模型库；本包没有假造整机 STEP 或给未选定的电池、天线画成已定型实物。

最终检查使用 KiCad 10.0.6 原生 CLI，报告包含默认关闭的规则列表；没有增加用于压低错误数的项目级例外。电源、USB 差分、天线、电池和制造工艺仍须工程评审和样机测试。

对**现有布线板**检查/重导出：

```sh
python hardware/custom/evt-a1/scripts/export.py \
  --cli /实际路径/kicad-cli \
  --pcb-python /实际路径/带pcbnew和wx的Python
```

macOS 使用 KiCad 自带的 Python.framework；Linux 使用安装了 KiCad Python bindings 的系统 Python。脚本先跑 ERC、填铜 DRC 和原理图一致性，出错立即停止；随后导出制造文件，生成真实板清单并比对原理图网表/BOM/坐标。坐标不是机械厂的直接机器程序。

`design.py` 是原始连接/布局生成器，会**覆盖未布线板**，不是打开项目的前置动作。重建需要官方下载的 Air780EGH `参考封装20251216` 解压到仓库 `work/hardware-design/`，KiCad10封装库位于脚本指定的 SharedSupport 路径。来源和文件校验值在 `sources.json`，跨系统时先改工作资源路径。

重布线流程为：生成未布线板和 DSN → `prepare_router.py` 调整导出供电层及平面 → Freerouting2.5.0 导出 SES → `import_route.py` 导入并加地过孔 → 填铜 DRC → 按报告运行 `finish_board.py` 清除真实残留/修复最小线宽 → 必要时 `stitch_islands.py` 补未连接地岛 → `sync_nc_nets.py` 同步原生 NC 网名及最小孔径 → `export.py` 重检及导出。每次修改都必须重新检查，不应跳过失败报告。

`routing/pawtrack.ses` 是本次已完成布线的路由会话快照。最终 CAD 还包含填铜、接地过孔和 NC 同步等后处理，**SES 不能取代最终 PCB/Gerber**。FreeRouting 命令需使用 JVM 版：`java -jar freerouting.jar -de cad/pawtrack.dsn -do routing/pawtrack.ses -mp 40 -mt 4 --gui.enabled=false`（工作目录本硬件包）。

外壳用 `python enclosure/build_enclosure.py` 从共享 CSG 原语生成 SCAD/STL，再运行 `python enclosure/preview.py` 检查实际网格。依赖固定在 `requirements-design.txt`；网格闭合不等于装配、防水或拉力实测。

任何改版均需更新 BOM、坐标、制造文件、检查报告和 SHA256；清除制造 HOLD 必须有评审及实测证据，不能只改文件中的状态词。
