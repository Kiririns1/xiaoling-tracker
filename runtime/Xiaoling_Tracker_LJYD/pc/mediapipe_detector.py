"""MediaPipe Tasks Pose Landmarker Full, upper-body display."""
from pathlib import Path
import time
import cv2
import mediapipe as mp

UPPER = (0, 2, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 23, 24)
PAIRS = ((0, 2), (0, 5), (2, 7), (5, 8), (9, 10), (11, 12),
         (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24))


class MediaPipeDetector:
    def __init__(self, threshold=.6, model_name='lite'):
        model = Path(__file__).parent / f'models/pose_landmarker_{model_name}.task'
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model.read_bytes()),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1,
            min_pose_detection_confidence=.5, min_pose_presence_confidence=.5,
            min_tracking_confidence=.5, output_segmentation_masks=False)
        self.detector = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.threshold = threshold
        self.timestamp = -1
        self.points = [None]*33
        self.last_ms = 0

    def process(self, frame):
        started = time.monotonic()
        timestamp = max(self.timestamp+1, time.monotonic_ns()//1000000)
        self.timestamp = timestamp
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.detector.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
        self.points = [None]*33
        height, width = frame.shape[:2]
        if result.pose_landmarks:
            for i, point in enumerate(result.pose_landmarks[0]):
                if (point.visibility is not None and point.presence is not None
                        and point.visibility >= self.threshold and point.presence >= self.threshold
                        and 0 <= point.x < 1 and 0 <= point.y < 1):
                    self.points[i] = (point.x*width, point.y*height)
        display = frame.copy()
        for a, b in PAIRS:
            if self.points[a] is not None and self.points[b] is not None:
                cv2.line(display, tuple(map(round, self.points[a])), tuple(map(round, self.points[b])), (0, 255, 0), 1)
        for i in UPPER:
            if self.points[i] is not None:
                cv2.circle(display, tuple(map(round, self.points[i])), 2, (0, 0, 255), -1)
        self.last_ms = (time.monotonic()-started)*1000
        return display

    def status(self):
        count = sum(self.points[i] is not None for i in UPPER)
        return f'MP Upper {count}/{len(UPPER)} | {self.last_ms:.0f}ms'

    def close(self):
        self.detector.close()
