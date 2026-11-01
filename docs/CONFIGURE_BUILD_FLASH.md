# 自行配置、构建与烧录

本发布副本已留空凭据；原工程和原型机未改动。使用原型机已配置好的固件演示时，优先直接运行电脑端，不需要重新刷机。

## 1. 填写自己的配置

在自己的**本地私有工作副本**中配置，填写后的文件与编译产物不要提交回公开仓库。

1. 打开 `source/apps/main/cloud/ljyd_cloud.h`，设置你的产品 PID，以及：

   ```c
   #define CONFIG_XJIANG_CLOUD_SECERT "这里填写你自己的灵机产品密钥"
   ```

2. 在自己的灵机平台产品中配置并发布智能体，绑定设备服务；需要使用模型／插件 API 时，在平台配置你自己的 API Key。本项目没有在电脑端读取通用 `secret.h` 或直接调用模型 API 的入口。
3. Wi-Fi 上网信息通过平台正常 BLE 配网流程设置。若使用相机 AP，编辑 `source/apps/main/peripheral/fresh_http.c` 的 `.ap` 配置，自行填写 `ssid` 和不少于 8 位的 `password`；发布副本将这些值留空，`ssid_len=0` 使用字符串长度。
4. 所有 SDK 示例里的网络、产品密钥等配置字面量也已留空；示例程序需使用者自行填写后才可独立使用。协议字段名、测试数据和密码学常量不属于私人凭据，保持原样。

## 2. 构建环境

已验证的固件工具链为 ESP-IDF **5.4.1**、ESP32-S3，Python 3.12。仓库含工程与 SDK／受管依赖快照，不含完整 ESP-IDF 安装及工具链。

安装 ESP-IDF 5.4.1 的 ESP32-S3 工具并进入已经导出环境的 ESP-IDF PowerShell 终端。在仓库根目录执行：

```powershell
$env:ADF_PATH = (Resolve-Path .\source).Path
idf.py -C .\source\apps build
```

应用为 `source/apps/build/xiaoling_11885.bin`。沿用项目分区表与 sdkconfig，不要任意切换开发板型号或删除受管依赖快照。IDF 所需 PSRAM 任务栈补丁参考 `source/idf_patches/idf_v5.4_freertos.patch`；已有厂商修改的 SDK 应先核对，避免重复应用补丁。

原 `source/build.ps1` 也完整保留，但它的默认工具路径来自开发机。换电脑时请用 `-IdfPath`、`-ToolsPath` 指向自己的安装，并按脚本要求准备 `idf5.4_py3.12_env` 等工具目录；裁判运行电脑程序不需要安装这些固件构建工具。

## 3. 烧录配置好的固件

确认原型机板型 ESP32-S3、16MB Flash／8MB PSRAM。端口名以自己电脑设备管理器为准，`COM3` 只是开发时的端口。

从 Arduino 或不同分区布局切换时，先备份，再在自己已配置并构建的工程中完整烧录：

```powershell
idf.py -C .\source\apps -p COM3 flash
```

如果已经使用本项目相同分区表、活动应用是 `ota_0`，可只升级应用以保留 NVS：

```powershell
idf.py -C .\source\apps -p COM3 app-flash
```

不要在未核对活动 OTA 槽和分区时只刷应用。首次部署后，按平台流程完成 BLE 配网。不要把 `firmware/` 的空凭据镜像误当作已经配置好产品密钥的联网固件。

## 4. 发布镜像说明

`firmware/` 内的镜像从本仓库的空配置源码单独重新编译。功能版本仍为 `3.1.2-silent-controls`；文件哈希与旧的私人凭据固件不同，这是配置清空后重编译的正常结果。

镜像保留 ESP-IDF 常规校验和／SHA 校验，可用 `python -m esptool image_info firmware/xiaoling_11885.bin` 检查。没有向原型机烧录本次空凭据镜像，也不宣称它已完成云端联网验收。
