# PawTrack：从拿到项目到真实定位

本指南选择了固定路线：**Waveshare ESP32-S3-SIM7670G-4G 开发板 + 数据 SIM → 你的 HTTPS 服务 → 微信小程序**。电脑用来配置、烧录和测试；设备正常运行后，位置通过自己的 4G 上传，电脑不必随宠物携带。

当前交付包含可运行的小程序、后端、可编译固件、自动化测试、部署和运维工具。软件闭环已测试；真实微信账号、公网服务器、SIM、开发板与佩戴样机尚未在本环境验证。先做到“你手拿设备走一圈，小程序显示真实路线”，再制作可佩戴外壳。

## 1. 今天先看效果

用已安装的微信开发者工具，导入仓库里的 `miniprogram` 文件夹，使用项目自带游客 AppID，信任你自己的项目并编译。首页默认演示模式：地图、绿色路线、宠物标记、采集时间和 40 个模拟点。关闭“体验演示”可查看微信登录入口。演示不会成为真实宠物的位置记录。

在项目根目录执行软件验证（需要 Python 3.13、Node 22 和 C 编译器；macOS 可安装 Xcode Command Line Tools）：

```sh
python3 -m venv work/venv
work/venv/bin/pip install -r requirements.lock.txt
work/venv/bin/python tools/check.py
```

测试会启动临时本地 HTTP 服务、执行实际小程序页面控制器，覆盖两个设备的绑定和切换、上传/重复包、地图坐标、寻找模式、日期轨迹、权限隔离和删除。微信交换在测试中使用隔离替身；正式服务没有“假登录开关”。

## 2. 采购并准备账号

按 [国内采购与组装](../hardware/procurement-and-assembly.md) 从微雪国内官方渠道买一套完整 V2 开发板和匹配天线，补齐数据 USB 线、稳定 USB 电源、测试用移动电源及经确认兼容的实名数据 SIM。不要买成裸 SIM7670G 模块，也不必购买单独 GNSS 板、ESP32 或摄像头。

同时准备微信小程序账号和一台公网服务器：

| 项目 | 本项目采用的起步配置 | 拿到什么才算准备完成 |
|---|---|---|
| 微信小程序 | 使用你自己的真实账号，先开发/体验版 | AppID、AppSecret、开发者和体验者权限 |
| 服务器 | Ubuntu 24.04 LTS，2 核、2GB 内存、20GB 磁盘，单实例 | SSH 登录、公网 IP、Docker Compose 可运行 |
| 域名 | 专用 API 子域名，例如 api.你的域名 | DNS 指向服务器，80/443 可访问 |
| SIM | 单设备、小流量套餐起步，先选 1GB/月预算档 | 已激活、有流量、能用于该模组，卖家给出 APN |

这些配置是项目起步决定，不是购买价格或续航承诺。域名/主体、服务类目、隐私声明和发布资格，以当前微信后台及服务商要求为准；本轮未代办认证或支付订单。微信官方开发文档本轮无法抓取，真实平台要求必须以实际后台核对。

## 3. 把后端放到服务器

Docker 安装按 [Docker 官方 Ubuntu 指南](https://docs.docker.com/engine/install/ubuntu/)。SSH 登录自己的服务器后，执行：

```sh
git clone https://github.com/horizon-527/pawtrack.git
cd pawtrack
cp .env.example .env
chmod 600 .env
```

用编辑器打开 `.env`，只在自己的服务器上填写：

```dotenv
WECHAT_APP_ID=你的真实AppID
WECHAT_APP_SECRET=你的真实AppSecret
PAWTRACK_DOMAIN=你的API域名
```

域名只写主机名，不加 `https://` 或路径。云安全组放行 80、443；SSH 只对自己的来源开放。确认 DNS 后启动：

```sh
docker compose --env-file .env -f deploy/compose.yaml config --quiet
docker compose --env-file .env -f deploy/compose.yaml up -d --build
docker compose --env-file .env -f deploy/compose.yaml ps
```

应看到 api、gateway、backup。api 的 8788 端口只给容器网关访问，不能自行映射到公网；服务信任的是网关补充的客户地址。Caddy 使用 Let's Encrypt 签发证书，RSA 叶证书用于起步模组兼容，未降低 TLS 认证要求。

在电脑上检查真正的服务（替换域名）：

```sh
work/venv/bin/python tools/doctor.py --base https://你的API域名
```

应显示 health=passed、anonymousAccessRejected=true、电脑上的证书链和主机名验证通过。这个检查不代表模组 TLS 或真实微信登录已通过。部署、备份和恢复详见 [运维说明](../deploy/README.md)。

## 4. 连接真正的微信小程序

在微信公众平台进入你的小程序，配置 `https://你的API域名` 为 request 合法域名，并确认服务器可访问微信登录接口。准备实际运营方名称和联系方式，再在电脑的仓库根目录生成一个独立真机项目：

```sh
work/venv/bin/python tools/configure_miniprogram.py \
  --appid 你的真实AppID \
  --base https://你的API域名 \
  --operator '你的运营方名称' \
  --contact '你的实际联系方式'
```

输出为 `work/miniprogram-real`。它启用合法域名检查、使用真实 AppID 和 HTTPS 地址，原来的游客演示项目仍可使用。**AppSecret 不放进小程序**。

微信工具导入这个新目录，编译，关闭演示，点击微信登录。如果成功且显示“请先使用设备绑定码添加宠物”，真实认证已完成。先在开发者手机预览，再把测试手机加为体验者。发布审核在真机验收完成之后进行。

## 5. 给设备生成身份并绑定

在服务器仓库根目录执行（一个设备执行一次）：

```sh
docker compose --env-file .env -f deploy/compose.yaml exec api \
  python tools/manage.py provision pet-001 --output /data/pet-001.json
mkdir -p secrets
chmod 700 secrets
docker compose --env-file .env -f deploy/compose.yaml cp api:/data/pet-001.json secrets/pet-001.json
chmod 600 secrets/pet-001.json
```

文件有三个字段：deviceId 是名称编号；bindingCode 粘贴到小程序绑定框，24 小时有效且只能使用一次；deviceToken 只配置到固件。不要把这份文件提交 Git 或发送到公开聊天。

在小程序填宠物名称和 bindingCode，点击绑定。先完成绑定，再给设备运行上传固件。如果绑定码已过期且设备未绑定，用 `binding-code pet-001 --output /data/pet-001-renewed.json` 生成新文件；它也会换 deviceToken，必须同步更新固件。

可先用软件模拟设备验证公网链路：把私有文件通过自己的 SSH 通道复制到电脑的 `secrets` 目录，在电脑执行：

```sh
work/venv/bin/python tools/device_simulator.py \
  --credentials secrets/pet-001.json --base https://你的API域名 --count 3
```

这一步上传的是**模拟位置**。建议用单独编号 `sim-001` 做预联调，避免混入真实设备历史；模拟器保持明确的模拟提示。切换寻找模式后，目标间隔改为 10 秒。正式设备固定上报 WGS84。

## 6. 装配、配置 CA 并烧录

按 [采购与组装](../hardware/procurement-and-assembly.md) 进行断电插卡、接 LTE/GNSS 天线、板级开关配置、模块 AT 口识别、根 CA 导入和 ESP32 烧录。完整命令见 [固件说明](../firmware/espidf/README.md)。

固件配置四项：HTTPS 服务地址、该设备的 deviceToken、SIM APN、已导入模组的可信根 CA 文件名。默认固件凭证为空，不能直接烧入就联网；必须为你自己的设备构建。

## 7. 你手拿设备走一圈

从 USB 稳定供电开始，设备和天线放在非金属保护盒里，由人手持。在开阔室外先等 GNSS 定位，再走 300～500 米，手机只用来查看小程序。电脑断开，设备用符合厂商要求的 USB 移动电源供电，确认仍由自己的 SIM 上传。

普通模式目标每 60 秒采集/回传；寻找模式目标 10 秒；小程序前台约每 5 秒刷新位置，轨迹自动刷新约 30 秒，手动刷新立即重新请求。设备网络调用会阻塞，实际间隔可能更长，实测不达标就记录失败。无 GPS、断网、旧位置会显示不同状态；未校准电量显示“暂不可用”。

按照 [实测验收表](acceptance.md) 逐项检查。先完成人持设备的定位/网络/重启验证，再按实测电流决定电池、按实测尺寸做外壳，最后才进行监督下的短时佩戴。任何未通过项目都不能记录为“已完成”。

## 8. 日常使用

打开小程序 → 关闭演示 → 微信登录 → 选择宠物 → 看当前位置、采集时间和在线状态；选日期看轨迹；寻找时开启寻找模式，看到“设备已确认”后再以实际更新速度判断。退出小程序不影响设备自己上传。

普通用户退出登录不会删除历史。删除账户会删除轨迹、撤销用户会话和原设备密钥；重新使用需要管理员生成新的设备身份材料、更新固件并重新绑定。自动备份里旧记录在 7 天保留期到期后清理。

遇到问题按 [排查表](troubleshooting.md) 查对应环节；先判断是“尚未定位”“设备离线”“微信登录失败”还是“服务不可用”，避免一开始就反复擦除设备缓存。
