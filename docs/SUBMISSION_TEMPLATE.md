# 赛事提交内容模板

> 上传成功后，将以下占位项替换成你的真实信息再提交。

作品名称：小灵 · 视觉追踪与坐姿语音助手

参赛队伍／作者：【请填写】

项目版本：v3.1.2-competition（固件功能版本 3.1.2-silent-controls）

GitHub 仓库地址：https://github.com/【你的GitHub用户名】/xiaoling-tracker

完整发行包：https://github.com/【你的GitHub用户名】/xiaoling-tracker/releases/tag/v3.1.2-competition

源码查看方式：进入仓库首页阅读 README，展开 source 查看 ESP32-S3 固件、电脑视觉程序及 SDK 依赖；主要功能入口已在 README 链接。

运行查看方式：下载 Release ZIP，完整解压，按 docs/JUDGE_QUICKSTART.md 准备 Windows、Python 3.12、原型机和网络，在 runtime/Xiaoling_Tracker_LJYD 同一目录安装并启动。设备 IP 通过 -DeviceHost 参数填写。重新部署时按 docs/CONFIGURE_BUILD_FLASH.md 自行填写产品密钥、Wi-Fi 和平台 API 配置，再编译烧录。

硬件：赛事随附 ESP32-S3 原型机（BF3901 摄像头、双轴舵机、WS2812 灯圈及语音模块）。

说明：公开发布源码和重新编译镜像均为留空配置版本。原型机中已经完成配置的版本可用于演示；重新部署者应自行准备平台产品／服务和网络配置。
