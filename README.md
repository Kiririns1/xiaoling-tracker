# 小灵 · 视觉追踪与坐姿语音助手

比赛提交版 **v3.1.2** · ESP32-S3 原型机 + Windows 电脑端 + 灵机一动云端语音

本项目使用原型机摄像头采集画面，在电脑上进行手部、人脸及坐姿识别，由 ESP32-S3 执行双轴舵机、灯光和语音交互。原型机、电脑和有互联网的 Wi-Fi 需要同时工作。

## 裁判从这里开始

1. 下载本仓库或 Releases 中的比赛提交 ZIP，**完整解压**，不要直接从压缩包内运行程序。
2. 阅读 [裁判运行指南](docs/JUDGE_QUICKSTART.md)，完成自己的网络与必要的云端配置。
3. 进入 **`runtime/Xiaoling_Tracker_LJYD/`**。新电脑安装 Python 3.12（64 位，勾选 Add python.exe to PATH），双击该目录里的 **`setup_pc.cmd`**，等待安装成功。
4. 仍在**同一个目录**启动程序。设备 IP 恰好为 `172.20.10.2` 时可直接双击 `run_pc.cmd`；其他地址在该目录打开 PowerShell，运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_pc.ps1 -DeviceHost "设备的实际IP" -Rotate 90
   ```

首次需要安装 Python 和依赖；本包是原版 Python 程序，**不是免安装 EXE**。不要复制其他电脑的 `.venv`。安装和启动始终使用上述同一目录，避免混用源码目录和运行目录。程序与原交付电脑端逐文件校验一致。

使用已经配置好并烧录比赛固件的原型机时，无需重新烧录。若要使用本仓库重新配置、编译或给另一块板烧录，请先完成下节的配置。

## 密钥、Wi-Fi、API：需要使用者自行配置

**发布源码和本次重新编译的固件均不带可用的产品密钥、私人 Wi-Fi 或模型 API 凭据。使用自己的设备／产品重新部署前，必须自行配置。**

| 配置项 | 实际配置位置 |
| --- | --- |
| 灵机产品 PID 与产品密钥 | `source/apps/main/cloud/ljyd_cloud.h`，`CONFIG_XJIANG_CLOUD_SECERT` 已留空；PID 默认保留项目值 `11885`，使用自己的产品时同步修改 |
| 原型机联网 Wi-Fi | 按灵机一动正常 BLE 配网流程，填写自己的 Wi-Fi 名称和密码；不在仓库中保存私人 Wi-Fi |
| 摄像头演示 AP（如需使用） | `source/apps/main/peripheral/fresh_http.c` 的 AP `ssid`、`password` 已留空，`ssid_len=0` 表示按字符串计算长度；使用 AP 前自行填写名称和不少于 8 位的 WPA2 密码 |
| 模型／其他服务 API Key | 本版通过灵机平台进行云端对话，不直接在电脑端调用模型 API。需要自有模型或插件 API 的，在自己的平台配置中填写；仓库不提供可用 API Key |
| 电脑连接设备的地址 | 启动参数 `-DeviceHost`，填写原型机本次联网后的实际 IP |

这版工程没有名为 `secret.h` 的有效产品配置文件；请使用上表的实际入口。不能只新建一个程序没有读取的 `secret.h`，也不要把密钥发到 Issue 或提交到 Git 历史。

**`firmware/` 是从本包留空配置的源码重新编译的镜像。它不能在未配置产品密钥的情况下注册或连接你的云端产品，也不能通过编辑 `.bin` 来填密钥。** 请在自己的本地私有副本中填写配置、重新编译后烧录。原来已经烧录并验证过的原型机固件、本地工程及旧交付包均未修改。

完整步骤见 [配置、构建和烧录](docs/CONFIGURE_BUILD_FLASH.md)。

## 功能与演示

| 场景 | 操作 |
| --- | --- |
| 语音唤醒与连续聊天 | “你好小灵”或“你好小林”，随后连续问答 |
| 双轴手／脸追踪 | “开始追踪手”“开始追踪脸”“停止追踪”；电脑程序需运行 |
| 坐姿检测与校准 | “开始坐姿检测”“校准坐姿”“查询坐姿状态” |
| 坐姿追脸暂停／恢复 | “暂停坐姿追脸”“恢复坐姿追脸” |
| 静音继续控制 | “停止聊天”只关闭语音；坐姿、追踪、校准、灯光指令继续执行；再次唤醒恢复语音 |
| 灯光 | “开灯”“关灯”“亮度调整为五”，支持零到十；保留手势灯控 |
| 天气／番茄时钟 | 依赖使用者在灵机平台配置并发布对应插件及服务绑定 |

键盘：`1` 手部，`2` 人脸，`M` 切换，`F` 追踪开关，空格停止，`P` 坐姿开关，`C` 校准，`R` 旋转，`Q` 退出。

## 目录与源码查看方式

```text
README.md                         比赛入口
runtime/Xiaoling_Tracker_LJYD/     原样电脑程序、模型、安装及启动脚本
firmware/                        留空配置、重新编译的 ESP32-S3 镜像
source/                          完整项目源码与厂商 SDK／依赖快照
docs/                            裁判指南、配置烧录、GitHub 上传及提交模板
tools/verify_submission.py        发布完整性与空凭据检查
RELEASE_MANIFEST.json             文件校验值、配置脱敏清单及验证结果
LICENSE                          原工程许可证（保留原文）
```

主要代码：

- 电脑视觉入口：[tracker_camera.py](source/pc/tracker_camera.py)
- 坐姿判断：[posture.py](source/pc/posture.py)
- 语音、静音与控制分流：[tracker_dialog.c](source/apps/main/peripheral/tracker_dialog.c)
- 舵机／追踪状态机：[tracker_control.cpp](source/apps/main/peripheral/tracker_control.cpp)
- HTTP 图像与控制：[fresh_http.c](source/apps/main/peripheral/fresh_http.c)
- 云端接入：[agent_app.c](source/apps/main/agent/agent_app.c)

`source/` 内保留原开发文档与历史验证记录，可能包含开发机路径或旧版说明；裁判运行和本次留空配置请以本 README 及 `docs/` 为准。

## 硬件与运行条件

ESP32-S3（16MB Flash、8MB PSRAM）、BF3901 摄像头、左右舵机 GPIO5、上下舵机 GPIO6、GPIO7 的 8 颗 WS2812、原配语音模块。USB 用于供电／可选烧录，图像和控制经局域网传输；画面端口 80，控制端口 81。

语音识别与播报需要互联网。静音待唤醒期间仍上传麦克风用于在线识别，静音并不等于关闭麦克风。识别与校准需要电脑程序保持运行。摄像头运动或图像过期时会暂停相应判定；坐姿是相对校准后的视觉提示。

## 版本与验证

功能基线是 `3.1.2-silent-controls`。原型机此前已实测确认普通聊天连续两轮有声，以及“追脸 → 停止聊天 → 静音执行坐姿／校准 → 再唤醒恢复语音”。本提交仅留空配置值并重编译，不改控制、识别或语音功能代码，不重新烧录原型机。

本次发布副本的构建、依赖安装、新目录启动检查及文件校验结果见 [发布验证](docs/VERIFICATION.md)。空凭据镜像不会被描述成已经连接云端或完成联网功能验收。

## 赛事提交与 GitHub 上传

按 [上传教程](docs/GITHUB_UPLOAD.md) 上传本目录；总 ZIP 放在 GitHub **Releases** 附件中。仓库地址尚需你上传后生成，可按 [赛事提交模板](docs/SUBMISSION_TEMPLATE.md) 填写“仓库地址、查看方式、下载运行方式”。

第三方库、模型及厂商静态库保留原许可证，见 [第三方说明](docs/THIRD_PARTY.md)。
