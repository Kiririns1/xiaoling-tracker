"""Screen-relative shoulder and nose geometry, calibrated to a neutral pose."""
import math
from collections import deque
from statistics import median

from posture_config import *


def metrics(points, require_eyes=False):
    left, right, nose = points[11], points[12], points[0]
    if left is None or right is None or nose is None:
        return None
    a, b = sorted((left, right), key=lambda p: p[0])
    dx, dy = b[0]-a[0], b[1]-a[1]
    if dx < MIN_SHOULDER_WIDTH:
        return None
    angle = math.degrees(math.atan2(dy, dx))
    offset = (nose[0]-(a[0]+b[0])/2) / dx
    head_height = ((a[1]+b[1])/2 - nose[1]) / dx
    if head_height <= 0 or not all(math.isfinite(v) for p in (left, right, nose) for v in p):
        return None
    base = (angle, offset, head_height, dx)
    eyes = [points[2], points[5]]
    if any(p is None for p in eyes):
        return None if require_eyes else base
    if not all(math.isfinite(v) for p in eyes for v in p):return None
    eye_height = ((a[1]+b[1])/2-(eyes[0][1]+eyes[1][1])/2)/dx
    if eye_height <= 0:return None
    return base + (eye_height,)


def classify(current, baseline):
    if current is None:
        return '无法判断：鼻子、双眼或双肩不可见', None
    if baseline is None:
        return '请坐直并按 C 校准', None
    da, dh = current[0]-baseline[0], current[1]-baseline[1]
    messages = []
    if abs(da) >= SHOULDER_ANGLE_DEGREES:
        messages.append('注意坐姿向画面' + ('右' if da>0 else '左') + '倾斜（肩线倾斜）')
    if dh <= -HEAD_OFFSET_RATIO:
        messages.append('头部向画面左偏')
    elif dh >= HEAD_OFFSET_RATIO:
        messages.append('头部向画面右偏')
    if len(current) >= 4 and len(baseline) >= 4:
        if len(current)>=5 and len(baseline)>=5 and baseline[2]>0 and baseline[4]>0:
            if (1-current[2]/baseline[2] >= NOSE_HEIGHT_DROP_RATIO and
                    1-current[4]/baseline[4] >= EYE_HEIGHT_DROP_RATIO):
                messages.append('注意坐姿前倾')
        if current[3]/baseline[3] >= NEAR_CAMERA_WIDTH_RATIO:
            messages.append('身体靠近摄像头（相对校准）')
    return '；'.join(messages) if messages else '头肩位置在阈值范围内', (da, dh)


class PostureFilter:
    """Unique-frame, confidence-filtered observations; elapsed seconds, not counts."""
    def __init__(self, hold=HOLD_SECONDS, cooldown=COOLDOWN_SECONDS):
        self.hold, self.cooldown = hold, cooldown
        self.reset()
        self.last_alert = -math.inf

    def reset(self):
        self.baseline = None
        self.calibrating = False
        self.samples = []
        self.history = deque(maxlen=SMOOTH_FRAMES)
        self.bad_since = self.last_seen = None

    def start_calibration(self, now):
        self.reset()
        self.calibrating = True
        self.calibration_started = now

    def invalidate(self):
        self.history.clear()
        self.bad_since = self.last_seen = None
        if self.calibrating:
            self.samples.clear()

    def observe(self, current, now):
        if current is None:
            self.invalidate()
            return '无法判断：鼻子、双眼或双肩不可见', None, False
        if self.last_seen is not None and now-self.last_seen > MAX_OBSERVATION_GAP:
            self.invalidate()
        if self.baseline is not None and len(current)!=len(self.baseline):
            self.invalidate()
            return '无法判断：关键点不完整', None, False
        if self.samples and len(current)!=len(self.samples[-1][1]):self.samples.clear()
        self.last_seen = now
        if self.calibrating:
            if now-self.calibration_started > 10:
                self.calibrating = False
                return '校准超时：请稳定坐直后按 C 重试', None, False
            self.samples.append((now, current))
            self.samples = self.samples[-20:]
            if len(self.samples) >= 10 and now-self.samples[0][0] >= 1:
                rows = [s for _, s in self.samples]
                center = tuple(median(s[i] for s in rows) for i in range(len(current)))
                stable = (max(s[2] for s in rows)-min(s[2] for s in rows) <= .12
                    and (len(current)<5 or max(s[4] for s in rows)-min(s[4] for s in rows) <= .12)
                    and max(s[0] for s in rows)-min(s[0] for s in rows) <= 6
                    and max(s[1] for s in rows)-min(s[1] for s in rows) <= .18
                    and max(s[3] for s in rows)/min(s[3] for s in rows) <= 1.15)
                if stable:
                    self.baseline, self.calibrating = center, False
                    self.history.clear()
                    return '校准成功', (0., 0.), False
            return f'校准中：保持坐直 {min(len(self.samples),10)}/10 帧', None, False
        if self.baseline is None:
            return '请坐直并按 C 校准', None, False
        self.history.append((now, current))
        while self.history and now-self.history[0][0] > MAX_OBSERVATION_GAP:
            self.history.popleft()
        smooth = tuple(median(s[i] for _, s in self.history) for i in range(len(current)))
        text, delta = classify(smooth, self.baseline)
        if text == '头肩位置在阈值范围内':
            self.bad_since = None
            return text, delta, False
        if self.bad_since is None:
            self.bad_since = now
        elapsed = now-self.bad_since
        alert = elapsed >= self.hold and now-self.last_alert >= self.cooldown
        if alert:
            self.last_alert = now
        return text + f'（持续 {elapsed:.1f}/{self.hold:g} 秒）', delta, alert
