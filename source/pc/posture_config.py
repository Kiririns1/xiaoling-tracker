"""坐姿调参：修改后重启电脑程序，并坐直按 C 重新校准。"""
SHOULDER_ANGLE_DEGREES = 8.0  # 相对校准肩线角度，度；越小越敏感。
HEAD_OFFSET_RATIO = 0.25      # 头部横向偏移 / 肩宽，保留原检测。
MIN_SHOULDER_WIDTH = 15       # 像素；过小的目标不判断。
NOSE_HEIGHT_DROP_RATIO = 0.20 # 鼻肩垂直距离比坐直时缩短20%。
EYE_HEIGHT_DROP_RATIO = 0.15  # 双眼中心到肩线距离缩短15%；与鼻子条件同时满足。
NEAR_CAMERA_WIDTH_RATIO = 1.25 # 肩宽达到校准的1.25倍，保留靠近提醒。
HOLD_SECONDS = 1.0           # 异常持续多久才提醒、闪灯。
COOLDOWN_SECONDS = 5.0      # 两次提醒最小间隔。
SMOOTH_FRAMES = 3            # 中值平滑窗口。
MAX_OBSERVATION_GAP = 1.5    # 检测中断超过此秒数，清除异常计时。
POSE_CONFIDENCE = 0.6        # 鼻/眼/肩关键点置信度下限。
METRICS_LOG_SECONDS = 2.0    # 实时参数输出间隔，方便调参。

FACE_TARGET_Y = 0.35         # 脸部目标高度，0顶部/1底部；留出肩部空间。
CAMERA_SETTLE_SECONDS = 0.6  # 镜头运动结束后等待再判断坐姿。
